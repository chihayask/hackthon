# -*- coding: utf-8 -*-
# 生成 physics/scale_specs.json —— 22 个任务的"尺度一致性"物理规格。
#
# 这份规格由机械设计制造及其自动化成员（M3）编写，是本项目里**纯物理先验**的载体：
# 它描述"这个现象必须满足什么"，与任何具体公式无关。
# 因此同一份规格既能验证标准答案（金标准自检），也能验证智能体给出的候选式（判别力），
# 且完全不依赖参考公式本身。
#
# 六类检验与它们在机械/物理里的出处：
#   scaling     幂律标度      —— 相似性原理 / 量纲分析的幂律形式
#   invariance  无量纲群不变  —— Buckingham π 定理
#   limit       极限行为      —— 小量近似（线性化）、边界退化
#   monotonic   单调性        —— 力学、热力学中的单调响应
#   sign        符号          —— 能量、力、粒子数的物理符号约定
#   symmetry    交换对称      —— 同类量的地位对称（m1↔m2、q1↔q2）
#
# 约定：
#   * 标度检验在"基准点"上做乘性扰动，基准点取各变量声明区间的几何中点；
#   * 极限检验的探测点按声明区间的百分比向极限逼近，允许略微越出采样盒
#     （极限是函数形式的性质，不是数据的性质）；
#   * 自由参数取物理真值（由 reference/*.json 的 true_constants 提供），
#     因此尺度检验**不需要拟合**就能给出结论 —— 这是它与留出集/外推检验的本质区别。
#
# 用法：python examples/make_scale_specs.py   ->  physics/scale_specs.json
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
REF_DIR = os.path.join(ROOT, 'reference')
OUT_PATH = os.path.join(ROOT, 'physics', 'scale_specs.json')

SCHEMA = 'formula-agh/scale-specs@1'


def scaling(var, lam, power, note):
    return {'kind': 'scaling', 'var': var, 'lambda': lam, 'expect_power': power, 'note': note}


def multi_scaling(vars_, lam, power, note):
    return {'kind': 'scaling', 'scale': {v: 1.0 for v in vars_}, 'lambda': lam,
            'expect_power': power, 'note': note}


def invariance(vars_, lam, note):
    return {'kind': 'invariance', 'scale': {v: 1.0 for v in vars_}, 'lambda': lam, 'note': note}


def limit(var, to, target, note, rel_tol=5e-3):
    return {'kind': 'limit', 'var': var, 'to': to, 'target': target,
            'rel_tol': rel_tol, 'note': note}


def monotonic(var, direction, note):
    return {'kind': 'monotonic', 'var': var, 'direction': direction, 'note': note}


def sign(expect, note):
    return {'kind': 'sign', 'expect': expect, 'note': note}


def symmetry(a, b, note):
    return {'kind': 'symmetry', 'swap': [a, b], 'note': note}


