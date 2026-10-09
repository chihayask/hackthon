# -*- coding: utf-8 -*-
# 判别力对照表：把"三重验证 + 尺度检验"在同一批公式上的表现摊开算清楚。
#
# 对每个任务跑两个方向：
#   参考式（物理上正确的那个）——应当全部通过；
#   错误式（物理上合理、结构错误）——应当全部被拒绝。
# 逐项统计每个判据各自拦下了多少，才能回答"验证做得够不够硬"。
#
# 输出：
#   evidence/discrimination.json   机器可读的完整数据
#   runs/discrim-{ref,wrong}-<task>/  每次判定的完整证据（含 checks/*.json）
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.evidence import write_evidence
from formula_agh.scale_checks import load_specs, run_scale_checks
from formula_agh.settings import verify_settings
from formula_agh.verify import VerifyError, load_task, verify_formula

TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
SPECS = os.path.join(ROOT, 'physics', 'scale_specs.json')
OUT = os.path.join(ROOT, 'runs')
EVIDENCE = os.path.join(ROOT, 'evidence')

# 与 examples/scale_check_all.py 保持同一份错误式来源：真实跑过的候选式。
EXTRA_WRONG = {
    'phys-pendulum-exact': '2*pi*sqrt(L/g)',
}


def load_references():
    out = {}
    for name in sorted(os.listdir(REF)):
        if name.endswith('.json'):
            with open(os.path.join(REF, name), encoding='utf-8') as fh:
                ref = json.load(fh)
            out[ref['task_id']] = ref
    return out


def load_wrong():
    out = {}
    runs_dir = os.path.join(ROOT, 'runs')
    for name in sorted(os.listdir(runs_dir)):
        if not name.startswith('variant-'):
            continue
        path = os.path.join(runs_dir, name, 'result.json')
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as fh:
            payload = json.load(fh)
        if payload.get('task_id') and payload.get('formula'):
            out[payload['task_id']] = payload['formula']
    for task_id, formula in EXTRA_WRONG.items():
        out.setdefault(task_id, formula)
    return out


def evaluate(task_id, formula, params, specs, settings=None):
    # 阈值一律取自 config/agent.yaml（经 settings.verify_settings），
    # 绝不使用 verify_formula 的函数默认值——否则拿到的判定与正式运行不一致。
    settings = settings or verify_settings()
    task_dir = os.path.join(TASKS, task_id)
    columns, meta = load_task(task_dir)
    record = {'task_id': task_id, 'formula': formula, 'triple': None, 'scale': None,
              'settings': dict(settings)}
    try:
        # 走与 CLI 完全相同的开关：dimension_check / scale_check 都从 config 来。
        # 注意 verify_formula 的 scale_check 默认值是 False（纯引擎原语不读配置），
        # 直接调用它会**静默地少一道门**——这一点写进了 evidence/交叉评审发现.md。
        report = verify_formula(
            formula, columns, meta, parameters=params,
            holdout_threshold=float(settings['holdout_threshold']),
            extrapolation_threshold=float(settings['extrapolation_threshold']),
            holdout_ratio=float(settings['holdout_ratio']),
            extrapolation_ratio=float(settings['extrapolation_ratio']),
            seed=int(settings['seed']),
            dimension_check=bool(settings['dimension_check']),
            scale_check=bool(settings['scale_check']))
        record['triple'] = {
            'verdict': report.verdict,
            'parameters': report.parameters,
            'checks': {c.name: {'passed': c.passed, 'reason': c.reason,
                                'metrics': c.metrics} for c in report.checks},
        }
    except VerifyError as exc:
        record['triple'] = {'verdict': 'error', 'parameters': {},
                            'checks': {}, 'error': str(exc)}
    spec = (specs.get('tasks') or {}).get(task_id)
    if spec:
        nominal = dict(spec.get('nominal_parameters') or {})
        try:
            scale_report = run_scale_checks(task_id, formula, meta, spec, parameters=nominal)
            record['scale'] = {
                'verdict': scale_report.verdict,
                'checks': {c.name: {'passed': c.passed, 'reason': c.reason,
                                    'metrics': c.metrics} for c in scale_report.checks},
            }
        except VerifyError as exc:
            record['scale'] = {'verdict': 'error', 'checks': {}, 'error': str(exc)}
    return record


