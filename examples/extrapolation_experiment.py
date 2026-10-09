# -*- coding: utf-8 -*-
# 受控外推实验：只用窄域数据拟合，再走出去看它从哪里开始崩。
#
# 为什么不用现成的划分直接画：
#   项目默认的三段划分是按"跨度最大的自变量"切的，而错误往往出在另一个自变量上
#   （例如 G*m1*m2/r 的幂次错在 r，但划分轴是 m1）。要在图上把"崩溃区间"指出来，
#   必须自己控制训练域。所以这里做的是一个**受控实验**：
#     1. 选定物理自变量（如 r）；
#     2. 只用它的一段窄窗口内的数据拟合候选式的自由参数；
#     3. 在窗口之外预测，量出误差随该变量增长的过程；
#     4. 把"预测曲线 vs 真实曲线"画出来，外推区高亮。
#
# 这一步同时回答两个问题：
#   * 验证引擎的"外推检验"到底在拦什么（给评审看的直观证据）；
#   * 哪些错误是"域内根本看不出来"的——这正是数值拟合最危险的地方。
#
# 输出：
#   runs/extrap-<task>/            每个实验的完整证据（含 figures/）
#   evidence/figures/*.png|.svg    供文档与视频使用的图
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.evidence import write_evidence
from formula_agh.figures import DEFAULT_COLORS as C, Chart
from formula_agh.safe_eval import compile_formula
from formula_agh.verify import (CheckResult, VerifyError, VerifyReport, _fit_parameters,
                                load_task, split_columns)

TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
RUNS = os.path.join(ROOT, 'runs')
FIGS = os.path.join(ROOT, 'evidence', 'figures')

# 每个实验：任务 / 错误候选式 / 候选式的自由参数 / 要扫的自变量 / 训练窄窗（占全域的百分比）
CASES = [
    dict(task='phys-gravitation', candidate='G*m1*m2/r', free=['G'], axis='r',
         window=(0.0, 0.42), unit='m',
         headline='把 r 的平方反比写成一次反比：域内靠参数抵消，域外按 r 线性发散'),
    dict(task='phys-coulomb', candidate='k*q1*q2/r', free=['k'], axis='r',
         window=(0.0, 0.42), unit='m',
         headline='库仑定律同样的错误幂次：误差随距离单调放大'),
    dict(task='phys-surface-gravity', candidate='G*M/R', free=['G'], axis='R',
         window=(0.0, 0.42), unit='m',
         headline='把 R 的平方反比写成一次反比：半径越大偏差越大'),
    dict(task='phys-stefan-boltzmann', candidate='sigma*A*T**2', free=['sigma'], axis='T',
         window=(0.0, 0.42), unit='K',
         headline='把温度的四次方写成二次方：域内可以凑合，域外高温端迅速崩溃'),
    dict(task='phys-hydrogen-level',
         candidate='-me*el**4/(2*(4*pi*eps0)**2*hbar**2*n)', free=['eps0', 'hbar'],
         axis='n', window=(0.0, 0.42), unit='',
         headline='把主量子数的 n^-2 写成 n^-1：能级越高偏差越大'),
    dict(task='phys-pendulum-exact', candidate='2*pi*sqrt(L/g)', free=[], axis='theta0',
         window=(0.0, 0.35), unit='rad',
         headline='小角度近似：它根本没有振幅项，域内几乎无差，大摆角处偏差按 theta0^2 增长'),
]


