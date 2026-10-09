# -*- coding: utf-8 -*-
# 尺度一致性检验（scale consistency）：量纲之外的第二层物理判据。
#
# 为什么需要这一层
# ----------------
# 量纲齐次只能排除"单位不对"的公式，排不掉"单位对、形状错"的公式。
# 例如 G*m1*m2/r 与 G*m1*m2/r**2 在自由参数吸收单位的前提下都能通过结构一致性检查，
# 但只有后者满足"距离加倍、力变四分之一"的幂律标度。
# 机械专业训练里的极限分析、对称性、单调性、无量纲群分析，正好补上这一层。
#
# 本模块实现 6 类检验（任务书要求 >= 3 类）：
#   1. scaling     幂律标度      : x -> lambda*x 时 y -> lambda^p
#   2. invariance  无量纲群不变性 : Buckingham pi —— 按指定指数同时缩放后 y 不变
#   3. limit       极限行为      : var -> to 时 y -> target（小量近似、边界退化）
#   4. monotonic   单调性        : y 对某变量在声明区间内单调增/减
#   5. sign        符号          : y 在采样盒内恒正 / 恒负
#   6. symmetry    交换对称性    : 同类变量互换后 y 不变
#
# 规格来源
# --------
# physics/scale_specs.json 由机械成员（M3）按物理先验编写，描述的是
# "这个现象必须满足什么"，与任何具体公式无关。因此同一份规格既能验证参考公式
# （金标准自检），也能验证智能体给出的候选式（判别力）。
#
# 红线
# ----
# physics/ 与 reference/ 一样位于 tasks/ 之外，绝不进入智能体上下文；
# 智能体只能看到 tasks/<id>/data.csv 与 meta.json。
from __future__ import annotations

import itertools
import json
import math
import os
from datetime import datetime
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .safe_eval import UnsafeExpression, compile_formula
from .verify import CheckResult, VerifyError, VerifyReport

SPEC_SCHEMA = 'formula-agh/scale-specs@1'

# 各类检验的默认相对容差。取值理由：
# 数值检验只在"物理上可分辨"的量级上做判断，因此容差远大于浮点误差，
# 但仍远小于典型错误公式的偏差（错幂次通常是 2 倍量级）。
DEFAULT_TOL = {
    'scaling': 1e-4,
    'invariance': 1e-4,
    'limit': 5e-3,
    'monotonic': 1e-4,
    'sign': 0.0,
    'symmetry': 1e-4,
}


def _safe_name(text: str) -> str:
    # 检验名会变成 runs/<id>/checks/<name>.json 的文件名，必须文件系统安全。
    out = []
    for ch in str(text):
        out.append(ch if (ch.isalnum() or ch in '-_') else '-')
    return ''.join(out)


def _at_fraction(bounds: Sequence[float], t: float) -> float:
    # 在声明区间内按比例取点；正区间用几何插值，跨零区间用线性插值。
    lo, hi = float(bounds[0]), float(bounds[1])
    if lo > 0:
        return lo * (hi / lo) ** float(t)
    return lo + (hi - lo) * float(t)


def _base_point(meta: Mapping[str, object]) -> Dict[str, float]:
    # 基准点：每个变量取声明区间的几何中点。
    # 用几何中点而不是算术中点，是因为物理量的合理扰动通常是乘性的（×2、÷2），
    # 在基准点上做乘性扰动才不会被区间的量级跨度带偏。
    sampling = meta.get('sampling') or {}
    point: Dict[str, float] = {}
    for name, bounds in sampling.items():
        point[str(name)] = _at_fraction(bounds, 0.5)
    return point


