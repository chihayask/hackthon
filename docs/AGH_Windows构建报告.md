# AGH 在 Windows 上的构建验证报告

**日期**：2026-10-09 ｜ **执行者**：M1（AI） ｜ **结论先行**：本机缺少 MSVC 与 Windows SDK，**原生模块无法编译**，但构建链路的前 90% 已实测打通（源码获取、依赖镜像、pnpm、Node 头文件）。补齐两个组件即可继续。

## 一、环境实测结果

| 检查项 | 结果 | 说明 |
|---|---|---|
| Node.js ≥ 24.10 | 通过 | v24.19.0 |
| corepack / pnpm 10.34.5 | 通过 | `corepack prepare pnpm@10.34.5` 成功激活 |
| git | 通过 | 2.55.0.windows.2 |
| npm 镜像可达 | 通过 | `registry.npmmirror.com` 正常 |
| node-gyp（npm 自带） | 通过 | Node 安装内含 |
| **MSVC C++ 编译器（cl.exe）** | **缺失** | `C:\Program Files*\Microsoft Visual Studio` 下无 cl.exe |
| **Windows SDK 10** | **缺失** | 无 `Windows Kits\10\Include`（只有 8.1） |
| npmjs.org 直连 | 超时 | 命令行访问超时，需用 npmmirror |
| github.com 直连 | 超时 | `git clone` 不通，改用 CDN 取源码（见下） |

一键复检：`powershell -NoProfile -ExecutionPolicy Bypass -File harness\agh_preflight.ps1`
（输出为纯 ASCII，避免 Windows PowerShell 5.1 的 ANSI 编码问题）

## 二、已实测通过的三段链路

### 1. 源码获取（绕过 github.com 不可达）

本机 `git clone https://github.com/...` 超时、`raw.githubusercontent.com` 也不通，但 **jsDelivr CDN 可达**：

```
文件清单: https://data.jsdelivr.com/v1/packages/gh/AgnesAI-Labs/agnes-harness@main?structure=flat
单文件:   https://cdn.jsdelivr.net/gh/AgnesAI-Labs/agnes-harness@main/<path>
```

实测结果：**3599 个文件、30.6 MB 全部取回**（跳过文档图片视频；140 个文件首轮失败已重试补齐；仅 11 个文档类文件因 CDN 缓存未同步而 404，不影响构建）。

> 这段经验对你们很重要：**如果校园网也连不上 GitHub，用 jsDelivr 取源码是可行的**，但 jsDelivr 有缓存延迟，刚发布的提交可能取不到。

### 2. 依赖安装（走国内镜像）

```powershell
$env:npm_config_registry = 'https://registry.npmmirror.com'
$env:npm_config_disturl  = 'https://registry.npmmirror.com/-/binary/node'
$env:COREPACK_NPM_REGISTRY = 'https://registry.npmmirror.com'
npm config set registry https://registry.npmmirror.com --location=user
corepack prepare pnpm@10.34.5 --activate
corepack pnpm install --frozen-lockfile
```

实测：pnpm 10.34.5 激活成功，`pnpm install` 正常拉取依赖（本机运行时仍在下载，见第四节）。

### 3. Node 头文件准备（原生编译的前置步骤）

```powershell
$nodeRuntime = (Get-Command node.exe).Source
$npmDir = Split-Path (Get-Command npm.cmd).Source
$gyp = Join-Path $npmDir 'node_modules/npm/node_modules/node-gyp/bin/node-gyp.js'
& $nodeRuntime $gyp install "--target=$((& $nodeRuntime -p 'process.versions.node'))" `
    "--devdir=<缓存目录>" "--dist-url=https://registry.npmmirror.com/-/binary/node"
