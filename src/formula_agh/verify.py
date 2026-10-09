# -*- coding: utf-8 -*-
# 三重验证：留出集 / 外推区 / 量纲一致性。
#
# 设计原则：
# 1. 同一份数据 + 同一个公式，任何人重跑结论一致（固定种子、无隐藏状态）。
# 2. 每项检验都给出可解释理由，供智能体下一轮自我否定时引用。
# 3. reference.json（标准答案）绝不参与本模块的任何判断，只允许 scoring 单独使用。
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .safe_eval import UnsafeExpression, compile_formula
from .units import DimensionError, UnknownUnit, expected_dimension, infer_from_source


class VerifyError(ValueError):
    pass


@dataclass
class CheckResult:
    name: str
    passed: bool
    reason: str
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class VerifyReport:
    task_id: str
    formula: str
    parameters: Dict[str, float]
    verdict: str
    checks: List[CheckResult]
    rounds_hint: str
    # 本次调用**请求**拟合的自由参数名字。必须与 parameters（拟合值）分开记录：
    # 拟合失败时 parameters 为空，若只记它，第三方就无法知道当时到底把哪些符号
    # 当成了自由参数，独立复算会走成另一条分支（量纲严格比对 vs 结构一致性）。
    # 这个缺陷由 recheck 在 variant-phys-energy-shift 等 3 条运行上抓出来。
    free_parameters: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        payload = asdict(self)
        payload['checks'] = [asdict(c) for c in self.checks]
        return json.dumps(payload, ensure_ascii=False, indent=2)


def load_task(task_dir):
    # 读取 data.csv 与 meta.json；不读取 reference.json。
    csv_path = os.path.join(task_dir, 'data.csv')
    meta_path = os.path.join(task_dir, 'meta.json')
    if not os.path.exists(csv_path):
        raise VerifyError('缺少 data.csv: ' + csv_path)
    if not os.path.exists(meta_path):
        raise VerifyError('缺少 meta.json: ' + meta_path)
    with open(meta_path, encoding='utf-8') as fh:
        meta = json.load(fh)
    raw = np.genfromtxt(csv_path, delimiter=',', names=True, dtype=float)
    names = list(raw.dtype.names or ())
    columns = {}
    for name in names:
        columns[name] = np.asarray(raw[name], dtype=float)
    return columns, meta


def split_columns(columns, var_names, y_name='y', holdout_ratio=0.2,
                  extrapolation_ratio=0.15, seed=20261008):
    # 三段划分，全部按自变量取值确定，保证可复现且外推区非空：
    #   外推区 = 主自变量取值最小的一端 + 最大的一端（严格位于训练支撑域之外）
    #   留出区 = 中间区域内随机抽取
    #   训练区 = 其余点；支撑域 [support_lo, support_hi] 只由训练点决定
    y = np.asarray(columns[y_name], dtype=float)
    n = int(y.shape[0])
    if n < 50:
        raise VerifyError('样本量过少，无法做三重验证')
    cols = []
    for name in var_names:
        cols.append(np.asarray(columns[name], dtype=float))
    x_all = np.column_stack(cols)
    spread = x_all.max(axis=0) - x_all.min(axis=0)
    axis = int(np.argmax(spread))
    key = x_all[:, axis]
    sorted_idx = np.argsort(key, kind='stable')
    n_extrap_total = max(6, int(round(n * extrapolation_ratio)))
    n_tail = n_extrap_total // 2
    low_tail = sorted_idx[:n_tail]
    high_tail = sorted_idx[n - n_tail:]
    middle = sorted_idx[n_tail:n - n_tail]
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(middle.shape[0])
    n_holdout = max(1, int(round(n * holdout_ratio)))
    n_holdout = min(n_holdout, int(middle.shape[0]) - 10)
    holdout_idx = middle[shuffled[:n_holdout]]
    train_idx = middle[shuffled[n_holdout:]]
    train_mask = np.zeros(n, dtype=bool)
    train_mask[train_idx] = True
    holdout_mask = np.zeros(n, dtype=bool)
    holdout_mask[holdout_idx] = True
    extrapolation_mask = np.zeros(n, dtype=bool)
    extrapolation_mask[low_tail] = True
    extrapolation_mask[high_tail] = True
    lo = x_all[train_idx].min(axis=0)
    hi = x_all[train_idx].max(axis=0)
    if int(extrapolation_mask.sum()) < 5 or not train_mask.any():
        raise VerifyError('数据无法形成外推区，请检查采样范围或 extrapolation_ratio')
    return {
        'train': train_mask,
        'holdout': holdout_mask,
        'extrapolation': extrapolation_mask,
        'split_axis': axis,
        'support_lo': lo,
        'support_hi': hi,
    }

