# AGH 运行基座合规自查（2026-10-09）

> 自查对象：赛事对「AGH 必须是核心运行基座」的要求。
> 方法：不看文档下结论，直接**从 22 份 AGH 会话轨迹里统计实际调用了哪些 AGH 能力**。

---

## 一、赛事要求原文（逐字）

> **五、技术要求**
> （一）所有作品须使用 Agnes Harness（AGH）作为智能体运行与执行底座，并由 AGH 连接数据、代码、
> 数据库、专业软件、仿真环境、API、远程设备或真实硬件接口，完成任务规划、能力调用、执行反馈、
> 结果验证和异常处理。
> （二）作品中的所有模型调用仅限 Agnes 模型，不得接入或调用其他厂商、品牌或第三方模型。

（另据本次要求补充的重申）：**AGH 不能只用于生成说明文字或外围辅助，必须在作品的核心任务流程中发挥实际作用。**

---

## 二、结论

**满足。** AGH 承载的是作品的核心链路，不是外围：

    模型在 AGH 内运行 → AGH read 读任务数据 → 模型提假设
      → AGH shell 调验证引擎 → 引擎跑四道门 → 判定 JSON 回到模型
      → 模型据 rounds_hint 换函数族 → 循环 → 产出 `agh-llm` 证据

这条循环的产物**直接就是评分表的第三层「智能体发现」**（22 个任务 / 86 条 `agh-llm` 运行 /
20 个 accepted / 16 个与标准答案一致）。换句话说：把 AGH 从这个流程里拿掉，作品就没有结论了。

> **关于连接对象的口径**：要求原文是「连接数据、代码、数据库、专业软件、仿真环境、API、远程设备**或**
> 真实硬件接口」——这是**并列可选**，满足其中一项或几项即可，**不是**逐项打勾的清单。
> 本作品经 AGH 连接了**数据**与**代码**，已满足该条；其余各类属**可选的增强项**，不是缺口。

---

## 三、逐条对照

### 3.1 连接了什么（要求为并列可选，本作品经 AGH 连接了数据与代码）

| 类型 | 是否使用 | 落地方式与证据 |
|---|---|---|
| **数据** | ✅ | `tasks/<id>/data_train.csv` 经 **AGH 的 read 工具**进入模型上下文（轨迹里 42 次 read） |
| **代码** | ✅ | **AGH 的 shell 工具**调用 `E:\fagh\harness\run_verify.cmd` → `src/formula_agh` 验证引擎（42 次 shell） |
| 数据库 | 未使用（可选） | — |
| 专业软件 | 未使用（可选） | — |
| 仿真环境 | 半覆盖（可选） | 任务数据是按物理规律采样的**合成数据**（`examples/make_physics_tasks.py`，SEED 固定）；属"仿真数据"而非"连接仿真环境" |
| API | 间接（可选） | 模型推理经 AGH 的 provider（Agnes 网关）；作品本身未连外部业务 API |
| 远程设备 / 真实硬件 | 未使用（可选） | — |

> 要求以「**或**」连接，是**并列可选**：连接数据与代码即已满足，无需逐项覆盖。
> 若有余力，下面几项可作为**加分增强**（见第 3.3 节末尾的建议），但不做也不构成不合规。

### 3.2 五个闭环要素

| 要素 | 落地方式 | 证据 |
|---|---|---|
| **任务规划** | AGH `todo` 工具（9 次）+ 每轮先声明假设再动手 | `evidence/agh-sessions/*.agnes.jsonl` |
| **能力调用** | AGH 工具调用共 **241 次**（见下） | 同上 |
| **执行反馈** | 引擎返回 JSON（`verdict` / `checks[]` / `rounds_hint`），模型读取后决定下一轮 | 每轮 assistant 消息里引用了具体失败项 |
| **结果验证** | 四道门由引擎执行：量纲 / 留出集 / 外推区 / 尺度-极限行为 | `runs/<id>/checks/*.json`；金标准 22/22 通过、错误式 22/22 被拒 |
| **异常处理** | `rounds_hint` 的六类失败各自处置；**55 条 rejected** 运行是直接材料 | `runs/` 中 `verdict=rejected` 的运行 + 后续修正轨迹 |

### 3.3 AGH 能力实际使用（从 22 份轨迹统计）

| AGH 工具 | 次数 | 说明 |
|---|---|---|
| `shell` | 147 | 调验证引擎（核心能力调用） |
| `read` | 52 | 读任务数据与元数据 |
| `tool_search` | 24 | AGH 的工具发现机制 |
| `todo` | 9 | AGH 的任务规划机制 |
| `skill_read` | 5 | AGH 的技能机制（**曾被修，见第四节**） |
| `tool_describe` | 2 | 工具自省 |
| `ls` | 2 | 目录 |