TASKS = {
    'phys-buoyancy': {
        'physics_note': '阿基米德浮力：F = rho*V*g。三个变量地位均等，都是"乘性"进入公式。',
        'checks': [
            scaling('rho', 2.0, 1.0, '密度加倍，浮力加倍'),
            scaling('V', 2.0, 1.0, '排开体积加倍，浮力加倍'),
            scaling('g', 2.0, 1.0, '重力加速度加倍，浮力加倍'),
            monotonic('rho', 'increasing', '越密的液体浮力越大'),
            monotonic('V', 'increasing', '排开越多浮力越大'),
            sign('positive', '浮力方向向上，若以向上为正则恒正'),
        ],
    },
    'phys-coulomb': {
        'physics_note': '库仑定律：F = k*q1*q2/r**2。平方反比是电磁学的核心标度。',
        'checks': [
            scaling('r', 2.0, -2.0, '距离加倍，力变四分之一（平方反比）'),
            scaling('q1', 2.0, 1.0, '电量加倍，力加倍'),
            symmetry('q1', 'q2', '两个点电荷地位完全对称，互换后力不变'),
            monotonic('r', 'decreasing', '距离越大作用力越小'),
            sign('positive', '同号电荷定义为排斥为正；此处数据取 q1,q2 同号'),
        ],
    },
    'phys-cyclotron': {
        'physics_note': '回旋频率：f = q*B/m。注意它对质量是反比、对磁感应强度是正比，符号容易写反。',
        'checks': [
            scaling('B', 2.0, 1.0, '磁场加倍，回旋频率加倍'),
            scaling('m', 2.0, -1.0, '质量加倍，回旋频率减半'),
            scaling('q', 2.0, 1.0, '电荷加倍，回旋频率加倍'),
            monotonic('B', 'increasing', '磁场越强转得越快'),
            monotonic('m', 'decreasing', '越重的粒子转得越慢'),
            sign('positive', '频率为正'),
        ],
    },
    'phys-elastic-pe': {
        'physics_note': '弹性势能 E = c*x**2/2。二次型意味着"形变加倍、能量变四倍"，且能量对形变正负号不敏感。',
        'checks': [
            scaling('x', 2.0, 2.0, '形变加倍，弹性势能变四倍（二次型）'),
            scaling('c', 2.0, 1.0, '刚度加倍，同形变下储能加倍'),
            {'kind': 'scaling', 'var': 'x', 'lambda': -1.0, 'expect_power': 2.0,
             'label': 'x-parity',
             'note': '把形变反向（x -> -x），弹性势能不变：势能是形变的偶函数'},
            monotonic('x', 'increasing', '在 x>0 一侧，形变越大储能越多'),
            sign('positive', '储能恒为正（零点取在自然长度）'),
        ],
    },
    'phys-energy-shift': {
        'physics_note': '能级差决定的光子频率：f = (A-B)/h。对 A 递增、对 B 递减，两者符号相反。',
        'checks': [
            scaling('h', 2.0, -1.0, '普朗克常数加倍，同一能级差对应的频率减半'),
            monotonic('A', 'increasing', '上能级越高，跃迁频率越高'),
            monotonic('B', 'decreasing', '下能级越高，能级差越小，频率越低'),
            sign('positive', '本任务采样保证 A > B，故频率恒正'),
        ],
    },
    'phys-grav-potential-energy': {
        'physics_note': '引力势能 E = -G*m1*m2/r。负号是物理约定（无穷远为零势能），且只与距离一次方成反比。',
        'checks': [
            scaling('r', 2.0, -1.0, '距离加倍，势能绝对值减半（一次反比，不是平方反比）'),
            symmetry('m1', 'm2', '两个质点在引力势能里对称'),
            monotonic('r', 'increasing', '距离变大时势能从更负趋近于零，因此是递增'),
            sign('negative', '束缚态引力势能恒为负'),
        ],
    },
    'phys-gravitation': {
        'physics_note': '万有引力：F = G*m1*m2/r**2。与库仑定律同形，平方反比。',
        'checks': [
            scaling('r', 2.0, -2.0, '距离加倍，引力变四分之一'),
            scaling('m1', 2.0, 1.0, '质量加倍，引力加倍'),
            symmetry('m1', 'm2', '两个质点地位对称，互换后引力不变'),
            monotonic('r', 'decreasing', '距离越大引力越小'),
            sign('positive', '引力大小恒为正'),
        ],
    },
    'phys-hydrogen-level': {
        'physics_note': '玻尔氢原子能级 E_n = -me*el**4/(2*(4*pi*eps0)**2*hbar**2*n**2)。'
                        '主量子数在分母平方项里，这是本任务集最具区分度的标度。',
        'checks': [
            scaling('n', 2.0, -2.0, '主量子数加倍，能级绝对值变四分之一（n 的平方反比）'),
            monotonic('n', 'increasing', 'n 越大能级越高（从 -13.6 eV 趋近 0），因此数值递增'),
            sign('negative', '束缚态能量恒为负'),
        ],
    },
    'phys-ideal-gas': {
        'physics_note': '理想气体状态方程：p = n*R*T/V。对 V 反比是"体积越大压强越小"的直接体现。',
        'checks': [
            scaling('V', 2.0, -1.0, '体积加倍，压强减半'),
            scaling('T', 2.0, 1.0, '温度加倍，压强加倍'),
            scaling('n', 2.0, 1.0, '物质量加倍，压强加倍'),
            monotonic('V', 'decreasing', '等温下体积越大压强越小'),
            sign('positive', '绝对压强恒为正'),
        ],
    },
    'phys-index-vacuum': {
        'physics_note': '真空/介质中的波速 c = 1/sqrt(eps*mu)。开方使标度指数出现 1/2，'
                        '这是"开方写错成一次方"的典型陷阱。',
        'checks': [
            scaling('eps', 2.0, -0.5, '介电常数加倍，波速变为 1/sqrt(2) 倍'),
            multi_scaling(['eps', 'mu'], 2.0, -1.0,
                          '介电常数与磁导率同时加倍，波速减半（根号内的二次缩放）'),
            monotonic('eps', 'decreasing', '介电常数越大波速越慢'),
            sign('positive', '波速恒为正'),
        ],
    },
    'phys-joule-heating': {
        'physics_note': '焦耳定律：P = I**2*R。电流是二次进入，电阻是一次。',
        'checks': [
            scaling('I', 2.0, 2.0, '电流加倍，发热功率变四倍（平方关系）'),
            scaling('R', 2.0, 1.0, '电阻加倍，发热功率加倍（线性关系）'),
            monotonic('I', 'increasing', '电流越大发热越多'),
            monotonic('R', 'increasing', '同电流下电阻越大发热越多'),
            sign('positive', '发热功率恒为正'),
        ],
    },
    'phys-kinetic-energy': {
        'physics_note': '平动动能 E = m*v**2/2。速度二次、质量一次，与弹簧势能同构。',
        'checks': [
            scaling('v', 2.0, 2.0, '速度加倍，动能变四倍（这是最容易被写成一次的标度）'),
            scaling('m', 2.0, 1.0, '质量加倍，动能加倍'),
            {'kind': 'scaling', 'var': 'v', 'lambda': -1.0, 'expect_power': 2.0,
             'label': 'v-parity',
             'note': '速度反向动能不变：动能是速度的偶函数（不含一次项）'},
            monotonic('v', 'increasing', '速度越大动能越大'),
            sign('positive', '动能恒为正'),
        ],
    },
    'phys-ohm': {
        'physics_note': '欧姆定律：U = I*R。两个变量都是一次进入，地位在标度上等价、但在物理上不可互换。',
        'checks': [
            scaling('I', 2.0, 1.0, '电流加倍，电压加倍'),
            scaling('R', 2.0, 1.0, '电阻加倍，电压加倍'),
            monotonic('I', 'increasing', '电流越大压降越大'),
            monotonic('R', 'increasing', '电阻越大压降越大'),
            sign('positive', '电压取正向定义时恒正'),
        ],
    },
    'phys-pendulum-exact': {
        'physics_note': '有限振幅单摆周期 T = 2*pi*sqrt(L/g)*(1 + theta0**2/16)。'
                        '它是小角度公式的一阶修正：theta0 -> 0 时必须退化为 2*pi*sqrt(L/g)，'
                        '且在采样区间内必须随 theta0 严格增大。小角度公式恰好是"漏掉 theta0 依赖"的典型错误。',
        'checks': [
            scaling('L', 4.0, 0.5, '摆长变 4 倍，周期变 2 倍（平方根关系）'),
            scaling('g', 4.0, -0.5, '重力加速度变 4 倍，周期减半'),
            limit('theta0', 0.0, '2*pi*sqrt(L/g)',
                  'theta0 -> 0 时退化为小角度周期公式（小量近似）'),
            monotonic('theta0', 'increasing',
                      '振幅越大周期越长；小角度公式在此处完全平坦，必被否决'),
            sign('positive', '周期恒为正'),
        ],
    },
    'phys-pendulum-period': {
        'physics_note': '小角度单摆：T = 2*pi*sqrt(L/g)。平方根标度是本任务的全部内容。',
        'checks': [
            scaling('L', 4.0, 0.5, '摆长变 4 倍，周期变 2 倍'),
            scaling('g', 4.0, -0.5, '重力加速度变 4 倍，周期减半'),
            monotonic('L', 'increasing', '摆越长周期越长'),
            monotonic('g', 'decreasing', '重力越强周期越短'),
            sign('positive', '周期恒为正'),
        ],
    },
    'phys-radioactive-decay': {
        'physics_note': '指数衰减 N = N0*exp(-t/tau)。三条硬性质：t=0 时等于 N0、'
                        '对时间单调递减、任何时刻都不为负（粒子数不能是负数）。'
                        '线性近似 N0*(1-t/tau) 会在 t>tau 后给出负的粒子数，必须被否决。',
        'checks': [
            scaling('N0', 2.0, 1.0, '初始核数加倍，任意时刻剩余数加倍'),
            limit('t', 0.0, 'N0', 't -> 0 时剩余数趋于初始值 N0'),
            monotonic('t', 'decreasing', '时间越长剩余越少'),
            monotonic('tau', 'increasing', '寿命越长，同一时刻剩余越多'),
            sign('positive', '粒子数不可能为负——这条否决线性近似'),
        ],
    },
    'phys-snells-law': {
        'physics_note': '斯涅尔定律的几何等价形式 y = d*sin(theta2)/sqrt(1-(n*sin(theta2))**2)。'
                        'theta2 -> 0 时必须退化为 y ≈ d*theta2（近轴近似）；'
                        '折射率 n 只以 n*sin(theta2) 的无量纲组合出现。',
        'checks': [
            scaling('d', 3.0, 1.0, '几何尺度 d 加倍，位移加倍'),
            limit('theta2', 0.0, 'd*theta2', '近轴近似：小角度下 sin(theta2) -> theta2'),
            monotonic('theta2', 'increasing', '入射角越大横向位移越大'),
            sign('positive', '取正向几何约定时位移恒正'),
        ],
    },
    'phys-spring-energy': {
        'physics_note': '弹簧弹性势能 E = k*x**2/2。与 phys-elastic-pe 同构，是"同一物理规律的两种记法"，'
                        '放在任务集里用来检验结论的一致性。',
        'checks': [
            scaling('x', 2.0, 2.0, '形变加倍，储能变四倍'),
            scaling('k', 2.0, 1.0, '劲度系数加倍，同形变下储能加倍'),
            {'kind': 'scaling', 'var': 'x', 'lambda': -1.0, 'expect_power': 2.0,
             'label': 'x-parity',
             'note': '压缩与拉伸储能相同：势能是形变的偶函数'},
            monotonic('x', 'increasing', '形变越大储能越多'),
            sign('positive', '储能恒为正'),
        ],
    },
    'phys-stefan-boltzmann': {
        'physics_note': '斯特藩-玻尔兹曼定律：P = sigma*A*T**4。温度是四次方，'
                        '这是全任务集中幂次最高、最容易写错（写成 T 或 T**2）的一条。',
        'checks': [
            scaling('T', 2.0, 4.0, '温度加倍，辐射功率变 16 倍（四次方）'),
            scaling('A', 2.0, 1.0, '面积加倍，辐射功率加倍'),
            scaling('sigma', 2.0, 1.0, '常数加倍，功率加倍'),
            monotonic('T', 'increasing', '温度越高辐射越强，且是强非线性增长'),
            sign('positive', '辐射功率恒为正'),
        ],
    },
    'phys-surface-gravity': {
        'physics_note': '球对称天体表面重力：g = G*M/R**2。半径是平方反比，'
                        '半径写在分子是"单位对、形状错"的典型错误。',
        'checks': [
            scaling('R', 2.0, -2.0, '半径加倍，表面重力变四分之一（平方反比）'),
            scaling('M', 2.0, 1.0, '质量加倍，表面重力加倍'),
            monotonic('R', 'decreasing', '半径越大表面重力越小'),
            sign('positive', '重力加速度大小恒为正'),
        ],
    },
    'phys-transit-depth': {
        'physics_note': '掩星光深 y = A*(Rp/Rs)**2。它只依赖半径比这个无量纲数——'
                        '把 Rp 与 Rs 同时缩放任意倍数，y 必须不变（Buckingham π 的直接体现）。'
                        '同时 y 对 Rp 是二次关系。',
        'checks': [
            scaling('A', 2.0, 1.0, '基准光深加倍，结果加倍'),
            scaling('Rp', 2.0, 2.0, '行星半径加倍，光深变四倍（半径比平方）'),
            invariance(['Rp', 'Rs'], 3.0,
                       '行星与恒星半径同时放大 3 倍，光深不变：只依赖无量纲半径比'),
            monotonic('Rp', 'increasing', '行星越大遮挡越多'),
            monotonic('Rs', 'decreasing', '恒星越大，同样行星造成的相对光深越小'),
            sign('positive', '光深恒为正'),
        ],
    },
    'phys-weight': {
        'physics_note': '重力 W = m*g。两个变量都是一次进入，是最简单的乘性关系。',
        'checks': [
            scaling('m', 2.0, 1.0, '质量加倍，重力加倍'),
            scaling('g', 2.0, 1.0, '重力加速度加倍，重力加倍'),
            monotonic('m', 'increasing', '质量越大越重'),
            monotonic('g', 'increasing', '重力场越强越重'),
            sign('positive', '重力大小恒为正'),
        ],
    },
}


