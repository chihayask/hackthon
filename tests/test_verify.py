# -*- coding: utf-8 -*-
# 自测：验证引擎必须在真实物理任务上区分「真发现」与「看似拟合」
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.safe_eval import UnsafeExpression, compile_formula, is_safe
from formula_agh.units import DimensionError, infer_from_source, unit_dimension
from formula_agh.verify import load_task, verify_formula

TASKS = os.path.join(ROOT, 'tasks')


def _task(name):
    return load_task(os.path.join(TASKS, name))


def test_ast_whitelist_blocks_dangerous_input():
    assert is_safe('a*b', ['a', 'b'])
    assert not is_safe('__import__(1)', ['a'])
    assert not is_safe('open(1)', ['a'])
    assert not is_safe('a if a else a', ['a'])
    with pytest.raises(UnsafeExpression):
        compile_formula('[1, 2]', [])


def test_units_inference():
    dim = infer_from_source('m1*m2/r**2', {'m1': 'kg', 'm2': 'kg', 'r': 'm'})
    assert dim != unit_dimension('N')
    with pytest.raises(DimensionError):
        infer_from_source('m1 + r', {'m1': 'kg', 'r': 'm'})
    with pytest.raises(DimensionError):
        infer_from_source('sin(m1)', {'m1': 'kg'})


def test_gravitation_correct_formula_accepted():
    columns, meta = _task('phys-gravitation')
    report = verify_formula('G*m1*m2/r**2', columns, meta, parameters=['G'])
    checks = {c.name: c for c in report.checks}
    assert report.verdict == 'accepted', report.to_json()
    assert checks['holdout'].passed and checks['extrapolation'].passed
    assert report.parameters['G'] == pytest.approx(6.674e-11, rel=0.05)


def test_gravitation_wrong_power_shows_worse_extrapolation():
    # 错误幂次在留出集与外推区都失败，且外推区误差与留出集同量级——
    # 说明模型是整体性错误，而不是只在边界失灵。
    columns, meta = _task('phys-gravitation')
    correct = verify_formula('G*m1*m2/r**2', columns, meta, parameters=['G'])
    wrong = verify_formula('G*m1*m2/r', columns, meta, parameters=['G'])
    c_checks = {c.name: c for c in correct.checks}
    w_checks = {c.name: c for c in wrong.checks}
    assert correct.verdict == 'accepted'
    assert wrong.verdict == 'rejected'
    assert w_checks['extrapolation'].metrics['normalized_rmse'] > 10 * c_checks['extrapolation'].metrics['normalized_rmse']


def test_small_angle_law_fails_at_large_amplitude():
    # 这是本项目最有说服力的一类对比：小角度近似在域内几乎看不出来，
    # 但在大摆角处误差显著放大。验证引擎必须把这个差异量出来。
    columns, meta = _task('phys-pendulum-exact')
    exact = verify_formula('2*pi*sqrt(L/g)*(1 + theta0**2/16)', columns, meta)
    approx = verify_formula('2*pi*sqrt(L/g)', columns, meta)
    e_checks = {c.name: c for c in exact.checks}
    a_checks = {c.name: c for c in approx.checks}
    assert exact.verdict == 'accepted', exact.to_json()
    assert e_checks['holdout'].metrics['normalized_rmse'] < a_checks['holdout'].metrics['normalized_rmse']
    assert e_checks['extrapolation'].metrics['normalized_rmse'] < a_checks['extrapolation'].metrics['normalized_rmse']
    # 注意：外推误差不一定大于留出误差，取决于误差结构；
    # 本任务里留出区落在中等摆角（近似已明显失真），所以留出误差反而更大。
    assert a_checks['holdout'].metrics['normalized_rmse'] > 0.05


def test_ideal_gas_missing_volume_rejected():
    columns, meta = _task('phys-ideal-gas')
    report = verify_formula('R*n*T', columns, meta, parameters=['R'])
    assert report.verdict == 'rejected'


def test_dimension_violation_is_caught_without_free_parameters():
    columns, meta = _task('phys-kinetic-energy')
    report = verify_formula('m*v/2', columns, meta)
    checks = {c.name: c for c in report.checks}
    assert checks['dimension'].passed is False, report.to_json()
    assert report.verdict == 'rejected'


def test_boltzmann_fourth_power_accepted_and_square_rejected():
    columns, meta = _task('phys-stefan-boltzmann')
    good = verify_formula('sigma*A*T**4', columns, meta, parameters=['sigma'])
    assert good.verdict == 'accepted', good.to_json()
    bad = verify_formula('sigma*A*T**2', columns, meta, parameters=['sigma'])
    assert bad.verdict == 'rejected'


def test_nonlinear_parameter_in_denominator_is_fitted():
    # hbar 以平方形式出现在分母，线性空间拟合会失败，必须靠对数空间多起点搜索
    columns, meta = _task('phys-hydrogen-level')
    report = verify_formula('-me*el**4/(2*(4*pi*eps0)**2*hbar**2*n**2)', columns, meta,
                            parameters=['eps0', 'hbar'])
    assert report.verdict == 'accepted', report.to_json()


def test_reproducibility_two_runs_identical():
    columns, meta = _task('phys-coulomb')
    first = verify_formula('k*q1*q2/r**2', columns, meta, parameters=['k']).to_json()
    second = verify_formula('k*q1*q2/r**2', columns, meta, parameters=['k']).to_json()
    assert first == second


def test_reference_answer_is_never_read():
    # 参考公式在仓库根的 reference/，不在 tasks/ 内；把它临时放进任务目录也不得影响结论
    task_dir = os.path.join(TASKS, 'phys-weight')
    trap = os.path.join(task_dir, 'reference.json')
    columns, meta = _task('phys-weight')
    baseline = verify_formula('m*g', columns, meta).to_json()
    created = False
    if not os.path.exists(trap):
        with open(trap, 'w', encoding='utf-8') as fh:
            fh.write('{"formula": "WRONG_ANSWER_TO_TRAP_LEAKAGE"}')
        created = True
    try:
        columns2, meta2 = _task('phys-weight')
        after = verify_formula('m*g', columns2, meta2).to_json()
        assert baseline == after
    finally:
        if created:
            os.remove(trap)


def test_noise_is_not_accepted_as_a_law():
    # 负对照：用随机噪声替换 y，正确行为是被拒绝
    columns, meta = _task('phys-ohm')
    rng = np.random.default_rng(7)
    noisy = dict(columns)
    noisy['y'] = rng.normal(0.0, 1.0, np.asarray(columns['y']).size)
    report = verify_formula('I*R', noisy, meta)
    assert report.verdict == 'rejected', report.to_json()