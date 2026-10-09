# -*- coding: utf-8 -*-
# 判别力验证：为每个任务生成'物理上合理但结构错误'的候选，确认验证引擎把它们全部拒绝。
# 这是任务集与验证器的联合金标准证据：正确式必须过，错误式必须不过。
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

# task_id -> 结构错误的候选式（保留正确的自由参数名）
VARIANTS = {
    'phys-gravitation': 'G*m1*m2/r',
    'phys-coulomb': 'k*q1*q2/r',
    'phys-ideal-gas': 'R*n*T',
    'phys-kinetic-energy': 'm*v/2',
    'phys-spring-energy': 'k*x/2',
    'phys-pendulum-period': '2*pi*L/g',
    'phys-ohm': 'I/R',
    'phys-joule-heating': 'I*R',
    'phys-surface-gravity': 'G*M/R',
    'phys-stefan-boltzmann': 'sigma*A*T**2',
    'phys-buoyancy': 'rho*V',
    'phys-weight': 'm/g',
    'phys-grav-potential-energy': '-G*m1*m2/r**2',
    'phys-elastic-pe': 'c*x/2',
    # 注意：'(A-B)*h' 与正确式只差参数倍率，拟合后可完全等价，属不可区分，故不用它
    'phys-energy-shift': 'A*B/h',
    'phys-cyclotron': 'q*B*m',
    'phys-snells-law': 'd*sin(theta2)*n',
    'phys-radioactive-decay': 'N0*(1-t/tau)',
    'phys-hydrogen-level': '-me*el**4/(2*(4*pi*eps0)**2*hbar**2*n)',
    'phys-transit-depth': 'A*(Rp/Rs)',
    'phys-index-vacuum': 'eps*mu',
    # 本项目最有说服力的一类"错误"：小角度近似。它在任何单点上都不荒谬，
    # 但在大摆角处系统性偏离——正是外推区要抓的东西。
    'phys-pendulum-exact': '2*pi*sqrt(L/g)',
}


def main():
    rows = []
    ok = 0
    total = 0
    for task_id, wrong in sorted(VARIANTS.items()):
        task_dir = os.path.join(TASKS, task_id)
        with open(os.path.join(REF, task_id + '.json'), encoding='utf-8') as fh:
            ref = json.load(fh)
        params = ref.get('free_parameters') or []
        columns, meta = load_task(task_dir)
        total += 1
        try:
            report = verify_formula(
                wrong, columns, meta, parameters=params,
                holdout_threshold=SETTINGS['holdout_threshold'],
                extrapolation_threshold=SETTINGS['extrapolation_threshold'],
                holdout_ratio=SETTINGS['holdout_ratio'],
                extrapolation_ratio=SETTINGS['extrapolation_ratio'],
                seed=SETTINGS['seed'],
                dimension_check=SETTINGS['dimension_check'],
                scale_check=SETTINGS['scale_check'],
                fit_max_residual=SETTINGS['fit_max_residual'])
        except Exception as exc:
            rows.append((task_id, 'ERROR', str(exc)[:40]))
            continue
        failed = ','.join(c.name for c in report.checks if not c.passed) or '-'
        rows.append((task_id, report.verdict, failed))
        if report.verdict == 'rejected':
            ok += 1
        write_evidence(os.path.join(OUT, 'variant-' + task_id), report,
                       'python examples/variant_check.py  # task=' + task_id,
                       inputs=[task_dir], settings_in=SETTINGS,
                       hypothesis_source="fixture-variant",
                       notes=('判别力：物理上合理但结构错误的候选式 '
                              + json.dumps(wrong, ensure_ascii=False) + '；期望 rejected'))
    print('%-30s %-10s %s' % ('task', 'verdict', 'failed_checks'))
    for r in rows:
        print('%-30s %-10s %s' % r)
    print('')
    print('wrong variants rejected: %d / %d' % (ok, total))
    return 0 if ok == total else 1


if __name__ == '__main__':
    sys.exit(main())