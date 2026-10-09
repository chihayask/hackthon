# -*- coding: utf-8 -*-
# 汇总图：给评委看的两张"全局"图。
#
#   fig-discrimination   每个判据单独作为唯一门时能拦下多少错误式（含"合起来"那一列）
#   fig-error-plane      留出集误差 vs 外推区误差的决策平面：两条阈值线把平面分成四块
#
# 数据来源是 evidence/discrimination.json —— 由 examples/discrimination_report.py
# 对 22 个参考式与 22 个结构错误式真实跑出来的记录，不是手填的数字。
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.figures import DEFAULT_COLORS as C, Chart

EVIDENCE = os.path.join(ROOT, 'evidence')
FIGS = os.path.join(EVIDENCE, 'figures')
DATA = os.path.join(EVIDENCE, 'discrimination.json')


def load():
    with open(DATA, encoding='utf-8') as fh:
        return json.load(fh)


def pick_metric(metrics):
    # 判定口径随引擎版本会调整；这里按存在的键取值，并在轴标题里如实写明用的是哪个。
    for key in ('relative_error_median', 'relative_rmse', 'normalized_rmse'):
        if key in metrics:
            return key, float(metrics[key])
    return None, None


def judge_hits(records, judge):
    # 以"公式"为单位统计：该判据能不能单独拦住这个错误式。
    caught = 0
    total = 0
    for record in records:
        total += 1
        triple = record.get('triple') or {}
        scale = record.get('scale') or {}
        if judge == 'scale':
            if scale.get('verdict') == 'rejected':
                caught += 1
            continue
        if judge == 'pipeline':
            if triple.get('verdict') != 'accepted' or scale.get('verdict') == 'rejected':
                caught += 1
            continue
        check = (triple.get('checks') or {}).get(judge)
        if check is not None and not check['passed']:
            caught += 1
    return caught, total


def judge_pass(records, judge):
    ok = 0
    for record in records:
        triple = record.get('triple') or {}
        scale = record.get('scale') or {}
        if judge == 'scale':
            if scale.get('verdict') == 'accepted':
                ok += 1
            continue
        if judge == 'pipeline':
            if triple.get('verdict') == 'accepted' and scale.get('verdict') != 'rejected':
                ok += 1
            continue
        check = (triple.get('checks') or {}).get(judge)
        if check is not None and check['passed']:
            ok += 1
    return ok, len(records)


def chart_discrimination(data):
    judges = [('dimension', '量纲一致性'), ('holdout', '留出集'),
              ('extrapolation', '外推区'), ('scale', '尺度检验（6 类）'),
              ('pipeline', '全部门联合判定')]
    refs = data['records']['reference']
    wrongs = data['records']['wrong']

    labels, ref_rate, wrong_rate = [], [], []
    table = []
    for key, title in judges:
        passed, total_ref = judge_pass(refs, key)
        caught, total_wrong = judge_hits(wrongs, key)
        labels.append(title)
        ref_rate.append(100.0 * passed / max(1, total_ref))
        wrong_rate.append(100.0 * caught / max(1, total_wrong))
        table.append((title, passed, total_ref, caught, total_wrong))

    chart = (Chart(1080, 620)
             .set_title('每个判据单独把关时的判别力（22 个参考式 / 22 个结构错误式）')
             .set_axes('判据', '比例 / %', 'linear', 'linear', ylim=(-16, 158), xticks=False))
    n = len(labels)
    slot = 1.0 / n
    bar_w = slot * 0.30
    for index, (label, green, red) in enumerate(zip(labels, ref_rate, wrong_rate)):
        centre = (index + 0.5) * slot
        if index % 2 == 0:
            chart.band(centre - slot * 0.46, centre + slot * 0.46, '#f4f4f4', 1.0)
        # 图例只保留两条：同一颜色的柱子不必逐个进图例。
        chart.bar_rect(centre - bar_w * 0.55, centre, green,
                       '参考式通过率（22 个参考式）' if index == 0 else '',
                       C['reference'])
        chart.bar_rect(centre, centre + bar_w * 0.55, red,
                       '错误式拦下率（22 个结构错误式）' if index == 0 else '',
                       C['candidate'])
        chart.text(centre - bar_w * 0.28, green + 3.0, '%d/%d' % table[index][1:3],
                   '#2b6b2b', 14, 'middle')
        chart.text(centre + bar_w * 0.28, red + 3.0, '%d/%d' % table[index][3:5],
                   '#a32020', 14, 'middle')
    for centre, label in zip([(i + 0.5) * slot for i in range(n)], labels):
        chart.text(centre, -9.0, label, C['text'], 15, 'middle')
    chart.save(os.path.join(FIGS, 'fig-discrimination.png'))
    return table


