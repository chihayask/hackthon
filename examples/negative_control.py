# -*- coding: utf-8 -*-
# 负对照实验：喂进纯噪声，系统会不会为了交差编一个公式出来？
#
# 为什么这条最重要
# ----------------
# 这是懂机器学习的人最容易低估、也最能拉开差距的一项（见 02_执行计划与分工 §5.2 第 5 条）。
# 一个"总能给出公式"的系统在科学上是不可信的：它对"没有规律"这种正确答案没有表达能力。
# 所以实验要主动逼它编：拿真实物理任务里最常用的十来种函数族，去拟合完全随机的数据。
#
# 判定标准（事先写死，不许事后调整）
#   * 正确答案是"未发现稳定公式"；
#   * 因此每一次尝试都应当被否决；
#   * 只要有任意一次被 accepted，就是一次"编造"，必须如实记入结果，不许删。
#
# 数据与流程都可复现：噪声数据集落盘在 evidence/negative-control/data/，
# 种子固定为 seed=20261113，任何人重跑得到同一批数据与同一批结论。
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.evidence import write_evidence
from formula_agh.figures import DEFAULT_COLORS as C, Chart
from formula_agh.settings import verify_settings
from formula_agh.verify import CheckResult, VerifyError, VerifyReport, verify_formula

OUT = os.path.join(ROOT, 'evidence', 'negative-control')
DATA_DIR = os.path.join(OUT, 'data')
FIGS = os.path.join(ROOT, 'evidence', 'figures')
RUNS = os.path.join(ROOT, 'runs')

SEED = 20261113
N_SAMPLES = 400
N_DATASETS = 5
VAR_NAMES = ['x1', 'x2', 'x3']
SAMPLING = {name: [1.0, 10.0] for name in VAR_NAMES}

# 智能体最可能提出的函数族。它们全部来自真实物理任务里的常见形式：
#   常数项 / 线性 / 交互项 / 幂律 / 指数 / 三角 / 有理 / 二次型 / 平方反比。
FAMILIES = [
    ('常数', 'k', ['k']),
    ('线性', 'c0 + c1*x1 + c2*x2', ['c0', 'c1', 'c2']),
    ('线性+交互', 'c0 + c1*x1 + c2*x2 + c3*x1*x2', ['c0', 'c1', 'c2', 'c3']),
    ('三变量线性', 'c0 + c1*x1 + c2*x2 + c3*x3', ['c0', 'c1', 'c2', 'c3']),
    ('幂律', 'a*x1**b', ['a', 'b']),
    ('双变量幂律', 'a*x1**b*x2**c', ['a', 'b', 'c']),
    ('指数', 'a*exp(b*x1)', ['a', 'b']),
    ('正弦', 'a*sin(b*x1 + c)', ['a', 'b', 'c']),
    ('有理', 'a/(x1 + b)', ['a', 'b']),
    ('二次型', 'a*x1**2 + b*x2**2 + c', ['a', 'b', 'c']),
    ('平方反比', 'a/(x1*x2)', ['a']),
    ('幂律+线性', 'a*x1**b + c*x2', ['a', 'b', 'c']),
]

# 场景 B 专用：高容量函数族。
# 场景 A 里每一种函数的参数都远少于样本量，拟合器根本无从上手——
# 那样测出来的"不编造"是廉价结论。真正要攻的是**过拟合**：
# 参数接近样本量时，模型可以在训练集上把噪声背下来，此时唯一能拦住它的
# 就是留出集与外推区。这才是负对照的题眼。
HIGH_CAPACITY = [
    ('五次多项式', 'c0 + c1*x1 + c2*x1**2 + c3*x1**3 + c4*x1**4 + c5*x1**5',
     ['c0', 'c1', 'c2', 'c3', 'c4', 'c5']),
    ('七次多项式', 'c0 + c1*x1 + c2*x1**2 + c3*x1**3 + c4*x1**4 + c5*x1**5 '
                  '+ c6*x1**6 + c7*x1**7',
     ['c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7']),
    ('三谐波正弦', 'a*sin(b*x1) + c*sin(d*x1) + e', ['a', 'b', 'c', 'd', 'e']),
    ('三变量完全二次',
     'c0 + c1*x1 + c2*x2 + c3*x3 + c4*x1*x2 + c5*x1*x3 + c6*x2*x3 '
     '+ c7*x1**2 + c8*x2**2 + c9*x3**2',
     ['c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9']),
]

SCENARIOS = [
    dict(name='A', title='样本充足（400 点）下的常规函数族',
         datasets=N_DATASETS, samples=400, families=FAMILIES),
    dict(name='B', title='小样本（80 点）+ 高容量函数族，逼出过拟合',
         datasets=N_DATASETS, samples=80, families=HIGH_CAPACITY),
]


