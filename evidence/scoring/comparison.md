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
| 智能体发现（与标准答案一致，仅计 hypothesis_source=agh-llm） | 22 | 17 | 77.3% |
| （参考）人工提供的候选式，不计入上行 | 1 | - | - |

## 二、按难度分层

| 层级 | 任务数 | 金标准通过 | 错误式拒绝 | 智能体命中 |
|---|---|---|---|---|
| base | 13 | 13 | 13 | 11/13 |
| challenge | 9 | 9 | 9 | 6/9 |

## 三、逐任务对照

| 任务 | 层级 | 标准公式 | 智能体公式 | 留出集 | 外推区 | 量纲 | 与答案一致 |
|---|---|---|---|---|---|---|---|
| phys-buoyancy | base | `rho*V*g` | `rho*V*g` | 0.0086714 | 0.00848339 | pass | 结构相同 |
| phys-coulomb | base | `k*q1*q2/r**2` | `k*q1*q2/r**2` | 0.00598585 | 0.0053982 | pass | 结构相同 |
| phys-cyclotron | challenge | `q*B/m` | `q*B/m` | 0.00507573 | 0.00236068 | pass | 结构相同 |
| phys-elastic-pe | challenge | `c*x**2/2` | `0.5*c*x**2` | 0.00589003 | 0.00354736 | pass | 数值等价 |
| phys-energy-shift | challenge | `(A-B)/h` | `(A-B)/h` | 0.0641222 | 0.0309727 | pass | 结构相同 |
| phys-grav-potential-energy | base | `-G*m1*m2/r` | `G*m1*m2/r` | 0.00664254 | 0.00484022 | pass | 不一致 (偏差 0.000124) |
| phys-gravitation | base | `G*m1*m2/r**2` | `G*m1*m2/r**2` | 0.00688375 | 0.00619655 | pass | 结构相同 |
| phys-hydrogen-level | challenge | `-me*el**4/(2*(4*pi*eps0)**2*hbar**2*n**2)` | `A*(-1)*me*el**4/(eps0**2*hbar**2*n**2)` |  |  | fail | 不可判定 |
| phys-ideal-gas | base | `n*R*T/V` | `R*n*T/V` | 0.00606509 | 0.00805481 | pass | 不一致 (偏差 0.000608) |
| phys-index-vacuum | challenge | `1/sqrt(eps*mu)` | `1/sqrt(eps*mu)` | 0.0212973 | 0.0185376 | pass | 结构相同 |
| phys-joule-heating | base | `I**2*R` | `I**2*R` | 0.00528938 | 0.00530535 | pass | 结构相同 |
| phys-kinetic-energy | base | `m*v**2/2` | `0.5*m*v**2` | 0.00508397 | 0.0052265 | pass | 数值等价 |
| phys-ohm | base | `I*R` | `I*R` | 0.00736598 | 0.00621277 | pass | 结构相同 |
| phys-pendulum-exact | challenge | `2*pi*sqrt(L/g)*(1 + theta0**2/16)` | `2*3.141592653589793*sqrt(L/g)*(1+theta0**2/16+11*theta0**4/3072+theta0**2/16*theta0**2)` | 0.132816 | 0.0740181 | pass | 不一致 (偏差 0.0933) |
| phys-pendulum-period | base | `2*pi*sqrt(L/g)` | `2*3.141592653589793*sqrt(L/g)` | 0.0118581 | 0.00998851 | pass | 数值等价 |
| phys-radioactive-decay | challenge | `N0*exp(-t/tau)` | `N0*exp(-t/tau)` | 0.00476177 | 0.00313099 | pass | 结构相同 |
| phys-snells-law | challenge | `d*sin(theta2)/sqrt(1-(n*sin(theta2))**2)` | `d*tan(theta2)*(1+(n-1)*theta2)` | 0.0420306 | 0.0589524 | pass | 不一致 (偏差 0.0531) |
| phys-spring-energy | base | `k*x**2/2` | `0.5*k*x**2` | 0.0057766 | 0.00579946 | pass | 数值等价 |
| phys-stefan-boltzmann | base | `sigma*A*T**4` | `sigma*A*T**4` | 0.00553959 | 0.00546602 | pass | 结构相同 |
| phys-surface-gravity | base | `G*M/R**2` | `G*M/R**2` | 0.00527124 | 0.00500282 | pass | 结构相同 |
| phys-transit-depth | challenge | `A*(Rp/Rs)**2` | `A*Rp**2/Rs**2` | 0.00564293 | 0.00466753 | pass | 数值等价 |
| phys-weight | base | `m*g` | `m*g` | 0.00869578 | 0.00575099 | pass | 结构相同 |

## 四、如实说明（不掩盖空缺）

- 有 1 个候选式运行标了 agh-llm 但**没有** AGH 会话号（provenance_bound=false），已单列不计入绑定层：标签是自报的，只有绑定到真实会话才可核对。请让调用方设置 FORMULA_AGH_SESSION_ID（见 harness/run_agent_discovery.ps1）。