def _error_metrics(pred, truth):
    """一次算齐全部误差指标；**判定用 relative_error_median**，其余作为诊断一并留证。

    判定口径的三次演进（M2 的自我否定过程，每一步都有实测数据）
    ----------------------------------------------------------
    第 1 版 normalized_rmse = RMSE / std(y)
        把"预测准不准"和"目标量动态范围大不大"混在一起。实测它在
        phys-energy-shift 上算出 0.0641，误杀了正确的普朗克关系式
        （该式逐点最大相对误差只有 3.4%）。

    第 2 版 relative_rmse = RMSE / 中位|y|
        修好了 energy-shift，但暴露了另一个问题：这是一个**全局**口径。
        phys-cyclotron 的 y=qB/m 跨 17 倍动态范围，RMSE 被少数大 |y| 点主导，
        换一个划分种子就在 0.015~0.088 之间跳——判定随种子翻转。
        同时它把 2*pi*sqrt(L/g)（小角度近似）放进来了（rel≈0.047 < 0.05）。

    第 3 版（当前）relative_error_median = median( |pred-truth| / |truth| )
        逐点相对误差取中位数：无量纲、对动态范围免疫、对近零尾部稳健。

    实测（22 个金标准 x 5 个种子，21 个错误式，见 docs/M2_验证口径修正.md）：

        口径              金标准最坏值   错误式最好值   分离倍数
        normalized_rmse      0.0697        0.2255        3.23
        relative_rmse        0.0876        0.1855        2.12
        relative_error_median 0.0130       0.1374       10.58   <-- 当前

        小角度近似 2*pi*sqrt(L/g)          中位相对误差 0.0276 -> 被拒
        泰勒展开冒充指数衰减                 中位相对误差 4.40   -> 被拒
        金标准最坏（radioactive-decay）     0.0130             -> 通过
        换 5 个种子：金标准最坏值不变（判定不翻转）

    四个口径的数值全部写进 checks/*.json，评审可以自己挑口径复核，
    不必相信我们的结论。
    """
    truth = np.asarray(truth, dtype=float)
    pred = np.asarray(pred, dtype=float)
    finite = np.isfinite(pred) & np.isfinite(truth)
    required = max(3, int(0.5 * truth.size))
    nonfinite_ratio = float(np.mean(~finite)) if pred.size else 1.0
    inf = float("inf")
    if finite.sum() < required:
        return {
            "rmse": inf, "relative_error_median": inf, "relative_error_p75": inf,
            "relative_error_p90": inf, "rmsre": inf, "relative_rmse": inf,
            "normalized_rmse": inf, "max_relative_error": inf,
            "nonfinite_ratio": nonfinite_ratio, "n_finite": int(finite.sum()),
            "n_relative_points": 0,
        }
    p = pred[finite]
    t = truth[finite]
    err = p - t
    rmse = float(math.sqrt(float(np.mean(err ** 2))))

    reference = float(np.median(np.abs(t)))
    if not math.isfinite(reference) or reference <= 0:
        reference = float(math.sqrt(float(np.mean(t ** 2)))) or 1.0
    spread = float(np.std(t)) or 1.0

    # 逐点相对误差：只在 |truth| > 0 的点上定义。
    nonzero = np.abs(t) > 0
    n_rel = int(nonzero.sum())
    if n_rel >= required:
        rel = np.abs(err[nonzero] / t[nonzero])
        rel_median = float(np.median(rel))
        rel_p75 = float(np.percentile(rel, 75))
        rel_p90 = float(np.percentile(rel, 90))
        rmsre = float(math.sqrt(float(np.mean(rel ** 2))))
        max_rel = float(np.max(rel))
    else:
        rel_median = rel_p75 = rel_p90 = rmsre = max_rel = inf

    return {
        # ---- 判定口径 ----
        "relative_error_median": rel_median,
        # ---- 诊断口径（全部留证，便于第三方换口径复核）----
        "relative_error_p75": rel_p75,
        "relative_error_p90": rel_p90,
        "rmsre": rmsre,
        "max_relative_error": max_rel,
        "rmse": rmse,
        "relative_rmse": rmse / reference,
        "normalized_rmse": rmse / spread,
        "nonfinite_ratio": nonfinite_ratio,
        "n_finite": int(finite.sum()),
        "n_relative_points": n_rel,
    }