class _Evaluator:
    # 把公式包装成"给定变量取值 -> 返回标量"的函数。
    # 只依赖 safe_eval 的 AST 白名单，公式仍是不可信输入。

    def __init__(self, formula: str, var_names: Sequence[str],
                 params: Mapping[str, float]):
        self.var_names = [str(v) for v in var_names]
        self.params = {str(k): float(v) for k, v in dict(params).items()}
        try:
            self.fn = compile_formula(formula, self.var_names + list(self.params))
        except UnsafeExpression as exc:
            raise VerifyError('尺度检验无法编译公式: ' + str(exc)) from exc

    def __call__(self, values: Mapping[str, float]) -> float:
        env: Dict[str, np.ndarray] = {}
        for name in self.var_names:
            if name not in values:
                raise VerifyError('尺度检验缺少变量取值: ' + name)
            env[name] = np.asarray([float(values[name])], dtype=float)
        for name, value in self.params.items():
            # 自由参数同样允许被探测点覆盖：这样"物理常数加倍、结果减半"
            # 这类关于常数的标度性质也能被检验（例如 f=(A-B)/h 对 h）。
            env[name] = np.asarray([float(values.get(name, value))], dtype=float)
        try:
            out = np.asarray(self.fn(env), dtype=float)
        except Exception as exc:  # 公式在探测点上不可求值
            raise VerifyError('公式在探测点上不可求值: ' + type(exc).__name__) from exc
        return float(out.reshape(-1)[0])


def _finite(*values: float) -> bool:
    return all(math.isfinite(float(v)) for v in values)


def _product(axes: Sequence[Sequence[float]]):
    # 笛卡尔积；空轴时退化为一个空组合。
    if not axes:
        return [()]
    return itertools.product(*axes)


def _rel_error(got: float, want: float, scale: float) -> float:
    denom = max(abs(float(scale)), 1e-300)
    return abs(float(got) - float(want)) / denom


# ---------------------------------------------------------------------------
# 1. 幂律标度
# ---------------------------------------------------------------------------
def check_scaling(ev, base, spec, tol):
    scale_map = spec.get('scale')
    if not scale_map:
        var = spec.get('var')
        if not var:
            return CheckResult(spec['name'], False, '规格缺少 var/scale 字段')
        scale_map = {str(var): 1.0}
    lam = float(spec.get('lambda', 2.0))
    power = float(spec.get('expect_power', 0.0))

    y0 = ev(base)
    pert = dict(base)
    for name, expo in scale_map.items():
        if str(name) not in base:
            return CheckResult(spec['name'], False, '规格引用了 meta.json 中不存在的变量: ' + str(name))
        pert[str(name)] = base[str(name)] * (lam ** float(expo))
    y1 = ev(pert)

    if not _finite(y0, y1):
        return CheckResult(spec['name'], False,
                           '标度探测点出现非有限值（%s -> %s）：公式在该尺度下数值发散' % (y0, y1))
    if abs(y0) < 1e-300:
        return CheckResult(spec['name'], False, '基准点取值为 0，无法计算标度比')
    if y0 * y1 <= 0:
        return CheckResult(spec['name'], False,
                           '缩放后 y 变号（%.6g -> %.6g）：与物理量的正负不符' % (y0, y1))

    got = y1 / y0
    want = lam ** power
    err = _rel_error(got, want, want)
    passed = err <= tol
    reason = ('缩放 %s 倍后 y 变为 %.6g 倍，物理预期 %.6g 倍（相对偏差 %.2e，容差 %.0e）'
              % (_describe_scale(scale_map, lam), got, want, err, tol))
    if not passed:
        reason += '；幂律标度不符，属于"单位对、形状错"的候选式'
    return CheckResult(spec['name'], passed, reason,
                       {'ratio': got, 'expected_ratio': want, 'rel_error': err,
                        'lambda': lam, 'expect_power': power})


def _describe_scale(scale_map, lam):
    parts = []
    for name, expo in scale_map.items():
        if float(expo) == 1.0:
            parts.append('%s×%g' % (name, lam))
        else:
            parts.append('%s×%g^%g' % (name, lam, float(expo)))
    return '、'.join(parts)


# ---------------------------------------------------------------------------
# 2. 无量纲群不变性（Buckingham pi）
# ---------------------------------------------------------------------------
def check_invariance(ev, base, spec, tol):
    # 与 scaling 共用实现，只是把"预期倍数"固定为 1：
    # 若 y 可由某组无量纲数完全决定，则按该组指数同时缩放输入时 y 必须不变。
    inner = dict(spec)
    inner['expect_power'] = 0.0
    scale_map = spec.get('scale') or {}
    lam = float(spec.get('lambda', 3.0))
    result = check_scaling(ev, base, inner, tol)
    result.name = spec['name']
    if result.passed:
        result.reason = ('无量纲群不变性成立：同时缩放 %s 后 y 保持不变（相对偏差 %.2e），'
                         '说明公式只通过这些量的无量纲组合依赖它们'
                         % (_describe_scale(scale_map, lam), result.metrics.get('rel_error', 0.0)))
    else:
        result.reason = ('无量纲群不变性被破坏：同时缩放 %s 后 y 变化了 %.6g 倍（应为 1 倍）；'
                         '该公式引入了本不该出现的绝对尺度' % (_describe_scale(scale_map, lam),
                                                     result.metrics.get('ratio', float('nan'))))
    return result


