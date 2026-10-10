
# v0.1.1 — 可交付性修复与溯源绑定

本版是针对外部审计（2026-10-10）结论的整改版本。**功能接口与 v0.1.0 一致**，
主要修复"从零不可复现"与"来源标签可误标"两类问题。

## 修复的可交付性问题

| 问题 | 原因与处置 |
|---|---|
| **干净 clone 无法运行** | 本地忽略规则（`_*.py`、`_*.json`）没有路径锚点，误伤了 `src/formula_agh/__init__.py`、`__main__.py`、`src/scoring/__init__.py` 以及 70 个 `evidence/runs/*/checks/_duplicate_check_names.json`（后者在 `manifest.sha256` 里）。规则已锚定到仓库根，共补交 74 个必需文件 |
| 复现脚本不 fail-fast | 步骤以非预期退出码结束时只记录、不终止。现在每步声明预期退出码（默认 0/1），其余退出码、超时、启动失败一律**立即中止**并指出失败步骤 |
| 声明但未交付的证据产物 | 补齐 `evidence/threshold_sensitivity.json`（四组阈值，参考式误杀 0）与 `evidence/extrapolation_crashes.json`（6 组外推实验） |
| 测试数三处不一致 | README / 项目说明 / 提交清单统一为 **100 / 100** |

## 溯源绑定

`harness/run_verify.cmd` 原先无条件写入 `FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm`，
导致任何人手工调用该脚本都会留下"模型自主发现"证据。现在：

- 来源由**调用方**显式声明；包装脚本默认记为 `cli`
- `run.json` 新增 `session_id`、`agent_workspace`、`provenance_bound`
- AGH 批量驱动脚本预建会话并把会话号传给包装脚本，来源标签因此绑定到可核对的会话
- 评分脚本把"已绑定"与"未绑定"的候选式**分别统计**，未绑定不计入绑定层
- 演示脚本回退到内置生成器时标记为 `fixture-fallback`，不再按开关一律标 `agh-llm`

**历史运行未绑定**：v0.1.0 之前产生的 86 条 `agh-llm` 运行没有会话号，
因此 `agent_candidates_bound` 为 0、`agent_candidates_unbound` 为 22。这是如实状态，不是回填。

## 其他

- Windows 包装脚本不再无条件优先使用打包的 exe（曾导致源码更新后仍跑旧 exe、新字段未写入证据）；exe 需 `set FORMULA_AGH_USE_EXE=1` 显式开启
- AGH 驱动脚本不再写死本机绝对路径：入口取自 `-AghEntry` 或 `AGH_ENTRY`，工作目录默认落在系统临时目录；项目路径含空格时明确报错并提示建立无提示符别名
- 表述更正：数据为**按公开物理定律生成的合成采样**（非实测观测数据）；`phys-index-vacuum` 的目标量是介质中光速（m/s）而非折射率；`phys-pendulum-exact` 是二阶展开而非精确解
- README 新增「主张限定」：明确可支撑与不可支撑的表述

## 本版新增的可审计性改进

### 量纲检验分档上报

原先不论哪种情况都报"通过"，读者会以为量纲门全程严格生效。现在每次检验都带 `mode`：

| 档位 | 含义 |
|---|---|
| `strict` | 完整量纲比对（无自由参数，或**全部自由参数都声明了单位**） |
| `structural` | 只做结构一致性——部分自由参数会吸收单位，严格比对做不了 |
| `skipped` | 缺单位信息 / 单位表未收录 / y 的单位不可识别 |

同时支持为**自由参数声明单位**（`units` 里写 `k: N/m` 即可）：声明后它按已知量纲符号
参与严格比对，契约校验也不再把它当作"未声明变量"报警告。

### 证据覆盖留痕

`write_evidence` 允许覆盖已有运行（原地复现与各检查脚本的重跑依赖它），
但覆盖不再是静默的：会在目录里写下 `overwritten_from.json`，
记录被覆盖那一份的任务、判定、公式、来源与会话号，并纳入 `manifest.sha256`。
完整内容不可恢复，但"这条 run_id 被重写过"本身成为证据。

### 测试

单元测试增至 **100 / 100**，新增 12 项专门覆盖上述三条（绑定、留痕、分档），
防止这几处证据可信度缺陷回归。

## 验证结果

| 项 | 结果 |
|---|---|
| 干净 clone 单元测试 | **100 / 100 通过**，exit 0 |
| 干净 clone 从零复现 | 15 步全部 exit 0，**指纹与基线逐位一致** |
| 金标准自检 / 判别力 | 22 / 22 通过、22 / 22 拒绝 |
| 负对照 | 80 次尝试，0 次输出表达式 |

## 下载与使用

| 文件 | 说明 |
|---|---|
| `formula_agh.exe` | 单文件，拷贝即用 |
| `formula_agh_onedir_0.1.1_win64.zip` | 目录式，解压即用，启动更快 |

均需放在**项目根目录**下运行（验证需要 `tasks/`、`reference/`、`sealed/` 等数据）。
`config/agent.yaml` 已内联，同时优先读取 exe 同级目录的同名文件。

    formula_agh.exe settings
    formula_agh.exe import <文件> --task-id <id> --target <列名> [--units ...]
    formula_agh.exe verify --task tasks/phys-ohm --formula "I*R"
    formula_agh.exe recheck --runs runs --tasks tasks --out recheck

已知限制：单文件版在含空格的 USB 路径下启动时报 `Could not create temporary directory`，
换普通路径或改用目录式产物即可。

## 从 v0.1.0 升级

无接口变更。若你在 v0.1.0 上跑过验证，请注意 `run.json` 新增了溯源字段；
评分脚本现在会把未绑定会话号的 `agh-llm` 运行单列。