def _normalized_rmse(pred, truth):
    """保留旧名字，返回第 1 版口径，供历史脚本比对；判定不再使用它。"""
    return float(_error_metrics(pred, truth)["normalized_rmse"])


def _levenberg_marquardt(residual, x0, y_scale, max_iter=200, lam0=1e-2):
    # 纯 numpy 的 Levenberg-Marquardt；不依赖 scipy。
    x = np.asarray(x0, dtype=float).copy()
    lam = float(lam0)
    r = np.asarray(residual(x), dtype=float)
    cost = float(np.dot(r, r))
    best_x = x.copy()
    best_cost = cost
    n = x.size
    eps = 1e-6
    improved = 0
    for _ in range(max_iter):
        J = np.zeros((r.size, n), dtype=float)
        for k in range(n):
            step = eps * max(1.0, abs(x[k]))
            xp = x.copy()
            xp[k] = xp[k] + step
            J[:, k] = (np.asarray(residual(xp), dtype=float) - r) / step
        JtJ = J.T @ J
        Jtr = J.T @ r
        try:
            delta = np.linalg.solve(JtJ + lam * np.eye(n), -Jtr)
        except np.linalg.LinAlgError:
            lam = lam * 10.0
            if lam > 1e12:
                break
            continue
        x_new = x + delta
        r_new = np.asarray(residual(x_new), dtype=float)
        cost_new = float(np.dot(r_new, r_new))
        if np.isfinite(cost_new) and cost_new < cost:
            x = x_new
            r = r_new
            cost = cost_new
            lam = max(lam * 0.3, 1e-12)
            improved += 1
            if cost < best_cost:
                best_cost = cost
                best_x = x.copy()
            if float(np.max(np.abs(delta))) < 1e-10:
                break
        else:
            lam = lam * 10.0
            if lam > 1e12:
                break
    return best_x, best_cost, improved


def _magnitude_estimate(param_names, env_mutable, y):
    # 量级估计：目标典型量级 / 特征典型量级。对乘性参数准，对分母中的参数不准，故仅作起点之一。
    target_scale = float(np.median(np.abs(y))) or 1.0
    est = []
    for name in param_names:
        guess = 1.0
        if name in env_mutable:
            vals = np.asarray(env_mutable[name], dtype=float)
            scale = float(np.median(np.abs(vals)))
            if scale > 0 and np.isfinite(scale):
                guess = target_scale / scale
        if not np.isfinite(guess) or guess <= 0:
            guess = 1.0
        est.append(guess)
    return est


def _magnitude_estimate(param_names, env_mutable, y):
    target_scale = float(np.median(np.abs(y))) or 1.0
    est = []
    for name in param_names:
        guess = 1.0
        if name in env_mutable:
            vals = np.asarray(env_mutable[name], dtype=float)
            scale = float(np.median(np.abs(vals)))
            if scale > 0 and np.isfinite(scale):
                guess = target_scale / scale
        if not np.isfinite(guess) or guess <= 0:
            guess = 1.0
        est.append(guess)
    return est