# ---------------------------------------------------------------------------
# 3. 极限行为 / 小量近似
# ---------------------------------------------------------------------------
def check_limit(ev, base, spec, tol):
    var = str(spec['var'])
    if var not in base:
        return CheckResult(spec['name'], False, '规格引用了 meta.json 中不存在的变量: ' + var)
    sampling = spec.get('sampling') or {}
    bounds = sampling.get(var)
    if not bounds:
        return CheckResult(spec['name'], False, '规格缺少变量区间: ' + var + '（无法确定探测步长）')
    span = float(bounds[1]) - float(bounds[0])
    if span <= 0:
        return CheckResult(spec['name'], False, '变量区间跨度为 0: ' + var)

    to = float(spec['to'])
    direction = 1.0 if to <= base[var] else -1.0
    delta0 = float(spec.get('probe_span_fraction', 0.1)) * span
    deltas = [delta0, delta0 / 4.0, delta0 / 16.0]

    target_ev = _Evaluator(spec['target'], ev.var_names, ev.params)
    probes: List[float] = []
    got_values: List[float] = []
    want_values: List[float] = []
    for delta in deltas:
        point = dict(base)
        point[var] = to + direction * delta
        probes.append(point[var])
        y_got = ev(point)
        y_want = target_ev(point)
        if not _finite(y_got, y_want):
            return CheckResult(spec['name'], False,
                               '极限探测点 %s=%.6g 出现非有限值（公式 %.6g / 目标 %.6g）'
                               % (var, point[var], y_got, y_want))
        got_values.append(y_got)
        want_values.append(y_want)

    # 归一化方式：逐探测点用"该点极限式的量级"作分母。
    # 为什么不用最粗探测点统一作分母：那样一个恒定的**相对**偏差（例如漏掉折射率因子，
    # 使结果始终偏大 18%）会因为探测点整体变小而显得像在收敛，从而放过错误公式。
    # 只有当极限式本身在某探测点上趋近 0 时才退回统一分母，并在指标里如实标注。
    ref = max((abs(w) for w in want_values), default=0.0)
    if ref <= 0:
        ref = 1.0
    floor = 1e-9 * ref
    rel_errors: List[float] = []
    fallback_used = False
    for g, w in zip(got_values, want_values):
        if abs(w) > floor:
            rel_errors.append(_rel_error(g, w, abs(w)))
        else:
            fallback_used = True
            rel_errors.append(_rel_error(g, w, ref))

    # 通过条件（两条满足其一即可，且都必须单调不增）：
    #   A. 最靠近极限的探测点上偏差已小于容差 —— 极限成立的最强证据；
    #   B. 偏差按"探测距离每缩小 4 倍、偏差至少缩小 2 倍"的一阶速率收缩。
    # 为什么需要 B：像 e^{-t/tau} 在 t->0 这种一阶极限，任何有限探测距离上
    # 都留有残差；但残差随距离线性趋于零这一事实本身就是极限成立的证据。
    # 反过来，偏差停在一个非零常数的公式（例如漏掉某个因子）两条都不满足。
    near = min(rel_errors)
    monotone = all(rel_errors[i] >= rel_errors[i + 1] - 1e-12 for i in range(len(rel_errors) - 1))
    contraction = []
    for i in range(len(rel_errors) - 1):
        prev, nxt = rel_errors[i], rel_errors[i + 1]
        contraction.append(0.0 if prev <= 0.0 else nxt / prev)
    contraction_ok = bool(contraction) and all(r <= 0.5 for r in contraction)
    passed = bool(monotone and (near <= tol or contraction_ok))

    reason = ('%s -> %g 时，公式与极限式 %s 的相对偏差依次为 %s（每步探测距离缩小 4 倍）；'
              % (var, to, spec['target'], '、'.join('%.2e' % r for r in rel_errors)))
    if passed and near <= tol:
        reason += '最靠近极限处偏差已小于容差 %.0e，小量近似成立' % tol
    elif passed:
        reason += ('收敛比 %s，达到一阶收敛（每步至少缩小 2 倍），极限行为成立'
                   % '、'.join('%.2f' % r for r in contraction))
    elif not monotone:
        reason += '偏差未随逼近极限而单调减小，极限行为不稳定'
    else:
        reason += ('逼近极限后仍不吻合（最小偏差 %.2e > 容差 %.0e，收敛比 %s 未达一阶），'
                   '该极限行为不成立'
                   % (near, tol, '、'.join('%.2f' % r for r in contraction)))
    return CheckResult(spec['name'], passed, reason,
                       {'rel_errors': rel_errors, 'probe_values': probes,
                        'nearest_rel_error': near, 'monotone': bool(monotone),
                        'contraction': contraction, 'contraction_ok': contraction_ok,
                        'coarse_normalization_used': bool(fallback_used),
                        'limit_target': spec['target'], 'limit_at': to})


