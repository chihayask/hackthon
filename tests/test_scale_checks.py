# -*- coding: utf-8 -*-
# 尺度一致性检验的自测：
# 一份物理规格要同时满足两个方向的要求——
#   * 不能误杀：22 个参考公式必须全部通过；
#   * 不能放水：物理上合理但结构错误的候选式必须被否决。
# 两者缺一，尺度检验就只是装饰。
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.scale_checks import (SPEC_SCHEMA, HANDLERS, list_spec_task_ids,
                                      load_specs, run_scale_checks)
from formula_agh.verify import VerifyError, load_task

TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
SPECS_PATH = os.path.join(ROOT, 'physics', 'scale_specs.json')


def _specs():
    return load_specs(SPECS_PATH)


def _task(name):
    return load_task(os.path.join(TASKS, name))


def _reference(task_id):
    with open(os.path.join(REF, task_id + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _report(task_id, formula, params=None):
    columns, meta = _task(task_id)
    spec = _specs()['tasks'][task_id]
    if params is None:
        params = spec.get('nominal_parameters') or {}
    return run_scale_checks(task_id, formula, meta, spec, parameters=params)


def _failed(report):
    return [c.name for c in report.checks if not c.passed]


def test_specs_cover_every_task_and_kind():
    specs = _specs()
    assert specs['schema'] == SPEC_SCHEMA
    task_ids = list_spec_task_ids(specs)
    assert len(task_ids) == 22, task_ids
    for name in os.listdir(TASKS):
        if os.path.isdir(os.path.join(TASKS, name)):
            assert name in task_ids, '任务集里有任务但规格里没有: ' + name
    kinds = set()
    for task_id in task_ids:
        checks = specs['tasks'][task_id]['checks']
        assert checks, task_id
        for item in checks:
            assert item['kind'] in HANDLERS, (task_id, item['kind'])
            kinds.add(item['kind'])
    # 任务书要求至少 3 类尺度检验；这里实际覆盖 6 类。
    assert {'scaling', 'limit', 'monotonic', 'sign', 'symmetry', 'invariance'} <= kinds


def test_every_reference_formula_passes_scale_checks():
    # 金标准：规格写错的第一表现就是参考公式自己过不了。
    failures = []
    for task_id in list_spec_task_ids(_specs()):
        ref = _reference(task_id)
        report = _report(task_id, ref['formula'], ref.get('true_constants') or {})
        if report.verdict != 'accepted':
            failures.append((task_id, _failed(report)))
    assert not failures, failures


def test_wrong_power_is_caught_by_scaling_even_without_fitting():
    # G*m1*m2/r 与参考式只差一个幂次；标度检验不看拟合，直接判死。
    report = _report('phys-gravitation', 'G*m1*m2/r')
    assert report.verdict == 'rejected'
    assert 'scale-scaling-r' in _failed(report)


def test_small_angle_formula_is_flat_in_amplitude():
    # 小角度近似对 theta0 完全没有依赖；尺度检验必须把"漏掉自变量"识别为平坦。
    report = _report('phys-pendulum-exact', '2*pi*sqrt(L/g)')
    assert report.verdict == 'rejected'
    names = _failed(report)
    assert 'scale-monotonic-theta0' in names
    flat = [c for c in report.checks if c.name == 'scale-monotonic-theta0'][0]
    assert flat.metrics['variation'] < flat.metrics['min_variation']


def test_linear_decay_goes_negative_and_is_rejected():
    # 线性近似 N0*(1-t/tau) 在 t > tau 后给出负的粒子数。
    report = _report('phys-radioactive-decay', 'N0*(1-t/tau)')
    assert report.verdict == 'rejected'
    assert 'scale-sign-y' in _failed(report)


def test_decay_limit_is_accepted_but_linear_form_still_fails_sign():
    # N0*(1-t/tau) 的 t->0 极限是对的（这一点必须承认），
    # 它被否决的理由只能是符号，而不是极限 —— 检验理由必须精确。
    report = _report('phys-radioactive-decay', 'N0*(1-t/tau)')
    checks = {c.name: c for c in report.checks}
    assert checks['scale-limit-t-to-0-0'].passed
    assert not checks['scale-sign-y'].passed


def test_free_parameter_scaling_is_checked():
    # 频率与普朗克常数成反比：这是"常数以什么幂次进入公式"的检验。
    good = _report('phys-energy-shift', '(A-B)/h', {'h': 6.62607015e-34})
    bad = _report('phys-energy-shift', '(A-B)*h', {'h': 6.62607015e-34})
    assert good.verdict == 'accepted'
    assert 'scale-scaling-h' in _failed(bad)


def test_dimensionless_group_invariance():
    # 掩星光深只依赖半径比：同时缩放 Rp 与 Rs 必须不改变结果。
    good = _report('phys-transit-depth', 'A*(Rp/Rs)**2')
    bad = _report('phys-transit-depth', 'A*Rp/Rs')
    assert good.verdict == 'accepted'
    assert 'scale-invariance-Rp-Rs' not in _failed(good)
    assert 'scale-scaling-Rp' in _failed(bad)


def test_limit_check_rejects_constant_relative_error():
    # d*sin(theta2)*n 与近轴极限 d*theta2/... 相比，
    # 相对偏差是恒定的 (n-1)。它随探测点变小而变小的是绝对值，不是相对值，
    # 检验不能因此判它通过。
    report = _report('phys-snells-law', 'd*sin(theta2)*n', {'d': 1.0})
    assert report.verdict == 'rejected'
    assert 'scale-limit-theta2-to-0-0' in _failed(report)


def test_scale_check_fails_loudly_on_bad_input():
    # 缺少规格、缺少采样区间都必须报错退出，不许静默给一个"通过"。
    meta = {'var_names': ['a', 'b'], 'sampling': {'a': [1, 2], 'b': [1, 2]}}
    with pytest.raises(VerifyError):
        run_scale_checks('x', 'a*b', meta, {})
    with pytest.raises(VerifyError):
        run_scale_checks('x', 'a*b', meta, {'checks': []})
    with pytest.raises(VerifyError):
        run_scale_checks('x', 'a*b', {'var_names': ['a', 'b']},
                         {'checks': [{'kind': 'sign', 'expect': 'positive'}]})


def test_scale_checks_never_opens_a_reference_file():
    # 与 M2 的答案隔离原则一致：尺度检验只看公式与规格。
    # 用行为验证而不是扫源码——注释里提到 reference/ 是无害的，
    # 真正要保证的是"运行期一次都没有打开过标准答案"。
    import builtins

    real_open = builtins.open
    opened = []

    def guard(file, *args, **kwargs):
        path = str(file).replace('\\', '/')
        opened.append(path)
        assert 'reference' not in path, '尺度检验打开了标准答案: ' + path
        return real_open(file, *args, **kwargs)

    builtins.open = guard
    try:
        report = _report('phys-gravitation', 'G*m1*m2/r**2')
    finally:
        builtins.open = real_open
    assert report.verdict == 'accepted'
    assert opened, '守卫没有记录到任何文件访问，测试本身失效了'


def test_every_check_has_a_distinct_evidence_name():
    # 检验名就是证据文件名；重名会让后一条覆盖前一条。
    for task_id in list_spec_task_ids(_specs()):
        ref = _reference(task_id)
        report = _report(task_id, ref['formula'], ref.get('true_constants') or {})
        names = [c.name for c in report.checks]
        assert len(names) == len(set(names)), (task_id, names)
