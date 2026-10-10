# 独立复算报告（M2）

对 runs/ 下每一次运行，从 data.csv 重新划分、重新拟合、重新判定，
再与原始 result.json 逐项比对。复算不复用原始拟合值。

- 生成时间（UTC）：2026-10-10T08:54:56+00:00
- 运行总数：332
- 判定一致：273
- 独立复算通过率：98.2%

- 属于标准三重验证、纳入复算统计的运行：278
- 由其它判定套件产出、不纳入统计的运行：50

| run_id | 状态 | 原判定 | 复算判定 | manifest | 说明 |
|---|---|---|---|---|---|
| 0 | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214409-phys-weight | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214613-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214719-phys-buoyancy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214749-phys-coulomb | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214756-phys-coulomb | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214822-phys-cyclotron | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214857-phys-cyclotron | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214923-phys-elastic-pe | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-214935-phys-elastic-pe | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-215018-phys-energy-shift | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220108-phys-grav-potential-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220200-phys-grav-potential-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220218-phys-gravitation | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220340-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220344-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220358-phys-joule-heating | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220404-phys-joule-heating | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220421-phys-kinetic-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220450-phys-ohm | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220517-phys-pendulum-exact | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220522-phys-pendulum-exact | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220530-phys-pendulum-exact | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220616-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220633-phys-pendulum-period | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220743-phys-radioactive-decay | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220836-phys-radioactive-decay | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220841-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220848-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-220913-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221042-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221048-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221121-phys-spring-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221200-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221203-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221205-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221207-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221209-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221220-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221223-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221231-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221311-phys-surface-gravity | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221314-phys-surface-gravity | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221339-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221447-phys-hydrogen-level | missing-formula | rejected | - | ok | run.json 没有公式，无法复算 |
| 20261009-221613-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221622-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221636-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221649-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221715-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221751-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221812-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221907-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-221922-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-222001-phys-transit-depth | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-222014-phys-transit-depth | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223204-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223213-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223219-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223243-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223255-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223310-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223333-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223340-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223349-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223403-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223414-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223423-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223517-phys-stefan-boltzmann | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223549-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223609-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223617-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223627-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223639-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223850-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223857-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223905-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223914-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223920-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-223926-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225105-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225213-phys-buoyancy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225239-phys-coulomb | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225303-phys-elastic-pe | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225328-phys-energy-shift | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225332-phys-energy-shift | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225421-phys-grav-potential-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225424-phys-grav-potential-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225452-phys-gravitation | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225535-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225546-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225604-phys-ideal-gas | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225622-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225649-phys-joule-heating | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225715-phys-kinetic-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225731-phys-ohm | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225754-phys-pendulum-period | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225824-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225845-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225850-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225855-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225901-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225910-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-225930-phys-spring-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-230000-phys-stefan-boltzmann | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-230022-phys-surface-gravity | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-230058-phys-transit-depth | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261009-230224-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131214-phys-buoyancy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131321-phys-coulomb | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131349-phys-cyclotron | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131412-phys-elastic-pe | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131446-phys-energy-shift | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131513-phys-grav-potential-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131517-phys-grav-potential-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131537-phys-gravitation | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131558-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131618-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131621-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131629-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131631-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131650-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131653-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131656-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131700-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131702-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131711-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131714-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131725-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131727-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131729-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131732-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131734-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131737-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131739-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131742-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131746-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131749-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131751-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131755-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131815-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131818-phys-hydrogen-level | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131837-phys-ideal-gas | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131918-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-131939-phys-joule-heating | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132001-phys-kinetic-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132013-phys-kinetic-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132044-phys-ohm | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132107-phys-pendulum-exact | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132142-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132150-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132155-phys-pendulum-period | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132203-phys-buoyancy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132233-phys-coulomb | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132259-phys-cyclotron | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132408-phys-elastic-pe | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132425-phys-energy-shift | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132609-phys-grav-potential-energy | missing-formula | rejected | - | ok | run.json 没有公式，无法复算 |
| 20261010-132702-phys-grav-potential-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-132740-phys-gravitation | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133048-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133154-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133230-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133243-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133249-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133323-phys-ideal-gas | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133352-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133415-phys-joule-heating | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133440-phys-kinetic-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133504-phys-ohm | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133526-phys-pendulum-exact | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133529-phys-pendulum-exact | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133622-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133630-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-133950-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134503-phys-snells-law | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134546-phys-spring-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134613-phys-stefan-boltzmann | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134634-phys-surface-gravity | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134658-phys-transit-depth | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134708-phys-transit-depth | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 20261010-134740-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 5.67e-8 | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| 8.314462618 | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| R | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| a | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| c | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| d | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| demo-accepted-01 | unresolvable | accepted | - | 缺失/不完整 | 任务目录不存在，本次运行无法被独立复算（历史遗留运行） |
| discrim-ref-phys-buoyancy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-coulomb | stale-metrics | accepted | accepted | ok | 判定可复现，但指标数值对不上（metric 最大相对差 1 > 1e-03，参数最大相对差 0）：该证据很可能由旧口径或旧阈值产出，应重跑后再引用。 |
| discrim-ref-phys-cyclotron | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-elastic-pe | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-energy-shift | agree | accepted | accepted | ok | 判定与指标在 1e-03 容差内一致，仅浮点末位差异（metric 最大相对差 0.000896，参数最大相对差 0）。 |
| discrim-ref-phys-grav-potential-energy | stale-metrics | accepted | accepted | ok | 判定可复现，但指标数值对不上（metric 最大相对差 1 > 1e-03，参数最大相对差 0）：该证据很可能由旧口径或旧阈值产出，应重跑后再引用。 |
| discrim-ref-phys-gravitation | stale-metrics | accepted | accepted | ok | 判定可复现，但指标数值对不上（metric 最大相对差 0.001818 > 1e-03，参数最大相对差 0）：该证据很可能由旧口径或旧阈值产出，应重跑后再引用 |
| discrim-ref-phys-hydrogen-level | agree | accepted | accepted | ok | 判定与指标在 1e-03 容差内一致，仅浮点末位差异（metric 最大相对差 0.000268，参数最大相对差 0）。 |
| discrim-ref-phys-ideal-gas | agree | accepted | accepted | ok | 判定与指标在 1e-03 容差内一致，仅浮点末位差异（metric 最大相对差 0.000608，参数最大相对差 0）。 |
| discrim-ref-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-joule-heating | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-kinetic-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-ohm | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-pendulum-exact | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-pendulum-period | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-snells-law | agree | accepted | accepted | ok | 判定与指标在 1e-03 容差内一致，仅浮点末位差异（metric 最大相对差 0.000611，参数最大相对差 0）。 |
| discrim-ref-phys-spring-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-stefan-boltzmann | agree | accepted | accepted | ok | 判定与指标在 1e-03 容差内一致，仅浮点末位差异（metric 最大相对差 0.00021，参数最大相对差 0）。 |
| discrim-ref-phys-surface-gravity | agree | accepted | accepted | ok | 判定与指标在 1e-03 容差内一致，仅浮点末位差异（metric 最大相对差 0.000391，参数最大相对差 0）。 |
| discrim-ref-phys-transit-depth | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-ref-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-buoyancy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-coulomb | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-cyclotron | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-elastic-pe | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-energy-shift | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-grav-potential-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-gravitation | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-ideal-gas | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-index-vacuum | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-joule-heating | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-kinetic-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-ohm | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-pendulum-exact | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-radioactive-decay | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-spring-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-surface-gravity | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-transit-depth | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| discrim-wrong-phys-weight | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| extrap-phys-coulomb | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：extrapolation,narrow_fit），没有走标准三重验证，本模块不做一致性断言。若要作为提交证据，请用统一引擎重 |
| extrap-phys-gravitation | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：extrapolation,narrow_fit），没有走标准三重验证，本模块不做一致性断言。若要作为提交证据，请用统一引擎重 |
| extrap-phys-hydrogen-level | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：extrapolation,narrow_fit），没有走标准三重验证，本模块不做一致性断言。若要作为提交证据，请用统一引擎重 |
| extrap-phys-pendulum-exact | out-of-scope | accepted | rejected | ok | 该运行由其它判定套件产出（检验项：extrapolation,narrow_fit），没有走标准三重验证，本模块不做一致性断言。若要作为提交证据，请用统一引擎重 |
| extrap-phys-stefan-boltzmann | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：extrapolation,narrow_fit），没有走标准三重验证，本模块不做一致性断言。若要作为提交证据，请用统一引擎重 |
| extrap-phys-surface-gravity | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：extrapolation,narrow_fit），没有走标准三重验证，本模块不做一致性断言。若要作为提交证据，请用统一引擎重 |
| h | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| hbar | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| negctl-summary | unresolvable | accepted | - | ok | 任务目录不存在，本次运行无法被独立复算（历史遗留运行） |
| phys-gravitation-cand01 | stale-metrics | accepted | accepted | ok | 判定可复现，但指标数值对不上（metric 最大相对差 0.8 > 1e-03，参数最大相对差 0）：该证据很可能由旧口径或旧阈值产出，应重跑后再引用。 |
| phys-gravitation-cand02 | stale-metrics | rejected | rejected | ok | 判定可复现，但指标数值对不上（metric 最大相对差 0.8 > 1e-03，参数最大相对差 0）：该证据很可能由旧口径或旧阈值产出，应重跑后再引用。 |
| refcheck-phys-buoyancy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-coulomb | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-cyclotron | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-elastic-pe | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-energy-shift | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-grav-potential-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-gravitation | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-hydrogen-level | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-ideal-gas | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-index-vacuum | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-joule-heating | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-kinetic-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-ohm | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-pendulum-exact | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-pendulum-period | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-radioactive-decay | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-snells-law | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-spring-energy | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-stefan-boltzmann | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-surface-gravity | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-transit-depth | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| refcheck-phys-weight | agree | accepted | accepted | ok | 判定与全部检验项逐位一致，独立复算通过 |
| scale-ref-phys-buoyancy | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-V,scale-monotonic-rho,scale-scaling-V,scale-sca |
| scale-ref-phys-coulomb | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-r,scale-scaling-q1,scale-scaling-r,scale-sign-y |
| scale-ref-phys-cyclotron | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-B,scale-monotonic-m,scale-scaling-B,scale-scali |
| scale-ref-phys-elastic-pe | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-x,scale-scaling-c,scale-scaling-x,scale-scaling |
| scale-ref-phys-energy-shift | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-A,scale-monotonic-B,scale-scaling-h,scale-sign- |
| scale-ref-phys-grav-potential-energy | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-r,scale-scaling-r,scale-sign-y,scale-symmetry-m |
| scale-ref-phys-gravitation | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-r,scale-scaling-m1,scale-scaling-r,scale-sign-y |
| scale-ref-phys-hydrogen-level | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-n,scale-scaling-n,scale-sign-y），没有走标准三重验证，本模块不做 |
| scale-ref-phys-ideal-gas | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-V,scale-scaling-T,scale-scaling-V,scale-scaling |
| scale-ref-phys-index-vacuum | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-eps,scale-scaling-eps,scale-scaling-eps-mu,scal |
| scale-ref-phys-joule-heating | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-I,scale-monotonic-R,scale-scaling-I,scale-scali |
| scale-ref-phys-kinetic-energy | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-v,scale-scaling-m,scale-scaling-v,scale-scaling |
| scale-ref-phys-ohm | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-I,scale-monotonic-R,scale-scaling-I,scale-scali |
| scale-ref-phys-pendulum-exact | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-limit-theta0-to-0-0,scale-monotonic-theta0,scale-scaling- |
| scale-ref-phys-pendulum-period | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-L,scale-monotonic-g,scale-scaling-L,scale-scali |
| scale-ref-phys-radioactive-decay | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-limit-t-to-0-0,scale-monotonic-t,scale-monotonic-tau,scal |
| scale-ref-phys-snells-law | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-limit-theta2-to-0-0,scale-monotonic-theta2,scale-scaling- |
| scale-ref-phys-spring-energy | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-x,scale-scaling-k,scale-scaling-x,scale-scaling |
| scale-ref-phys-stefan-boltzmann | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-T,scale-scaling-A,scale-scaling-T,scale-scaling |
| scale-ref-phys-surface-gravity | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-R,scale-scaling-M,scale-scaling-R,scale-sign-y） |
| scale-ref-phys-transit-depth | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-invariance-Rp-Rs,scale-monotonic-Rp,scale-monotonic-Rs,sc |
| scale-ref-phys-weight | out-of-scope | accepted | accepted | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-g,scale-monotonic-m,scale-scaling-g,scale-scali |
| scale-variant-phys-buoyancy | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-V,scale-monotonic-rho,scale-scaling-V,scale-sca |
| scale-variant-phys-coulomb | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-r,scale-scaling-q1,scale-scaling-r,scale-sign-y |
| scale-variant-phys-cyclotron | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-B,scale-monotonic-m,scale-scaling-B,scale-scali |
| scale-variant-phys-elastic-pe | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-x,scale-scaling-c,scale-scaling-x,scale-scaling |
| scale-variant-phys-energy-shift | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-A,scale-monotonic-B,scale-scaling-h,scale-sign- |
| scale-variant-phys-grav-potential-energy | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-r,scale-scaling-r,scale-sign-y,scale-symmetry-m |
| scale-variant-phys-gravitation | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-r,scale-scaling-m1,scale-scaling-r,scale-sign-y |
| scale-variant-phys-hydrogen-level | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-n,scale-scaling-n,scale-sign-y），没有走标准三重验证，本模块不做 |
| scale-variant-phys-ideal-gas | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-V,scale-scaling-T,scale-scaling-V,scale-scaling |
| scale-variant-phys-index-vacuum | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-eps,scale-scaling-eps,scale-scaling-eps-mu,scal |
| scale-variant-phys-joule-heating | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-I,scale-monotonic-R,scale-scaling-I,scale-scali |
| scale-variant-phys-kinetic-energy | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-v,scale-scaling-m,scale-scaling-v,scale-scaling |
| scale-variant-phys-ohm | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-I,scale-monotonic-R,scale-scaling-I,scale-scali |
| scale-variant-phys-pendulum-exact | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-limit-theta0-to-0-0,scale-monotonic-theta0,scale-scaling- |
| scale-variant-phys-pendulum-period | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-L,scale-monotonic-g,scale-scaling-L,scale-scali |
| scale-variant-phys-radioactive-decay | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-limit-t-to-0-0,scale-monotonic-t,scale-monotonic-tau,scal |
| scale-variant-phys-snells-law | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-limit-theta2-to-0-0,scale-monotonic-theta2,scale-scaling- |
| scale-variant-phys-spring-energy | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-x,scale-scaling-k,scale-scaling-x,scale-scaling |
| scale-variant-phys-stefan-boltzmann | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-T,scale-scaling-A,scale-scaling-T,scale-scaling |
| scale-variant-phys-surface-gravity | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-R,scale-scaling-M,scale-scaling-R,scale-sign-y） |
| scale-variant-phys-transit-depth | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-invariance-Rp-Rs,scale-monotonic-Rp,scale-monotonic-Rs,sc |
| scale-variant-phys-weight | out-of-scope | rejected | rejected | ok | 该运行由其它判定套件产出（检验项：scale-monotonic-g,scale-monotonic-m,scale-scaling-g,scale-scali |
| variant-phys-buoyancy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-coulomb | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-cyclotron | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-elastic-pe | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-energy-shift | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-grav-potential-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-gravitation | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-hydrogen-level | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-ideal-gas | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-index-vacuum | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-joule-heating | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-kinetic-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-ohm | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-pendulum-exact | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-pendulum-period | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-radioactive-decay | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-snells-law | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-spring-energy | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-stefan-boltzmann | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-surface-gravity | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-transit-depth | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |
| variant-phys-weight | agree | rejected | rejected | ok | 判定与全部检验项逐位一致，独立复算通过 |

## 证据过期（判定可复现，但指标数值由旧口径产出）

以下运行的最终判定与新引擎一致，但记录的误差数值对不上——
通常是因为它们产生于判定口径/阈值变更之前。**引用前必须重跑**：
否则评审按当前口径复算会得到不同的数字。

- discrim-ref-phys-coulomb
- discrim-ref-phys-grav-potential-energy
- discrim-ref-phys-gravitation
- phys-gravitation-cand01
- phys-gravitation-cand02

## 无法复算的历史运行（如实列出，不隐藏）

以下运行目录的 run.json 指向的任务目录已不存在，属于早期迭代产物，**不可复现**，不作为提交证据使用：

- demo-accepted-01
- negctl-summary