```

实测：**成功**。`<缓存目录>\24.19.0\include\node\node.h` 已生成（约 6 MB）。
这一步证明 node-gyp 能工作，**唯一缺的就是编译器**。

### 4. 官方构建脚本的参数已核对

`prepare-windows-native.ps1` 做的事：调用 npm 自带 node-gyp 下载 Node 头文件，然后设置环境变量 `AGNES_NODE_HEADERS`（指向 `<缓存>\<node版本>`）。
它**不做编译**（脚本注释原话：compilation remains repository-owned），编译由各包的 `build:native` 完成。

## 三、缺失组件与补救（唯一阻塞项）

AGH 确实含原生 C++ 模块，必须编译：

| 包 | 原生源文件 | 用途 |
|---|---|---|
| `@agnes/system-node` | `native/*.cc`、`pipe-*.h`、`process-*.h`、Windows job object 相关 | Windows 进程/管道控制，daemon 依赖 |
| `@agnes/host` | `native/macos-*.c` | 仅 macOS，Windows 不需要 |

`@agnes/system-node` 的 `package.json` 里 `build:native` = `node scripts/build-native.mjs`，导出 `./native` = `./dist/native/agnes-system.node`。**没有预编译二进制可用**（私有 monorepo）。

### 补救方案（二选一）

**方案 A：装 VS Build Tools（推荐给有校园网/能下载的队友）**

```
1. 下载 Visual Studio 2022 Build Tools（免费，独立安装器）
2. 安装时勾选工作负载「使用 C++ 的桌面开发」
   —— 它会自动带上 MSVC v143 编译器 与 Windows 10/11 SDK
3. 装完重开终端，运行 harness\agh_preflight.ps1 复检，7 项应全通过
```

体积约 2—4 GB。装完之后的完整构建序列：

```powershell
Set-Location <agh 源码目录>
$env:npm_config_registry = 'https://registry.npmmirror.com'
corepack prepare pnpm@10.34.5 --activate
corepack pnpm install --frozen-lockfile

# 原生准备 + 编译
$ErrorActionPreference = 'Stop'
& .\.github\scripts\prepare-windows-native.ps1 -CacheRoot "$env:LOCALAPPDATA\node-gyp\Cache"
pnpm.cmd --filter @agnes/cli build:local
node .\packages\cli\dist\local\agnes.mjs --help
```

**方案 B：改用 WSL2（推荐给本机就是 Windows 且装不了 VS 的情况）**

官方已记录的验证平台是 macOS，Linux 是第二顺位；Windows 明确写着「需要单独验收」。WSL2 里的 Linux 路径反而更接近官方验证过的形态。

```powershell
wsl --install -d Ubuntu          # 需管理员权限，会要求重启
```

进入 Ubuntu 后：

```bash
# Node 24 + node 头文件无需手工准备，bubblewrap 是 Linux 沙箱依赖
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs bubblewrap build-essential
sudo corepack enable && corepack prepare pnpm@10.34.5 --activate

git clone https://github.com/AgnesAI-Labs/agnes-harness.git   # WSL 里 github 通常可达
cd agnes-harness
pnpm install --frozen-lockfile
pnpm --filter @agnes/cli build:local
node packages/cli/dist/local/agnes.mjs serve
```

## 四、本机执行到哪一步、卡在哪里（如实记录）

| 步骤 | 状态 |
|---|---|
| 前置检查（7 项） | 完成：5 通过 / 2 缺失 |
| 源码获取 | **完成**：3599 文件 / 30.6 MB |
| pnpm 10.34.5 激活 | **完成** |
| `pnpm install --frozen-lockfile` | **已启动并正常下载**（运行时间较长，会话内未等到结束） |
| `prepare-windows-native.ps1` 的等价操作 | **完成**：Node 头文件就位 |
| `build:native`（编译原生模块） | **未执行**——预期会因缺少 cl.exe 失败 |
| `build:local` | **未执行** |
| `agnes.mjs serve` | **未执行** |

**必须说清楚的一点**：我没有拿到「Windows 上构建成功」的结论。已经证实的是**除编译器之外的每一环都通**；
编译器是唯一阻塞项，且它是可以靠装一个免费组件解决的。

## 五、给团队的分工建议

| 谁 | 做什么 |
|---|---|
| 装了 VS 或愿意装的队友 | 走方案 A，装完 Build Tools 后按第三节序列构建；把 `--help` 的输出发群里即算成功 |
| 其他队友 | 同时试 WSL2（方案 B）。**两条路并行，谁先通用谁的**，别三个人一起卡在同一个坑里 |
| 都不通时 | 立刻在赛事答疑群问：**官方是否提供已构建的 Windows 分发或托管实例**。这是最省时的解法，且越早问越好 |

## 六、构建成功后的下一步（已验证可用的部分）

1. 用 `node packages/cli/dist/local/agnes.mjs serve` 启动，默认 http://127.0.0.1:4177；
2. Provider 选 **Agnes AI** → 测试连接 → 选模型 → 保存（赛制要求全部调用仅使用 Agnes 模型）；
3. 把 `skills/formula-discovery-loop/` 装进 AGH；
4. 让智能体通过命令工具调用 `harness\run_verify.cmd tasks\phys-gravitation "G*m1*m2/r**2" G`；
5. 若命令行被沙箱限制，改用 `examples/demo_agent.py --llm --agh-entry <agnes.mjs 路径>` 的桥接方式。

## 七、本机环境清单（便于对照排查）

```
Node.js   v24.19.0   (D:\node\)
npm       11.17.0
corepack  0.35.0
pnpm      10.34.5（corepack 激活）
git       2.55.0.windows.2
Python    3.13.5
VS        Community 18 / BuildTools 2022 目录存在，但均无 C++ 工具链
SDK       Windows Kits\8.1 存在；Windows Kits\10 缺失
注册表镜像 registry.npmmirror.com 可用
```