def chart_error_plane(data):
    refs = data['records']['reference']
    wrongs = data['records']['wrong']

    metric_key = None
    for record in refs + wrongs:
        triple = record.get('triple') or {}
        for name in ('holdout', 'extrapolation'):
            metrics = ((triple.get('checks') or {}).get(name) or {}).get('metrics') or {}
            key, _ = pick_metric(metrics)
            if key:
                metric_key = key
                break
        if metric_key:
            break
    metric_key = metric_key or 'normalized_rmse'
    label_map = {
        'relative_error_median': '留出集/外推区中位相对误差（当前判定口径）',
        'relative_rmse': '留出集/外推区 RMSE 相对误差',
        'normalized_rmse': '留出集/外推区归一化 RMSE（RMSE/std(y)）',
    }
    axis_label = label_map.get(metric_key, metric_key)

    def collect(records):
        xs, ys, missed = [], [], 0
        for record in records:
            checks = (record.get('triple') or {}).get('checks') or {}
            hold = (checks.get('holdout') or {}).get('metrics') or {}
            ext = (checks.get('extrapolation') or {}).get('metrics') or {}
            hx = hold.get(metric_key)
            ey = ext.get(metric_key)
            if hx is None or ey is None:
                missed += 1
                continue
            xs.append(float(hx))
            ys.append(float(ey))
        return xs, ys, missed

    rx, ry, r_miss = collect(refs)
    wx, wy, w_miss = collect(wrongs)

    # 阈值线取自引擎当前的判定口径（config/agent.yaml 统一管理）；图中如实标出。
    hold_t, ext_t = 0.08, 0.15
    values = [v for v in list(rx) + list(ry) + list(rx) if v > 0]
    values += [v for v in list(wx) + list(wy) if v > 0]
    lo = max(1e-5, min(values) * 0.5) if values else 1e-5
    hi = max(values) * 2.0 if values else 1.0

    chart = (Chart(1000, 700)
             .set_title('决策平面：留出集误差 vs 外推区误差（两条线是当前阈值）')
             .set_axes(axis_label, axis_label, 'log', 'log', xlim=(lo, hi), ylim=(lo, hi))
             .hline(ext_t, '#c07000', 1.6, (7, 4), '外推区阈值 %.2f' % ext_t))
    chart.vline(hold_t, '#c07000', 1.6, (7, 4), '留出集阈值 %.2f' % hold_t)
    chart.scatter(rx, ry, C['reference'], 11, '参考式（22 个，全部在阈值内）', 0.95)
    chart.scatter(wx, wy, C['candidate'], 10, '结构错误式（越出阈值即被拦下）', 0.9)
    note = '另有 %d 个错误式在拟合/语法阶段就被拦下，未进入误差平面' % (r_miss + w_miss)
    chart.text(lo * 1.6, hi * 0.55, note, '#555555', 14)
    chart.save(os.path.join(FIGS, 'fig-error-plane.png'))
    return metric_key, hold_t, ext_t, len(rx), len(wx), r_miss + w_miss


def chart_layers(data):
    # 任务集构成与判据覆盖：base / challenge 两层的任务数与每个任务的判据条目数。
    specs_path = os.path.join(ROOT, 'physics', 'scale_specs.json')
    with open(specs_path, encoding='utf-8') as fh:
        specs = json.load(fh)
    tasks_dir = os.path.join(ROOT, 'tasks')
    layers = {'base': [], 'challenge': []}
    for task_id in sorted(specs['tasks']):
        meta_path = os.path.join(tasks_dir, task_id, 'meta.json')
        with open(meta_path, encoding='utf-8') as fh:
            meta = json.load(fh)
        layer = str(meta.get('layer') or 'base')
        count = len(specs['tasks'][task_id]['checks'])
        layers.setdefault(layer, []).append((task_id, count))
    order = [name for name in ('base', 'challenge') if layers.get(name)]
    top = max([len(items) for items in layers.values()] +
              [sum(c for _t, c in items) for items in layers.values()] + [1])
    chart = (Chart(1000, 560)
             .set_title('任务集构成：两个难度层的任务数与物理判据条目数')
             .set_axes('难度层', '数量', 'linear', 'linear',
                       ylim=(-top * 0.10, top * 1.34), xticks=False))
    slot = 1.0 / max(1, len(order))
    labels = {'base': '基础层 base', 'challenge': '挑战层 challenge'}
    for index, layer in enumerate(order):
        items = layers[layer]
        centre = (index + 0.5) * slot
        counts = [c for _t, c in items]
        chart.bar_rect(centre - slot * 0.24, centre - slot * 0.02, float(len(items)),
                       '%s：任务数' % labels.get(layer, layer),
                       C['reference'] if layer == 'base' else C['accent'])
        chart.bar_rect(centre + slot * 0.02, centre + slot * 0.24, float(sum(counts)),
                       '物理判据条目数（均值 %.1f / 任务）'
                       % (sum(counts) / max(1, len(counts))), C['truth'])
        chart.text(centre - slot * 0.13, float(len(items)) + top * 0.02, str(len(items)),
                   '#2b6b2b', 15, 'middle')
        chart.text(centre + slot * 0.13, float(sum(counts)) + top * 0.02, str(sum(counts)),
                   '#1f4f7a', 15, 'middle')
    for index, layer in enumerate(order):
        centre = (index + 0.5) * slot
        chart.text(centre, -top * 0.055, labels.get(layer, layer), C['text'], 15, 'middle')
    chart.save(os.path.join(FIGS, 'fig-task-layers.png'))
    return {layer: (len(items), sum(c for _t, c in items)) for layer, items in layers.items()}


def main():
    os.makedirs(FIGS, exist_ok=True)
    data = load()
    table = chart_discrimination(data)
    print('%-34s %-14s %-14s' % ('判据（单独把关）', '参考式通过', '错误式拦下'))
    for title, passed, total_ref, caught, total_wrong in table:
        print('%-34s %-14s %-14s' % (title, '%d/%d' % (passed, total_ref),
                                     '%d/%d' % (caught, total_wrong)))
    print('')
    print('error plane:', chart_error_plane(data))
    print('layers:', chart_layers(data))
    print('figures:', sorted(f for f in os.listdir(FIGS) if f.startswith('fig-')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
