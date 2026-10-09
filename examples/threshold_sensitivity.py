# -*- coding: utf-8 -*-
# 阈值敏感性：判据的判别力是不是"调出来的"？
#
# 动机（这是一次交叉评审发现的真问题）
# ------------------------------------
# 尺度检验在 22 个结构错误式上单独表现很好，但用**当前生效阈值**跑三重验证时，
# 三重验证自己就能拦下全部 22 个——也就是说在这批用例上尺度检验的增量是 0。
# 那么尺度检验到底值不值得做？答案取决于一个更严的问题：
#   **换一组阈值（口径），三重验证还能不能全拦住？**
# 如果它只在某一组精心调过的阈值下才成立，那"判别力"就是调参调出来的。
#
# 本脚本不重新拟合，只用 evidence/discrimination.json 里已经记录下来的
# 逐项指标重算判定（留出集、外推区、量纲三项都与阈值线性可分），
# 因此结论是精确的、可复算的，而不是又一次实验噪声。
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.settings import verify_settings

EVIDENCE = os.path.join(ROOT, 'evidence')
DATA = os.path.join(EVIDENCE, 'discrimination.json')

# 逐个判据的"判定值"在 metrics 里的键；口径调整时这里跟着改，脚本体不用动。
CRITERION_KEYS = {
    'relative_error_median': 'relative_error_median',
    'relative_rmse': 'relative_rmse',
    'normalized_rmse': 'normalized_rmse',
}

GRID = [
    ('当前生效（严）', None, None),
    ('中等', 0.05, 0.10),
    ('宽松（历史默认）', 0.08, 0.15),
    ('很宽松', 0.15, 0.30),
]


def check_value(record, name):
    check = ((record.get('triple') or {}).get('checks') or {}).get(name)
    if not check:
        return None, False
    metrics = check.get('metrics') or {}
    for key in CRITERION_KEYS.values():
        if key in metrics:
            return float(metrics[key]), bool(check['passed'])
    return None, bool(check['passed'])


def verdict_at(record, holdout_t, ext_t):
    # 只在"三重验证"这一层重算：拟合/语法失败与阈值无关，直接沿用。
    triple = record.get('triple') or {}
    checks = triple.get('checks') or {}
    for name in ('expression', 'fit'):
        if name in checks and not checks[name]['passed']:
            return 'rejected', name
    for name, threshold in (('dimension', None), ('holdout', holdout_t),
                            ('extrapolation', ext_t)):
        if name not in checks:
            continue
        check = checks[name]
        if threshold is None:
            if not check['passed']:
                return 'rejected', name
            continue
        value, _passed = check_value(record, name)
        if value is None:
            if not check['passed']:
                return 'rejected', name
            continue
        if value > threshold:
            return 'rejected', name
    return 'accepted', ''


def scale_rejects(record):
    return (record.get('scale') or {}).get('verdict') == 'rejected'


def main():
    with open(DATA, encoding='utf-8') as fh:
        data = json.load(fh)
    refs = data['records']['reference']
    wrongs = data['records']['wrong']
    settings = verify_settings()

    rows = []
    for title, h_t, e_t in GRID:
        if h_t is None:
            h_t = float(settings['holdout_threshold'])
            e_t = float(settings['extrapolation_threshold'])
        triple_caught = 0
        scale_only = 0
        ref_false_alarm = 0
        for record in wrongs:
            verdict, _stage = verdict_at(record, h_t, e_t)
            if verdict == 'rejected':
                triple_caught += 1
            elif scale_rejects(record):
                scale_only += 1
        for record in refs:
            verdict, _stage = verdict_at(record, h_t, e_t)
            if verdict != 'accepted':
                ref_false_alarm += 1
        rows.append({'thresholds': title, 'holdout': h_t, 'extrapolation': e_t,
                     'wrong_total': len(wrongs),
                     'triple_caught': triple_caught,
                     'caught_only_by_scale': scale_only,
                     'pipeline_caught': triple_caught + scale_only,
                     'reference_false_alarm': ref_false_alarm})

    print('%-18s %-9s %-9s %-16s %-16s %-16s %s'
          % ('阈值设定', '留出集', '外推区', '三重验证拦下', '仅尺度检验拦下', '合计拦下', '参考式误杀'))
    for row in rows:
        print('%-18s %-9.3g %-9.3g %-16s %-16s %-16s %d'
              % (row['thresholds'], row['holdout'], row['extrapolation'],
                 '%d/%d' % (row['triple_caught'], row['wrong_total']),
                 '%d/%d' % (row['caught_only_by_scale'], row['wrong_total']),
                 '%d/%d' % (row['pipeline_caught'], row['wrong_total']),
                 row['reference_false_alarm']))

    payload = {
        'note': ('阈值敏感性：用已记录的逐项指标重算不同阈值下的判定，'
                 '回答"判别力是不是调出来的"。不重新拟合，结论可精确复算。'),
        'current_settings': dict(settings),
        'rows': rows,
    }
    with open(os.path.join(EVIDENCE, 'threshold_sensitivity.json'), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print('')
    print('wrote evidence/threshold_sensitivity.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
