# AGH 启动失败：诊断与修复（2026-10-10）

> **结论**：AGH 之前完全无法启动，根因是 **`~/.agh` 目录上残留了一条沙箱用户组
> `CodexSandboxUsers` 的访问控制项**，导致 AGH 的「私有文件」强制校验判定该目录不私有，
> 于是把凭证库当成不可用。移除这条 ACE 后 AGH 恢复正常。

## 一、症状（修复前）

```
$ node agnes.mjs -p "ok" --mode json --cwd <项目>
local daemon scope resolution failed: The credential store is unavailable.

$ node agnes.mjs daemon start        → 同样的错误
$ node agnes.mjs doctor profile      → ✗ profile resolution failed
$ node agnes.mjs doctor storage      → ✓ 正常
```

## 二、根因（读源码 + 实测得到）

| 位置 | 事实 |
|---|---|
| `host/src/adapters/credential-files.ts:51-59` | Windows 下强制级别由 `windowsPrivateFilesAvailable()` 决定 |
| 同上 `:127-131` `requireEnforcement` | 级别不是 `full` 就直接抛，凭证读取必然失败 |
| 同上 `:249-264` `checkCredentialParents` | 逐个校验 `~/.agh` → `secrets` → `secrets/<provider>` 是否为私有目录 |
| `host/src/configuration.ts:648-653` | 读取异常被转成 `CONFIG_CREDENTIAL_STORE`（"The credential store is unavailable."） |
| `cli/src/boot/backend.ts:590` | 引导阶段再把它包装成 `scope resolution failed` |

**实测**（直接调用原生模块的判定函数）：

```
hasPrivateDacl(C:/Users/34908/.agh)                                  → false   ← 问题在这里
hasPrivateDacl(~/.agh/secrets)                                       → true
hasPrivateDacl(~/.agh/secrets/agnes-ai)                              → true
hasPrivateDacl(~/.agh/secrets/agnes-ai/account-…-r1)                 → true
readPrivateFile(该凭证文件)                                           → 成功，115 字节
```

`~/.agh` 的 ACL 里有三条：

```
NT AUTHORITY\SYSTEM : FullControl
传奇鼓手486\34908   : FullControl
传奇鼓手486\CodexSandboxUsers : ReadAndExecute, Synchronize   ← 沙箱残留，AGH 不接受
```

## 三、修复

移除那条沙箱 ACE（用 SID，避免中文组名编码问题；SID 已记录，可回滚）：

```powershell
# CodexSandboxUsers 的 SID
#   S-1-5-21-3843274295-2439810304-3332280151-1008
icacls C:\Users\34908\.agh /remove:g *S-1-5-21-3843274295-2439810304-3332280151-1008
```

想恢复沙箱访问时（可选）：

```powershell
icacls C:\Users\34908\.agh /grant "*S-1-5-21-3843274295-2439810304-3332280151-1008:(OI)(CI)(RX)"
```

## 四、验证（修复后）

```
hasPrivateDacl(~/.agh) / secrets / agnes-ai / 凭证文件   → 全部 true
node agnes.mjs doctor profile                            → ✓ profile
node agnes.mjs -p "只回复 ok" --mode json                → {"reason":"completed","text":"ok", …}
```

## 五、一份自我更正（值得留档）

本文第一版把根因误判为「原生模块 `agnes-system.node` 损坏，只导出 `abiVersion`」，
并写进了提交。**那是错的**，错在测量方法：

```js
Object.keys(require('agnes-system.node'))   // → [ 'abiVersion' ]   ← 假象
Object.getOwnPropertyNames(...).length      // → 24
typeof m.hasPrivateDacl                     // → 'function'
```

N-API 用 `napi_default` 注册的属性**不可枚举**，所以 `Object.keys()` 看不到它们。
据此我还做了一次 MSVC 重建（成功但当然没改善），随后把产物回滚。
**教训**：判定「某能力不存在」之前，先换一种测量方式复核——尤其是在准备据此改动别人环境的时候。

## 六、对项目的影响

这次修复解开了两个高价值任务的阻塞：

1. **22 任务绑定溯源重跑**（审计的核心诉求：`agh-llm` 必须绑定到真实 AGH 会话）
2. **去提示消融**（输入 `blind/` 与审计 `hint_audit` 早已就绪）

编排侧无需改动：`harness/run_agent_discovery.ps1` 已支持
「每次运行新建时间戳工作区 → 天然全新会话」「预建会话取得 sessionId → 溯源绑定」
「来源由调用方显式声明」「模型路由守卫」以及 `-DryRun`。

```powershell
powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 `
    -Tasks "<22 个任务 id>" -MaxRounds 3 `
    -WorkRoot E:\agh-runs3 -Wrapper "E:\fagh\harness\run_verify.cmd"
```
