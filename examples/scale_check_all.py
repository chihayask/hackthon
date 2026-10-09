# -*- coding: utf-8 -*-
# 尺度一致性检验的批量执行：金标准自检 + 判别力测试。
#
# 两种用法，都产出真实可归档的证据（runs/<run_id>/）：
#
#   1) 金标准自检（默认）
#      把每个任务的**参考公式**送进尺度检验。
#      期望：22/22 全部通过。若有参考公式过不了，说明规格写错了或任务本身有问题。
#
#   2) 判别力测试（--variants）
#      把每个任务上"物理上合理、结构错误"的候选式送进尺度检验。
#      期望：全部被否决。这是尺度检验作为独立判据的硬证据——
#      它**不需要拟合**，只看函数形式，因此在拟合失败之前就能拦下错误式。
#
# 注意：本脚本会读取 reference/，与 examples/reference_check.py 同等对待，
# 智能体在任何情况下都不得读取该目录。
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.evidence import write_evidence
from formula_agh.scale_checks import list_spec_task_ids, load_specs, run_scale_checks
from formula_agh.verify import VerifyError, load_task

TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
SPECS = os.path.join(ROOT, 'physics', 'scale_specs.json')
OUT = os.path.join(ROOT, 'runs')


def load_references():
    out = {}
    for name in sorted(os.listdir(REF)):
        if not name.endswith('.json'):
            continue
        with open(os.path.join(REF, name), encoding='utf-8') as fh:
            ref = json.load(fh)
        out[ref['task_id']] = ref
    return out


# 历史运行里没有单独归档、但已被文档与单元测试记录在案的错误候选式。
# 小角度近似是本项目最重要的一条对比（见 README.md 与
# tests/test_verify.py::test_small_angle_law_fails_at_large_amplitude）：
# 它在域内几乎看不出差别，却漏掉了振幅这个自变量。
EXTRA_VARIANTS = {
    'phys-pendulum-exact': {
        'formula': '2*pi*sqrt(L/g)',
        'origin_run': 'tests/test_verify.py::test_small_angle_law_fails_at_large_amplitude',
        'origin_verdict': 'rejected',
    },
}


def variant_formulas():
    # 从已被否决的历史运行里取回候选式。不重新编造——用的是真实跑过的式子。
    out = {}
    runs_dir = os.path.join(ROOT, 'runs')
    if not os.path.isdir(runs_dir):
        return out
    for name in sorted(os.listdir(runs_dir)):
        if not name.startswith('variant-'):
            continue
        result_path = os.path.join(runs_dir, name, 'result.json')
        if not os.path.exists(result_path):
            continue
        with open(result_path, encoding='utf-8') as fh:
            payload = json.load(fh)
        task_id = payload.get('task_id')
        formula = payload.get('formula')
        if task_id and formula:
            out[task_id] = {'formula': formula, 'origin_run': name,
                            'origin_verdict': payload.get('verdict')}
    for task_id, case in EXTRA_VARIANTS.items():
        out.setdefault(task_id, case)
    return out


def run_one(task_id, formula, params, specs, run_id, note):
    task_dir = os.path.join(TASKS, task_id)
    if not os.path.isdir(task_dir):
        return None, 'MISSING_TASK'
    columns, meta = load_task(task_dir)
    spec = (specs.get('tasks') or {}).get(task_id)
    if not spec:
        return None, 'MISSING_SPEC'
    try:
        report = run_scale_checks(task_id, formula, meta, spec, parameters=params)
    except VerifyError as exc:
        return None, 'ERROR: ' + str(exc)
    command = ('python -m formula_agh scale-check --task tasks/%s --formula %s'
               % (task_id, json.dumps(formula, ensure_ascii=False)))
    if params:
        command += ' --params ' + ','.join('%s=%r' % (k, v) for k, v in sorted(params.items()))
    command += ' --run-id ' + run_id
    write_evidence(os.path.join(OUT, run_id), report, command,
                   inputs=[task_dir, 'physics/scale_specs.json'], notes=note)
    return report, None


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--variants', action='store_true',
                        help='跑判别力测试（错误候选式），而不是金标准自检')
    parser.add_argument('--only', default='', help='只跑指定任务，逗号分隔')
    args = parser.parse_args(argv)

    specs = load_specs(SPECS)
    only = [x for x in args.only.split(',') if x]

    if args.variants:
        cases = variant_formulas()
        prefix = 'scale-variant-'
        kind = '判别力'
    else:
        cases = load_references()
        prefix = 'scale-ref-'
        kind = '金标准'

    rows = []
    ok = 0
    total = 0
    for task_id in list_spec_task_ids(specs):
        if only and task_id not in only:
            continue
        case = cases.get(task_id)
        if not case:
            rows.append((task_id, 'NO_CASE', '-', '-'))
            continue
        formula = case['formula']
        params = (case.get('true_constants') or None) if not args.variants else None
        if params is None:
            params = (specs['tasks'][task_id].get('nominal_parameters') or None)
        total += 1
        run_id = prefix + task_id
        report, err = run_one(task_id, formula, params, specs, run_id,
                              note='%s尺度检验：%s' % (kind, task_id))
        if report is None:
            rows.append((task_id, err, '-', formula))
            continue
        failed = [c.name for c in report.checks if not c.passed]
        if report.verdict == 'accepted':
            ok += 1
        rows.append((task_id, report.verdict,
                     '%d/%d' % (len(report.checks) - len(failed), len(report.checks)),
                     (','.join(failed) if failed else formula)[:60]))

    print('%-30s %-11s %-7s %s' % ('task', 'verdict', 'passed', 'detail'))
    for row in rows:
        print('%-30s %-11s %-7s %s' % row)
    print('')
    if args.variants:
        print('错误候选式被尺度检验否决: %d / %d' % (ok, total))
        print('（期望值 = 0，即全部被否决）')
    else:
        print('参考公式通过尺度检验: %d / %d' % (ok, total))
    return 0 if ((ok == total) != args.variants) else 1


if __name__ == '__main__':
    sys.exit(main())
