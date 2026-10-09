# AGH 事实核对与路线修正（基于官方代码库）

**来源**：https://github.com/AgnesAI-Labs/agnes-harness（Apache-2.0，TypeScript，pre-alpha）
**核对日期**：2026-10-07 ｜ **用途**：把 M1 今晚要确认的事项从"猜"变成"已知"，并修正我们的实现路线

---

## 一、已确认的事实（可直接依赖）

| 项 | 确认结果 |
|---|---|
| 分发方式 | **源码构建**，无公共安装包。Node.js **≥24.10**、pnpm **10.34.5** |
| 构建命令 | `pnpm install --frozen-lockfile` → `pnpm --filter @agnes/cli build:local` → `node packages/cli/dist/local/agnes.mjs serve` |
| 默认 Web 地址 | `http://127.0.0.1:4177`（以终端实际输出为准） |
| Windows 构建 | 仓库提供 `.github/scripts/prepare-windows-native.ps1`；需 **Node 同版本 headers + Visual Studio C++ Build Tools + Windows SDK** |
| 支持的模型 Provider | Agnes AI、Kimi、GLM、Qwen、DeepSeek、OpenAI、Anthropic、Google、OpenRouter、MiniMax、xAI；Web 把 **Agnes AI 优先展示** |
| 演示所用模型 | `agnes-3.0-flash`（README 示例）；公开基准用的是 Agnes 2.5 Pro Beta |
| CLI 程序化输出 | `agnes.mjs --mode json --chunks --meta "..."` —— **适合脚本消费**（正好用于批量运行） |
| 会话导出 | `agnes.mjs export <SESSION_ID> --format agnes -o session.jsonl`；另有 `--format sharegpt`、`--html`、`--raw` |
| 工具记录读取 | SDK/RPC `_agnes/v1/session.readToolDetail`，按 `callSeq`/`resultSeq` 分页读取完整工具调用与结果 |
| 扩展方式 | 后端工具插件（`ctx.extension().registerTool()`）、Skill、MCP、前端面板、皮肤 |
| 插件形状 | `package.json` 的 `agnes.plugins` 指向模块导出；`inject: ['extension']`；参数为 TypeBox Schema |
| 内置插件助手 | 默认启用的 `@agnes/plugin-helper`：**用自然语言描述需求，它生成插件源码并安装到当前 AGH** |
| 安装流程 | inspect → install → trust → enable（可理解为"审阅源码后才信任"） |
| 会话共享 | 同一 `AGH_HOME` / `AGNES_PROFILE` 下，Web、CLI、SDK 看到同一批会话 |
| 退出码 | 0 完成 ｜ 1 失败 ｜ 2 参数错 ｜ 3 已停驻等待 ｜ 4 预算/阻断 ｜ 5 达最大步数 |
| 许可证 | Apache-2.0（对比赛合规友好，登记进素材来源清单即可） |

---

## 二、⚠️ 最重要的一条：AGH 目前**不能执行 Python**

官方 `packages/runtime-python/README.md` 原文：runtime 工厂**直接拒绝执行**（`E_PRESET_UNSUPPORTED`），"生产 Python kernel、I/O bridge、snapshot/restore backend **均未实现**"；`docs/reference/limitations.zh-CN.md` 亦写明："**Python：生产 Python runtime 与 Python thin SDK 仍非本文可用路径**"。

**这条为什么关键**：我们原计划把三重验证（拟合、符号回归、量纲检查）写成 Python 交给 AGH 执行——**这条路现在不通**。必须在今晚改道，否则下周会在"为什么 AGH 跑不了我的 Python"上白耗两天。

### 修正后的路线（三条，按推荐度排序）

**路线 A（推荐）：Python 作为外部命令行工具，由 AGH 的命令工具调用**
- 我们把验证逻辑写成独立 CLI：`python -m formula_agh.verify --task <id> --run-id <id> --json`
- AGH 的智能体通过命令工具执行它，读取 stdout 的 JSON 作为"执行反馈"
- 好处：计算仍在 Python（numpy/scipy/sympy 全部可用）；**每次调用都会进入 AGH 的工具记录**，天然形成比赛要的"运行证据"；对 AGH 内部实现零依赖
- 代价：命令执行会有审批与沙箱策略（Windows 沙箱边界官方称"未完整关闭"），需要在配置里设好允许范围

