
# v0.1.0 — FORMULA-AGH 验证引擎（Windows 可执行版）

面向公开科学数据的可验证公式发现系统。智能体在 Agnes Harness（AGH）内运行，
由模型生成假设并迭代，由独立的验证引擎完成判定，全部判定落盘为可复算的证据。

本 Release 提供**无需安装 Python** 的 Windows 可执行文件。

## 本版内容

- 验证引擎与命令行入口：`formula_agh`，子命令
  `verify` / `batch` / `validate-tasks` / `split` / `recheck` / `archive` / `settings`
- 四类判定检验：量纲齐次性、留出集误差、外推区误差、尺度与极限行为
- 三段划分与物理封印、独立复算、证据归档与 SHA256 清单
- 评分对照脚本（唯一允许读取 `reference/` 的组件，与智能体进程隔离）
- 一键复现脚本与 60 项单元测试
- 打包产物：单文件与目录式两种形式

## 验证结果（可由源码一键复算）

| 层次 | 检查数 | 符合预期 | 通过率 |
|---|---|---|---|
| 金标准自检 | 22 | 22 | 100% |
| 判别力（结构错误式被拒绝） | 22 | 22 | 100% |
| 智能体发现（仅计 `hypothesis_source=agh-llm`） | 22 | 16 | 72.7% |

其余可复算指标：单元测试 60 / 60；一键复现 15 步全部通过，指纹与基线逐位一致；
负对照 80 次尝试 0 次输出表达式；对抗性用例 14 个 / 13 项判定，13 通过、1 项属已知边界。

## 下载与使用

两个下载项功能相同，按使用场景选择：

| 文件 | 形态 | 说明 |
|---|---|---|
| `formula_agh.exe` | 单文件 20.6 MB | 启动时自解压，拷贝即用 |
| `formula_agh_onedir_0.1.0_win64.zip` | 目录式 21.6 MB | 解压即用，不自解压，启动更快 |

两个产物均需放在**项目根目录**下运行，验证过程需要 `tasks/`、`reference/`、`sealed/`、`physics/` 等数据。
`config/agent.yaml` 已内联进产物，同时程序会优先读取 exe 同级目录的同名文件，便于覆盖阈值。

    formula_agh.exe settings
    formula_agh.exe validate-tasks --tasks tasks --reference reference --require-split --strict
    formula_agh.exe split --tasks tasks --sealed sealed
    formula_agh.exe verify --task tasks/phys-ohm --formula "I*R"
    formula_agh.exe recheck --runs runs --tasks tasks --out recheck
    formula_agh.exe archive --runs runs --out evidence --check

`harness/run_verify.cmd` 会自动优先使用 exe，找不到再回退到 `python -m formula_agh`。

## 已知限制

- 单文件版在**包含空格的 USB 路径**（例如本项目自身目录）下启动时报
  `Could not create temporary directory`，属 PyInstaller 引导程序创建解压临时目录的环境问题。
  换到普通路径，或使用目录式产物，即可正常运行。
- 符号错误无法识别：自由参数可吸收符号。
- 量纲检验在缺少单位信息时降级为跳过，理由字段会写明。
- 两个任务尚未通过：`phys-hydrogen-level`、`phys-snells-law`，完整失败轨迹已保留。

## 复现

    set PYTHONPATH=src
    python reproduce.py

预期输出：`复现成功：指纹与基线完全一致`。

源码与完整证据见仓库主页与 `README.md`。
