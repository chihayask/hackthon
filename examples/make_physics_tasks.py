# -*- coding: utf-8 -*-
# 真实物理定律任务集生成器。
#
# 数据来源说明（会写进数据卡，不藏）：
#   * 公式与变量语义来自公开物理定律，逐条附来源链接；
#   * 采样点由本脚本按 meta 中声明的区间独立均匀采样生成（SEED 固定，可复现）；
#   * 参考公式写入 reference/ 目录，tasks/ 下不出现，避免进入智能体上下文。
#
# 用法: python examples/make_physics_tasks.py
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

SEED = 20261008
N = 400
NOISE = 0.004
NOISE_ABS = {
    'phys-energy-shift': 0.01,
    'phys-pendulum-exact': 0.0005,
    'phys-hydrogen-level': 0.01,
    'phys-radioactive-decay': 0.01,
}
RNG = np.random.default_rng(SEED)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
CONST = {
    'G': 6.674e-11, 'k': 8.9875517923e9, 'R': 8.314462618, 'sigma': 5.670374419e-8,
    'h': 6.62607015e-34, 'eps0': 8.8541878128e-12, 'hbar': 1.054571817e-34,
    'd': 1.0,
}


def u(lo, hi):
    return RNG.uniform(lo, hi, N)


SPECS = [
    dict(id='phys-gravitation', layer='base', domain='gravitation',
         phenomenon='两质点间引力与质量乘积成正比、与距离平方成反比',
         vars={'m1': ('kg', 0.5, 5.0), 'm2': ('kg', 0.5, 5.0), 'r': ('m', 1.0, 3.0)},
         expr='G*m1*m2/r**2', params=['G'], y_unit='N',
         source=['https://en.wikipedia.org/wiki/Newton%27s_law_of_universal_gravitation']),
    dict(id='phys-coulomb', layer='base', domain='electromagnetism',
         phenomenon='两静止点电荷间作用力与电量乘积成正比、与距离平方成反比',
         vars={'q1': ('C', 1e-3, 5e-3), 'q2': ('C', 1e-3, 5e-3), 'r': ('m', 0.1, 0.5)},
         expr='k*q1*q2/r**2', params=['k'], y_unit='N',
         source=['https://en.wikipedia.org/wiki/Coulomb%27s_law']),
    dict(id='phys-ideal-gas', layer='base', domain='thermodynamics',
         phenomenon='理想气体压强与物质量、温度成正比，与体积成反比',
         vars={'n': ('mol', 1.0, 4.0), 'T': ('K', 250.0, 400.0), 'V': ('m^3', 0.01, 0.05)},
         expr='n*R*T/V', params=['R'], y_unit='Pa',
         source=['https://en.wikipedia.org/wiki/Ideal_gas_law']),
    dict(id='phys-kinetic-energy', layer='base', domain='mechanics',
         phenomenon='平动动能与质量成正比、与速度平方成正比',
         vars={'m': ('kg', 0.5, 10.0), 'v': ('m/s', 1.0, 20.0)},
         expr='m*v**2/2', params=[], y_unit='J',
         source=['https://en.wikipedia.org/wiki/Kinetic_energy']),
    dict(id='phys-spring-energy', layer='base', domain='mechanics',
         phenomenon='弹簧弹性势能与劲度系数和形变量平方成正比',
         vars={'k': ('N/m', 10.0, 200.0), 'x': ('m', 0.01, 0.5)},
         expr='k*x**2/2', params=[], y_unit='J',
         source=['https://en.wikipedia.org/wiki/Elastic_energy']),
    dict(id='phys-pendulum-period', layer='base', domain='oscillation',
         phenomenon='小角度单摆周期与摆长平方根成正比、与重力加速度平方根成反比',
         vars={'L': ('m', 0.2, 2.0), 'g': ('m/s^2', 1.6, 12.0)},
         expr='2*pi*sqrt(L/g)', params=[], y_unit='s',
         source=['https://en.wikipedia.org/wiki/Pendulum_(mechanics)']),
    dict(id='phys-ohm', layer='base', domain='circuits',
         phenomenon='导体两端电压等于电流与电阻之积',
         vars={'I': ('A', 0.05, 2.0), 'R': ('ohm', 1.0, 50.0)},
         expr='I*R', params=[], y_unit='V',
         source=['https://en.wikipedia.org/wiki/Ohm%27s_law']),
    dict(id='phys-joule-heating', layer='base', domain='circuits',
         phenomenon='电阻发热功率与电流平方和电阻成正比',
         vars={'I': ('A', 0.1, 2.0), 'R': ('ohm', 1.0, 50.0)},
         expr='I**2*R', params=[], y_unit='W',
         source=['https://en.wikipedia.org/wiki/Joule_heating']),
    dict(id='phys-surface-gravity', layer='base', domain='gravitation',
         phenomenon='球对称天体表面重力加速度与质量成正比、与半径平方成反比',
         vars={'M': ('kg', 1e23, 1e25), 'R': ('m', 1e6, 1e7)},
         expr='G*M/R**2', params=['G'], y_unit='m/s^2',
         source=['https://en.wikipedia.org/wiki/Gravity']),
    dict(id='phys-stefan-boltzmann', layer='base', domain='radiation',
         phenomenon='黑体辐射总功率与面积和温度四次方成正比',
         vars={'A': ('m^2', 0.1, 2.0), 'T': ('K', 300.0, 1000.0)},
         expr='sigma*A*T**4', params=['sigma'], y_unit='W',
         source=['https://en.wikipedia.org/wiki/Stefan%E2%80%93Boltzmann_law']),
    dict(id='phys-buoyancy', layer='base', domain='fluids',
         phenomenon='浮力等于排开液体的重量',
         vars={'rho': ('kg/m^3', 800.0, 1200.0), 'V': ('m^3', 0.001, 0.02), 'g': ('m/s^2', 9.0, 10.5)},
         expr='rho*V*g', params=[], y_unit='N',
         source=['https://en.wikipedia.org/wiki/Buoyancy']),
    dict(id='phys-weight', layer='base', domain='mechanics',
         phenomenon='物体所受重力等于质量与重力加速度之积',
         vars={'m': ('kg', 0.5, 20.0), 'g': ('m/s^2', 1.6, 12.0)},
         expr='m*g', params=[], y_unit='N',
         source=['https://en.wikipedia.org/wiki/Weight']),
    dict(id='phys-grav-potential-energy', layer='base', domain='gravitation',
         phenomenon='两质点间引力势能与距离成反比',
         vars={'m1': ('kg', 0.5, 5.0), 'm2': ('kg', 0.5, 5.0), 'r': ('m', 1.0, 3.0)},
         expr='-G*m1*m2/r', params=['G'], y_unit='J',
         source=['https://en.wikipedia.org/wiki/Gravitational_energy']),
    dict(id='phys-elastic-pe', layer='challenge', domain='mechanics',
         phenomenon='弹性势能随形变量与劲度系数的组合变化',
         vars={'c': ('N/m', 10.0, 200.0), 'x': ('m', 0.01, 0.5)},
         expr='c*x**2/2', params=[], y_unit='J',
         source=['https://en.wikipedia.org/wiki/Elastic_energy']),
    dict(id='phys-energy-shift', layer='challenge', domain='quantum',
         phenomenon='能级差决定的光子频率',
         vars={'A': ('J', 5e-19, 1e-18), 'B': ('J', 1e-21, 1e-20)},
         expr='(A-B)/h', params=['h'], y_unit='Hz',
         source=['https://en.wikipedia.org/wiki/Planck_relation']),
    dict(id='phys-cyclotron', layer='challenge', domain='electromagnetism',
         phenomenon='带电粒子回旋角频率与磁感应强度成正比、与质量成反比',
         vars={'q': ('C', 1e-19, 1e-18), 'B': ('T', 0.1, 2.0), 'm': ('kg', 1e-30, 1e-26)},
         expr='q*B/m', params=[], y_unit='Hz',
         source=['https://en.wikipedia.org/wiki/Cyclotron_resonance']),
    dict(id='phys-snells-law', layer='challenge', domain='optics',
         phenomenon='折射光线的几何关系（斯涅尔定律的等价形式）',
         vars={'n': ('-', 1.0, 1.4), 'theta2': ('rad', 0.05, 0.6)},
         expr='d*sin(theta2)/sqrt(1-(n*sin(theta2))**2)', params=['d'], y_unit='m',
         source=['https://en.wikipedia.org/wiki/Snell%27s_law']),
    dict(id='phys-radioactive-decay', layer='challenge', domain='nuclear',
         phenomenon='放射性衰变中剩余原子核数量随时间指数衰减',
         vars={'N0': ('-', 1e20, 1e22), 't': ('s', 0.0, 10.0), 'tau': ('s', 1.0, 5.0)},
         expr='N0*exp(-t/tau)', params=[], y_unit='-',
         source=['https://en.wikipedia.org/wiki/Radioactive_decay']),
    dict(id='phys-hydrogen-level', layer='challenge', domain='quantum',
         phenomenon='氢原子束缚态能级与主量子数平方成反比',
         vars={'me': ('kg', 9.0e-31, 9.5e-31), 'el': ('C', 1.55e-19, 1.65e-19), 'n': ('-', 1.0, 6.0)},
         expr='-me*el**4/(2*(4*pi*eps0)**2*hbar**2*n**2)',
         params=['eps0', 'hbar'], y_unit='J',
         source=['https://en.wikipedia.org/wiki/Bohr_model']),
    dict(id='phys-transit-depth', layer='challenge', domain='astronomy',
         phenomenon='掩星法中的相对光深与半径比平方成正比',
         vars={'A': ('-', 0.5, 1.0), 'Rp': ('m', 6e6, 9e7), 'Rs': ('m', 6e8, 7e8)},
         expr='A*(Rp/Rs)**2', params=[], y_unit='-',
         source=['https://en.wikipedia.org/wiki/Astronomical_transit']),
    dict(id='phys-pendulum-exact', layer='challenge', domain='oscillation',
         phenomenon='有限振幅单摆的精确周期（小角度近似的修正项）',
         vars={'L': ('m', 0.2, 2.0), 'g': ('m/s^2', 1.6, 12.0), 'theta0': ('rad', 0.05, 1.20)},
         expr='2*pi*sqrt(L/g)*(1 + theta0**2/16)', params=[], y_unit='s',
         source=['https://en.wikipedia.org/wiki/Pendulum_(mechanics)']),
    dict(id='phys-index-vacuum', layer='challenge', domain='optics',
         phenomenon='介质折射率与介电常数、磁导率的关系',
         vars={'eps': ('F/m', 2e-11, 8e-11), 'mu': ('H/m', 1.2e-6, 1.3e-6)},
         expr='1/sqrt(eps*mu)', params=[], y_unit='m/s',
         source=['https://en.wikipedia.org/wiki/Refractive_index']),
]


