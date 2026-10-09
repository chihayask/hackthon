
# FORMULA-AGH

**面向公开科学数据的可验证公式发现智能体。**

在 [Agnes Harness (AGH)](https://github.com/AgnesAI-Labs/agnes-harness) 上，让模型自主完成
「读数据 → 提假设 → 调验证引擎 → 读判定 → 换函数族」的闭环，
并把**每一次判定**都落成可独立复算的证据。

![python](https://img.shields.io/badge/python-3.12%2B-blue)
![deps](https://img.shields.io/badge/dependencies-numpy%20only-green)
![tests](https://img.shields.io/badge/tests-60%2F60%20passing-brightgreen)
![reproduce](https://img.shields.io/badge/reproduce-fingerprint%20identical-brightgreen)

> 2026 年江苏省 AI+科学与工程创新实践黑客松（高校组）· 本科生组
> 参考方向：AI4S 与科学实验 / 数学 AI 与算法发现 / Agent 与 Harness 工程

---

## 目录

- [它解决什么问题](#它解决什么问题)
- [工作原理](#工作原理)
- [快速开始](#快速开始)
- [操作过程](#操作过程)
- [运行所需代码](#运行所需代码)
- [结果](#结果)
- [项目结构](#项目结构)
- [设计原则](#设计原则)
- [已知边界](#已知边界)
- [排错](#排错)
- [许可与素材来源](#许可与素材来源)

---

## 它解决什么问题

让 AI「从数据里猜出一个公式」不难，难的是**证明这个公式是真的**。

把 LLM 接到数据上做符号回归，最常见的失败不是算不出来，而是**算出来的东西经不起看**：

- 过拟合：域内贴合、域外崩溃；
- 记忆冒充发现：背下训练集里的答案；
- 单位对、形状错：量纲能凑上，幂次或结构是错的；
- 为了交差编造：数据是纯噪声时，硬凑一个「公式」出来。

本项目把重心从"搜索技巧"移到**判定纪律**：先验证，再宣布。

> **宁可报告「未发现稳定公式」，也不报告一个自己都不确定的结果。**

---

## 工作原理

### 1. 闭环：六步循环

    ① 读数据        AGH 的 read 工具读 tasks/<id>/data_train.csv 与 meta.json
    ② 声明假设      先写清函数形式与依据（量纲 / 单调性 / 极限行为 / 上一轮失败原因）
    ③ 调用引擎      AGH 的 shell 工具调用 run_verify.cmd → python -m formula_agh verify
    ④ 执行反馈      引擎返回 JSON：verdict、checks[]、rounds_hint
    ⑤ 结果验证      四道门全部通过才算 accepted
    ⑥ 异常处理      按失败类型换函数族，并把上一轮的否决理由写进下一轮假设
                    —— 形成可追溯的推理链，而不是反复调参

模型在 AGH 内运行；AGH 提供会话、工具、审批、技能与轨迹。
拿掉 AGH，这条链路就不存在——**这是"运行基座"，不是外围辅助**。

### 2. 四道门（核心判据）

| 门 | 检什么 | 为什么需要它 |
|---|---|---|
| **量纲** | 量纲齐次性（无自由参数时严格比对；有自由参数时做结构一致性检查） | 排除数学上成立、物理上荒谬的表达式 |
| **留出集** | 支撑域内、智能体不可见的点 | 排除记忆式拟合 |
| **外推区** | **严格位于训练支撑域之外的两端** | **区分「拟合」与「真发现」** |
| **尺度 / 极限** | 幂律标度、无量纲群、极限值、单调性、符号、对称性 | **不依赖任何误差统计量** |

判定用的误差口径是 `relative_error_median = median(|pred-truth| / |truth|)`
（无量纲、对动态范围免疫、对近零尾部稳健）。口径经过四次演进，
每一次都有实测数据支撑，见 [docs/判据口径演进.md](docs/判据口径演进.md)——**我们推翻过自己原来的判据**。

### 3. 为什么"尺度门"比阈值硬

这是本项目最想让评审看到的一点。

误差阈值是**相对**的：换个口径、换个种子，结论就可能翻转。
而幂律标度是**结构**的：把自变量 `r` 加倍，若因变量变成 0.5 倍，那么幂次就是 −1——
**不管误差阈值设成多少，`1/r` 都不可能是 `1/r²`。**

因此当模型提出 `G·m₁·m₂/r` 时，引擎给出的否决理由不是"误差超了 0.02"，
而是"r 加倍后 y 变 0.5 倍，物理预期 0.25 倍"——模型据此直接把幂次改成 −2，一次通过：
拟合出的 `G = 6.662e-11`，与公认值 `6.674e-11` 偏差 0.2%。

**依据来自尺度门，不依赖任何阈值；换口径也不会翻。**

### 4. 证据纪律（比结果更重要）

| 纪律 | 落地方式 |
|---|---|
| 标准答案隔离 | `reference/` 在 `tasks/` 之外，**只有评分脚本**读它。行为证明：把 `reference/` 整个移走，验证结论逐位不变（`tests/test_isolation.py`） |
| 留出集物理隔离 | 留出点与外推点写在 `sealed/`（`tasks/` 之外）；`split.json` **不含任何行号**，只有规则、计数、支撑域与集合指纹 |
| **假设来源必填** | `run.json` 的 `hypothesis_source` 区分 `agh-llm`（模型自主提出）/ `reference` / `fixture-variant` / `cli` / `unclassified`。**只有 `agh-llm` 计入「智能体发现」层** |
| 运行目录不可变 | `runs/<run_id>/` 一经生成即不可变；复核产物一律写 `recheck/`；`manifest.sha256` 覆盖每个文件 |
| 失败照实写 | 55 条 rejected 运行全部留档；已知边界逐条写进 [docs/自我怀疑与边界回应.md](docs/自我怀疑与边界回应.md) |

> 真实运行暴露过的两个溯源缺陷——**模型自主提出的公式被记成 `cli`**、**评分脚本按 run_id 前缀判类**——
> 都已修复，并各自补了回归测试锁住行为。

### 5. 架构

    ┌────────────────────────── Agnes Harness (AGH) ──────────────────────────┐
    │  会话 / 工具 / 审批 / 技能 / 轨迹                                        │
    │                                                                          │
    │   ┌────────────┐   read    ┌──────────────────────────┐                  │
    │   │ Agnes 模型 │ ────────► │ tasks/<id>/data_train.csv │                  │
    │   │ (自主决策) │ ◄──────── │          meta.json        │                  │
    │   └─────┬──────┘  上下文   └──────────────────────────┘                  │
    │         │ shell                                                          │
    │         ▼                                                                │
    │   harness/run_verify.cmd  ──►  python -m formula_agh verify              │
    └─────────┬────────────────────────────────────────────────────────────────┘
              │  (PYTHONPATH=src, FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm)
              ▼
    ┌──────────────────────────── 验证引擎 (src/formula_agh) ─────────────────┐
    │  safe_eval(AST 白名单) → units 量纲 → verify 三段划分+拟合                │
    │  → scale_checks 尺度/极限 → evidence 落盘 runs/<run_id>/                 │
    └─────────┬───────────────────────────────────────────────────────────────┘
              │  verdict / checks[] / rounds_hint  (JSON)
              ▼
    ┌────────────────────────── 证据与评分（隔离） ───────────────────────────┐
    │  evidence/ 归档索引 + AGH 原生轨迹  │  src/scoring/compare.py 读 reference/ │
    └──────────────────────────────────────────────────────────────────────────┘

---

## 快速开始

### 环境要求

| 项 | 要求 |
|---|---|
| Python | 3.12+（基线固化于 3.12.14；本机实测 3.13.5） |
| 依赖 | **只有 numpy**（参数拟合是自己实现的 Levenberg–Marquardt，不用 scipy；测试用自带 `run_tests.py`，不用 pytest） |
| 操作系统 | Windows / Linux / macOS 均可（开发与验证在 Windows） |

    pip install -r requirements.txt      # 实际上就是 numpy

### 一条命令复现全部结论

必须在**项目根目录**执行，并先把源码目录加进模块搜索路径（不设它 `python -m formula_agh` 会 `ModuleNotFoundError`）：

    set PYTHONPATH=src          :: Windows cmd
    $env:PYTHONPATH='src'       :: PowerShell
    export PYTHONPATH=src       :: bash

然后：

    python reproduce.py

它跑完 15 个步骤（契约校验 → 三段划分与物理封印 → 划分一致性 → 单元测试 → 金标准自检 → 判别力 →
候选批量验证 → 判别力报告 → 尺度检验 ×2 → 负对照 → 对抗性测试 → 独立复算 → 评分对照 → 证据归档），
最后与基线指纹逐字段比对：

    复现成功：指纹与基线完全一致。
      任务 22 个，本流水线运行 135 条，对抗用例 14 项，全部逐位一致。

干净目录复现（`runs/ evidence/ sealed/` 从零重建）：

    python reproduce.py --clean D:\repro

> 环境差异（python/numpy 版本）**默认只提示、不判失败**；要连环境也逐字比，加 `--strict-env`。

---

## 操作过程

### 场景 A：只跑验证引擎（不需要 AGH）

最常用的日常动作，引擎侧的全部验收都走这条路。

    :: 0) 看当前生效的判据与阈值
    python -m formula_agh settings

    :: 1) 校验任务集（格式、字段完整性、答案泄漏、与 reference/ 交叉核对）
    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict

    :: 2) 生成三段划分并做物理封印（产出 tasks/*/split.json、data_train.csv、sealed/）
    python -m formula_agh split --tasks tasks --sealed sealed

    :: 3) 重算一致性（验收标准：重跑两次逐位一致）
    python -m formula_agh split --tasks tasks --check

    :: 4) 验证单个公式
    python -m formula_agh verify --task tasks/phys-ohm --formula "I*R"

    :: 5) 独立复算（对每条运行重新划分、重新拟合、重新判定，不改写 runs/）
    python -m formula_agh recheck --runs runs --tasks tasks --out recheck

    :: 6) 证据归档与孤儿检测
    python -m formula_agh archive --runs runs --out evidence --check

    :: 7) 单元测试
    python run_tests.py

### 场景 B：让 AGH 自主发现公式（核心操作，需要 AGH）

**前置条件**（缺一不可，踩过的坑都在这）：

1. **AGH 已构建**：`agnes-harness/packages/cli/dist/local/agnes.mjs`（构建见 AGH 官方文档；
   Windows 原生依赖需要 Node 头文件与 MSVC）
2. **AGH 用默认 home**（`~/.agh`，已登录 Agnes 账号）。
   ⚠️ **不要设 `AGH_HOME`** 指向空目录，否则启动即 `E_PRESET_UNRESOLVED: no-routes`
3. **无空格路径别名**：AGH 的审批校验器要求 allow 规则的 argv 以**绝对路径形状**开头，
   而本项目路径含空格。因此建一个目录联接：

       cmd /c mklink /J E:\fagh "E:\...\hackathon-2026"

4. **审批门**：AGH 的审批 seam **只在上下文未被污染时**采信命令表
   （`!req.taint || scope.includes('/')`）。模型一旦读过任何工具输出，规则即失效、请求落到没人应答的
   prompter → 被拒。**一条窄规则最多只能预批第一次 shell 调用**，做不到多轮自主。
   因此用户层 profile 需设 `approvals: { mode: off }`
   （`~/.agh/profiles/local-dev/profile.yaml`）。**代价：关掉全部审批门。**

然后一条命令批量跑：

    powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 -Tasks "phys-ohm,phys-weight" -MaxRounds 3

脚本会为每个任务：

- 建一个**独立工作区** `E:\agh-runs\<task>\`，里面**只放该任务对智能体可见的两个文件**
  （`meta.json` + `data_train.csv`）→ 「不许看 `sealed/` / `reference/`」从纪律变成**结构**
- 把技能装进该工作区的技能根 `<work>/.agh/skills/`，
  否则模型调用 `skill_read` 会得到 `NOT_FOUND`（AGH 的技能根是 `<workspace>/.agh/skills/dir/SKILL.md`）
- 用 `--cwd <workspace>` 起一个**独立 AGH 会话**（会话键由 cwd 派生），避免 22 个任务挤进同一个上下文
- 把模型的输出与会话 ID 存进 `evidence/agh-sessions/<task>.json`

跑完导出 AGH 原生轨迹（评审要看的就是这个）：

    node <agnes.mjs> export <sessionId> --html -o evidence/agh-sessions/<task>.html
    node <agnes.mjs> export <sessionId> --format agnes -o evidence/agh-sessions/<task>.agnes.jsonl

### 场景 C：与标准答案对照（评分）

    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

产出 `comparison.md|json|csv`：金标准自检、判别力、**智能体发现层**三层对照表。
标准答案**只被这个脚本读取**。

---

## 运行所需代码

### 完整命令清单

    :: —— 验证引擎 ——
    python -m formula_agh settings
    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict
    python -m formula_agh split   --tasks tasks --sealed sealed [--check]
    python -m formula_agh verify  --task tasks/<id> --formula "<公式>" --params "<自由参数名,逗号分隔>"
    python -m formula_agh batch   --tasks tasks --out runs
    python -m formula_agh recheck --runs runs --tasks tasks --out recheck
    python -m formula_agh archive --runs runs --out evidence [--check]

    :: —— 评分与对照 ——
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

    :: —— 复现与测试 ——
    python reproduce.py [--clean <目录>] [--update-baseline] [--strict-env]
    python run_tests.py

    :: —— AGH 自主发现 ——
    powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 -Tasks "<id,id>" -MaxRounds 3

    :: —— AGH 会话与导出 ——
    node <agnes.mjs> sessions --json
    node <agnes.mjs> export <sessionId> --html -o out.html
    node <agnes.mjs> doctor provider --probe        # 确认模型路由可用

### Windows 包装脚本（供 AGH 的命令工具直接调用）

`harness/*.cmd` 会自动设置 `PYTHONPATH` 与归档开关。核心是 `run_verify.cmd`：

    @echo off
    setlocal
    set ROOT=%~dp0..
    set PY=%ROOT%\.venv\Scripts\python.exe
    if not exist "%PY%" set PY=python
    set PYTHONPATH=%ROOT%\src
    set FORMULA_AGH_AUTOARCHIVE=1
    set FORMULA_AGH_RUNS=runs
    set FORMULA_AGH_EVIDENCE=evidence
    if "%FORMULA_AGH_HYPOTHESIS_SOURCE%"=="" set FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm
    pushd "%ROOT%"
    "%PY%" -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" --out "runs"
    set RC=%ERRORLEVEL%
    popd
    exit /b %RC%

它一次做对三件事：设好 `PYTHONPATH`、验证后自动归档、并把 `hypothesis_source` 标成 `agh-llm`。

> ⚠️ **人工调试时先** `set FORMULA_AGH_HYPOTHESIS_SOURCE=cli`，否则你的手工验证会被记成"模型自主发现"，
> 造成**假溯源**。本项目真的发生过一次，记录已删除并重跑。

### 阈值只在一处

所有阈值与开关都在 [config/agent.yaml](config/agent.yaml)，**不得在脚本或提示词里硬编码**：

    verify:
      holdout_ratio: 0.2
      holdout_error_threshold: 0.02
      extrapolation_ratio: 0.15
      extrapolation_error_threshold: 0.03
      dimension_check: true
      scale_check: true
    run:
      seed: 20261008

---

## 结果

由 `src/scoring/compare.py` 产出，**可一键复算**（`evidence/scoring/comparison.md`）：

| 层次 | 检查数 | 符合预期 | 通过率 |
|---|---|---|---|
| 金标准自检（标准答案必须被接受） | 22 | 22 | **100%** |
| 判别力（结构错误式必须被拒绝） | 22 | 22 | **100%** |
| **智能体发现**（仅计 `hypothesis_source=agh-llm`） | 22 | **16** | **72.7%** |
| └ 按难度：base / challenge | 13 / 9 | 10 / 6 | — |

**AGH 自主闭环实测**：

| 指标 | 数值 |
|---|---|
| 跑过闭环的任务 | 22 / 22 |
| `agh-llm` 证据运行 | **86 条**（其中 **55 条 rejected**） |
| 给出 accepted 公式的任务 | **20 / 22** |
| 与标准答案一致 | **16 / 22** |
| AGH 工具调用 | 241 次（`shell` / `read` / `tool_search` / `todo` / `skill_read` / `tool_describe` / `ls`） |
| 负对照（纯噪声） | 5 份噪声 × 12 函数族 = 80 次尝试，**0 次编造** |
| 对抗性用例 | 14 用例 / 13 判定，13 通过 + 1 已知边界 |
| 一键复现 | 15 步全绿，**指纹与基线逐位一致** |
| 单元测试 | **60 / 60** |

**自否定的例子**（评审最看重的"依据否决理由自我修正"）：

| 任务 | 第 1 轮 | 被哪道门拦下 | 第 2 轮 |
|---|---|---|---|
| `phys-coulomb` | `k*q1*q2/r2` | 外推 + 尺度 | `k*q1*q2/r**2` ✅ |
| `phys-elastic-pe` | `0.5*c*x2` | 尺度 + 留出 | `0.5*c*x**2` ✅ |
| `phys-gravitation` | `G*m1*m2/r` | 尺度（r 加倍 y 变 0.5 倍，预期 0.25 倍） | `G*m1*m2/r**2` ✅ |
| `phys-stefan-boltzmann` | `A*T**4`（把已声明单位的 A 当系数） | 量纲 | `sigma*A*T**4`（sigma 为自由参数） ✅ |

---

## 项目结构

    config/agent.yaml          阈值与开关的唯一来源（判据口径、阈值、种子、各门开关）
    src/formula_agh/           验证引擎
      ├ safe_eval.py           AST 白名单求值（公式是不可信输入，绝不执行越界语法）
      ├ units.py               量纲推断与比对
      ├ verify.py              三段划分、自由参数拟合、四道门编排
      ├ scale_checks.py        幂律标度 / 无量纲群 / 极限 / 单调性 / 符号 / 对称性
      ├ split.py               划分落盘与物理封印
      ├ contract.py            数据契约校验（含答案泄漏检测）
      ├ recheck.py             独立复算
      ├ archive.py             证据归档与孤儿检测
      ├ evidence.py            runs/<run_id>/ 落盘与 manifest.sha256
      ├ settings.py            配置读取（唯一的阈值入口）
      └ cli.py                 命令行入口
    src/scoring/compare.py     评分对照（唯一允许读 reference/ 的组件，与智能体进程隔离）
    tasks/<id>/                data.csv（全量）· data_train.csv（智能体可见）· meta.json · split.json
    reference/<id>.json        标准答案（智能体不可读）
    sealed/<id>/               留出集与外推集数据点，物理封印在 tasks/ 之外
    runs/<run_id>/             每次运行的完整证据（公式、参数、逐项判定、指标、SHA256 清单）
    evidence/                  证据包：归档副本 + 索引 + AGH 原生轨迹 + 各类报告
    recheck/                   独立复算结果（不改写 runs/）
    physics/scale_specs.json   每个任务的尺度/极限行为规格
    harness/                   AGH 调用的包装脚本 + 批量发现驱动脚本
    skills/                    AGH 技能：formula-discovery-loop（方法论纪律）
    docs/                      说明、数据卡、素材来源、口径修正、怀疑清单、交叉评审
    expected/                  复现基线指纹
    superseded/runs/           任务已不存在的历史运行（已隔离，未删除）

---

## 设计原则

1. **先验证，再宣布。** 没有通过四道门的公式不叫"发现"。
2. **判据要能自我证伪。** 我们推翻过自己的口径（见 `docs/判据口径演进.md`），
   也把"识别不了的边界"写进文档而不是藏起来。
3. **证据优先于功能。** `reference/` 与 `sealed/` 对智能体物理不可读；
   运行目录不可变；每条运行的 SHA256 清单覆盖 `run.json`。
4. **溯源不许猜。** `hypothesis_source` 必须如实标注；**只有 `agh-llm` 计入智能体发现层**，
   演示脚本与人手给出的候选式一律单列。
5. **失败是材料。** 55 条 rejected 运行与一次真实自我否定，比 16 条成功更能说明系统的可靠性。

**不做什么**：不接受仅有概念说明或界面原型的项目形态；不做"看起来对就放过"的验证。

---

## 已知边界

不藏，逐条写清（完整版见 [docs/自我怀疑与边界回应.md](docs/自我怀疑与边界回应.md)）：

- **符号错误判据识别不了**：自由参数会吸收符号——去掉引力势能公式的负号后，`G` 取负值即可完全等价。
  交物理审查兜底，对抗性用例中如实标注为「无法识别」。
- **量纲检验在缺单位信息时降级为「跳过」**：降级结果仍是 `passed=True`，但理由写明跳过，
  契约校验同时给 warn。**降级不会静默，但确实是降级。**
- **封印只防目录遍历**：智能体若持有宿主机绝对路径仍可读到 `sealed/`。
  本项目的做法是把每个任务跑在**只含可见文件的独立工作区**里，让封印变成结构而非约定。
- **外推区比真实实验数据温和**：数据按声明区间均匀采样生成，两端不稀疏。
- **仍有 2 个任务未通过**：`phys-hydrogen-level`（自由参数在分母平方项，需对数空间多起点搜索）、
  `phys-snells-law`。两者都留了完整失败轨迹。
- **AGH 审批门被关闭**：为了让 AGH 连续多轮无人值守地调用 shell，当前用 `approvals.mode: off`
  代替了逐次审批。**长期方案是 AGH 工具插件**（`ctx.extension().registerTool()`），工具不走 shell 审批门。
- **模型仅限 Agnes**：本项目全程使用 `agnes-3.0-flash`。

---

## 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `ModuleNotFoundError: formula_agh` | 没设 `PYTHONPATH` | 先 `set PYTHONPATH=src`，或用 `harness\*.cmd` |
| `UnicodeEncodeError` / 中文乱码 | 终端编码不是 UTF-8 | 加 `-X utf8`，并 `set PYTHONIOENCODING=utf-8` |
| AGH 启动即 `E_PRESET_UNRESOLVED: no-routes` | `AGH_HOME` 指向了空目录 | 删除 `AGH_HOME`，用默认 `~/.agh` |
| AGH 报 `INTERNAL_ERROR (-32603)` 且日志无信息 | 预设里的 allow 规则形状不合法（守护进程**故意抹掉**异常消息），或预设未重建 | 预设文本是**编译期内联**的，改 yaml 必须重建；用 `harness/check_agh_command_rule.ts` 先校验规则 |
| 模型提出假设但被记成 `cli` | 没走 `run_verify.cmd`（包装脚本才带 provenance） | 一律用包装脚本；人工调试先设 `FORMULA_AGH_HYPOTHESIS_SOURCE=cli` |
| `skill_read` 返回 `NOT_FOUND` | 技能不在 AGH 的技能根（`<workspace>/.agh/skills/dir/SKILL.md`） | 把技能复制进工作区技能根；全新工作区首次调用可能与发现竞态，**重试一次**即可 |
| `reproduce.py` 报「新增/缺失」若干处 | 工作区里正在并发跑实验 | 用 `--clean` 在干净目录复现，那才是可比对的基准 |

---

## 许可与素材来源

- 作品由参赛队员在赛事期间**独立完成**，无挂名；相关声明见 [独立完成声明.md](独立完成声明.md)。
- 全部模型调用**仅使用 Agnes 模型**；运行底座为 **Agnes Harness (AGH)**，遵循 Apache-2.0。
- 使用的公开数据、开源组件与素材逐项列明于 [docs/素材来源清单.md](docs/素材来源清单.md)。
- 结果公布后按赛事要求开源本代码库。
