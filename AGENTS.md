# AGENTS.md — FORMULA-AGH（hackathon-2026）

本目录是 2026 年江苏省 AI+科学与工程创新实践黑客松参赛项目 **FORMULA-AGH**：
面向公开科学数据的**可验证公式发现智能体**。三人小队：M1 智能体底座与编排（人工智能）、
**M2 验证引擎与工程可靠性（计算机科学与技术）**、M3 物理正确性与任务设计（机械）。

## 接手任何工作前，先读这一份

    docs/M2_任务进度与交接.md

它记录了任务目标、逐项完成度、当前关键数字、验证命令、环境事实、踩过的坑与遗留项。
**不要靠读文档判断"现在行不行"**，跑一次：

    set PYTHONPATH=src
    python reproduce.py

退出码 `0` 且打印 `复现成功` = 流水线仍然成立（15 步 + 与基线指纹比对）。

## 硬规则（改代码前必须知道）

1. **证据纪律优先于功能**。`reference/`（标准答案）与 `sealed/`（留出/外推点）智能体不可读；
   只有评分脚本 `src/scoring/compare.py` 允许读 `reference/`。
2. **`runs/<run_id>/` 一经生成即不可变**。复核产物一律写 `recheck/`。
3. **假设来源必填**，且**不许按前缀猜**：`run.json` 的 `hypothesis_source` 区分
   `agh-llm`（模型自主提出）/ `reference` / `fixture-variant` / `cli` / `unclassified` 等。
   **只有 `agh-llm` 计入「智能体发现」层**，不得用演示脚本的产出支撑自主闭环的结论。
4. **阈值只有一处**：`config/agent.yaml`。不得在提示词或脚本里硬编码阈值。
5. **失败与边界照实写**。`docs/M2_怀疑清单与回应.md` 逐条写明哪些问题能证伪、哪些识别不了。
6. **不删 `superseded/runs/`**，那是已隔离的历史证据。

## 跑起来

    set PYTHONPATH=src          :: 不设它，python -m formula_agh 会 ModuleNotFoundError

    python reproduce.py                              # 15 步全跑 + 指纹比对
    python run_tests.py                              # 单元测试（不依赖 pytest）
    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict
    python -m formula_agh split --tasks tasks --check
    python -m formula_agh archive --runs runs --out evidence --check
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

依赖**只有 numpy**。`harness/*.cmd` 是给 AGH 命令工具用的包装脚本（自动设 PYTHONPATH 与自动归档）。

## 环境

* 本机 `python` = `D:\miniconda3\python.exe`（3.13.5 / numpy 2.4.6）；
  复现基线固化于 **python 3.12.14 / numpy 2.3.5**。环境差异默认只提示、不判失败，加 `--strict-env` 可严格比对。
* `.env` 存密钥，已 gitignore，且被 `reproduce.py` 的 `EXCLUDE_FILES` 挡在干净目录外——**绝不提交、绝不复制**。
* 人工调用 `harness/run_verify.cmd` 调试时，先 `set FORMULA_AGH_HYPOTHESIS_SOURCE=cli`，
  否则会被默认标成 `agh-llm` 造成**假溯源**。

## 更细的文档

| 文件 | 内容 |
|---|---|
| `docs/M2_任务进度与交接.md` | **进度与交接总入口** |
| `README.md` | 项目总览、四道验证门、全部命令 |
| `docs/M2_交付说明.md` | 逐项验收对照与接口契约 |
| `docs/M2_验证口径修正.md` | 四次判据口径演进（我们推翻过自己的判据） |
| `docs/M2_怀疑清单与回应.md` | 能证伪的与识别不了的，逐条 |
| `docs/M2_交叉评审意见.md` | 交叉评审的 3 条反对意见与处置 |
| `docs/M2_复现验收单.md` | 六步核对单 + 三人签字栏 |
| `docs/M2_AGH接入阻塞报告.md` | AGH 接入全过程与两个溯源缺陷 |
| `docs/AGH_Windows构建报告.md` | Windows 构建 AGH 的完整踩坑记录 |
