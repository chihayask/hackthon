
# FORMULA-AGH

面向科学数据的可验证公式发现系统（当前任务集为按公开物理定律生成的合成采样，见 §2 与 §13）。系统在 Agnes Harness（AGH）内运行，
由模型完成假设生成与迭代决策，由独立的验证引擎完成判定，全部判定过程落盘为可复算的证据。

![python](https://img.shields.io/badge/python-3.12%2B-blue)
![deps](https://img.shields.io/badge/dependencies-numpy%20only-green)
![tests](https://img.shields.io/badge/tests-100%2F100%20passing-brightgreen)
![reproduce](https://img.shields.io/badge/reproduce-fingerprint%20identical-brightgreen)

> 2026 年江苏省 AI+科学与工程创新实践黑客松（高校组），本科生组。
> 参考方向：AI4S 与科学实验、数学 AI 与算法发现、Agent 与 Harness 工程。
> 运行底座：Agnes Harness。模型：agnes-3.0-flash。

---

## 目录

- [1. 系统概述](#1-系统概述)
- [2. 问题背景](#2-问题背景)
- [3. 系统架构](#3-系统架构)
- [4. 判定判据](#4-判定判据)
- [5. 证据与溯源约束](#5-证据与溯源约束)
- [6. 环境与依赖](#6-环境与依赖)
- [7. 操作流程](#7-操作流程)
- [8. 命令参考](#8-命令参考)
- [9. 配置](#9-配置)
- [10. 实验结果](#10-实验结果)
- [11. 目录结构](#11-目录结构)
- [12. 设计约束](#12-设计约束)
- [13. 已知边界](#13-已知边界)
- [14. 故障排查](#14-故障排查)
- [15. 许可与素材来源](#15-许可与素材来源)

---

## 1. 系统概述

系统输入为任务集。**当前 22 个任务的数据均由 `examples/make_physics_tasks.py` 按公开物理定律的声明区间合成采样，不是实测观测数据**；接入自有数据的路径见 §7.4，导入器会强制标注数据来源。

单个任务的执行循环：

    1. 数据读取      AGH read 工具载入 tasks/<id>/data_train.csv 与 meta.json
    2. 假设生成      模型给出候选函数形式、量纲依据与自由参数列表
    3. 工具调用      AGH shell 工具调用 harness/run_verify.cmd
    4. 引擎执行      validation engine 完成三段划分、参数拟合与四类检验
    5. 结果回传      引擎输出 JSON，字段为 verdict、checks[]、rounds_hint
    6. 迭代决策      模型依据 checks 中未通过的项调整函数族，进入下一轮

模型、工具调用、会话状态与运行轨迹均位于 AGH 内。移除 AGH 后该流程不具备可执行性。

## 2. 问题背景

符号回归在有限样本上的主要失效模式如下：

| 失效模式 | 表现 |
|---|---|
| 过拟合 | 训练域内残差低，外推区残差高 |
| 训练集记忆 | 拟合结果复现训练点，无泛化能力 |
| 量纲可凑合 | 量纲齐次性成立，幂次或函数结构错误 |
| 噪声拟合 | 输入为纯噪声时仍输出表达式 |

上述四类失效无法通过单一误差阈值区分。系统的处理方式是在拟合结果之外引入独立的检验维度，
并以可复算的证据形式记录判定过程。

## 3. 系统架构

    ┌────────────────────────── Agnes Harness (AGH) ──────────────────────────┐
    │  session / tools / approval / skills / trace                             │
    │                                                                          │
    │   ┌────────────┐   read    ┌──────────────────────────┐                  │
    │   │  LLM       │ ────────► │ tasks/<id>/data_train.csv │                  │
    │   │  agnes-3.0 │ ◄──────── │          meta.json        │                  │
    │   └─────┬──────┘  context  └──────────────────────────┘                  │
    │         │ shell                                                          │
    │         ▼                                                                │
    │   harness/run_verify.cmd  ──►  python -m formula_agh verify              │
    └─────────┬────────────────────────────────────────────────────────────────┘
              │  PYTHONPATH=src；来源与会话号由 AGH 驱动脚本显式传入
              ▼
    ┌──────────────────────────── validation engine ──────────────────────────┐
    │  safe_eval (AST whitelist) → units → verify (split + fit)                │
    │  → scale_checks → evidence (runs/<run_id>/)                              │
    └─────────┬───────────────────────────────────────────────────────────────┘
              │  verdict / checks[] / rounds_hint (JSON)
              ▼
    ┌────────────────────────── evidence and scoring ─────────────────────────┐
    │  evidence/ index + AGH traces  │  src/scoring/compare.py reads reference/ │
    └──────────────────────────────────────────────────────────────────────────┘

## 4. 判定判据

### 4.1 四类检验

| 检验项 | 检验内容 | 作用 |
|---|---|---|
| dimension | 量纲齐次性。无自由参数时与 y 的量纲严格比对；存在自由参数时执行结构一致性检查 | 排除量纲不成立的表达式 |
| holdout | 支撑域内的留出点上的误差 | 排除训练集记忆 |
| extrapolation | 训练支撑域之外的样本点，取自变量两端 | 区分插值拟合与外推泛化 |
| scale / limit | 幂律标度指数、无量纲群不变性、极限值、单调性、符号、对称性 | 检验函数结构，不依赖误差统计量 |

### 4.2 尺度与极限判据

误差阈值属统计量，其取值影响判定结果，且随划分种子与口径定义变化。
标度指数由表达式的代数结构决定，不依赖拟合残差阈值（标度比较本身仍有量级上的数值容差，见 `src/formula_agh/scale_checks.py`）。

以引力任务为例。候选式 `G*m1*m2/r` 在留出集上的中位相对误差为 0.3677，超过阈值；
同时尺度检验给出的否决依据为：自变量 `r` 加倍后因变量变为 0.5 倍，对应标度指数 -1，
与量纲分析要求的 -2 不符。该结论不引用任何误差数值。

模型据此将幂次修正为 -2，候选式 `G*m1*m2/r**2` 通过全部检验，
拟合结果 `G = 6.662e-11`，与 CODATA 推荐值 `6.674e-11` 的相对偏差为 0.2%。

### 4.3 误差口径

判定口径为 `relative_error_median = median(|pred - truth| / |truth|)`。

选择依据：该量无量纲，对目标量动态范围不敏感，对接近零的尾部样本稳定。
口径经过四次修订，每次修订的实测对比见 [docs/判据口径演进.md](docs/判据口径演进.md)。

## 5. 证据与溯源约束

| 约束 | 实现方式 |
|---|---|
| 标准答案隔离 | `reference/` 位于 `tasks/` 之外，仅 `src/scoring/compare.py` 读取。隔离性由 `tests/test_isolation.py` 验证：移除 `reference/` 后验证结论逐位不变 |
| 留出集隔离 | 留出点与外推点写入 `sealed/`。`split.json` 不含样本行号，仅记录划分规则、计数、支撑域与集合指纹 |
| 假设来源标注 | `run.json` 的 `hypothesis_source` 字段取值包括 `agh-llm`（模型提出）、`reference`、`fixture-variant`、`cli`、`unclassified` 等。统计时仅 `agh-llm` 计入智能体发现层 |
| 运行目录不可变 | `runs/<run_id>/` 生成后不修改。复算结果写入 `recheck/`。`manifest.sha256` 覆盖目录内全部文件 |
| 失败记录 | 未通过判定的运行仍完整落盘。已知边界记录于 [docs/自我怀疑与边界回应.md](docs/自我怀疑与边界回应.md) |

运行过程中出现过两处溯源缺陷：模型提出的假设被记录为 `cli`、评分脚本按 `run_id` 前缀判类。
两处均已修复，并补充了对应的回归测试。

## 6. 环境与依赖

| 项 | 值 |
|---|---|
| Python | 3.12 或以上。当前基线记录于 3.13.5 / numpy 2.4.6；环境差异默认只提示、不判失败，加 `--strict-env` 才严格比对 |
| 依赖 | numpy。参数拟合为自行实现的 Levenberg–Marquardt 算法，不使用 scipy；测试由 `run_tests.py` 驱动，不使用 pytest |
| 操作系统 | Windows、Linux、macOS。开发与验证在 Windows 完成 |

    pip install -r requirements.txt

### 复现

在项目根目录执行，并将源码目录加入模块搜索路径。未设置时 `python -m formula_agh` 会抛出 `ModuleNotFoundError`：

    set PYTHONPATH=src          :: Windows cmd
    $env:PYTHONPATH='src'       :: PowerShell
    export PYTHONPATH=src       :: bash

    python reproduce.py

该脚本依次执行 17 个步骤，并与基线指纹逐字段比对：

    复现成功：指纹与基线完全一致。
      任务 22 个，本流水线运行 135 条，对抗用例 14 项，全部逐位一致。

17 个步骤为：契约校验、三段划分与封印、划分一致性、单元测试、金标准自检、判别力、
候选批量验证、判别力报告、尺度检验（参考式）、尺度检验（错误式）、负对照、对抗性测试、
独立复算、评分对照、证据归档、提示泄漏审计、交付报告重建。

在空目录中重建全部产物：

    python reproduce.py --clean D:\repro

python 与 numpy 的版本差异默认输出提示而不判失败。需要严格比对时加 `--strict-env`。

## 7. 操作流程

### 7.1 引擎侧（不依赖 AGH）

    python -m formula_agh settings

    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict

    python -m formula_agh split --tasks tasks --sealed sealed

    python -m formula_agh split --tasks tasks --check

    python -m formula_agh verify --task tasks/phys-ohm --formula "I*R"

    python -m formula_agh recheck --runs runs --tasks tasks --out recheck

    python -m formula_agh archive --runs runs --out evidence --check

    python run_tests.py

### 7.2 AGH 自主发现

前置条件：

1. AGH 已构建，入口为 `agnes-harness/packages/cli/dist/local/agnes.mjs`。
   Windows 原生依赖需要 Node 头文件与 MSVC 工具链。
2. AGH 使用默认 home `~/.agh`，且已完成账号登录。
   设置 `AGH_HOME` 指向无 provider 配置的目录会导致启动失败，
   错误为 `E_PRESET_UNRESOLVED: no-routes`。
3. 建立无空格路径别名。AGH 的审批规则校验器要求 allow 规则的 argv 以绝对路径形态起始，
   而本项目路径含空格，因此需要目录联接：

       cmd /c mklink /J C:\fagh "<本项目所在路径>"

   驱动脚本不写死任何本机路径：AGH 入口可用 `-AghEntry` 或环境变量 `AGH_ENTRY` 指定，
   工作目录默认落在系统临时目录，包装脚本默认取项目内的 `harness/run_verify.cmd`；
   若项目路径含空格，脚本会**明确报错**并提示改用上面的无空格别名，不会静默走错路径。

4. 审批配置。AGH 的 approval seam 仅在上下文未被工具输出污染时匹配命令表，
   判定条件为 `!req.taint || req.scope.includes('/')`。模型读取任意工具输出后 taint 置位，
   命令表失效，请求转交 prompter；无客户端应答时按拒绝处理。
   因此单条 allow 规则仅能预授权该会话内的首次 shell 调用，无法支撑多轮迭代。
   当前配置在用户层 profile 中设置 `approvals: { mode: off }`
   （`~/.agh/profiles/local-dev/profile.yaml`）。

批量执行：

    powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 -Tasks "phys-ohm,phys-weight" -MaxRounds 3

脚本对每个任务执行以下操作：

- 建立独立工作目录 `E:\agh-runs\<task>\`，其中仅包含 `meta.json` 与 `data_train.csv`，
  使 `sealed/` 与 `reference/` 的隔离由目录结构保证
- 将技能文件复制到工作目录的技能根 `<work>/.agh/skills/`。
  缺少该步骤时 `skill_read` 返回 `NOT_FOUND`，因为 AGH 的工作区技能根为
  `<workspace>/.agh/skills/dir/SKILL.md`
- 以 `--cwd <workspace>` 启动独立会话（会话键由 cwd 派生），避免多任务共用上下文
- 将模型输出与会话 ID 写入 `evidence/agh-sessions/<task>.json`

导出 AGH 原生轨迹：

    node <agnes.mjs> export <sessionId> --html -o evidence/agh-sessions/<task>.html
    node <agnes.mjs> export <sessionId> --format agnes -o evidence/agh-sessions/<task>.agnes.jsonl

### 7.3 评分对照

    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

输出 `comparison.md`、`comparison.json`、`comparison.csv`，包含金标准自检、判别力与智能体发现三层统计。

### 7.4 导入自有数据（任意表格转换为任务格式）

支持以下输入：

| 输入格式 | 说明 |
|---|---|
| `.csv` / `.tsv` / `.txt` | 分隔符自动嗅探（逗号、分号、制表符、竖线） |
| `.json` | 记录数组 `[{列: 值}, ...]` 或列对象 `{列: [值, ...]}` |
| `.xlsx` / `.xlsm` | 首个工作表；需要 openpyxl，缺失时给出明确提示 |

    python -m formula_agh import <文件> --task-id <id> --target <目标列名> \
        --units "x=m,k=N/m,y=J" --source-url "https://..." --variables x,k

转换器执行以下处理：

- 目标列重命名为 `y`；原列名写入 `meta.import.target_column_original`，保持可追溯
- 自变量默认为除目标列外的全部列，可用 `--variables` 显式指定
- 采样区间由数据实际取值范围推断，写入 `meta.sampling`，并标记为推断值
- 提供 `--formula` 时同时写入 `reference/<id>.json`（标准答案）
- 落盘后立即执行契约校验，错误与警告一并打印；有错误时退出码非 0

不合规的输入会被明确拒绝，并指出具体位置：

| 情形 | 处理 |
|---|---|
| 非数值单元格 / 空值 / NaN / Inf | 报错并给出行列位置（契约要求整表数值） |
| 表头重复列名或空列名 | 报错 |
| 目标列不存在 | 报错并列出实际列名 |
| 自变量少于 2 个，或目标列同时作为自变量 | 报错 |
| 样本量低于引擎硬下限 50 | 报错 |
| 任务目录已存在 | 报错；确认覆盖需 `--force` |

导入完成后按 7.1 的流程执行 `split` 与 `verify`。

## 8. 命令参考

    :: validation engine
    python -m formula_agh settings
    python -m formula_agh import  <file> --task-id <id> --target <col> [--units ...]
    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict
    python -m formula_agh split   --tasks tasks --sealed sealed [--check]
    python -m formula_agh verify  --task tasks/<id> --formula "<expr>" --params "<p1,p2>"
    python -m formula_agh batch   --tasks tasks --out runs
    python -m formula_agh recheck --runs runs --tasks tasks --out recheck
    python -m formula_agh archive --runs runs --out evidence [--check]

    :: scoring
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

    :: auditability
    python examples/hint_audit.py                      # 量化智能体可见面的提示泄漏
    python examples/make_blind_taskset.py --out blind  # 生成盲化派生任务集（去提示消融用）
    python examples/make_delivery_reports.py           # 从现有证据重建四份交付报告
    python examples/model_guard.py                     # 校验模型路由全部为 Agnes（通知五（二））

    :: reproduction and tests
    python reproduce.py [--clean <dir>] [--update-baseline] [--strict-env]
    python run_tests.py

    :: AGH autonomous discovery
    powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 -Tasks "<id,id>" -MaxRounds 3

    :: AGH session management
    node <agnes.mjs> sessions --json
    node <agnes.mjs> export <sessionId> --html -o out.html
    node <agnes.mjs> doctor provider --probe

### Windows 包装脚本

`harness/*.cmd` 设置 `PYTHONPATH` 与归档开关，供 AGH 的命令工具调用。
`run_verify.cmd` 内容如下：

    @echo off
    setlocal
    set ROOT=%~dp0..
    set PY=%ROOT%\.venv\Scripts\python.exe
    if not exist "%PY%" set PY=python
    set PYTHONPATH=%ROOT%\src
    set FORMULA_AGH_AUTOARCHIVE=1
    set FORMULA_AGH_RUNS=runs
    set FORMULA_AGH_EVIDENCE=evidence
    pushd "%ROOT%"
    "%PY%" -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" --out "runs"
    set RC=%ERRORLEVEL%
    popd
    exit /b %RC%

该脚本完成两件事：设置模块搜索路径、验证后自动归档。

**来源标签刻意不设默认值。** 旧版本在这里写死 `FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm`，
等于把"脚本被调用"当成"模型自主发现"——任何人手工敲一条都会留下 agh-llm 证据。
现在标签由**调用方**显式声明：`harness/run_agent_discovery.ps1` 会 export
`FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm` 与 `FORMULA_AGH_SESSION_ID`，
两者都到位时 `run.json` 的 `provenance_bound` 才为 true。
手工调用（不设环境变量）默认记为 `cli`，这是诚实的结果。

### 打包为 Windows 可执行文件

目标机不需要安装 Python。构建脚本在 `packaging/build_exe.cmd`：

    packaging\build_exe.cmd            :: 单文件  dist\formula_agh.exe
    packaging\build_exe.cmd onedir     :: 目录式  dist_onedir\formula_agh_onedir\

构建依赖 PyInstaller（实测 6.22.3）。`config/agent.yaml` 会一并内联进产物，
同时程序在运行时优先读取 **exe 同级目录**的 `config/agent.yaml`，
保证阈值仍然只有一处、且可被使用者覆盖。

产物与源码行为一致：

    dist\formula_agh.exe settings
    dist\formula_agh.exe verify --task tasks/phys-ohm --formula "I*R"
    dist\formula_agh.exe split --tasks tasks --check

exe 需放在**项目根目录**下运行（验证需要 `tasks/`、`reference/`、`sealed/`、`physics/` 等数据）。
默认**走源码** Python；要使用打包产物需显式开启：
`set FORMULA_AGH_USE_EXE=1`。旧版本无条件优先 exe，结果源码更新后包装脚本仍在跑旧 exe、
新字段根本没写进证据——静默走了一条与源码不同的路径。

已知限制：单文件模式在**本项目自身目录**（USB 盘且路径含空格）下启动时报
`Could not create temporary directory`，这是 PyInstaller 引导程序创建解压临时目录时的环境问题。
换到无空格路径、或改用 `onedir` 产物即可正常运行；目录式产物不受影响。

## 9. 配置

阈值与开关集中定义于 [config/agent.yaml](config/agent.yaml)，不在脚本或提示词中重复定义。

    verify:
      holdout_ratio: 0.2
      holdout_error_threshold: 0.02
      extrapolation_ratio: 0.15
      extrapolation_error_threshold: 0.03
      dimension_check: true
      scale_check: true
    run:
      seed: 20261008

## 10. 实验结果

数据来源：`src/scoring/compare.py`，可由 `evidence/scoring/comparison.md` 复算。

| 层次 | 检查数 | 符合预期 | 通过率 |
|---|---|---|---|
| 金标准自检 | 22 | 22 | 100% |
| 判别力（结构错误式被拒绝） | 22 | 22 | 100% |
| 智能体发现（仅统计 `hypothesis_source=agh-llm`） | 22 | 16 | 72.7% |
| 分层：base | 13 | 10 | 76.9% |
| 分层：challenge | 9 | 6 | 66.7% |

AGH 自主发现执行统计：

| 指标 | 数值 |
|---|---|
| 完成闭环的任务数 | 22 / 22 |
| `agh-llm` 运行条数 | 86（其中 55 条判定为 rejected） |
| 产出 accepted 表达式的任务数 | 20 / 22 |
| 与标准答案一致 | 16 / 22 |
| AGH 工具调用次数 | 241，涉及 shell、read、tool_search、todo、skill_read、tool_describe、ls |
| 负对照（纯噪声） | 5 组噪声 × 12 函数族 = 80 次尝试，0 次输出表达式 |
| 对抗性用例 | 14 个用例 / 13 项判定，13 通过，1 项属已知边界 |
| 一键复现 | 17 步全部通过，指纹与基线逐位一致 |
| 单元测试 | 100 / 100 |

迭代修正示例：

| 任务 | 首次候选式 | 未通过的检验项 | 修正后候选式 |
|---|---|---|---|
| phys-coulomb | `k*q1*q2/r2` | extrapolation、scale | `k*q1*q2/r**2` |
| phys-elastic-pe | `0.5*c*x2` | scale、holdout | `0.5*c*x**2` |
| phys-gravitation | `G*m1*m2/r` | scale（标度指数 -1，要求 -2） | `G*m1*m2/r**2` |
| phys-stefan-boltzmann | `A*T**4`（将带量纲的 A 作为系数） | dimension | `sigma*A*T**4`（sigma 为自由参数） |

## 11. 目录结构

    config/agent.yaml          阈值与开关的唯一来源
    src/formula_agh/           validation engine
      ├ safe_eval.py           AST 白名单求值
      ├ units.py               量纲推断与比对
      ├ verify.py              三段划分、参数拟合、四类检验编排
      ├ scale_checks.py        幂律标度、无量纲群、极限、单调性、符号、对称性
      ├ split.py               划分落盘与封印
      ├ contract.py            数据契约校验，含答案泄漏检测
      ├ recheck.py             独立复算
      ├ archive.py             证据归档与孤立文件检测
      ├ evidence.py            runs/<run_id>/ 落盘与 manifest.sha256
      ├ settings.py            配置读取
      └ cli.py                 命令行入口
    src/scoring/compare.py     评分对照，唯一允许读取 reference/ 的组件
    tasks/<id>/                data.csv、data_train.csv、meta.json、split.json
    reference/<id>.json        标准答案，智能体不可读
    sealed/<id>/               留出集与外推集样本
    runs/<run_id>/             单次运行的全部证据
    evidence/                  归档副本、索引、AGH 原生轨迹、各类报告
    recheck/                   复算结果
    physics/scale_specs.json   各任务的尺度与极限规格
    harness/                   包装脚本与批量发现驱动脚本
    skills/                    AGH 技能定义
    docs/                      数据卡、尺度检验说明、判据演进、边界回应、素材来源
    expected/                  复现基线指纹
    superseded/runs/           已隔离的历史运行

## 12. 设计约束

1. 未经四类检验通过的表达式不作为发现结果归档。
2. 判据需可通过 `python reproduce.py` 复算，且对已有结论具备证伪能力。
   历次判据修订记录于 `docs/判据口径演进.md`。
3. `reference/` 与 `sealed/` 对智能体不可读；运行目录不可变；每条运行的 SHA256 清单覆盖 `run.json`。
4. `hypothesis_source` 按实际来源标注。演示脚本输出与人工给出的候选式单独统计。
5. 未通过判定的运行保留为证据，用于评估判据的稳定性。

## 13. 已知边界

完整列表见 [docs/自我怀疑与边界回应.md](docs/自我怀疑与边界回应.md)。

- 符号错误无法识别。自由参数可吸收符号：移除引力势能公式的负号后，`G` 取负值即可完全等价。
- 量纲检验在缺少单位信息时降级为跳过。降级结果仍为 `passed=True`，理由字段写明跳过原因，
  契约校验同时输出 warn。
- 封印仅阻断目录遍历。智能体若持有宿主机绝对路径仍可读取 `sealed/`。
  当前实现将每个任务限制在仅含可见文件的独立工作目录内，以目录结构提供隔离。
- 外推样本的分布较真实实验数据更为均匀，两端样本密度未显著稀疏。
- 两个任务尚未通过：`phys-hydrogen-level`（自由参数位于分母平方项，需对数空间多起点搜索）、
  `phys-snells-law`。两个任务的完整失败轨迹均已保留。
- AGH 审批门当前处于关闭状态。为支持多轮无人值守调用，`approvals.mode` 设为 `off`。
  替代方案为注册 AGH 工具插件（`ctx.extension().registerTool()`），使校验调用不经过 shell 审批路径。
- 模型调用仅使用 `agnes-3.0-flash`。

### 主张限定

外部审计（2026-10-10）指出本项目的自主性主张需要收窄，予以采纳。当前可以支撑与不可支撑的表述如下：

| 可支撑 | 依据 |
|---|---|
| 在 AGH 内完成"读数据→提假设→调引擎→读判定→改假设"的多轮闭环 | 22 份 AGH 原生会话轨迹（`evidence/agh-sessions/`） |
| 模型依据验证反馈修正自身假设 | 例：`phys-energy-shift` 提出 `h*(A-B)` 被尺度检验否决，改为 `(A-B)/h` 后通过 |
| 验证引擎的判别力与金标准自检 | 22/22 金标准通过、22/22 结构错误式被拒（`evidence/scoring/`） |
| 纯噪声下不产出表达式 | 5 份噪声 × 12 函数族 = 80 次尝试，0 次接受 |

| 不可支撑 | 原因 |
|---|---|
| "从公开观测数据中发现公式" | **数据全部为按公开物理定律合成的采样**，不是实测数据 |
| "无先验的盲发现" | 任务元数据含定律名称与结构提示，启动提示也给了示例式；尺度反馈会暴露目标幂次 |
| "发现新物理规律" | 全部任务都是已知定律的恢复 |
| 智能体发现层的高覆盖率 | 历史运行的 `agh-llm` 标签**未绑定 AGH 会话号**（`provenance_bound=false`），评分脚本已单列该层，见 `agent_candidates_unbound` |

#### 提示泄漏实测（`examples/hint_audit.py`）

主张强度取决于模型能看到什么。实测 22 个任务的可见面（`evidence/hint_leak_audit.json`）：

| 泄漏面 | 命中 |
|---|---|
| `phenomenon` 文本（写着定律或现象） | 22 / 22 |
| `source` 链接（多数直指定律条目） | 22 / 22 |
| 任务名本身含现象词（如 `phys-ohms-law`） | 22 / 22 |
| `units`（暴露量纲结构） | 22 / 22 |
| 启动提示与技能里当作示例给出的公式 | 6 处（含 `sigma*A*T**4`） |

因此本项目的正确读法是**带物理先验的已知定律恢复**。要去掉先验，先得有盲化输入：

    python examples/make_blind_taskset.py --out blind --level metadata
    python -m formula_agh validate-tasks --tasks blind/tasks --reference blind/reference --require-split

生成 `blind/tasks/<匿名 id>`（meta 已去 phenomenon / source / domain，id 匿名）、
`blind/reference/`（评分侧答案）、`blind/physics/scale_specs.json`（键匿名、`physics_note` 中性化）
与 `blind/mapping.json`（**评审侧**映射，不得进入智能体可见面）。
盲化集的 `source` 是指向映射文件的占位串，会给出 22 条 `SOURCE_NOT_URL` 警告，属设计如此，勿加 `--strict`。

`--level strict` 进一步去掉 `units`（量纲门降级为 skipped）。要跑"完全无先验"支路，
还需在验证时加 `--no-scale-check`——尺度反馈的理由文本本身会写出目标幂次。

**去提示消融尚未执行**：它需要 AGH 可用（见下文"环境依赖"）。本仓库交付的是可执行的盲化输入与实测泄漏清单，
不是消融结论。

更准确的称谓是：**带物理先验与验证反馈的已知定律恢复智能体**。
去提示消融（盲化 task_id / phenomenon / 尺度反馈）与独立终测集尚未完成，列为后续工作。

## 14. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `ModuleNotFoundError: formula_agh` | 未设置 `PYTHONPATH` | 执行 `set PYTHONPATH=src`，或使用 `harness\*.cmd` |
| 中文输出乱码 | 终端编码非 UTF-8 | 加 `-X utf8`，并设置 `PYTHONIOENCODING=utf-8` |
| AGH 启动报 `E_PRESET_UNRESOLVED: no-routes` | `AGH_HOME` 指向无 provider 配置的目录 | 移除 `AGH_HOME`，使用默认 `~/.agh` |
| AGH 返回 `INTERNAL_ERROR (-32603)` 且日志无详细信息 | allow 规则形态不合法。守护进程不记录异常消息，或在修改预设后未重建 | 预设文本在构建期内联，修改 yaml 后需重建；重建前用 `harness/check_agh_command_rule.ts` 校验规则 |
| 模型提出的假设被记录为 `cli` | 调用方没有声明来源。包装脚本**故意不设默认值**，需由 AGH 驱动脚本 export `FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm` 与 `FORMULA_AGH_SESSION_ID` | 用 `harness/run_agent_discovery.ps1` 驱动；手工调试记 `cli` 是预期行为 |
| `skill_read` 返回 `NOT_FOUND` | 技能未放入工作区技能根 `<workspace>/.agh/skills/dir/SKILL.md` | 复制技能到该目录。新建工作区的首次调用可能与技能发现存在时序竞争，重试一次即可 |
| `reproduce.py` 报告新增或缺失条目 | 工作区内存在并发运行 | 使用 `--clean` 在空目录复现 |

## 15. 许可与素材来源

- 作品由参赛队员在赛事期间独立完成。
- 模型调用仅使用 Agnes 模型。运行底座为 Agnes Harness，许可为 Apache-2.0。
- 使用的公开数据、开源组件与素材列明于 [docs/素材来源清单.md](docs/素材来源清单.md)。
- 结果公布后按赛事要求开源本代码库。