def _fit_parameters(evaluate, env_mutable, y, param_names, initial=None, max_iter=200,
                    max_residual=0.5):
    # 参数拟合策略（纯 numpy，不依赖 scipy）：
    #   1. 在【对数空间】做 LM —— 对乘性、幂次、分母中的参数都稳健；
    #   2. 以量级估计与对数网格多起点，按残差挑前几名精修；
    #   3. 再补一轮线性空间精修，取两者更优解。
    n_points = int(len(y))
    y_scale = float(np.std(y)) or 1.0
    est = _magnitude_estimate(param_names, env_mutable, y)
    nparam = len(param_names)

    def predict(theta):
        env = dict(env_mutable)
        for name, value in zip(param_names, theta):
            env[name] = np.full(n_points, float(value))
        return evaluate(env)

    def residual(theta):
        pred = predict(theta)
        if pred.shape != y.shape or not np.all(np.isfinite(pred)):
            return np.full(n_points, 1e6)
        return (pred - y) / y_scale

    def residual_log(log_theta):
        theta = np.exp(np.clip(log_theta, -120.0, 120.0))
        return residual(theta)

    log_seeds = []
    if initial:
        log_seeds.append([math.log(max(1e-300, float(initial.get(n, est[i])))) for i, n in enumerate(param_names)])
    log_seeds.append([math.log(max(1e-300, e)) for e in est])
    ln10 = math.log(10.0)
    base_logs = [math.log(max(1e-300, e)) for e in est]
    # 细步长（每 1 个数量级一格）覆盖 1e-45..1e45；同时对每个参数按其量级估计居中扫描
    exps = list(range(-45, 46, 1))
    for e in exps:
        log_seeds.append([float(e) * ln10] * nparam)
    for i in range(nparam):
        center = base_logs[i]
        for off in range(-20, 21, 2):
            cand = list(base_logs)
            cand[i] = center + float(off) * ln10
            log_seeds.append(cand)

    scored = []
    for seed in log_seeds:
        theta = np.exp(np.clip(np.asarray(seed, dtype=float), -120.0, 120.0))
        r = residual(theta)
        cost = float(np.dot(r, r))
        if np.isfinite(cost):
            scored.append((cost, np.asarray(seed, dtype=float)))
    scored.sort(key=lambda item: item[0])
    if not scored:
        raise VerifyError('参数拟合失败：所有初值都不可行')

    x_best = None
    cost_best = float('inf')
    for _cost, seed in scored[:10]:
        log_x, log_cost, _imp = _levenberg_marquardt(residual_log, seed, 1.0, max_iter, lam0=1e-3)
        theta = np.exp(np.clip(log_x, -120.0, 120.0))
        cost_lin = float(np.dot(residual(theta), residual(theta)))
        for start, cost in ((theta, cost_lin), (theta, log_cost)):
            if np.isfinite(cost) and cost < cost_best:
                cost_best = cost
                x_best = start
        lin_x, lin_cost, _imp2 = _levenberg_marquardt(residual, theta, y_scale, max_iter)
        if np.isfinite(lin_cost) and lin_cost < cost_best:
            cost_best = lin_cost
            x_best = lin_x

    if x_best is None or not np.isfinite(cost_best):
        raise VerifyError('参数拟合失败：所有初值都未收敛')
    # 收敛门槛。注意这里用的是 RMSE/std(y) —— 正是判定阶段已经弃用的口径
    # （它随目标量动态范围变化，见 docs/M2_验证口径修正.md）。
    # 之所以保留：这是一道"这个函数形式根本没戏"的粗筛，不是精度判定，
    # 松一点是刻意的；真正的精度判定交给留出集与外推区。
    # 但阈值不再硬编码，改由 config/agent.yaml 的 verify.max_fit_residual 提供，
    # 并且训练残差会在 fit 检验的 metrics 里按四种口径同时留证。
    rms = math.sqrt(cost_best / max(1, n_points))
    if rms > max_residual:
        raise VerifyError('参数拟合不收敛：残差过大（RMSE/std(y) = %.3f > %.3f）'
                          % (rms, max_residual))
    out = {}
    for name, value in zip(param_names, x_best):
        out[name] = float(value)
    return out