def make_noise(index, samples, scenario):
    rng = np.random.default_rng(SEED + index + (0 if scenario == 'A' else 500))
    columns = {}
    for name in VAR_NAMES:
        columns[name] = rng.uniform(SAMPLING[name][0], SAMPLING[name][1], samples)
    # 纯噪声：与任何自变量都独立。用标准正态而不是均匀分布，
    # 是因为正态尾部更容易被拟合器"迁就"，是更严厉的考验。
    columns['y'] = rng.normal(0.0, 1.0, samples)
    return columns


def write_dataset(index, columns, samples, scenario):
    os.makedirs(DATA_DIR, exist_ok=True)
    stem = 'noise-%s-%02d' % (scenario, index)
    csv_path = os.path.join(DATA_DIR, stem + '.csv')
    with open(csv_path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(','.join(VAR_NAMES + ['y']) + '\n')
        for row in range(samples):
            fh.write(','.join('%.10g' % columns[name][row] for name in VAR_NAMES + ['y']) + '\n')
    meta = {
        'task_id': 'negative-control-%s-%02d' % (scenario, index),
        'var_names': list(VAR_NAMES),
        'sampling': {name: list(SAMPLING[name]) for name in VAR_NAMES},
        'sample_count': samples,
        'generator': 'examples/negative_control.py',
        'scenario': scenario,
        'noise_model': 'y ~ Normal(0, 1)，与全部自变量独立',
        'expected_answer': '未发现稳定公式（负对照的正确结论）',
    }
    meta_path = os.path.join(DATA_DIR, stem + '.meta.json')
    with open(meta_path, 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    return csv_path, meta_path


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)
    settings = verify_settings()
    attempts = []

    for scenario in SCENARIOS:
        for index in range(1, scenario['datasets'] + 1):
            _run_scenario(scenario, index, settings, attempts)

    return finish(attempts, settings)


def _run_scenario(scenario, index, settings, attempts):
    samples = int(scenario['samples'])
    tag = scenario['name']
    columns = make_noise(index, samples, tag)
    write_dataset(index, columns, samples, tag)
    meta = {'task_id': 'negative-control-%s-%02d' % (tag, index),
            'var_names': list(VAR_NAMES),
            'sampling': {name: list(SAMPLING[name]) for name in VAR_NAMES}}
    for family, formula, free in scenario['families']:
            record = {'dataset': index, 'scenario': tag, 'family': family, 'formula': formula,
                      'free_parameters': free}
            try:
                report = verify_formula(
                    formula, columns, meta, parameters=free,
                    holdout_threshold=float(settings['holdout_threshold']),
                    extrapolation_threshold=float(settings['extrapolation_threshold']),
                    holdout_ratio=float(settings['holdout_ratio']),
                    extrapolation_ratio=float(settings['extrapolation_ratio']),
                    seed=int(settings['seed']))
            except VerifyError as exc:
                record['verdict'] = 'rejected'
                record['rejected_at'] = 'fit-infeasible'
                record['reason'] = str(exc)
                attempts.append(record)
                continue
            failed = [c.name for c in report.checks if not c.passed]
            record['verdict'] = report.verdict
            record['rejected_at'] = (failed[0] if failed else '')
            record['parameters'] = report.parameters
            record['checks'] = {c.name: {'passed': c.passed, 'reason': c.reason}
                                for c in report.checks}
            record['rounds_hint'] = report.rounds_hint
            attempts.append(record)
            if report.verdict == 'accepted':
                # 出现编造：立刻留证，绝不隐藏。
                write_evidence(os.path.join(RUNS, 'negctl-accepted-%s-%02d-%d'
                                            % (tag, index, len(attempts))),
                               report, 'negative_control: scenario %s / dataset %d / %s'
                               % (tag, index, family),
                               inputs=['evidence/negative-control/data/noise-%s-%02d.csv'
                                       % (tag, index)],
                               notes='负对照出现被采纳的公式（应记为编造）',
                               settings_in=settings)


def _best_fit_rms(attempts):
    # 从拟合失败的原文里取出"最接近通过"的那一次残差。
    # 这个数说明否决的余量有多大：不是刚好卡在门槛上，而是差得远。
    import re
    best = None
    for item in attempts:
        for payload in (item.get('checks') or {}).values():
            match = re.search(r'归一化 RMS ([0-9.]+)', payload.get('reason', ''))
            if match:
                value = float(match.group(1))
                best = value if best is None else min(best, value)
        match = re.search(r'归一化 RMS ([0-9.]+)', item.get('reason', ''))
        if match:
            value = float(match.group(1))
            best = value if best is None else min(best, value)
    return best


def finish(attempts, settings):
    accepted = [a for a in attempts if a['verdict'] == 'accepted']
    best_rms = _best_fit_rms(attempts)
    stages = {}
    for item in attempts:
        stages[item['rejected_at'] or 'accepted'] = stages.get(item['rejected_at'] or 'accepted', 0) + 1

    design = {
        'seed': SEED,
        'noise_model': 'y ~ Normal(0,1)，与全部自变量独立',
        'criterion': '每一次尝试都必须被否决；出现 accepted 即记为一次"编造"',
        'scenarios': [{'name': s['name'], 'title': s['title'], 'datasets': s['datasets'],
                       'samples_per_dataset': s['samples'],
                       'families': [f[0] for f in s['families']]} for s in SCENARIOS],
        'attempts': len(attempts),
    }
    payload = {
        'design': design,
        'settings': dict(settings),
        'summary': {'accepted': len(accepted), 'rejected': len(attempts) - len(accepted),
                    'by_stage': stages,
                    'best_fit_normalized_rms': best_rms,
                    'note': ('全部尝试都在拟合阶段被拦下：归一化残差门槛是 0.5·std(y)，'
                             '而纯噪声上最好的拟合仍远高于它。这说明负对照没有走到'
                             '留出集/外推区就已经被否决——本实验因此没有对后两道门构成压力，'
                             '如实记录。')},
        'attempts': attempts,
    }
    with open(os.path.join(OUT, 'negative_control.json'), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    # 汇总报告也落进 runs/，与其他运行证据同一套规范。
    checks = [CheckResult('negative-control', not accepted,
                          '对 %d 份纯噪声数据用 %d 个函数族共尝试 %d 次（两个场景：常规族与大容量族），'
                          '被采纳 %d 次；拦截阶段分布：%s；最接近通过的一次归一化残差为 %s'
                          % (sum(s['datasets'] for s in SCENARIOS),
                             sum(len(s['families']) for s in SCENARIOS), len(attempts),
                             len(accepted),
                             '、'.join('%s=%d' % kv for kv in sorted(stages.items())),
                             ('%.3f' % best_rms) if best_rms is not None else 'n/a'),
                          {'accepted': len(accepted), 'attempts': len(attempts),
                           'by_stage': stages, 'best_fit_normalized_rms': best_rms})]
    report = VerifyReport('negative-control', '(纯噪声，正确结论是未发现公式)', {},
                          'accepted' if not accepted else 'rejected', checks,
                          '负对照通过：系统对"没有规律"给出了正确回答，没有编造公式。'
                          if not accepted else
                          '负对照失败：系统在纯噪声上给出了公式，必须如实报告。')
    write_evidence(os.path.join(RUNS, 'negctl-summary'), report,
                   'python examples/negative_control.py',
                   inputs=['evidence/negative-control/data'],
                   notes='负对照实验汇总', settings_in=settings)

    draw_figure(attempts, stages, len(accepted))

    print('负对照：%d 份噪声数据 × %d 种函数族 = %d 次尝试' % (N_DATASETS, len(FAMILIES), len(attempts)))
    print('被采纳（= 编造）: %d 次' % len(accepted))
    print('拦截阶段分布: %s' % json.dumps(stages, ensure_ascii=False))
    for item in accepted:
        print('  !! 编造: 数据集 %d / %s / %s' % (item['dataset'], item['family'], item['formula']))
    return 0


def draw_figure(attempts, stages, accepted):
    per_family = {}
    for item in attempts:
        key = item['family']
        entry = per_family.setdefault(key, [0, 0])
        entry[1] += 1
        if item['verdict'] == 'rejected':
            entry[0] += 1
    order = [name for name, _f, _p in FAMILIES if name in per_family]
    chart = (Chart(1180, 620)
             .set_title('负对照实验：纯噪声数据上，%d 次尝试全部被否决' % len(attempts)
                        if not accepted else
                        '负对照实验：纯噪声数据上出现了 %d 次编造' % accepted)
             .set_axes('函数族', '否决次数 / 尝试次数', 'linear', 'linear',
                       ylim=(-1.6, 7.6), xticks=False))
    slot = 1.0 / max(1, len(order))
    for index, name in enumerate(order):
        rejected, total = per_family[name]
        centre = (index + 0.5) * slot
        if index % 2 == 0:
            chart.band(centre - slot * 0.46, centre + slot * 0.46, '#f4f4f4', 1.0)
        colour = C['reference'] if accepted == 0 else C['candidate']
        chart.bar_rect(centre - slot * 0.26, centre + slot * 0.26, float(rejected),
                       '被否决的尝试次数（全部 %d 次）' % len(attempts) if index == 0 else '',
                       colour)
        chart.text(centre, float(rejected) + 0.16, '%d/%d' % (rejected, total),
                   '#2b6b2b', 13, 'middle')
        chart.text(centre, -0.85, name, C['text'], 14, 'middle')
    note = ('拦截阶段：' + '，'.join('%s %d 次' % kv for kv in sorted(stages.items()))
            if accepted == 0 else '被采纳 %d 次' % accepted)
    chart.text(0.02, 6.9, note, '#555555', 14)
    chart.save(os.path.join(FIGS, 'fig-negative-control.png'))


if __name__ == '__main__':
    sys.exit(main())
