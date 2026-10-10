# 证据归档索引（M2 维护）

运行目录 runs/<run_id>/ 一经生成即视为不可变证据；本目录保存其只读副本。
命名规则：<日期>_<任务编号>_<类型>_<序号>

- 最近更新（UTC）：2026-10-10T03:29:13+00:00
- 运行总数：257
- 本次新增归档：141
- 未变化（幂等跳过）：116
- 一致性：通过（无孤立文件）

## 假设来源分布（决定哪些运行能支撑「自主发现」）

| 来源 | 条数 | 含义 |
|---|---|---|
| agh-llm | 115 | 假设由 Agnes 模型经 AGH 命令工具提出（可用于支撑自主闭环） |
| cli | 2 | 公式由人在命令行给出 |
| fixture-variant | 22 | 人为构造的结构错误候选式（判别力测试） |
| reference | 22 | 标准答案原样送回引擎（金标准自检） |
| unclassified | 96 | 未标注来源——不计入任何能力声明，需补齐 |

未标注来源的运行（前 20 条，需补齐后才能计入任何能力声明）：

- demo-accepted-01
- discrim-ref-phys-buoyancy
- discrim-ref-phys-coulomb
- discrim-ref-phys-cyclotron
- discrim-ref-phys-elastic-pe
- discrim-ref-phys-energy-shift
- discrim-ref-phys-grav-potential-energy
- discrim-ref-phys-gravitation
- discrim-ref-phys-hydrogen-level
- discrim-ref-phys-ideal-gas
- discrim-ref-phys-index-vacuum
- discrim-ref-phys-joule-heating
- discrim-ref-phys-kinetic-energy
- discrim-ref-phys-ohm
- discrim-ref-phys-pendulum-exact
- discrim-ref-phys-pendulum-period
- discrim-ref-phys-radioactive-decay
- discrim-ref-phys-snells-law
- discrim-ref-phys-spring-energy
- discrim-ref-phys-stefan-boltzmann