# ---------------------------------------------------------------------------
# 4. 单调性
# ---------------------------------------------------------------------------
def check_monotonic(ev, base, spec, tol):
    var = str(spec['var'])
    if var not in base:
        return CheckResult(spec['name'], False, '规格引用了 meta.json 中不存在的变量: ' + var)
    bounds = (spec.get('sampling') or {}).get(var)
    if not bounds:
        return CheckResult(spec['name'], False, '规格缺少变量区间: ' + var)
    direction = str(spec.get('direction', 'increasing'))
    samples = int(spec.get('samples', 9))
    lo, hi = float(bounds[0]), float(bounds[1])
    if hi <= lo:
        return CheckResult(spec['name'], False, '变量区间跨度为 0: ' + var)

    # 采样方式随区间跨度自动选择：跨若干数量级的变量改用等比采样。
    # 理由：物理上"把质量加倍"是有意义的扰动，"把质量加 1e-27 kg"不是。
    # 线性采样会让 q*B/m 这类公式在高质量端看起来像一条水平线，
    # 从而把正确公式误判成"对质量无依赖"。
    if lo > 0 and hi / lo >= 10.0:
        xs = np.geomspace(lo, hi, max(3, samples))
        grid_note = '等比'
    else:
        xs = np.linspace(lo, hi, max(3, samples))
        grid_note = '等距'

    ys = []
    for x in xs:
        ys.append(ev(dict(base, **{var: float(x)})))
    ys_arr = np.asarray(ys, dtype=float)
    if not np.all(np.isfinite(ys_arr)):
        return CheckResult(spec['name'], False, '单调性扫描出现非有限值，公式在该区间数值发散')

    scale = float(np.max(np.abs(ys_arr))) or 1.0
    rel_steps = np.diff(ys_arr) / scale
    variation = float(abs(ys_arr[-1] - ys_arr[0]) / scale)
    min_variation = float(spec.get('min_variation', 1e-3))
    want_increasing = direction == 'increasing'
    want_text = '递增' if want_increasing else '递减'
    eps = 1e-12  # 只用来排除浮点噪声；"严格单调"本身由它保证

    reversed_steps = (rel_steps <= eps) if want_increasing else (rel_steps >= -eps)
    strict = not bool(np.any(reversed_steps))
    passed = bool(strict and variation >= min_variation)

    reason = ('在 %s ∈ [%.6g, %.6g] 上用%s网格扫描 %d 点：整体相对变化 %.3e'
              % (var, lo, hi, grid_note, len(xs), variation))
    if not strict:
        count = int(np.sum(reversed_steps))
        worst = float(np.max(rel_steps)) if want_increasing else float(np.min(rel_steps))
        reason += ('；有 %d 个步长方向相反（极值 %.3e），不满足全程%s'
                   % (count, worst, want_text))
    elif variation < min_variation:
        reason += ('；曲线在该变量上近乎平坦（低于判定门槛 %.0e），'
                   '说明公式漏掉了这个自变量的影响，而物理上它应当%s'
                   % (min_variation, want_text))
    else:
        reason += '；全程%s，单调性成立' % want_text
    return CheckResult(spec['name'], passed, reason,
                       {'direction': direction, 'rel_steps': rel_steps.tolist(),
                        'variation': variation, 'min_variation': min_variation,
                        'grid': grid_note, 'strict': bool(strict),
                        'range': [lo, hi]})