def build(spec):
    cols = {}
    for name, (unit, lo, hi) in spec['vars'].items():
        cols[name] = u(lo, hi)
    scope = dict(cols)
    for pname in spec['params']:
        scope[pname] = CONST[pname]
    scope['pi'] = math.pi
    scope['exp'] = np.exp
    scope['sqrt'] = np.sqrt
    scope['sin'] = np.sin
    scope['cos'] = np.cos
    val = np.asarray(eval(spec['expr'], {'__builtins__': {}}, scope), dtype=float)
    if spec['id'] in NOISE_ABS:
        # 参考值可能跨越零点的任务：相对噪声会失真，改用与量级挂钩的绝对噪声
        sigma = NOISE_ABS[spec['id']] * float(np.median(np.abs(val)))
        cols['y'] = val + RNG.normal(0.0, sigma, val.size)
    else:
        cols['y'] = val * (1.0 + RNG.normal(0.0, NOISE, val.size))
    return cols


def write_task(spec):
    cols = build(spec)
    task_dir = os.path.join(TASKS, spec['id'])
    os.makedirs(task_dir, exist_ok=True)
    keys = list(spec['vars'].keys()) + ['y']
    with open(os.path.join(task_dir, 'data.csv'), 'w', encoding='utf-8') as fh:
        fh.write(','.join(keys) + chr(10))
        for row in zip(*[cols[k] for k in keys]):
            fh.write(','.join('%.10g' % float(v) for v in row) + chr(10))
    units = {k: v[0] for k, v in spec['vars'].items()}
    units['y'] = spec['y_unit']
    meta = {
        'task_id': spec['id'],
        'var_names': list(spec['vars'].keys()),
        'units': units,
        'free_parameters': spec['params'],
        'source': spec['source'],
        'source_note': '公式与变量语义取自上述公开来源；采样点由 examples/make_physics_tasks.py 按 meta 声明区间生成（SEED=%d, N=%d）' % (SEED, N),
        'sampling': {k: [v[1], v[2]] for k, v in spec['vars'].items()},
        'sample_count': N,
        'noise_relative_sigma': NOISE,
        'layer': spec['layer'],
        'domain': spec['domain'],
        'phenomenon': spec['phenomenon'],
    }
    with open(os.path.join(task_dir, 'meta.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    os.makedirs(REF, exist_ok=True)
    ref = {
        'task_id': spec['id'],
        'formula': spec['expr'],
        'free_parameters': spec['params'],
        'true_constants': {p: CONST[p] for p in spec['params']},
        'y_unit': spec['y_unit'],
        'source': spec['source'],
    }
    with open(os.path.join(REF, spec['id'] + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(ref, fh, ensure_ascii=False, indent=2)
    if spec['id'] == 'phys-gravitation':
        cands = [{'formula': 'G*m1*m2/r**2', 'parameters': ['G'], 'expect': 'accepted'},
                 {'formula': 'G*m1*m2/r', 'parameters': ['G'], 'expect': 'rejected'}]
        with open(os.path.join(task_dir, 'candidates.json'), 'w', encoding='utf-8') as fh:
            json.dump(cands, fh, ensure_ascii=False, indent=2)
    return task_dir


def main():
    made = []
    for spec in SPECS:
        made.append(write_task(spec))
    print('tasks written:', len(made))
    base = sum(1 for s in SPECS if s['layer'] == 'base')
    print('base:', base, 'challenge:', len(SPECS) - base)
    return 0


if __name__ == '__main__':
    sys.exit(main())