# 与标准答案对照表（M2 评分脚本产出）

生成方式：

    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

标准答案只被本脚本读取。智能体侧（formula_agh）不持有任何指向 reference/ 的路径；
证据是：把 reference/ 改名后，全部验证结论逐位不变（tests/test_isolation.py）。

## 一、总览

| 层次 | 检查数 | 符合预期 | 通过率 |
|---|---|---|---|
| 金标准自检（标准答案必须被接受） | 22 | 22 | 100.0% |
| 判别力（结构错误的候选必须被拒绝） | 22 | 22 | 100.0% |
| 智能体发现（与标准答案一致，仅计 hypothesis_source=agh-llm） | 0 | 0 | n/a |
| （参考）人工提供的候选式，不计入上行 | 1 | - | - |

## 二、按难度分层

| 层级 | 任务数 | 金标准通过 | 错误式拒绝 | 智能体命中 |
|---|---|---|---|---|
| base | 13 | 13 | 13 | 0/0 |
| challenge | 9 | 9 | 9 | 0/0 |

## 三、逐任务对照

| 任务 | 层级 | 标准公式 | 智能体公式 | 留出集 | 外推区 | 量纲 | 与答案一致 |
|---|---|---|---|---|---|---|---|
| phys-buoyancy | base | `rho*V*g` | - |  |  | n/a | - |
| phys-coulomb | base | `k*q1*q2/r**2` | - |  |  | n/a | - |
| phys-cyclotron | challenge | `q*B/m` | - |  |  | n/a | - |
| phys-elastic-pe | challenge | `c*x**2/2` | - |  |  | n/a | - |
| phys-energy-shift | challenge | `(A-B)/h` | - |  |  | n/a | - |
| phys-grav-potential-energy | base | `-G*m1*m2/r` | - |  |  | n/a | - |
| phys-gravitation | base | `G*m1*m2/r**2` | - |  |  | n/a | - |
| phys-hydrogen-level | challenge | `-me*el**4/(2*(4*pi*eps0)**2*hbar**2*n**2)` | - |  |  | n/a | - |
| phys-ideal-gas | base | `n*R*T/V` | - |  |  | n/a | - |
| phys-index-vacuum | challenge | `1/sqrt(eps*mu)` | - |  |  | n/a | - |
| phys-joule-heating | base | `I**2*R` | - |  |  | n/a | - |
| phys-kinetic-energy | base | `m*v**2/2` | - |  |  | n/a | - |
| phys-ohm | base | `I*R` | - |  |  | n/a | - |
| phys-pendulum-exact | challenge | `2*pi*sqrt(L/g)*(1 + theta0**2/16)` | - |  |  | n/a | - |
| phys-pendulum-period | base | `2*pi*sqrt(L/g)` | - |  |  | n/a | - |
| phys-radioactive-decay | challenge | `N0*exp(-t/tau)` | - |  |  | n/a | - |
| phys-snells-law | challenge | `d*sin(theta2)/sqrt(1-(n*sin(theta2))**2)` | - |  |  | n/a | - |
| phys-spring-energy | base | `k*x**2/2` | - |  |  | n/a | - |
| phys-stefan-boltzmann | base | `sigma*A*T**4` | - |  |  | n/a | - |
| phys-surface-gravity | base | `G*M/R**2` | - |  |  | n/a | - |
| phys-transit-depth | challenge | `A*(Rp/Rs)**2` | - |  |  | n/a | - |
| phys-weight | base | `m*g` | - |  |  | n/a | - |

## 四、如实说明（不掩盖空缺）

- 有 1 个任务存在候选式运行，但其 hypothesis_source 不是 agh-llm（现为人工提供或命令行给出），因此**不计入**「智能体发现」层。对照表第 3 层为空，不能据此声称发现能力。

