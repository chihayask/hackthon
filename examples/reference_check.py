# -*- coding: utf-8 -*-
# 基准自检：把每个任务的参考公式送回验证引擎，确认任务集是可解的。
# 这是任务集的金标准证据：如果参考公式都过不了，说明任务本身有问题。
# 注意：本脚本会读取 reference/，而 AGH 智能体在任何情况下都不得读取该目录。
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.verify import load_task, verify_formula
from formula_agh.evidence import write_evidence
from formula_agh.settings import verify_settings

SETTINGS = verify_settings()

TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
OUT = os.path.join(ROOT, 'runs')


def main():
    rows = []
    accepted = 0
    total = 0
    for name in sorted(os.listdir(REF)):
        if not name.endswith('.json'):
            continue
        with open(os.path.join(REF, name), encoding='utf-8') as fh:
            ref = json.load(fh)
        task_id = ref['task_id']
        task_dir = os.path.join(TASKS, task_id)
        if not os.path.isdir(task_dir):
            rows.append((task_id, 'MISSING_TASK', '-', '-'))
            continue
        columns, meta = load_task(task_dir)
        params = ref.get('free_parameters') or []
        total += 1
        try:
            report = verify_formula(
                ref['formula'], columns, meta, parameters=params,
                holdout_threshold=SETTINGS['holdout_threshold'],
                extrapolation_threshold=SETTINGS['extrapolation_threshold'],
                holdout_ratio=SETTINGS['holdout_ratio'],
                extrapolation_ratio=SETTINGS['extrapolation_ratio'],
                seed=SETTINGS['seed'],
                dimension_check=SETTINGS['dimension_check'],
                scale_check=SETTINGS['scale_check'],
                fit_max_residual=SETTINGS['fit_max_residual'])
        except Exception as exc:
            rows.append((task_id, 'ERROR', str(exc)[:50], '-'))
            continue
        if report.verdict == 'accepted':
            accepted += 1
        hold = [c for c in report.checks if c.name == 'holdout']
        ext = [c for c in report.checks if c.name == 'extrapolation']
        hv = '%.4f' % hold[0].metrics.get('relative_rmse', -1) if hold else '-'
        ev = '%.4f' % ext[0].metrics.get('relative_rmse', -1) if ext else '-'
        rows.append((task_id, report.verdict, hv, ev))
        # 无论通过与否都留证：通过的那 22 条同样是"判据没有误杀正确答案"的证据，
        # 只留失败会使证据包出现无法核对的空洞（M2 修正）。
        write_evidence(
            os.path.join(OUT, 'refcheck-' + task_id), report,
            'python examples/reference_check.py  # task=' + task_id, inputs=[task_dir],
            settings_in=SETTINGS, hypothesis_source="reference",
            notes=('金标准自检：把标准答案原样送入验证引擎；期望 accepted。'
                   '参考公式来自 reference/' + task_id + '.json（评分侧文件，智能体不可读）'))
    print('%-30s %-10s %-9s %-9s' % ('task', 'verdict', 'holdout', 'extrap'))
    print('（相对误差口径：RMSE / 中位|y|；阈值见 config/agent.yaml）')
    for r in rows:
        print('%-30s %-10s %-9s %-9s' % r)
    print('')
    print('reference formulas accepted: %d / %d' % (accepted, total))
    return 0 if accepted == total else 1


if __name__ == '__main__':
    sys.exit(main())