def load_reference(task_id):
    with open(os.path.join(REF, task_id + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def normalized_rmse(pred, truth):
    truth = np.asarray(truth, dtype=float)
    pred = np.asarray(pred, dtype=float)
    finite = np.isfinite(pred)
    if finite.sum() < max(3, int(0.5 * truth.size)):
        return float('inf')
    scale = float(np.std(truth)) or 1.0
    return float(np.sqrt(np.mean((pred[finite] - truth[finite]) ** 2)) / scale)


def predict_over(task_id, formula, free, params, axis, sweep, stats):
    columns, meta = load_task(os.path.join(TASKS, task_id))
    var_names = [str(v) for v in meta['var_names']]
    evaluate = compile_formula(formula, var_names + list(free))
    env = {}
    for name in var_names:
        env[name] = np.full(sweep.shape, float(stats[name]))
    env[axis] = np.asarray(sweep, dtype=float)
    for name in free:
        env[name] = np.full(sweep.shape, float(params[name]))
    return evaluate(env)


def run_case(case, index):
    task_id = case['task']
    columns, meta = load_task(os.path.join(TASKS, task_id))
    var_names = [str(v) for v in meta['var_names']]
    ref = load_reference(task_id)
    axis = case['axis']
    free = list(case['free'])
    y = np.asarray(columns['y'], dtype=float)
    x = np.asarray(columns[axis], dtype=float)

    lo, hi = float(x.min()), float(x.max())
    span = hi - lo
    win_lo = lo + case['window'][0] * span
    win_hi = lo + case['window'][1] * span
    train_mask = (x >= win_lo) & (x <= win_hi)
    outside_mask = ~train_mask
    if train_mask.sum() < 30:
        raise VerifyError('%s: 窄窗内样本过少 (%d)' % (task_id, int(train_mask.sum())))

    # 1) 只用窄窗拟合候选式的自由参数 —— 复用的是验证引擎自己的拟合器，没有另写一套。
    fitted = {}
    fit_note = '该候选式没有自由参数，无需拟合'
    if free:
        evaluate = compile_formula(case['candidate'], var_names + free)
        env_train = {name: np.asarray(columns[name], dtype=float)[train_mask] for name in var_names}
        fitted = _fit_parameters(evaluate, env_train, y[train_mask], free)
        fit_note = '在窄窗内拟合得到 ' + ', '.join('%s=%.6g' % (k, v) for k, v in fitted.items())

    # 2) 在其余自变量取中位数的剖面上扫过整个取值范围
    stats = {name: float(np.median(np.asarray(columns[name], dtype=float))) for name in var_names}
    sweep = np.linspace(lo, hi, 320)
    y_cand = predict_over(task_id, case['candidate'], free, fitted, axis, sweep, stats)

    ref_free = [str(p) for p in (ref.get('free_parameters') or [])]
    ref_params = dict(ref.get('true_constants') or {})
    y_ref = predict_over(task_id, ref['formula'], ref_free, ref_params, axis, sweep, stats)

    # 3) 域内 / 域外误差（用真实数据点，而不是剖面，才是有意义的泛化误差）
    def predict_on(mask):
        env = {name: np.asarray(columns[name], dtype=float)[mask] for name in var_names}
        evaluate = compile_formula(case['candidate'], var_names + free)
        for name in free:
            env[name] = np.full(int(mask.sum()), float(fitted[name]))
        return evaluate(env)

    inside_rmse = normalized_rmse(predict_on(train_mask), y[train_mask])
    outside_rmse = normalized_rmse(predict_on(outside_mask), y[outside_mask])

    rel_err = np.abs(y_cand - y_ref) / np.maximum(np.abs(y_ref), 1e-300)
    outside_sweep = (sweep < win_lo) | (sweep > win_hi)
    if outside_sweep.any():
        idx = int(np.argmax(np.where(outside_sweep, rel_err, -1.0)))
        peak_err, peak_at = float(rel_err[idx]), float(sweep[idx])
    else:
        peak_err, peak_at = float(np.max(rel_err)), float(sweep[int(np.argmax(rel_err))])
    inside_peak = float(np.max(rel_err[~outside_sweep])) if (~outside_sweep).any() else 0.0

    run_id = 'extrap-%s' % task_id
    run_dir = os.path.join(RUNS, run_id)
    figure_dir = os.path.join(run_dir, 'figures')
    os.makedirs(figure_dir, exist_ok=True)

    xlabel = '%s%s' % (axis, (' / ' + case['unit']) if case['unit'] else '')
    name_curve = 'fig-extrap-%s-curve' % task_id
    name_error = 'fig-extrap-%s-error' % task_id
    band_label = '外推区（窄窗之外）'

    # --- 图 1：预测曲线 vs 真实曲线，外推区高亮 ---------------------------
    chart = (Chart(1080, 620)
             .set_title('外推崩溃：%s' % case['headline'])
             .set_axes(xlabel, 'y', 'linear', 'linear')
             .band(win_hi, float(sweep[-1]), '#ffd9d9', 0.55, band_label)
             .band(float(sweep[0]), win_lo, '#ffd9d9', 0.55)
             .band(win_lo, win_hi, '#dff0d8', 0.45, '拟合所用窄窗')
             .line(sweep, y_ref, C['reference'], 2.6, '参考公式（物理真值）')
             .line(sweep, y_cand, C['candidate'], 2.6, '候选公式（仅窄窗拟合）', dash=(8, 5))
             .text(float(sweep[0]) + 0.02 * span, float(np.max(y_ref)) * 0.94,
                   '窄窗内归一化误差 %.4f' % inside_rmse, '#2b6b2b', 15)
             .text(win_hi + 0.02 * span, float(np.max(y_ref)) * 0.72,
                   '外推区归一化误差 %.4f' % outside_rmse, '#a32020', 15))
    chart.save(os.path.join(FIGS, name_curve + '.png'))
    chart.save(os.path.join(figure_dir, name_curve + '.svg'))

    # --- 图 2：相对误差随自变量的变化，崩溃区间直接标出来 ------------------
    err_chart = (Chart(1080, 560)
                 .set_title('误差随自变量的增长：崩溃发生在哪里')
                 .set_axes(xlabel, '相对误差 |Δy| / |y|', 'linear', 'log')
                 .band(win_hi, float(sweep[-1]), '#ffd9d9', 0.55, band_label)
                 .band(float(sweep[0]), win_lo, '#ffd9d9', 0.55)
                 .band(win_lo, win_hi, '#dff0d8', 0.45, '拟合所用窄窗')
                 .line(sweep, np.maximum(rel_err, 1e-12), C['candidate'], 2.6, '候选式相对误差'))
    if peak_err > 0:
        err_chart.scatter([peak_at], [max(peak_err, 1e-12)], '#7f0000', 8,
                          '外推区最大相对误差 %.3g' % peak_err)
    err_chart.save(os.path.join(FIGS, name_error + '.png'))
    err_chart.save(os.path.join(figure_dir, name_error + '.svg'))

    # --- 证据 -------------------------------------------------------------
    checks = [
        CheckResult('narrow_fit', inside_rmse <= 0.08,
                    '窄窗内归一化误差 %.4f（阈值 0.0800）；%s' % (inside_rmse, fit_note),
                    {'normalized_rmse': inside_rmse, 'window': [win_lo, win_hi],
                     'samples': int(train_mask.sum()), 'fitted': fitted}),
        CheckResult('extrapolation', outside_rmse <= 0.15,
                    '窄窗之外归一化误差 %.4f（阈值 0.1500）；剖面最大相对误差 %.3g 出现在 %s=%.6g'
                    % (outside_rmse, peak_err, axis, peak_at),
                    {'normalized_rmse': outside_rmse, 'peak_relative_error': peak_err,
                     'peak_at': peak_at, 'peak_inside_window': inside_peak,
                     'samples': int(outside_mask.sum()), 'window': [win_lo, win_hi]}),
    ]
    verdict = 'accepted' if all(c.passed for c in checks) else 'rejected'
    report = VerifyReport(task_id, case['candidate'], fitted, verdict, checks,
                          '受控外推实验：只在窄窗内拟合，用于定位公式开始失真的自变量区间。')
    command = ('python examples/extrapolation_experiment.py --task %s --candidate %s --axis %s'
               % (task_id, json.dumps(case['candidate'], ensure_ascii=False), axis))
    write_evidence(run_dir, report, command,
                   inputs=['tasks/' + task_id, 'physics/scale_specs.json'],
                   notes=case['headline'])
    return {
        'case_index': index, 'task_id': task_id, 'candidate': case['candidate'],
        'axis': axis, 'window': [win_lo, win_hi], 'unit': case['unit'],
        'headline': case['headline'], 'fitted': fitted, 'fit_note': fit_note,
        'inside_rmse': inside_rmse, 'outside_rmse': outside_rmse,
        'peak_relative_error': peak_err, 'peak_at': peak_at,
        'peak_inside_window': inside_peak,
        'verdict': verdict, 'run_id': run_id,
        'figures': ['evidence/figures/%s.png' % name_curve,
                    'evidence/figures/%s.png' % name_error],
    }


def main():
    os.makedirs(FIGS, exist_ok=True)
    rows = []
    for index, case in enumerate(CASES, 1):
        try:
            row = run_case(case, index)
        except VerifyError as exc:
            print('SKIP %-30s %s' % (case['task'], exc))
            continue
        rows.append(row)
        print('%-30s window=[%.4g, %.4g]  域内 %.4f  域外 %.4f  峰值 %.3g @ %.4g'
              % (row['task_id'], row['window'][0], row['window'][1],
                 row['inside_rmse'], row['outside_rmse'],
                 row['peak_relative_error'], row['peak_at']))

    payload = {
        'note': ('受控外推实验：每个任务只用一段窄窗口的数据拟合候选式的自由参数，'
                 '再在窗口之外预测，量出误差随自变量的增长。'),
        'experiments': rows,
    }
    os.makedirs(os.path.join(ROOT, 'evidence'), exist_ok=True)
    with open(os.path.join(ROOT, 'evidence', 'extrapolation_crashes.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print('')
    print('wrote evidence/extrapolation_crashes.json (%d 个实验)' % len(rows))
    return 0


if __name__ == '__main__':
    sys.exit(main())