def _check_dimension(formula, meta, free_parameters=None):
    # 量纲检验分两级，避免把'参数吸收单位'的正确物理公式误杀：
    #   无自由参数：公式推断量纲必须等于 y 的量纲（最严格）
    #   有自由参数：只做结构一致性检查（函数参数是否无量纲、加减是否同量纲），
    #               并明确说明'严格量纲比对因存在自由参数而推迟'。
    units_map = meta.get('units') or {}
    params = [str(p) for p in (free_parameters or [])]
    if not units_map or not isinstance(units_map, dict):
        return CheckResult('dimension', True, 'meta.json 未提供单位信息，量纲检验不适用', {})
    var_units = {}
    for key, value in units_map.items():
        if str(key) == 'y':
            continue
        var_units[str(key)] = str(value)
    try:
        inferred = infer_from_source(formula, var_units, params)
        want = expected_dimension(str(units_map.get('y', '')))
    except UnknownUnit as exc:
        return CheckResult('dimension', True, '存在未知单位，跳过量纲检验: ' + str(exc), {})
    except DimensionError as exc:
        return CheckResult('dimension', False, '量纲不成立（结构性错误）: ' + str(exc), {})
    except UnsafeExpression as exc:
        return CheckResult('dimension', False, '表达式不可用: ' + str(exc), {})
    if want is None:
        return CheckResult('dimension', True, 'y 的单位无法识别，跳过量纲比对', {})
    if params:
        return CheckResult('dimension', True,
                           '结构一致性通过；因存在自由参数 ' + ','.join(params) +
                           '（可吸收单位），严格量纲比对推迟到参数拟合之后',
                           {})
    if inferred == want:
        return CheckResult('dimension', True, '量纲一致（严格比对）', {})
    return CheckResult('dimension', False,
                       '量纲不一致：公式推出 ' + str(inferred) + '，而 y 应为 ' + str(want), {})

DEFAULT_SCALE_SPECS = 'physics/scale_specs.json'


def _scale_check_results(formula, meta, fitted, task_id, specs_path=None):
    """按 config 开关追加"尺度/极限行为"检验（规格由 M3 维护）。

    接口决策记录（回应 M3《交叉评审发现》发现 3）
    -------------------------------------------
    M3 给了三个方案，M2 采纳方案 A：尺度检验与留出集/外推区/量纲并列进 checks[]。
    理由与 M3 一致——尺度检验的失败理由（"曲线对振幅完全平坦，说明漏掉了这个自变量"）
    对智能体下一轮假设的价值远高于只放在评分阶段。

    实现细节：
    * 这里用**延迟导入**。scale_checks 依赖本模块（要 VerifyReport / CheckResult），
      顶层互相导入会成环。延迟导入让两边仍能各自独立演进而不用改对方。
    * 没有规格的任务返回一条显式的"未执行"记录（passed=True 但 marked skipped），
      而不是悄悄什么都不加——静默跳过正是本项目反复踩到的坑。
    """
    from . import scale_checks          # 延迟导入，避免循环依赖

    try:
        path = scale_checks._resolve_specs_path(specs_path or DEFAULT_SCALE_SPECS)
        specs = scale_checks.load_specs(path)
    except Exception as exc:  # noqa: BLE001 - 规格缺失要如实报，不能当通过
        return [CheckResult('scale-checks-unavailable', False,
                            '尺度规格不可用（' + str(specs_path or DEFAULT_SCALE_SPECS) + '）: '
                            + type(exc).__name__ + ': ' + str(exc), {'skipped': True})]
    spec = (specs.get('tasks') or {}).get(task_id)
    if not spec:
        return [CheckResult('scale-checks-missing', True,
                            'physics/scale_specs.json 未覆盖该任务，尺度检验未执行',
                            {'skipped': True})]
    try:
        report = scale_checks.run_scale_checks(task_id, formula, meta, spec,
                                               parameters=dict(fitted or {}) or None)
    except Exception as exc:  # noqa: BLE001 - 单个任务出错不应让整份报告消失
        return [CheckResult('scale-checks-error', False,
                            '尺度检验无法完成: ' + type(exc).__name__ + ': ' + str(exc),
                            {'skipped': True})]
    return list(report.checks)


