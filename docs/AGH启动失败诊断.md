# AGH 启动失败诊断（2026-10-10）

> 现状：本机上 **AGH 完全无法启动**，任何命令（含 `agh daemon start`）都以
> `local daemon scope resolution failed: The credential store is unavailable.` 结束。
> 这直接阻塞了两件高价值工作：**22 任务的绑定重跑**与**去提示消融**。
> 本文记录已定位到的确切调用链、做过的实验、以及下一步该查什么。

## 一、症状

```
$ node agnes.mjs -p "ok" --mode json --cwd <项目>
local daemon scope resolution failed: The credential store is unavailable.

$ node agnes.mjs daemon start
local daemon scope resolution failed: The credential store is unavailable.

$ node agnes.mjs doctor daemon          → ! daemon  not running
$ node agnes.mjs doctor storage         → ✓ storage（sqlite 正常）
$ node agnes.mjs doctor profile         → ✗ profile resolution failed
```

## 二、调用链（读 AGH 源码得到，不是推测）

| 位置 | 事实 |
|---|---|
| `cli/src/boot/backend.ts:590` | 引导阶段把底层异常包装成 `scope resolution` 失败 |
| `host/src/configuration.ts:648-653` | `readCredential()` 里 `credentialStore.read()` 抛错即转成 `CONFIG_CREDENTIAL_STORE`（"The credential store is unavailable."） |
| `host/src/adapters/credential-files.ts:127-131` | `requireEnforcement()`：**强制级别不是 full 就直接抛 `enforcement-unavailable`** |
| 同上 `:51-59` | 强制级别由 `windowsPrivateFilesAvailable()` 决定；为假时级别为 `unavailable` |
| `@agnes/system-node/dist/native/agnes-system.node` | 该函数来自这个原生模块 |
| `native/windows.cc:870-874` | 模块初始化开头有一道闸：`if (uv_version() != UV_VERSION_HEX)` 就抛 `E_SYSTEM_NATIVE_UNAVAILABLE`（"Rebuild Windows native artifact for the current Node.js/libuv runtime"），**并只留下极少的导出** |

**已排除的怀疑**：

- 凭证文件本身没问题：`~/.agh/secrets/agnes-ai/account-…-r1` 是 115 字节的合法 JSON
  （`version:1, kind:'api-key', provider:'agnes-ai'`），ACL 属主正确、用户有完全控制。
- Credential Manager 服务 `VaultSvc` 正在运行；该存储其实是**文件式**的，不依赖它。
- Node 版本符合要求：AGH `engines.node >= 24.10`，本机 `D:\node\node.exe` = v24.19.0（ABI 137）。
- 头文件与运行时 libuv **一致**：两者都是 **1.52.1**（`%LOCALAPPDATA%\node-gyp\Cache\24.19.0` 与
  `_nodeheaders\24.19.0` 的 `uv/version.h` 都是 1.52.1，运行时 `process.versions.uv` 也是 1.52.1）。

## 三、关键观察

直接 `require()` 那个 `.node`：

```
$ node -e "console.log(Object.keys(require('…/@agnes/system-node/dist/native/agnes-system.node')))"
[ 'abiVersion' ]
```

而 `native/windows.cc` 的 `initialize()` 本该注册 20 多个函数
（`hasPrivateDacl`、`readPrivateFile`、`protectPrivateFile`、`openPrivateFile` …）。
**导出表只剩 `abiVersion`**，说明加载到的那个模块没有走到注册那一步。

且本机存在**四份嵌套副本**的 `agnes-system.node`
（`packages/host/node_modules/@agnes/…` 下逐层嵌套）。我检查并重建的是其中一份，
**AGH 运行时实际加载哪一份尚未确认**——这是下一步最该先确定的事。

## 四、做过的实验（含结果）

| 实验 | 结果 |
|---|---|
| 用 VS 2022 BuildTools（`cl.exe` 在 `C:\Program Files (x86)\…\14.44.35207`）重建 `@agnes/system-node` 的原生件 | **构建成功**（EXIT=0，编译 `windows.cc` + `node-delay-load.cc`），但重建后 `require()` 仍只导出 `abiVersion`，AGH 仍报同一错误 |
| 重建前后对比 | 产物已**恢复原样**（`dist/native/_backup` 回滚，环境未被改动） |

## 五、下一步（建议按顺序）

1. **在你的正常交互会话里**先试一次 `agh daemon start`。若成功，本文可以作废——
   说明只是守护进程缺失，与原生件无关。（此前 22 任务是靠一个 10-09 13:46 启动、
   pid 59112 的守护进程跑的；它死后本地启动就暴露了这个问题。）
2. 若仍失败，确定**实际被加载的那份** `.node`：
   ```powershell
   node -e "console.log(require.resolve('@agnes/system-node'))"   # 在 AGH 的 CLI 目录下执行
   ```
   然后对照该路径下的 `dist/native/agnes-system.node` 是否也只导出 `abiVersion`。
   若否，说明加载的是另一份损坏副本，把**正确的那份**放到该路径即可。
3. 若确认要重建，注意构建脚本的取头文件顺序是
   `AGNES_NODE_HEADERS` → `%LOCALAPPDATA%\node-gyp\Cache\<node 版本>`，
   并需要 `<headers>/x64/node.lib`；本机两处头文件都是 24.19.0 / libuv 1.52.1，条件具备。
4. 若以上都不通，按 AGH 官方方式**重装依赖**（重新拉取与当前 Node 匹配的原生件）。

## 六、对项目的影响

- **22 任务绑定重跑**与**去提示消融**都只差"AGH 能启动"这一步；编排侧不需要再改代码：
  `harness/run_agent_discovery.ps1` 已支持 `-DryRun`，
  编排逻辑（工作区隔离、技能安装、来源与会话号传递、路由守卫）已在无 AGH 的情况下验证通过。
- AGH 恢复后的执行命令：
  ```powershell
  powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 `
      -Tasks "<22 个任务 id>" -MaxRounds 3 `
      -Wrapper "E:\fagh\harness\run_verify.cmd"
  ```