| run_id | 任务 | 判定 | 来源 | 归档目录 | 可独立复算 |
|---|---|---|---|---|---|
| 0 | phys-ideal-gas | rejected | agh-llm | runs/20261009_phys-ideal-gas_rejected_01 | agree |
| 20261009-214409-phys-weight | phys-weight | rejected | agh-llm | runs/20261009_phys-weight_rejected_01 | agree |
| 20261009-214613-phys-weight | phys-weight | accepted | agh-llm | runs/20261009_phys-weight_accepted_01 | agree |
| 20261009-214719-phys-buoyancy | phys-buoyancy | accepted | agh-llm | runs/20261009_phys-buoyancy_accepted_01 | agree |
| 20261009-214749-phys-coulomb | phys-coulomb | rejected | agh-llm | runs/20261009_phys-coulomb_rejected_01 | agree |
| 20261009-214756-phys-coulomb | phys-coulomb | accepted | agh-llm | runs/20261009_phys-coulomb_accepted_01 | agree |
| 20261009-214822-phys-cyclotron | phys-cyclotron | accepted | agh-llm | runs/20261009_phys-cyclotron_accepted_01 | agree |
| 20261009-214857-phys-cyclotron | phys-cyclotron | accepted | agh-llm | runs/20261009_phys-cyclotron_accepted_02 | agree |
| 20261009-214923-phys-elastic-pe | phys-elastic-pe | rejected | agh-llm | runs/20261009_phys-elastic-pe_rejected_01 | agree |
| 20261009-214935-phys-elastic-pe | phys-elastic-pe | accepted | agh-llm | runs/20261009_phys-elastic-pe_accepted_01 | agree |
| 20261009-215018-phys-energy-shift | phys-energy-shift | accepted | agh-llm | runs/20261009_phys-energy-shift_accepted_01 | agree |
| 20261009-220108-phys-grav-potential-energy | phys-grav-potential-energy | rejected | agh-llm | runs/20261009_phys-grav-potential-energy_rejected_01 | agree |
| 20261009-220200-phys-grav-potential-energy | phys-grav-potential-energy | accepted | agh-llm | runs/20261009_phys-grav-potential-energy_accepted_01 | agree |
| 20261009-220218-phys-gravitation | phys-gravitation | accepted | agh-llm | runs/20261009_phys-gravitation_accepted_01 | agree |
| 20261009-220340-phys-index-vacuum | phys-index-vacuum | accepted | agh-llm | runs/20261009_phys-index-vacuum_accepted_01 | agree |
| 20261009-220344-phys-index-vacuum | phys-index-vacuum | accepted | agh-llm | runs/20261009_phys-index-vacuum_accepted_02 | agree |
| 20261009-220358-phys-joule-heating | phys-joule-heating | rejected | agh-llm | runs/20261009_phys-joule-heating_rejected_01 | agree |
| 20261009-220404-phys-joule-heating | phys-joule-heating | accepted | agh-llm | runs/20261009_phys-joule-heating_accepted_01 | agree |
| 20261009-220421-phys-kinetic-energy | phys-kinetic-energy | accepted | agh-llm | runs/20261009_phys-kinetic-energy_accepted_01 | agree |
| 20261009-220450-phys-ohm | phys-ohm | accepted | agh-llm | runs/20261009_phys-ohm_accepted_01 | agree |
| 20261009-220517-phys-pendulum-exact | phys-pendulum-exact | rejected | agh-llm | runs/20261009_phys-pendulum-exact_rejected_01 | agree |
| 20261009-220522-phys-pendulum-exact | phys-pendulum-exact | rejected | agh-llm | runs/20261009_phys-pendulum-exact_rejected_02 | agree |
| 20261009-220530-phys-pendulum-exact | phys-pendulum-exact | accepted | agh-llm | runs/20261009_phys-pendulum-exact_accepted_01 | agree |
| 20261009-220616-phys-pendulum-period | phys-pendulum-period | rejected | agh-llm | runs/20261009_phys-pendulum-period_rejected_01 | agree |
| 20261009-220633-phys-pendulum-period | phys-pendulum-period | accepted | agh-llm | runs/20261009_phys-pendulum-period_accepted_01 | agree |
| 20261009-220743-phys-radioactive-decay | phys-radioactive-decay | rejected | agh-llm | runs/20261009_phys-radioactive-decay_rejected_01 | agree |
| 20261009-220836-phys-radioactive-decay | phys-radioactive-decay | rejected | agh-llm | runs/20261009_phys-radioactive-decay_rejected_02 | agree |
| 20261009-220841-phys-radioactive-decay | phys-radioactive-decay | accepted | agh-llm | runs/20261009_phys-radioactive-decay_accepted_01 | agree |
| 20261009-220848-phys-radioactive-decay | phys-radioactive-decay | accepted | agh-llm | runs/20261009_phys-radioactive-decay_accepted_02 | agree |
| 20261009-220913-phys-radioactive-decay | phys-radioactive-decay | accepted | agh-llm | runs/20261009_phys-radioactive-decay_accepted_03 | agree |
| 20261009-221042-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_01 | agree |
| 20261009-221048-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_02 | agree |
| 20261009-221121-phys-spring-energy | phys-spring-energy | accepted | agh-llm | runs/20261009_phys-spring-energy_accepted_01 | agree |
| 20261009-221200-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_01 | agree |
| 20261009-221203-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_02 | agree |
| 20261009-221205-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_03 | agree |
| 20261009-221207-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_04 | agree |
| 20261009-221209-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_05 | agree |
| 20261009-221220-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_06 | agree |
| 20261009-221223-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_07 | agree |
| 20261009-221231-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_08 | agree |
| 20261009-221311-phys-surface-gravity | phys-surface-gravity | rejected | agh-llm | runs/20261009_phys-surface-gravity_rejected_01 | agree |
| 20261009-221314-phys-surface-gravity | phys-surface-gravity | accepted | agh-llm | runs/20261009_phys-surface-gravity_accepted_01 | agree |
| 20261009-221339-phys-weight | phys-weight | accepted | agh-llm | runs/20261009_phys-weight_accepted_02 | agree |
| 20261009-221447-phys-hydrogen-level | phys-hydrogen-level | rejected | agh-llm | runs/20261009_phys-hydrogen-level_rejected_01 | missing-formula |
| 20261009-221613-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_03 | agree |
| 20261009-221622-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_04 | agree |
| 20261009-221636-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_05 | agree |
| 20261009-221649-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_06 | agree |
| 20261009-221715-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_09 | agree |
| 20261009-221751-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_10 | agree |
| 20261009-221812-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_11 | agree |
| 20261009-221907-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_12 | agree |
| 20261009-221922-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_13 | agree |
| 20261009-222001-phys-transit-depth | phys-transit-depth | rejected | agh-llm | runs/20261009_phys-transit-depth_rejected_01 | agree |
| 20261009-222014-phys-transit-depth | phys-transit-depth | accepted | agh-llm | runs/20261009_phys-transit-depth_accepted_01 | agree |
| 20261009-223204-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_11 | agree |
| 20261009-223213-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_12 | agree |
| 20261009-223219-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_13 | agree |
| 20261009-223243-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_14 | agree |
| 20261009-223255-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_15 | agree |
| 20261009-223310-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_16 | agree |
| 20261009-223333-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_17 | agree |
| 20261009-223340-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_18 | agree |
| 20261009-223349-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_19 | agree |
| 20261009-223403-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_20 | agree |
| 20261009-223414-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_21 | agree |
| 20261009-223423-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_22 | agree |
| 20261009-223517-phys-stefan-boltzmann | phys-stefan-boltzmann | accepted | agh-llm | runs/20261009_phys-stefan-boltzmann_accepted_03 | agree |
| 20261009-223549-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_17 | agree |
| 20261009-223609-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_18 | agree |
| 20261009-223617-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_19 | agree |
| 20261009-223627-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_20 | agree |
| 20261009-223639-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_21 | agree |
| 20261009-223850-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_22 | agree |
| 20261009-223857-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_23 | agree |
| 20261009-223905-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_24 | agree |
| 20261009-223914-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_25 | agree |
| 20261009-223920-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_26 | agree |
| 20261009-223926-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_27 | agree |
| 20261009-225105-phys-weight | phys-weight | accepted | agh-llm | runs/20261009_phys-weight_accepted_05 | agree |
| 20261009-225213-phys-buoyancy | phys-buoyancy | accepted | agh-llm | runs/20261009_phys-buoyancy_accepted_04 | agree |
| 20261009-225239-phys-coulomb | phys-coulomb | accepted | agh-llm | runs/20261009_phys-coulomb_accepted_04 | agree |
| 20261009-225303-phys-elastic-pe | phys-elastic-pe | accepted | agh-llm | runs/20261009_phys-elastic-pe_accepted_04 | agree |
| 20261009-225328-phys-energy-shift | phys-energy-shift | rejected | agh-llm | runs/20261009_phys-energy-shift_rejected_04 | agree |
| 20261009-225332-phys-energy-shift | phys-energy-shift | accepted | agh-llm | runs/20261009_phys-energy-shift_accepted_04 | agree |
| 20261009-225421-phys-grav-potential-energy | phys-grav-potential-energy | rejected | agh-llm | runs/20261009_phys-grav-potential-energy_rejected_04 | agree |
| 20261009-225424-phys-grav-potential-energy | phys-grav-potential-energy | accepted | agh-llm | runs/20261009_phys-grav-potential-energy_accepted_04 | agree |
| 20261009-225452-phys-gravitation | phys-gravitation | accepted | agh-llm | runs/20261009_phys-gravitation_accepted_05 | agree |
| 20261009-225535-phys-hydrogen-level | phys-hydrogen-level | rejected | agh-llm | runs/20261009_phys-hydrogen-level_rejected_04 | agree |
| 20261009-225546-phys-hydrogen-level | phys-hydrogen-level | rejected | agh-llm | runs/20261009_phys-hydrogen-level_rejected_05 | agree |
| 20261009-225604-phys-ideal-gas | phys-ideal-gas | accepted | agh-llm | runs/20261009_phys-ideal-gas_accepted_04 | agree |
| 20261009-225622-phys-index-vacuum | phys-index-vacuum | accepted | agh-llm | runs/20261009_phys-index-vacuum_accepted_05 | agree |
| 20261009-225649-phys-joule-heating | phys-joule-heating | accepted | agh-llm | runs/20261009_phys-joule-heating_accepted_04 | agree |
| 20261009-225715-phys-kinetic-energy | phys-kinetic-energy | accepted | agh-llm | runs/20261009_phys-kinetic-energy_accepted_04 | agree |
| 20261009-225731-phys-ohm | phys-ohm | accepted | agh-llm | runs/20261009_phys-ohm_accepted_04 | agree |
| 20261009-225754-phys-pendulum-period | phys-pendulum-period | accepted | agh-llm | runs/20261009_phys-pendulum-period_accepted_04 | agree |
| 20261009-225824-phys-radioactive-decay | phys-radioactive-decay | accepted | agh-llm | runs/20261009_phys-radioactive-decay_accepted_06 | agree |
| 20261009-225845-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_28 | agree |
| 20261009-225850-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_29 | agree |
| 20261009-225855-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_30 | agree |
| 20261009-225901-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_31 | agree |
| 20261009-225910-phys-snells-law | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_32 | agree |
| 20261009-225930-phys-spring-energy | phys-spring-energy | accepted | agh-llm | runs/20261009_phys-spring-energy_accepted_04 | agree |
| 20261009-230000-phys-stefan-boltzmann | phys-stefan-boltzmann | accepted | agh-llm | runs/20261009_phys-stefan-boltzmann_accepted_04 | agree |
| 20261009-230022-phys-surface-gravity | phys-surface-gravity | accepted | agh-llm | runs/20261009_phys-surface-gravity_accepted_04 | agree |
| 20261009-230058-phys-transit-depth | phys-transit-depth | accepted | agh-llm | runs/20261009_phys-transit-depth_accepted_04 | agree |
| 20261009-230224-phys-weight | phys-weight | accepted | agh-llm | runs/20261009_phys-weight_accepted_06 | agree |
| 5.67e-8 | phys-stefan-boltzmann | rejected | agh-llm | runs/20261009_phys-stefan-boltzmann_rejected_14 | agree |
| 8.314462618 | phys-ideal-gas | accepted | agh-llm | runs/20261009_phys-ideal-gas_accepted_01 | agree |
| R | phys-ideal-gas | rejected | agh-llm | runs/20261009_phys-ideal-gas_rejected_02 | agree |
| a | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_07 | agree |
| d | phys-snells-law | rejected | agh-llm | runs/20261009_phys-snells-law_rejected_08 | agree |
| demo-accepted-01 | mech-gravity | accepted | unclassified | runs/20261009_mech-gravity_accepted_01 | unresolvable |
| discrim-ref-phys-buoyancy | phys-buoyancy | accepted | unclassified | runs/20261009_phys-buoyancy_accepted_02 | agree |
| discrim-ref-phys-coulomb | phys-coulomb | accepted | unclassified | runs/20261009_phys-coulomb_accepted_02 | stale-metrics |
| discrim-ref-phys-cyclotron | phys-cyclotron | accepted | unclassified | runs/20261009_phys-cyclotron_accepted_03 | agree |
| discrim-ref-phys-elastic-pe | phys-elastic-pe | accepted | unclassified | runs/20261009_phys-elastic-pe_accepted_02 | agree |
| discrim-ref-phys-energy-shift | phys-energy-shift | accepted | unclassified | runs/20261009_phys-energy-shift_accepted_02 | agree |
| discrim-ref-phys-grav-potential-energy | phys-grav-potential-energy | accepted | unclassified | runs/20261009_phys-grav-potential-energy_accepted_02 | stale-metrics |
| discrim-ref-phys-gravitation | phys-gravitation | accepted | unclassified | runs/20261009_phys-gravitation_accepted_02 | stale-metrics |
| discrim-ref-phys-hydrogen-level | phys-hydrogen-level | accepted | unclassified | runs/20261009_phys-hydrogen-level_accepted_01 | agree |
| discrim-ref-phys-ideal-gas | phys-ideal-gas | accepted | unclassified | runs/20261009_phys-ideal-gas_accepted_02 | agree |
| discrim-ref-phys-index-vacuum | phys-index-vacuum | accepted | unclassified | runs/20261009_phys-index-vacuum_accepted_03 | agree |
| discrim-ref-phys-joule-heating | phys-joule-heating | accepted | unclassified | runs/20261009_phys-joule-heating_accepted_02 | agree |
| discrim-ref-phys-kinetic-energy | phys-kinetic-energy | accepted | unclassified | runs/20261009_phys-kinetic-energy_accepted_02 | agree |
| discrim-ref-phys-ohm | phys-ohm | accepted | unclassified | runs/20261009_phys-ohm_accepted_02 | agree |
| discrim-ref-phys-pendulum-exact | phys-pendulum-exact | accepted | unclassified | runs/20261009_phys-pendulum-exact_accepted_02 | agree |
| discrim-ref-phys-pendulum-period | phys-pendulum-period | accepted | unclassified | runs/20261009_phys-pendulum-period_accepted_02 | agree |
| discrim-ref-phys-radioactive-decay | phys-radioactive-decay | accepted | unclassified | runs/20261009_phys-radioactive-decay_accepted_04 | agree |
| discrim-ref-phys-snells-law | phys-snells-law | accepted | unclassified | runs/20261009_phys-snells-law_accepted_01 | agree |
| discrim-ref-phys-spring-energy | phys-spring-energy | accepted | unclassified | runs/20261009_phys-spring-energy_accepted_02 | agree |
| discrim-ref-phys-stefan-boltzmann | phys-stefan-boltzmann | accepted | unclassified | runs/20261009_phys-stefan-boltzmann_accepted_01 | agree |
| discrim-ref-phys-surface-gravity | phys-surface-gravity | accepted | unclassified | runs/20261009_phys-surface-gravity_accepted_02 | agree |
| discrim-ref-phys-transit-depth | phys-transit-depth | accepted | unclassified | runs/20261009_phys-transit-depth_accepted_02 | agree |
| discrim-ref-phys-weight | phys-weight | accepted | unclassified | runs/20261009_phys-weight_accepted_03 | agree |
| discrim-wrong-phys-buoyancy | phys-buoyancy | rejected | unclassified | runs/20261009_phys-buoyancy_rejected_01 | agree |
| discrim-wrong-phys-coulomb | phys-coulomb | rejected | unclassified | runs/20261009_phys-coulomb_rejected_02 | agree |
| discrim-wrong-phys-cyclotron | phys-cyclotron | rejected | unclassified | runs/20261009_phys-cyclotron_rejected_01 | agree |
| discrim-wrong-phys-elastic-pe | phys-elastic-pe | rejected | unclassified | runs/20261009_phys-elastic-pe_rejected_02 | agree |
| discrim-wrong-phys-energy-shift | phys-energy-shift | rejected | unclassified | runs/20261009_phys-energy-shift_rejected_01 | agree |
| discrim-wrong-phys-grav-potential-energy | phys-grav-potential-energy | rejected | unclassified | runs/20261009_phys-grav-potential-energy_rejected_02 | agree |
| discrim-wrong-phys-gravitation | phys-gravitation | rejected | unclassified | runs/20261009_phys-gravitation_rejected_01 | agree |
| discrim-wrong-phys-hydrogen-level | phys-hydrogen-level | rejected | unclassified | runs/20261009_phys-hydrogen-level_rejected_02 | agree |
| discrim-wrong-phys-ideal-gas | phys-ideal-gas | rejected | unclassified | runs/20261009_phys-ideal-gas_rejected_03 | agree |
| discrim-wrong-phys-index-vacuum | phys-index-vacuum | rejected | unclassified | runs/20261009_phys-index-vacuum_rejected_01 | agree |
| discrim-wrong-phys-joule-heating | phys-joule-heating | rejected | unclassified | runs/20261009_phys-joule-heating_rejected_02 | agree |
| discrim-wrong-phys-kinetic-energy | phys-kinetic-energy | rejected | unclassified | runs/20261009_phys-kinetic-energy_rejected_01 | agree |
| discrim-wrong-phys-ohm | phys-ohm | rejected | unclassified | runs/20261009_phys-ohm_rejected_01 | agree |
| discrim-wrong-phys-pendulum-exact | phys-pendulum-exact | rejected | unclassified | runs/20261009_phys-pendulum-exact_rejected_03 | agree |
| discrim-wrong-phys-pendulum-period | phys-pendulum-period | rejected | unclassified | runs/20261009_phys-pendulum-period_rejected_02 | agree |
| discrim-wrong-phys-radioactive-decay | phys-radioactive-decay | rejected | unclassified | runs/20261009_phys-radioactive-decay_rejected_03 | agree |
| discrim-wrong-phys-snells-law | phys-snells-law | rejected | unclassified | runs/20261009_phys-snells-law_rejected_09 | agree |
| discrim-wrong-phys-spring-energy | phys-spring-energy | rejected | unclassified | runs/20261009_phys-spring-energy_rejected_01 | agree |
| discrim-wrong-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | unclassified | runs/20261009_phys-stefan-boltzmann_rejected_15 | agree |
| discrim-wrong-phys-surface-gravity | phys-surface-gravity | rejected | unclassified | runs/20261009_phys-surface-gravity_rejected_02 | agree |
| discrim-wrong-phys-transit-depth | phys-transit-depth | rejected | unclassified | runs/20261009_phys-transit-depth_rejected_02 | agree |
| discrim-wrong-phys-weight | phys-weight | rejected | unclassified | runs/20261009_phys-weight_rejected_02 | agree |
| extrap-phys-coulomb | phys-coulomb | rejected | unclassified | runs/20261010_phys-coulomb_rejected_01 | out-of-scope |
| extrap-phys-gravitation | phys-gravitation | rejected | unclassified | runs/20261010_phys-gravitation_rejected_01 | out-of-scope |
| extrap-phys-hydrogen-level | phys-hydrogen-level | rejected | unclassified | runs/20261010_phys-hydrogen-level_rejected_01 | out-of-scope |
| extrap-phys-pendulum-exact | phys-pendulum-exact | accepted | unclassified | runs/20261010_phys-pendulum-exact_accepted_01 | out-of-scope |
| extrap-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | unclassified | runs/20261010_phys-stefan-boltzmann_rejected_01 | out-of-scope |
| extrap-phys-surface-gravity | phys-surface-gravity | rejected | unclassified | runs/20261010_phys-surface-gravity_rejected_01 | out-of-scope |
| h | phys-energy-shift | rejected | agh-llm | runs/20261009_phys-energy-shift_rejected_02 | agree |
| hbar | phys-hydrogen-level | rejected | agh-llm | runs/20261009_phys-hydrogen-level_rejected_06 | agree |
| negctl-summary | negative-control | accepted | unclassified | runs/20261009_negative-control_accepted_01 | unresolvable |
| phys-gravitation-cand01 | phys-gravitation | accepted | cli | runs/20261009_phys-gravitation_accepted_03 | stale-metrics |
| phys-gravitation-cand02 | phys-gravitation | rejected | cli | runs/20261009_phys-gravitation_rejected_02 | stale-metrics |
| refcheck-phys-buoyancy | phys-buoyancy | accepted | reference | runs/20261009_phys-buoyancy_refcheck_01 | agree |
| refcheck-phys-coulomb | phys-coulomb | accepted | reference | runs/20261009_phys-coulomb_refcheck_01 | agree |
| refcheck-phys-cyclotron | phys-cyclotron | accepted | reference | runs/20261009_phys-cyclotron_refcheck_01 | agree |
| refcheck-phys-elastic-pe | phys-elastic-pe | accepted | reference | runs/20261009_phys-elastic-pe_refcheck_01 | agree |
| refcheck-phys-energy-shift | phys-energy-shift | accepted | reference | runs/20261009_phys-energy-shift_refcheck_01 | agree |
| refcheck-phys-grav-potential-energy | phys-grav-potential-energy | accepted | reference | runs/20261009_phys-grav-potential-energy_refcheck_01 | agree |
| refcheck-phys-gravitation | phys-gravitation | accepted | reference | runs/20261009_phys-gravitation_refcheck_01 | agree |
| refcheck-phys-hydrogen-level | phys-hydrogen-level | accepted | reference | runs/20261009_phys-hydrogen-level_refcheck_01 | agree |
| refcheck-phys-ideal-gas | phys-ideal-gas | accepted | reference | runs/20261009_phys-ideal-gas_refcheck_01 | agree |
| refcheck-phys-index-vacuum | phys-index-vacuum | accepted | reference | runs/20261009_phys-index-vacuum_refcheck_01 | agree |
| refcheck-phys-joule-heating | phys-joule-heating | accepted | reference | runs/20261009_phys-joule-heating_refcheck_01 | agree |
| refcheck-phys-kinetic-energy | phys-kinetic-energy | accepted | reference | runs/20261009_phys-kinetic-energy_refcheck_01 | agree |
| refcheck-phys-ohm | phys-ohm | accepted | reference | runs/20261009_phys-ohm_refcheck_01 | agree |
| refcheck-phys-pendulum-exact | phys-pendulum-exact | accepted | reference | runs/20261009_phys-pendulum-exact_refcheck_01 | agree |
| refcheck-phys-pendulum-period | phys-pendulum-period | accepted | reference | runs/20261009_phys-pendulum-period_refcheck_01 | agree |
| refcheck-phys-radioactive-decay | phys-radioactive-decay | accepted | reference | runs/20261009_phys-radioactive-decay_refcheck_01 | agree |
| refcheck-phys-snells-law | phys-snells-law | accepted | reference | runs/20261009_phys-snells-law_refcheck_01 | agree |
| refcheck-phys-spring-energy | phys-spring-energy | accepted | reference | runs/20261009_phys-spring-energy_refcheck_01 | agree |
| refcheck-phys-stefan-boltzmann | phys-stefan-boltzmann | accepted | reference | runs/20261009_phys-stefan-boltzmann_refcheck_01 | agree |
| refcheck-phys-surface-gravity | phys-surface-gravity | accepted | reference | runs/20261009_phys-surface-gravity_refcheck_01 | agree |
| refcheck-phys-transit-depth | phys-transit-depth | accepted | reference | runs/20261009_phys-transit-depth_refcheck_01 | agree |
| refcheck-phys-weight | phys-weight | accepted | reference | runs/20261009_phys-weight_refcheck_01 | agree |
| scale-ref-phys-buoyancy | phys-buoyancy | accepted | unclassified | runs/20261009_phys-buoyancy_accepted_03 | out-of-scope |
| scale-ref-phys-coulomb | phys-coulomb | accepted | unclassified | runs/20261009_phys-coulomb_accepted_03 | out-of-scope |
| scale-ref-phys-cyclotron | phys-cyclotron | accepted | unclassified | runs/20261009_phys-cyclotron_accepted_04 | out-of-scope |
| scale-ref-phys-elastic-pe | phys-elastic-pe | accepted | unclassified | runs/20261009_phys-elastic-pe_accepted_03 | out-of-scope |
| scale-ref-phys-energy-shift | phys-energy-shift | accepted | unclassified | runs/20261009_phys-energy-shift_accepted_03 | out-of-scope |
| scale-ref-phys-grav-potential-energy | phys-grav-potential-energy | accepted | unclassified | runs/20261009_phys-grav-potential-energy_accepted_03 | out-of-scope |
| scale-ref-phys-gravitation | phys-gravitation | accepted | unclassified | runs/20261009_phys-gravitation_accepted_04 | out-of-scope |
| scale-ref-phys-hydrogen-level | phys-hydrogen-level | accepted | unclassified | runs/20261009_phys-hydrogen-level_accepted_02 | out-of-scope |
| scale-ref-phys-ideal-gas | phys-ideal-gas | accepted | unclassified | runs/20261009_phys-ideal-gas_accepted_03 | out-of-scope |
| scale-ref-phys-index-vacuum | phys-index-vacuum | accepted | unclassified | runs/20261009_phys-index-vacuum_accepted_04 | out-of-scope |
| scale-ref-phys-joule-heating | phys-joule-heating | accepted | unclassified | runs/20261009_phys-joule-heating_accepted_03 | out-of-scope |
| scale-ref-phys-kinetic-energy | phys-kinetic-energy | accepted | unclassified | runs/20261009_phys-kinetic-energy_accepted_03 | out-of-scope |
| scale-ref-phys-ohm | phys-ohm | accepted | unclassified | runs/20261009_phys-ohm_accepted_03 | out-of-scope |
| scale-ref-phys-pendulum-exact | phys-pendulum-exact | accepted | unclassified | runs/20261009_phys-pendulum-exact_accepted_03 | out-of-scope |
| scale-ref-phys-pendulum-period | phys-pendulum-period | accepted | unclassified | runs/20261009_phys-pendulum-period_accepted_03 | out-of-scope |
| scale-ref-phys-radioactive-decay | phys-radioactive-decay | accepted | unclassified | runs/20261009_phys-radioactive-decay_accepted_05 | out-of-scope |
| scale-ref-phys-snells-law | phys-snells-law | accepted | unclassified | runs/20261009_phys-snells-law_accepted_02 | out-of-scope |
| scale-ref-phys-spring-energy | phys-spring-energy | accepted | unclassified | runs/20261009_phys-spring-energy_accepted_03 | out-of-scope |
| scale-ref-phys-stefan-boltzmann | phys-stefan-boltzmann | accepted | unclassified | runs/20261009_phys-stefan-boltzmann_accepted_02 | out-of-scope |
| scale-ref-phys-surface-gravity | phys-surface-gravity | accepted | unclassified | runs/20261009_phys-surface-gravity_accepted_03 | out-of-scope |
| scale-ref-phys-transit-depth | phys-transit-depth | accepted | unclassified | runs/20261009_phys-transit-depth_accepted_03 | out-of-scope |
| scale-ref-phys-weight | phys-weight | accepted | unclassified | runs/20261009_phys-weight_accepted_04 | out-of-scope |
| scale-variant-phys-buoyancy | phys-buoyancy | rejected | unclassified | runs/20261009_phys-buoyancy_rejected_02 | out-of-scope |
| scale-variant-phys-coulomb | phys-coulomb | rejected | unclassified | runs/20261009_phys-coulomb_rejected_03 | out-of-scope |
| scale-variant-phys-cyclotron | phys-cyclotron | rejected | unclassified | runs/20261009_phys-cyclotron_rejected_02 | out-of-scope |
| scale-variant-phys-elastic-pe | phys-elastic-pe | rejected | unclassified | runs/20261009_phys-elastic-pe_rejected_03 | out-of-scope |
| scale-variant-phys-energy-shift | phys-energy-shift | rejected | unclassified | runs/20261009_phys-energy-shift_rejected_03 | out-of-scope |
| scale-variant-phys-grav-potential-energy | phys-grav-potential-energy | rejected | unclassified | runs/20261009_phys-grav-potential-energy_rejected_03 | out-of-scope |
| scale-variant-phys-gravitation | phys-gravitation | rejected | unclassified | runs/20261009_phys-gravitation_rejected_03 | out-of-scope |
| scale-variant-phys-hydrogen-level | phys-hydrogen-level | rejected | unclassified | runs/20261009_phys-hydrogen-level_rejected_03 | out-of-scope |
| scale-variant-phys-ideal-gas | phys-ideal-gas | rejected | unclassified | runs/20261009_phys-ideal-gas_rejected_04 | out-of-scope |
| scale-variant-phys-index-vacuum | phys-index-vacuum | rejected | unclassified | runs/20261009_phys-index-vacuum_rejected_02 | out-of-scope |
| scale-variant-phys-joule-heating | phys-joule-heating | rejected | unclassified | runs/20261009_phys-joule-heating_rejected_03 | out-of-scope |
| scale-variant-phys-kinetic-energy | phys-kinetic-energy | rejected | unclassified | runs/20261009_phys-kinetic-energy_rejected_02 | out-of-scope |
| scale-variant-phys-ohm | phys-ohm | rejected | unclassified | runs/20261009_phys-ohm_rejected_02 | out-of-scope |
| scale-variant-phys-pendulum-exact | phys-pendulum-exact | rejected | unclassified | runs/20261009_phys-pendulum-exact_rejected_04 | out-of-scope |
| scale-variant-phys-pendulum-period | phys-pendulum-period | rejected | unclassified | runs/20261009_phys-pendulum-period_rejected_03 | out-of-scope |
| scale-variant-phys-radioactive-decay | phys-radioactive-decay | rejected | unclassified | runs/20261009_phys-radioactive-decay_rejected_04 | out-of-scope |
| scale-variant-phys-snells-law | phys-snells-law | rejected | unclassified | runs/20261009_phys-snells-law_rejected_10 | out-of-scope |
| scale-variant-phys-spring-energy | phys-spring-energy | rejected | unclassified | runs/20261009_phys-spring-energy_rejected_02 | out-of-scope |
| scale-variant-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | unclassified | runs/20261009_phys-stefan-boltzmann_rejected_16 | out-of-scope |
| scale-variant-phys-surface-gravity | phys-surface-gravity | rejected | unclassified | runs/20261009_phys-surface-gravity_rejected_03 | out-of-scope |
| scale-variant-phys-transit-depth | phys-transit-depth | rejected | unclassified | runs/20261009_phys-transit-depth_rejected_03 | out-of-scope |
| scale-variant-phys-weight | phys-weight | rejected | unclassified | runs/20261009_phys-weight_rejected_03 | out-of-scope |
| variant-phys-buoyancy | phys-buoyancy | rejected | fixture-variant | runs/20261009_phys-buoyancy_variant_01 | agree |
| variant-phys-coulomb | phys-coulomb | rejected | fixture-variant | runs/20261009_phys-coulomb_variant_01 | agree |
| variant-phys-cyclotron | phys-cyclotron | rejected | fixture-variant | runs/20261009_phys-cyclotron_variant_01 | agree |
| variant-phys-elastic-pe | phys-elastic-pe | rejected | fixture-variant | runs/20261009_phys-elastic-pe_variant_01 | agree |
| variant-phys-energy-shift | phys-energy-shift | rejected | fixture-variant | runs/20261009_phys-energy-shift_variant_01 | agree |
| variant-phys-grav-potential-energy | phys-grav-potential-energy | rejected | fixture-variant | runs/20261009_phys-grav-potential-energy_variant_01 | agree |
| variant-phys-gravitation | phys-gravitation | rejected | fixture-variant | runs/20261009_phys-gravitation_variant_01 | agree |
| variant-phys-hydrogen-level | phys-hydrogen-level | rejected | fixture-variant | runs/20261009_phys-hydrogen-level_variant_01 | agree |
| variant-phys-ideal-gas | phys-ideal-gas | rejected | fixture-variant | runs/20261009_phys-ideal-gas_variant_01 | agree |
| variant-phys-index-vacuum | phys-index-vacuum | rejected | fixture-variant | runs/20261009_phys-index-vacuum_variant_01 | agree |
| variant-phys-joule-heating | phys-joule-heating | rejected | fixture-variant | runs/20261009_phys-joule-heating_variant_01 | agree |
| variant-phys-kinetic-energy | phys-kinetic-energy | rejected | fixture-variant | runs/20261009_phys-kinetic-energy_variant_01 | agree |
| variant-phys-ohm | phys-ohm | rejected | fixture-variant | runs/20261009_phys-ohm_variant_01 | agree |
| variant-phys-pendulum-exact | phys-pendulum-exact | rejected | fixture-variant | runs/20261009_phys-pendulum-exact_variant_01 | agree |
| variant-phys-pendulum-period | phys-pendulum-period | rejected | fixture-variant | runs/20261009_phys-pendulum-period_variant_01 | agree |
| variant-phys-radioactive-decay | phys-radioactive-decay | rejected | fixture-variant | runs/20261009_phys-radioactive-decay_variant_01 | agree |
| variant-phys-snells-law | phys-snells-law | rejected | fixture-variant | runs/20261009_phys-snells-law_variant_01 | agree |
| variant-phys-spring-energy | phys-spring-energy | rejected | fixture-variant | runs/20261009_phys-spring-energy_variant_01 | agree |
| variant-phys-stefan-boltzmann | phys-stefan-boltzmann | rejected | fixture-variant | runs/20261009_phys-stefan-boltzmann_variant_01 | agree |
| variant-phys-surface-gravity | phys-surface-gravity | rejected | fixture-variant | runs/20261009_phys-surface-gravity_variant_01 | agree |
| variant-phys-transit-depth | phys-transit-depth | rejected | fixture-variant | runs/20261009_phys-transit-depth_variant_01 | agree |
| variant-phys-weight | phys-weight | rejected | fixture-variant | runs/20261009_phys-weight_variant_01 | agree |