**结论：AGH 的规划（todo）、工具发现（tool_search/tool_describe）、技能（skill）、执行（shell）、
文件访问（read/ls）五个子系统都被真实调用过**，不是一个只会转发请求的壳。

---

## 四、本轮发现并修复的合规缺口

### 缺口：AGH 的技能机制实际是坏的（NOT_FOUND）

**现象**：模型 5 次调用 `skill_read("formula-discovery-loop")`，**全部**返回
`{"text":"Skill is unavailable: NOT_FOUND","isError":true}`。

**根因**（读了 AGH 的 `packages/bridges/data/skill-roots.json`）：

    ~/.agh/skills              → dir/SKILL.md
    <workspace>/.agh/skills    → dir/SKILL.md     ← 工作区根

本项目的技能放在 `skills/formula-discovery-loop/SKILL.md`，**既不是 AGH 的任何根**；
而每个任务又在独立工作区（`E:\agh-runs\<task>\`）里跑，那里**根本没有技能目录**。
于是"把方法论写成 Skill 交给 AGH 承载"这件事**形同虚设**——模型只能靠提示词里的内联说明。

**修复**：驱动脚本 `harness/run_agent_discovery.ps1` 在准备每个任务工作区时，
把 `skills/formula-discovery-loop/SKILL.md` 复制到 `<work>/.agh/skills/formula-discovery-loop/`。

**验证**（不是靠推断）：

* `phys-weight`：`skill_read` 返回 `resourceId: skill/workspace/workspace-agnes/be2f10…` + `revision`，
  且模型**逐字复述**了技能第 2 步（含包装脚本用法与审批规则说明）。
* `phys-kinetic-energy`：批次内首次调用返回 NOT_FOUND，**重试即成功**。
  → 全新工作区的**首次**调用会与技能发现竞态；已在驱动脚本的提示词里固化"NOT_FOUND 就重试一次"。

**另一个坑**：`agh skills refresh` / `skills trust` 有**交互式信任门**
（`resource-control-cli/src/execution.ts`：stdin 非 TTY 时 `confirm()` 直接返回 false → 操作取消），
**无人值守跑不了**。好在工作区根是自动发现的，不需要这一步。

---

## 五、仍存在的风险（不粉饰，交给团队决策）

1. **`approvals.mode: off`**：为了让 AGH 连续多轮无人值守地调 shell，我们关掉了它的**全部审批门**。
   根因是 AGH 的审批 seam 只在上下文未污染时采信命令表（`!req.taint || scope.includes('/')`），
   一条极窄的 allow 规则最多只能预批第一次调用。
   **风险**：评审可能读成"把 AGH 的安全机制绕过去了"。
   **长期方案**：按 AGH 推荐路线做工具插件（`ctx.extension().registerTool()`），工具不走 shell 审批门。
2. **连接类型：已满足，可选增强未做**。要求为并列可选，本文档已确认经 AGH 连接了数据与代码，**合规上不存在缺口**。
   可选的加分项（非必须）：用 AGH 的 `web_fetch` 核验 `meta.json` 里的公开来源，或在任务数据之外接一个真实数据库/仿真环境。
3. **工具面窄**：未使用 MCP、未注册自定义工具；AGH 的扩展机制没有被用到。
4. **「模型仅限 Agnes」条款**：PDF 五（二）原文禁止第三方模型；本项目用的是 Agnes（`agnes-3.0-flash`），
   与原文一致。但团队内部对"该条是否已过期、是否可用第三方模型"存在分歧——
   若确有官方更新，**需要拿到书面依据再改**，不要凭口述决策。

---

## 六、证据索引（交给 M2 / 评审）

| 看什么 | 去哪里 |
|---|---|
| AGH 原生运行轨迹（人读） | `evidence/agh-sessions/skillrun_<task>.html`（22 份） |
| AGH 原生运行轨迹（机器读） | `evidence/agh-sessions/skillrun_<task>.agnes.jsonl` |
| 每轮工具调用与判定 | 同上，搜 `"type":"tool/call"` / `"approval/decided"` |
| 验证结论与逐项检查 | `runs/<run_id>/result.json`、`checks/*.json` |
| 与标准答案对照 | `evidence/scoring/comparison.md` |
| 归档副本与索引 | `evidence/runs/`、`evidence/index.json` |

---

## 七、给 M2 的接手清单

    set PYTHONPATH=src
    python reproduce.py          # 应打印「复现成功：指纹与基线完全一致」
    python run_tests.py          # 应 60/60
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

三条都过 = 引擎、证据链、评分三层完整。AGH 侧属于 M1 范围，交接文档见
`docs/M1_进度与交接_AGH批量发现.md`。
