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

## 三之二、**2026-10-12 复发**：这不是一次性修复

上面这条 ACE 在 10-12 又出现了，症状与此前完全一致：

    local daemon scope resolution failed: The credential store is unavailable.
    icacls %USERPROFILE%\.agh -> 486\CodexSandboxUsers:(OI)(CI)(RX)   ← 又回来了

**说明原因**：运行在沙箱中的进程访问 `~/.agh` 时会**重新加上**这条 ACE。
因此移除它不是「修好了」，而是**需要时可重跑的维护动作**——
写成一次性命令、只记在文档里，正是它复发的原因。

已固化为脚本（自动按组名解析 SID，不写死机器相关的 SID）：

```bat
harness\fix_agh_acl.cmd
```

**遇到 AGH 报「凭证库不可用」时先跑它**，不必重走一遍诊断。
如果跑完仍不可用，再按第二节的调用链往下查（`hasPrivateDacl` 各层、
`@agnes/system-node` 的导出、`~/.agh/secrets` 内容）。
## 三之三、**2026-10-12 第二种失败模式：死代理**（与凭证无关）

症状与第一种很容易混淆，但成因完全不同：

| 现象 | 凭证问题（第一种） | **死代理（本种）** |
|---|---|---|
| 任何命令立刻报「凭证库不可用」 | 是 | 否 |
| `doctor profile` | 失败 | **通过** |
| `doctor provider --probe` | 失败 | **通过**（进程内执行） |
| 实际推理 `-p "..."` | 失败 | **失败**：`reason=error`，会话事件里 `{"code":"TRANSPORT","message":"status=?"}` |

**根因链**（逐层实测得到）：

1. 环境变量 `HTTP_PROXY` / `HTTPS_PROXY` = `http://127.0.0.1:7890`，而**该端口没有监听**；
2. AGH 的推理是**经守护进程**走的，守护进程在带毒环境下启动，于是它的每个请求都进死代理；
3. 而 `doctor provider --probe` 是**进程内**执行、用当前进程的环境——
   把代理清空后它立刻通过（延迟 1914ms 的真实往返 vs 之前 25ms 的秒失败）；
4. 因此出现「探测正常、推理失败」的自相矛盾现象，靠日志很难看出。

**修复**：停掉守护进程，在清空代理变量的环境里重启它。实测后推理立即恢复：

```
{"reason":"completed","exitCode":0,"text":"ok"}
```

**已固化为驱动脚本的自动自检**：`harness/run_agent_discovery.ps1` 与
`sim/run_agent_inversion.ps1` 在运行前探测 `HTTPS_PROXY` 指向的端口；
**若无人监听，则清空代理变量并重启守护进程**，然后才开始跑。
只影响这两个脚本自己的进程，不改系统设置。

这一点对本项目尤其要紧：Agnes API 的 `api.agnes-ai.cn` 不在 `NO_PROXY` 名单里，
所以只要本地代理一停，AGH 就会整体失效，而症状看起来像「模型服务挂了」。
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