def verify_formula(formula, columns, meta, parameters=None, initial=None,
                   holdout_threshold=0.08, extrapolation_threshold=0.15,
                   holdout_ratio=0.2, extrapolation_ratio=0.15, seed=20261008,
                   dimension_check=True, scale_check=False, scale_specs_path=None,
                   fit_max_residual=0.5):
    # 对单个公式执行三重验证，返回结构化报告。
    #
    # dimension_check / scale_check 默认值刻意取 True / **False**：
    # 本函数是纯引擎原语，不读配置文件，保证"同样输入必得同样输出"。
    # 开关由各入口从 config/agent.yaml 读出后显式传入（CLI、examples、
    # adversarial、recheck 均已接线，并有测试锁死这一点）。
    task_id = str(meta.get('task_id', 'unknown'))
    var_names = [str(v) for v in meta.get('var_names', [])]
    if not var_names:
        raise VerifyError('meta.json 缺少 var_names')
    y = np.asarray(columns['y'], dtype=float)
    splits = split_columns(columns, var_names, 'y', holdout_ratio,
                           extrapolation_ratio, seed)
    train = splits['train']
    holdout = splits['holdout']
    extrap = splits['extrapolation']
    checks = []
    param_names = [str(p) for p in (parameters or [])]

    # 量纲检验本身也不能把整条流水线带崩：它是不可信输入的第一道门，
    # 任何意外都应当转化为"这一项不通过"，而不是未捕获异常。
    if dimension_check:
        try:
            checks.append(_check_dimension(formula, meta, param_names))
        except Exception as exc:  # noqa: BLE001 - 有意兜底，理由同上
            checks.append(CheckResult('dimension', False,
                                      '量纲检验发生未预期错误（按不通过处理）: '
                                      + type(exc).__name__ + ': ' + str(exc)))
    else:
        # 关闭也要留痕：一项检验"没跑"和"跑过了"必须在证据里能分开。
        checks.append(CheckResult('dimension', True,
                                  '量纲检验已按 config/agent.yaml 的 dimension_check=false 关闭',
                                  {'disabled': True}))

    try:
        evaluate = compile_formula(formula, list(var_names) + param_names)
    except UnsafeExpression as exc:
        checks.append(CheckResult('expression', False, '表达式不可用: ' + str(exc)))
        return VerifyReport(task_id, formula, {}, 'rejected', checks,
                            '表达式本身不合法，请先修正语法或去掉不支持的语法结构。',
                            list(param_names))

    env_base = {}
    for name in var_names:
        env_base[name] = np.asarray(columns[name], dtype=float)
    train_env = {}
    for name, values in env_base.items():
        train_env[name] = values[train]
    y_train = y[train]
    fitted = {}

    if param_names:
        try:
            fitted = _fit_parameters(evaluate, train_env, y_train, param_names, initial,
                                     max_residual=fit_max_residual)
        except VerifyError as exc:
            checks.append(CheckResult('fit', False, str(exc)))
            return VerifyReport(task_id, formula, {}, 'rejected', checks,
                                '拟合阶段失败。若反复不收敛，说明该函数形式与数据不匹配，'
                                '应更换函数族而不是只调初值。',
                                list(param_names))
        # 训练残差按四种口径一并留证：评审可以据此判断这道粗筛的松紧是否合适。
        try:
            _train_env = {}
            for _name, _values in env_base.items():
                _train_env[_name] = _values[train]
            for _name, _value in fitted.items():
                _train_env[_name] = np.full(int(train.sum()), float(_value))
            _train_metrics = _error_metrics(evaluate(_train_env), y_train)
        except Exception:  # noqa: BLE001 - 诊断信息缺失不该影响判定
            _train_metrics = {}
        _fit_metrics = dict(fitted)
        for _key in ('relative_error_median', 'relative_error_p90', 'rmsre',
                     'relative_rmse', 'normalized_rmse'):
            if _key in _train_metrics:
                _fit_metrics['train_' + _key] = _train_metrics[_key]
        checks.append(CheckResult('fit', True, '参数拟合收敛（训练集诊断见 metrics）',
                                  _fit_metrics))

        def eval_all(mask, _fitted=fitted, _base=env_base, _ev=evaluate):
            env = {}
            for name, values in _base.items():
                env[name] = values[mask]
            for name, value in _fitted.items():
                env[name] = np.full(int(mask.sum()), float(value))
            return _ev(env)
    else:
        def eval_all(mask, _base=env_base, _ev=evaluate):
            env = {}
            for name, values in _base.items():
                env[name] = values[mask]
            return _ev(env)

    pred_holdout = eval_all(holdout)
    hold_metrics = _error_metrics(pred_holdout, y[holdout])
    hold_metrics['threshold'] = holdout_threshold
    hold_metrics['criterion'] = 'relative_error_median'
    holdout_passed = hold_metrics['relative_error_median'] <= holdout_threshold
    checks.append(CheckResult(
        'holdout', holdout_passed,
        '留出集中位相对误差 %.4f（阈值 %.4f）；诊断口径 p90=%.4f、RMSE/中位|y|=%.4f、'
        'RMSE/std(y)=%.4f、非有限值比例 %.2f%%' % (
            hold_metrics['relative_error_median'], holdout_threshold,
            hold_metrics['relative_error_p90'], hold_metrics['relative_rmse'],
            hold_metrics['normalized_rmse'], 100.0 * hold_metrics['nonfinite_ratio']),
        hold_metrics))

    pred_extrap = eval_all(extrap)
    extrap_metrics = _error_metrics(pred_extrap, y[extrap])
    extrap_metrics['threshold'] = extrapolation_threshold
    extrap_metrics['criterion'] = 'relative_error_median'
    blowup = extrap_metrics['nonfinite_ratio']
    extrap_passed = (extrap_metrics['relative_error_median'] <= extrapolation_threshold) \
        and (blowup < 0.1)
    reason = ('外推区中位相对误差 %.4f（阈值 %.4f），非有限值比例 %.2f%%；'
              '诊断口径 p90=%.4f、RMSE/中位|y|=%.4f、RMSE/std(y)=%.4f' % (
                  extrap_metrics['relative_error_median'], extrapolation_threshold,
                  100.0 * blowup, extrap_metrics['relative_error_p90'],
                  extrap_metrics['relative_rmse'], extrap_metrics['normalized_rmse']))
    if (not extrap_passed) and holdout_passed:
        reason = reason + '；域内表现良好但离开支撑域后失效，属于过拟合式发现'
    checks.append(CheckResult('extrapolation', extrap_passed, reason, extrap_metrics))

    # 第四道门（可开关）：尺度 / 极限行为 / 单调性 / 符号 / 对称性。
    # 与前三道并列进 checks[]，失败理由直接进入智能体的下一轮提示（方案 A）。
    if scale_check:
        checks.extend(_scale_check_results(formula, meta, fitted, task_id,
                                           scale_specs_path))

    failed = [c.name for c in checks if not c.passed]
    scale_failed = [name for name in failed if name.startswith('scale-')]
    if not failed:
        verdict = 'accepted'
        hint = '全部检验通过，可进入结果归档；请在结论中说明验证证据的位置。'
    elif failed == ['dimension']:
        verdict = 'rejected'
        hint = '量纲不成立，属物理荒谬公式，必须否决并更换形式，不要继续微调参数。'
    elif failed == ['extrapolation']:
        verdict = 'rejected'
        hint = '典型过拟合式发现：域内拟合好、域外崩溃。请更换函数族或增加结构性约束，不要在原式上反复调参。'
    else:
        verdict = 'rejected'
        hint = '未通过项：' + '、'.join(failed) + '。请针对失败项提出新的假设。'
    if scale_failed:
        # 尺度检验的失败含义与数值误差不同：单位可能对、形状不对。
        hint += ('其中尺度/极限行为检验不通过（' + '、'.join(scale_failed) + '）：'
                 '说明公式的物理形状不对——例如漏掉了某个自变量、'
                 '或对某个量不是幂律关系。继续调参数不会有改善，必须更换函数族。')

    return VerifyReport(task_id, formula, fitted, verdict, checks, hint,
                        list(param_names))