**路线 B（备选）：把验证逻辑移植成 Node 后端插件**
- 用 `ctx.extension().registerTool()` 注册 `verify_holdout` / `verify_extrapolation` / `verify_dimension` 三个工具，直接在 AGH 进程内跑
- 好处：调用最"原生"，工具记录最干净；**可以直接让 `@agnes/plugin-helper` 生成初版**
- 代价：JavaScript 生态做符号回归/量纲分析远不如 Python；一周内重写风险高

**结论：主线走 A，把 B 留给"如果有余力再包一层外壳"。**

---

## 三、用 Skill 固化闭环（这是我们方案的关键拼图）

AGH 的 Skill 机制正好承载我们的核心方法论。把"假设 → 拟合 → 三重验证 → 自我否定"写成一份 Skill，智能体每轮都按同一套流程走：

- 好处一：**流程一致**，换任务、换人、重跑都是同一套，评审看到的轨迹可比较
- 好处二：Skill 在 AGH 里是**有来源与信任记录的资源**，"方法可复用"本身就是赛事说的"发展价值"
- 好处三：把我们的验证纪律写进 Skill，等于给智能体装了"不许自欺"的约束

**这份 Skill 的正文（初稿）建议包含**：
1. 每轮必须先声明假设，再调工具，不许先给结论；
2. 拟合完成后**必须**依次调用留出集、外推区、量纲三个验证工具，不得跳过；
3. 任一项不通过即**否决该假设**，并把否决理由写入轨迹；
4. 连续 3 次否决后必须更换函数族（触发重构），不许在原假设上反复微调；
5. **禁止**读取任何名为 reference / answer / ground_truth 的文件；
6. 结论必须包含"我是否推翻过自己"的说明。

> 注意第 5 条：这既是方法论纪律，也是对外可信度的证明——**写进 Skill 就等于写进代码，评审可以核对**。

---

## 四、证据链：用 AGH 自带能力，而不是自己造轮子

| 需求 | AGH 现成能力 | 我们的用法 |
|---|---|---|
| 逐轮轨迹 | 会话事件 + 工具记录 | 直接用；不自己造日志格式 |
| 完整工具调用参数与结果 | `session.readToolDetail` | 复盘与截图取证 |
| 可分享的证据文件 | `export --format agnes -o session.jsonl` | 每次关键运行导出一份存档 |
| 人可读的证据 | `export --html -o session.html` | **直接作为"运行与验证证据"的附件** |
| 证据归档自动化 | SDK `createClient` → `session.new` → `session.prompt` | 批量实验 + 自动导出，写进 M2 的归档脚本 |

**这省掉了我们原计划自己实现"轨迹落盘、证据归档"的大半工作量**——改成"调用 AGH 的导出 + 定期归档"即可。

---

## 五、⚠️ 第二个风险：Windows 不是已验收平台

官方 limitations 写明：
- "已记录的本地进程验证使用 **macOS/Node 24**；**Linux/Windows**、干净机器安装、签名与升级交付**仍需分别验收**"
- "Windows 安全：部分文件/符号链接、受限 token 与网络沙箱边界**未完整关闭**"

**这意味着 Windows 上构建失败或运行异常是可能发生的**，官方并不承诺等价。对策：

1. **今晚就把构建当硬性卡点**（见下节）。**两小时内不成功，立刻转 WSL2（Ubuntu）**——Linux 才是官方记录过的路径（需 bubblewrap + 可用的 user namespace）。
2. 如果 WSL 也不行，**立刻在赛事答疑群问**：官方是否提供已构建的 Windows 分发或托管实例。这个问题问得越早越好。
3. 三台机器分工：至少保证**一台**能跑通 AGH，其余人负责数据处理、验证逻辑、证据整理——不要让三个人同时卡在构建上。

---

## 六、今晚的 AGH 卡点流程（M1 执行，按顺序，每步留截图）

### 步骤 1：环境自检（10 分钟）

```powershell
node --version                 # 必须 >= v24.10
corepack pnpm --version        # 目标 10.34.5
git --version
# 还需确认已安装：Visual Studio C++ Build Tools + Windows SDK
```

### 步骤 2：获取源码并构建（40—90 分钟，Windows）