# ---------------------------------------------------------------------------
# 5. 符号
# ---------------------------------------------------------------------------
def check_sign(ev, base, spec, tol):
    expect = str(spec.get('expect', 'positive'))
    sampling = spec.get('sampling') or {}
    levels = int(spec.get('levels', 4))
    grid_vars = sorted(sampling.keys())
    # 用变量的笛卡尔积网格而不是逐变量扫描：
    # "剩余粒子数为负"这类错误只在若干变量同时取极端值时才暴露。
    axes = [[_at_fraction(sampling[name], float(t))
             for t in np.linspace(0.0, 1.0, levels)] for name in grid_vars]
    points: List[Dict[str, float]] = [dict(base)]
    for combo in _product(axes):
        if len(points) >= 512:
            break
        points.append(dict(base, **dict(zip(grid_vars, combo))))

    values: List[float] = []
    for point in points:
        try:
            values.append(ev(point))
        except VerifyError:
            values.append(float('nan'))
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return CheckResult(spec['name'], False, '全部 %d 个采样点都不可求值，公式在声明区间内无效' % len(points))

    arr = np.asarray(finite, dtype=float)
    if expect == 'positive':
        good = int(np.sum(arr > 0))
        want_text = '恒正'
    elif expect == 'negative':
        good = int(np.sum(arr < 0))
        want_text = '恒负'
    elif expect == 'nonzero':
        good = int(np.sum(np.abs(arr) > 0))
        want_text = '非零'
    else:
        return CheckResult(spec['name'], False, '未知的符号预期: ' + expect)

    total = int(arr.size)
    ratio = good / total
    passed = ratio >= 1.0 - float(tol)
    reason = ('在声明区间上采样 %d 点（%d 点可求值）：满足"%s"的有 %d 点（%.0f%%）'
              % (len(points), total, want_text, good, 100.0 * ratio))
    if passed:
        reason += '，符号性质成立'
    else:
        reason += '，符号性质被破坏——这是物理上不可接受的候选式（例如"剩余粒子数为负"）'
    return CheckResult(spec['name'], passed, reason,
                       {'expect': expect, 'satisfied': good, 'evaluated': total,
                        'ratio': ratio, 'min_value': float(arr.min()), 'max_value': float(arr.max())})


# ---------------------------------------------------------------------------
# 6. 交换对称性
# ---------------------------------------------------------------------------
def check_symmetry(ev, base, spec, tol):
    pair = spec.get('swap') or []
    if len(pair) != 2:
        return CheckResult(spec['name'], False, '规格 swap 必须给出两个变量名')
    a, b = str(pair[0]), str(pair[1])
    sampling = spec.get('sampling') or {}
    if a not in sampling or b not in sampling:
        return CheckResult(spec['name'], False, '规格缺少 %s / %s 的采样区间' % (a, b))

    # 构造一对"不对称"的取值，否则交换检验是空转。
    lo = max(float(sampling[a][0]), float(sampling[b][0]))
    hi = min(float(sampling[a][1]), float(sampling[b][1]))
    if lo >= hi:
        return CheckResult(spec['name'], False,
                           '%s 与 %s 的合法区间没有交集，无法构造交换检验点' % (a, b))
    x = _at_fraction([lo, hi], 0.25)
    y = _at_fraction([lo, hi], 0.75)
    p1 = dict(base, **{a: x, b: y})
    p2 = dict(base, **{a: y, b: x})
    y1 = ev(p1)
    y2 = ev(p2)
    if not _finite(y1, y2):
        return CheckResult(spec['name'], False, '交换检验点出现非有限值')
    scale = max(abs(y1), abs(y2), 1e-300)
    err = abs(y1 - y2) / scale
    passed = err <= tol
    reason = ('把 %s=%.6g, %s=%.6g 与两者互换后分别求值：%.6g vs %.6g，相对差异 %.2e'
              % (a, x, b, y, y1, y2, err))
    if passed:
        reason += '；两个同类量地位对称，符合物理'
    else:
        reason += '；同类量互换后结果改变，说明公式把两个物理上对称的量区别对待了'
    return CheckResult(spec['name'], passed, reason,
                       {'value_ab': y1, 'value_ba': y2, 'rel_error': err,
                        'swap': [a, b], 'probe': [x, y]})