def summarize(records):
    # 逐判据统计：参考式里"通过"的比例、错误式里"被拦下"的比例。
    buckets = {}

    def bucket(name):
        return buckets.setdefault(name, {'pass_on_ref': 0, 'ref_total': 0,
                                         'fail_on_wrong': 0, 'wrong_total': 0})

    def add(prefix, record, expect_pass):
        triple = record.get('triple') or {}
        checks = triple.get('checks') or {}
        for name in ('dimension', 'holdout', 'extrapolation', 'fit', 'expression'):
            if name not in checks:
                continue
            key = prefix + ':' + name
            entry = bucket(key)
            if expect_pass:
                entry['ref_total'] += 1
                if checks[name]['passed']:
                    entry['pass_on_ref'] += 1
            else:
                entry['wrong_total'] += 1
                if not checks[name]['passed']:
                    entry['fail_on_wrong'] += 1
        scale = record.get('scale') or {}
        for name, payload in (scale.get('checks') or {}).items():
            kind = name.split('-')[1] if name.count('-') >= 1 else name
            key = prefix + ':scale:' + kind
            entry = bucket(key)
            if expect_pass:
                entry['ref_total'] += 1
                if payload['passed']:
                    entry['pass_on_ref'] += 1
            else:
                entry['wrong_total'] += 1
                if not payload['passed']:
                    entry['fail_on_wrong'] += 1
        # 整条流水线的语义是"所有判据都通过才算采纳"（AND 门）。
        # 因此一个错误式只要被任意一道门拦下，就算被抓住了。
        verdict_key = prefix + ':verdict'
        entry = bucket(verdict_key)
        caught = (triple.get('verdict') != 'accepted') or (scale.get('verdict') == 'rejected')
        if expect_pass:
            entry['ref_total'] += 1
            if not caught:
                entry['pass_on_ref'] += 1
        else:
            entry['wrong_total'] += 1
            if caught:
                entry['fail_on_wrong'] += 1
        # 再单独记一列：只看三项数值判据（不含尺度检验）时能抓住多少。
        # 直接从同一份报告的逐项结果里推导，不需要重跑——
        # 报告里同时含数值判据与 scale-* 判据，把后者摘掉就是"三重验证单独把关"。
        numeric_only_ok = True
        for name, payload in checks.items():
            if name.startswith('scale-'):
                continue
            if not payload['passed']:
                numeric_only_ok = False
                break
        if not checks:
            numeric_only_ok = triple.get('verdict') == 'accepted'
        gap_key = prefix + ':verdict-numeric-only'
        gap_entry = bucket(gap_key)
        if expect_pass:
            gap_entry['ref_total'] += 1
            if numeric_only_ok:
                gap_entry['pass_on_ref'] += 1
        else:
            gap_entry['wrong_total'] += 1
            if not numeric_only_ok:
                gap_entry['fail_on_wrong'] += 1
        # 以及：三项数值判据放过了、但尺度检验拦下多少（尺度检验的增量价值）。
        scale_only_key = prefix + ':caught-by-scale-only'
        scale_only_entry = bucket(scale_only_key)
        if not expect_pass:
            scale_only_entry['wrong_total'] += 1
            if numeric_only_ok and scale.get('verdict') == 'rejected':
                scale_only_entry['fail_on_wrong'] += 1
            elif numeric_only_ok and not any(
                    n.startswith('scale-') for n in checks):
                scale_only_entry['fail_on_wrong'] += 1

    for record in records['reference']:
        add('ref', record, True)
    for record in records['wrong']:
        add('wrong', record, False)
    return buckets


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    specs = load_specs(SPECS)
    cache = os.path.join(EVIDENCE, 'discrimination.json')
    if '--resummarize' in argv and os.path.exists(cache):
        # 只重算汇总，不重跑拟合：判定结果没变，变的是统计口径。
        with open(cache, encoding='utf-8') as fh:
            records = json.load(fh)['records']
        return report(records)

    references = load_references()
    wrong = load_wrong()
    settings = verify_settings()
    print('生效阈值:', json.dumps(settings, ensure_ascii=False))

    records = {'reference': [], 'wrong': [], 'settings': dict(settings)}
    for task_id in sorted(references):
        ref = references[task_id]
        record = evaluate(task_id, ref['formula'], ref.get('free_parameters') or [], specs,
                          settings)
        record['role'] = 'reference'
        records['reference'].append(record)
        write_evidence(os.path.join(OUT, 'discrim-ref-' + task_id),
                       _as_report(record), 'discrimination: reference ' + task_id,
                       inputs=['tasks/' + task_id], notes='判别力对照：参考式',
                       settings_in=settings)
        print('ref   %-30s %s' % (task_id, record['triple']['verdict']))

    for task_id in sorted(wrong):
        record = evaluate(task_id, wrong[task_id], [], specs, settings)
        record['role'] = 'wrong'
        records['wrong'].append(record)
        write_evidence(os.path.join(OUT, 'discrim-wrong-' + task_id),
                       _as_report(record), 'discrimination: wrong ' + task_id,
                       inputs=['tasks/' + task_id], notes='判别力对照：错误式',
                       settings_in=settings)
        print('wrong %-30s %s' % (task_id, record['triple']['verdict']))

    return report(records)


def report(records):
    buckets = summarize(records)
    payload = {
        'note': ('判别力对照：同一批任务上，参考式与结构错误式的判定结果。'
                 '采纳语义是"所有判据都通过才采纳"，因此错误式被任意一道门拦下即记为被抓住。'),
        'reference_count': len(records['reference']),
        'wrong_count': len(records['wrong']),
        'buckets': buckets,
        'records': records,
    }
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(os.path.join(EVIDENCE, 'discrimination.json'), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print('')
    print('%-34s %-14s %-14s' % ('判据', '参考式通过', '错误式拦下'))
    for key in sorted(buckets):
        entry = buckets[key]
        print('%-34s %-14s %-14s' % (
            key,
            '%d/%d' % (entry['pass_on_ref'], entry['ref_total']) if entry['ref_total'] else '-',
            '%d/%d' % (entry['fail_on_wrong'], entry['wrong_total']) if entry['wrong_total'] else '-'))
    return 0


def _as_report(record):
    # 把对照记录包装成 evidence.write_evidence 需要的报告对象。
    from formula_agh.verify import CheckResult, VerifyReport
    triple = record.get('triple') or {}
    checks = []
    for name, payload in (triple.get('checks') or {}).items():
        checks.append(CheckResult(name, bool(payload['passed']), payload['reason'],
                                  payload.get('metrics') or {}))
    scale = record.get('scale') or {}
    for name, payload in (scale.get('checks') or {}).items():
        checks.append(CheckResult(name, bool(payload['passed']), payload['reason'],
                                  payload.get('metrics') or {}))
    if not checks:
        checks.append(CheckResult('input', False, (triple.get('error') or 'no checks')))
    verdict = 'accepted' if (triple.get('verdict') == 'accepted') else 'rejected'
    return VerifyReport(record['task_id'], record['formula'],
                        triple.get('parameters') or {}, verdict, checks,
                        '判别力对照记录（三重验证 + 尺度检验）')


if __name__ == '__main__':
    sys.exit(main())
