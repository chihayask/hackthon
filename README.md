# FORMULA-AGH

面向公开科学数据的**可验证公式发现智能体**。

> 2026 年江苏省 AI+科学与工程创新实践黑客松（高校组）
> 主赛道 B. 数学计算与科研智能体 ｜ 具体方向 B3. 科学计算与仿真
> 三名本科生：人工智能（M1 智能体底座与编排）、计算机科学与技术（M2 验证引擎与工程可靠性）、
> 机械设计制造及其自动化（M3 物理正确性与任务设计）

## 一句话说明

系统在 AgnesHarness（AGH）上走完「数据体检 → 假设生成 → 参数拟合 → 多重验证 → 自我否定 → 结论落盘」，
全程无人工干预；**每一次判定都由机器给出，且每一次运行都留下可独立复算的证据**。

## 一条命令复现全部结论

先在**项目根目录**把源码目录加进模块搜索路径（下同。不设它，`python -m formula_agh` 会 `ModuleNotFoundError`）：

    set PYTHONPATH=src          :: Windows cmd
    $env:PYTHONPATH='src'       :: PowerShell
    export PYTHONPATH=src       :: bash

然后：

    python reproduce.py

它依次跑完 15 个步骤（契约校验 → 三段划分与物理封印 → 划分一致性 → 单元测试 → 金标准自检 →
判别力 → 候选批量验证 → 判别力报告 → 尺度检验（参考式与错误式）→ 负对照实验 → 对抗性测试 →
独立复算 → 评分对照 → 证据归档），最后与 `expected/reproduction_baseline.json` 的指纹逐字段比对：

    复现成功：指纹与基线完全一致。
      任务 22 个，本流水线运行 135 条，对抗用例 14 项，全部逐位一致。

在干净目录里复现（先复制源码，再从头跑，`runs/ evidence/ sealed/` 全部从零重建）：

    python reproduce.py --clean D:\repro

依赖：**只需要 numpy**。参数拟合是自己实现的 Levenberg–Marquardt（不依赖 scipy），
测试用自带的 `run_tests.py`（不依赖 pytest）。详见 `requirements.txt`。

## 四道验证门

| 检验 | 检什么 | 为什么需要 |
|---|---|---|
| 量纲 | 量纲齐次性（无自由参数时严格比对） | 排除数学上成立、物理上荒谬的表达式 |
| 留出集 | 支撑域内、智能体不可见的点 | 排除记忆式拟合 |
| **外推区** | **严格位于训练支撑域之外的两端** | **区分「拟合」与「真发现」** |
| **尺度/极限行为** | 幂律标度、无量纲群、极限、单调性、符号、对称性 | **不依赖任何误差统计量**：单位可能对、形状不对的公式靠这道门 |

判定口径：`relative_error_median = median(|pred-truth|/|truth|)`。
四次口径演进的实测数据与理由见 `docs/M2_验证口径修正.md`——**我们推翻过自己原来的判据**。

## 目录

    config/agent.yaml        阈值与开关的唯一来源（判据口径、阈值、种子、各门开关）
    src/formula_agh/         验证引擎：safe_eval / units / verify / scale_checks /
                             split / contract / recheck / archive / evidence / settings / cli
    src/scoring/             评分对照（唯一允许读取 reference/ 的组件，与智能体进程隔离）
    tasks/<id>/              data.csv（全量）· data_train.csv（智能体可见）· meta.json · split.json
    reference/<id>.json      标准答案（智能体不可读，只给评分脚本）
    sealed/<id>/             留出集与外推集数据点，物理封印在 tasks/ 之外
    runs/<run_id>/           每次运行的完整证据（公式、参数、逐项判定、指标、SHA256 清单）
    evidence/                证据包：归档副本 + 索引 + 契约/划分/评分/对抗性报告
    recheck/                 独立复算结果（不改写 runs/，运行目录一经生成即不可变）
    physics/scale_specs.json 每个任务的尺度/极限行为规格（M3 维护）
    docs/                    项目说明、数据卡、素材来源、验证口径修正、怀疑清单回应、交叉评审
    superseded/runs/         任务已不存在的历史运行（不可复现，已隔离，未删除）

## 全部命令

    python -m formula_agh settings                    # 当前生效的判据与阈值
    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict
    python -m formula_agh split --tasks tasks --sealed sealed      # 划分落盘与物理封印
    python -m formula_agh split --tasks tasks --check              # 重算一致性
    python -m formula_agh verify --task tasks/phys-ohm --formula "I*R"
    python -m formula_agh batch --tasks tasks --out runs
    python -m formula_agh recheck --runs runs --tasks tasks --out recheck
    python -m formula_agh archive --runs runs --out evidence [--check|--prune]
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

Windows 下等价的包装脚本在 `harness/*.cmd`（供 AGH 的命令工具直接调用；
`run_verify.cmd` 会自动把每次运行归档进 `evidence/`）。

## 证据纪律（这一节比结果更重要）

1. **标准答案隔离**：`reference/` 在 `tasks/` 之外，只有评分脚本读它。
   行为证明：把 `reference/` 整个拿掉，验证结论逐位不变（`tests/test_isolation.py`）。
2. **留出集物理隔离**：留出点与外推点写在 `sealed/`，智能体按目录遍历读不到；
   `split.json` 不含任何行号。
3. **假设来源必填**：`run.json` 的 `hypothesis_source` 区分
   `agh-llm`（模型自主提出）/ `human-authored-fixture`（人工写死的演示装置）/ `reference` /
   `fixture-variant` / `fixture-experiment` / `cli`。
   **只有 `agh-llm` 计入「智能体发现」层**——演示脚本的产出不得用来支撑自主闭环的结论。
4. **运行目录不可变**：复核产物写到 `recheck/`，不改写 `runs/`；
   `manifest.sha256` 覆盖含 `run.json` 在内的每个文件。
5. **失败与边界照实写**：`docs/M2_怀疑清单与回应.md` 逐条写明哪些问题能证伪、哪些**识别不了**。

## 已知边界（不藏）

* 符号错误判据识别不了：自由参数会吸收符号（去掉引力势能公式的负号后，G 取负值即可完全等价）。
* 量纲检验在缺单位信息时降级为"跳过"（理由会写明，契约校验同时给 warn）——降级不会静默，但确实是降级。
* 封印只防目录遍历；智能体若持有宿主机绝对路径仍可读到 `sealed/`。
* 数据是按声明区间均匀采样生成的，外推区比真实实验数据温和。
* **智能体发现层目前只覆盖 1 个任务**（`phys-gravitation`，2 条 `agh-llm` 运行，含一次真实自我否定）：
  闭环已经打通，但覆盖度还不足以声称通用发现能力，扩到全部 22 个任务需要继续跑 AGH。
  真实运行暴露的两个溯源缺陷（模型提出的假设被记成 `cli`、评分按文件名判类）已修复，
  见 [docs/M2_AGH接入阻塞报告.md](docs/M2_AGH接入阻塞报告.md)。

## 许可与合规

* 作品由本队三名成员在赛事期间独立完成，无挂名。
* 全部模型调用仅使用 Agnes 模型。
* 使用的公开数据、开源组件与素材逐项列明于 `docs/素材来源清单.md`。
* 结果公布后按赛事要求开源。