HANDLERS = {
    'scaling': check_scaling,
    'invariance': check_invariance,
    'limit': check_limit,
    'monotonic': check_monotonic,
    'sign': check_sign,
    'symmetry': check_symmetry,
}


def load_specs(path: str) -> Mapping[str, object]:
    with open(path, encoding='utf-8') as fh:
        payload = json.load(fh)
    schema = payload.get('schema')
    if schema != SPEC_SCHEMA:
        raise VerifyError('尺度规格 schema 不匹配：期望 %s，实际 %s' % (SPEC_SCHEMA, schema))
    if not isinstance(payload.get('tasks'), dict):
        raise VerifyError('尺度规格缺少 tasks 字段')
    return payload


def list_spec_task_ids(specs: Mapping[str, object]) -> List[str]:
    return sorted(str(k) for k in (specs.get('tasks') or {}).keys())


def run_scale_checks(task_id: str,
                     formula: str,
                     meta: Mapping[str, object],
                     spec: Mapping[str, object],
                     parameters: Optional[Mapping[str, float]] = None,
                     defaults: bool = True) -> VerifyReport:
    # 按规格逐个执行尺度检验，返回与三重验证同构的报告，便于共用证据归档。
    if not spec:
        raise VerifyError('任务 %s 没有尺度规格' % task_id)
    sampling = meta.get('sampling') or {}
    if not sampling:
        raise VerifyError('meta.json 缺少 sampling，无法进行尺度检验')

    var_names = [str(v) for v in meta.get('var_names', [])]
    params = dict(parameters or {})
    # 未指定参数时，用规格里的标称值兜底（参考公式自检时用）。
    for name, value in (spec.get('nominal_parameters') or {}).items():
        params.setdefault(str(name), float(value))

    base = _base_point(meta)
    # 把自由参数的标称值并入基准点：尺度检验不只要问"自变量怎么缩放"，
    # 也要问"物理常数以什么幂次进入公式"。
    for name, value in params.items():
        base.setdefault(str(name), float(value))
    ev = _Evaluator(formula, var_names, params)

    checks: List[CheckResult] = []
    items = (spec.get('checks') or [])
    if not items:
        raise VerifyError('任务 %s 的尺度规格为空' % task_id)

    used_names: Dict[str, int] = {}
    for index, item in enumerate(items, 1):
        kind = str(item.get('kind', ''))
        handler = HANDLERS.get(kind)
        label = item.get('label') or _default_label(kind, item)
        base_name = 'scale-' + _safe_name(kind) + '-' + _safe_name(label)
        # 同一个变量上可能有多条同类检验（例如速度的二次标度与偶函数性）。
        # 检验名会变成文件名，重名会让后一条覆盖前一条的证据，必须去重。
        used_names[base_name] = used_names.get(base_name, 0) + 1
        name = base_name if used_names[base_name] == 1 else '%s-%d' % (base_name, used_names[base_name])
        enriched = dict(item)
        enriched['name'] = name
        enriched['sampling'] = sampling
        if handler is None:
            checks.append(CheckResult(name, False, '未知的尺度检验类型: ' + kind))
            continue
        tol = float(item.get('rel_tol', DEFAULT_TOL.get(kind, 1e-4)))
        try:
            checks.append(handler(ev, base, enriched, tol))
        except VerifyError as exc:
            checks.append(CheckResult(name, False, '尺度检验无法完成: ' + str(exc)))
        except Exception as exc:  # 单个检验出错不应让整份报告消失
            checks.append(CheckResult(name, False,
                                      '尺度检验内部错误 %s: %s' % (type(exc).__name__, exc)))

    failed = [c.name for c in checks if not c.passed]
    if not failed:
        verdict = 'accepted'
        hint = ('全部 %d 项尺度检验通过（幂律标度/无量纲群/极限行为/单调性/符号/对称性）；'
                '量纲之外，公式的物理形状也已核对。' % len(checks))
    else:
        verdict = 'rejected'
        hint = ('未通过的尺度检验：' + '、'.join(failed) +
                '。尺度检验不通过说明公式"单位可能对、形状不对"，'
                '必须更换函数族，继续调参数不会改善。')
    return VerifyReport(task_id, formula, params, verdict, checks, hint)


