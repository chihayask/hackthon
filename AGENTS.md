# AGENTS.md — FORMULA-AGH（开发者指引）

本目录是**可验证公式发现智能体** FORMULA-AGH。给接手代码的人/智能体看。

## 先跑一次，别靠读文档判断

    set PYTHONPATH=src
    python reproduce.py

退出码 `0` 且打印「复现成功：指纹与基线完全一致」= 流水线成立（15 步 + 指纹比对）。
项目总览与操作方式见 [README.md](README.md)。

## 硬规则（改代码前必须知道）

1. **证据纪律优先于功能**。`reference/`（标准答案）与 `sealed/`（留出/外推点）智能体不可读；
   只有评分脚本 `src/scoring/compare.py` 允许读 `reference/`。
2. **`runs/<run_id>/` 一经生成即不可变**。复核产物一律写 `recheck/`。
3. **假设来源必填**，且**不许按前缀猜**：`run.json` 的 `hypothesis_source` 区分
   `agh-llm`（模型自主提出）/ `reference` / `fixture-variant` / `cli` / `unclassified` 等。
   **只有 `agh-llm` 计入「智能体发现」层**，不得用演示脚本的产出支撑自主闭环的结论。
4. **阈值只有一处**：`config/agent.yaml`。不得在提示词或脚本里硬编码阈值。
5. **失败与边界照实写**。`docs/自我怀疑与边界回应.md` 逐条写明哪些问题能证伪、哪些识别不了。
6. **不删 `superseded/runs/`**，那是已隔离的历史证据。

## 跑起来

    set PYTHONPATH=src          :: 不设它，python -m formula_agh 会 ModuleNotFoundError

    python -m formula_agh settings          # 打印当前生效的判据与阈值
    python -m formula_agh import <file> --task-id <id> --target <col>   # 导入自有数据
    python reproduce.py                     # 15 步全跑 + 指纹比对
    python run_tests.py                     # 单元测试（不依赖 pytest）
    python -m formula_agh validate-tasks --tasks tasks --reference reference --require-split --strict
    python -m formula_agh split --tasks tasks --sealed sealed
    python -m formula_agh split --tasks tasks --check
    python -m formula_agh recheck --runs runs --tasks tasks --out recheck
    python -m formula_agh archive --runs runs --out evidence --check
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring
    powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 -Tasks "phys-ohm" -MaxRounds 3

    python examples/hint_audit.py           # 量化提示泄漏（智能体可见面泄漏了什么）
    python examples/make_blind_taskset.py   # 生成盲化派生任务集（去提示消融的输入）

依赖**只有 numpy**。`harness/*.cmd` 是给 AGH 命令工具用的包装脚本（自动设 PYTHONPATH 与自动归档）。

打包（目标机无需 Python）：`packaging\build_exe.cmd` 出单文件 exe，`packaging\build_exe.cmd onedir` 出目录式。
`harness/run_verify.cmd` 会自动优先用 exe，找不到再回退源码运行。

## 环境

* 本机 `python` = `D:\miniconda3\python.exe`（3.13.5 / numpy 2.4.6）；
  复现基线固化于 **python 3.12.14 / numpy 2.3.5**。环境差异默认只提示、不判失败，加 `--strict-env` 可严格比对。
* `.env` 存密钥，已 gitignore，且被 `reproduce.py` 的 `EXCLUDE_FILES` 挡在干净目录外——**绝不提交、绝不复制**。
* 人工调用 `harness/run_verify.cmd` 调试时，先 `set FORMULA_AGH_HYPOTHESIS_SOURCE=cli`，
  否则会被默认标成 `agh-llm` 造成**假溯源**。
* AGH 侧：用**默认 home**（`~/.agh`），**不要设 `AGH_HOME`** 指向空目录，否则启动即 `E_PRESET_UNRESOLVED: no-routes`。

## 文档地图

| 文件 | 内容 |
|---|---|
| `README.md` | **项目总览与操作入口（验收直接看这个）** |
| `docs/数据卡.md` | 任务集与数据的字段定义（含导入自有数据的规则） |
| `docs/尺度检验说明.md` | 尺度/极限检验怎么算 |
| `docs/判据口径演进.md` | 四次判据口径演进（我们推翻过自己的判据） |
| `docs/自我怀疑与边界回应.md` | 能证伪的与识别不了的，逐条 |
| `docs/素材来源清单.md` | 第三方素材来源与许可 |
| `独立完成声明.md` | 提交用声明（含成员分工，需本人签名） |