def load_true_constants():
    # 自由参数的物理真值取自 reference/*.json 的 true_constants；
    # 它们只用于让尺度检验有一个物理上正确的参数符号与量级，不参与公式判定。
    out = {}
    for name in sorted(os.listdir(REF_DIR)):
        if not name.endswith('.json'):
            continue
        with open(os.path.join(REF_DIR, name), encoding='utf-8') as fh:
            ref = json.load(fh)
        out[ref['task_id']] = dict(ref.get('true_constants') or {})
    return out


def main():
    constants = load_true_constants()
    tasks = {}
    missing = []
    for task_id in sorted(TASKS):
        body = TASKS[task_id]
        if task_id not in constants:
            missing.append(task_id)
            continue
        tasks[task_id] = {
            'physics_note': body['physics_note'],
            'nominal_parameters': constants[task_id],
            'checks': body['checks'],
        }
    if missing:
        raise SystemExit('reference/ 中缺少这些任务的 true_constants: ' + ', '.join(missing))

    payload = {
        'schema': SCHEMA,
        'generated_by': 'examples/make_scale_specs.py（M3 机械专业成员编写的物理规格）',
        'note': ('本文件描述每个现象必须满足的尺度性质，与任何具体公式无关。'
                 '用于尺度一致性检验（src/formula_agh/scale_checks.py）。'
                 '与 reference/ 同等对待：位于 tasks/ 之外，绝不进入智能体上下文。'),
        'kinds': {
            'scaling': '幂律标度：变量按 λ 缩放后 y 应变为 λ^p',
            'invariance': '无量纲群不变性（Buckingham π）：按指定指数同时缩放后 y 不变',
            'limit': '极限行为：变量趋于某值时 y 趋于给定极限式',
            'monotonic': '单调性：y 对某变量在声明区间内单调',
            'sign': '符号：y 在采样盒内恒正/恒负',
            'symmetry': '交换对称性：同类变量互换后 y 不变',
        },
        'tasks': tasks,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    total_checks = sum(len(t['checks']) for t in tasks.values())
    print('wrote %s' % OUT_PATH)
    print('tasks: %d, checks: %d' % (len(tasks), total_checks))
    kinds = {}
    for t in tasks.values():
        for c in t['checks']:
            kinds[c['kind']] = kinds.get(c['kind'], 0) + 1
    print('by kind: %s' % json.dumps(kinds, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