def _resolve_specs_path(path: str) -> str:
    if os.path.isabs(path) and os.path.exists(path):
        return path
    here = os.path.dirname(os.path.abspath(__file__))          # .../src/formula_agh
    root = os.path.dirname(os.path.dirname(here))              # 仓库根
    candidate = os.path.join(root, path)
    return candidate if os.path.exists(candidate) else path


def _parse_params(text: str) -> Dict[str, float]:
    # 支持 "G=6.674e-11,hbar=1.05e-34"；只给名字的参数回退到规格里的物理真值。
    out: Dict[str, float] = {}
    for chunk in str(text or '').split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        if '=' in chunk:
            name, _, value = chunk.partition('=')
            out[name.strip()] = float(value)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    # 独立入口：python -m formula_agh.scale_checks --task tasks/<id> --formula "..." [--params G=6.674e-11]
    #
    # 之所以做成独立模块入口而不是塞进 cli.py：尺度检验由 M3 独立维护，
    # 与 M2 的三重验证 CLI 解耦，任何一方改动都不会阻塞另一方。
    import argparse

    parser = argparse.ArgumentParser(
        prog='python -m formula_agh.scale_checks',
        description='FORMULA-AGH 尺度一致性检验（六类物理判据）')
    parser.add_argument('--task', required=True, help='任务目录，如 tasks/phys-gravitation')
    parser.add_argument('--formula', required=True, help='待检验的公式表达式')
    parser.add_argument('--params', default='', help='自由参数，如 G=6.674e-11')
    parser.add_argument('--specs', default='physics/scale_specs.json')
    parser.add_argument('--run-id', default='')
    parser.add_argument('--out', default='runs')
    parser.add_argument('--quiet', action='store_true', help='只输出判定，不输出逐项理由')
    args = parser.parse_args(list(argv) if argv is not None else None)

    from .evidence import write_evidence
    from .verify import load_task

    task_dir = args.task
    columns, meta = load_task(task_dir)
    task_id = str(meta.get('task_id') or os.path.basename(os.path.normpath(task_dir)))

    spec_path = _resolve_specs_path(args.specs)
    if not os.path.exists(spec_path):
        print(json.dumps({'error': '找不到尺度规格文件: ' + spec_path}, ensure_ascii=False, indent=2))
        return 2
    specs = load_specs(spec_path)
    spec = (specs.get('tasks') or {}).get(task_id)
    if not spec:
        print(json.dumps({'error': '尺度规格中没有任务: ' + task_id}, ensure_ascii=False, indent=2))
        return 2

    report = run_scale_checks(task_id, args.formula, meta, spec,
                              parameters=_parse_params(args.params))
    run_id = args.run_id or (datetime.now().strftime('%Y%m%d-%H%M%S') + '-scale-' + task_id)
    run_dir = os.path.join(args.out, run_id)
    command = ('python -m formula_agh.scale_checks --task ' + task_dir.replace(os.sep, '/') +
               ' --formula ' + json.dumps(args.formula, ensure_ascii=False))
    if args.params:
        command += ' --params ' + args.params
    command += ' --run-id ' + run_id + ' --out ' + args.out.replace(os.sep, '/')
    write_evidence(run_dir, report, command,
                   inputs=[task_dir.replace(os.sep, '/'), 'physics/scale_specs.json'],
                   notes='尺度一致性检验（M3）', hypothesis_source='cli')

    payload = json.loads(report.to_json())
    payload['run_dir'] = run_dir.replace(os.sep, '/')
    if args.quiet:
        payload['checks'] = [
            {'name': c['name'], 'passed': c['passed']} for c in payload['checks']
        ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.verdict == 'accepted' else 1


def _default_label(kind: str, item: Mapping[str, object]) -> str:
    if kind in ('scaling', 'invariance'):
        keys = item.get('scale') or {}
        if keys:
            return '-'.join(str(k) for k in keys)
        return str(item.get('var', 'x'))
    if kind == 'limit':
        return '%s-to-%s' % (item.get('var', 'x'), item.get('to', '0'))
    if kind == 'monotonic':
        return str(item.get('var', 'x'))
    if kind == 'symmetry':
        return '-'.join(str(v) for v in (item.get('swap') or ['a', 'b']))
    return str(item.get('var', 'y'))


if __name__ == '__main__':
    import sys as _sys
    _sys.exit(main())