```powershell
git clone https://github.com/AgnesAI-Labs/agnes-harness.git
cd agnes-harness
pnpm install --frozen-lockfile

# Windows 原生依赖准备（官方脚本）
$ErrorActionPreference = 'Stop'
& .\.github\scripts\prepare-windows-native.ps1 -CacheRoot "$env:LOCALAPPDATA\node-gyp\Cache"

pnpm.cmd --filter @agnes/cli build:local
node .\packages\cli\dist\local\agnes.mjs --help
```

> 官方也提供 `start-local-windows.ps1`（仓库根目录），可先试它，失败再按上面手动走。

### 步骤 3：独立实验实例（避免污染默认配置）

```powershell
$env:AGH_HOME = "D:\agh-home"          # 路径要短；默认是 ~/.agh
New-Item -ItemType Directory -Path $env:AGH_HOME -Force | Out-Null
$env:AGNES_PROFILE = 'local-dev'
node .\packages\cli\dist\local\agnes.mjs serve
```

### 步骤 4：配置 Agnes 模型并验证（20 分钟）

1. 浏览器打开终端打印的地址（默认 `http://127.0.0.1:4177`）
2. 进入 Provider 设置 → **选择 Agnes AI** → 核对 Base URL → 填 API key → **测试连接** → 选择返回目录中的模型 → 保存
3. 新建任务，工作目录指向你们的项目根，发一句只读请求：
   > 请只读取当前项目，说明主要目录及用途；不要修改文件或运行安装命令。
4. **跑通判定**：出现回答；若用了工具，展开记录能看到工具名、参数与结果；任务进入完成或明确的等待状态

### 步骤 5：用 CLI 再验证一次（10 分钟，关键）

```powershell
$AGH_ENTRY = "$PWD\packages\cli\dist\local\agnes.mjs"
node $AGH_ENTRY -p "只读概括当前项目"
node $AGH_ENTRY sessions --json          # 应能看到刚才 Web 创建的会话
node $AGH_ENTRY --mode json --chunks --meta "只读概括当前项目"   # 程序化输出能力验证
```

**第 5 步是路线 A 的前提**：如果 `--mode json` 能稳定输出结构化结果，批量运行与证据自动化就可落地。

### 步骤 6：导出证据验证（10 分钟）

```powershell
node $AGH_ENTRY sessions --json                      # 取一个 SESSION_ID
node $AGH_ENTRY export <SESSION_ID> --html -o demo-session.html
node $AGH_ENTRY export <SESSION_ID> --format agnes -o demo-session.jsonl
```

打开 `demo-session.html` 看是否包含完整工具调用记录——**这份 HTML 就是将来"运行与验证证据"的原型**。

---

## 七、今晚结束时的判定（三条，写进晚会记录）

| # | 判定项 | 通过 / 不通过 | 若不通的下一步 |
|---|---|---|---|
| 1 | Windows 上 AGH 能否构建并启动 Web？ | | → 转 WSL2；仍不通→答疑群问官方 |
| 2 | 能否拿到 Agnes 模型账号并成功"测试连接"？ | | → 立刻在答疑群问额度与开通方式 |
| 3 | `--mode json` 与 `export --html` 是否可用？ | | → 退化为手动截图取证（工作量上升） |

---

## 八、对我们方案的两处修订（已生效）

1. **三重验证的实现载体**：由"AGH 内执行 Python"改为"**Python CLI + AGH 命令工具调用**"；M1 负责接线，M2 负责验证逻辑与单元测试。
2. **证据链实现方式**：由"自研轨迹落盘 + 截图为证"改为"**AGH 原生轨迹 + export 导出 + 定期归档**"；M2 的归档脚本改为调用 `export`，工作量下降。

> 这两处修订让方案**更贴合赛事"AGH 为智能体运行与执行底座"的要求**——底座用的原生能力越多，评审越容易确认合规。

---

## 九、参考（已下载到本地，供离线查阅）

- `_agh_docs/install.md` 安装与源码构建
- `_agh_docs/quickstart.md` 快速开始与首次运行
- `_agh_docs/cli.md` CLI 与 TUI 指南
- `_agh_docs/cli-reference.md` 完整命令参考
- `_agh_docs/sessions.md` 会话、导出与恢复
- `_agh_docs/skills.md` Skill 机制
- `_agh_docs/plugins.md` 插件开发
- `_agh_docs/backend.md` 后端工具插件教程
- `_agh_docs/api.md` API 与 Schema 参考
- `_agh_docs/limitations.md` 已知限制（**含 Python 与 Windows 两条关键限制**）
- `_agh_readme.md` 仓库 README（英文版）
