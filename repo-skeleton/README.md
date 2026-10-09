> ⚠️ **本目录是 2026-10-07 起草的仓库骨架模板，已被实际实现取代，请勿参考。**
>
> 实际结构与命令以仓库根目录的 `README.md` 为准。这里的 `config/agent.yaml`、
> `tasks/README.md` 与真实的 `config/agent.yaml`（阈值唯一来源）、`docs/数据卡.md` 内容不一致，
> 且 `README.md` 里描述的 `src/main.py`、`src/batch.py`、`src/tools/` 从未按该结构实现
> （实际是 `src/formula_agh/` 包 + `src/scoring/` 评分包）。
>
> 保留原因：它是分工文档中"接口契约（10-09 前定稿）"的原始记录，可用于说明契约是怎么定的。
> 提交前若不再需要，可以整目录删除。

---

# FORMULA-AGH

面向公开科学数据的**可验证公式发现智能体**。

> 2026年江苏省AI+科学与工程创新实践黑客松（高校组）参赛项目 · 本科生组
> 主赛道：B. 数学计算与科研智能体 ｜ 具体方向：B3. 科学计算与仿真（辅 B2 算法发现与组合优化）

## 队伍与分工

三名本科生：人工智能（智能体编排）、计算机科学与技术（验证引擎与可复现工程）、机械设计制造及其自动化（物理正确性与任务设计）。详见 `docs/02_执行计划与分工.md`。

## 一句话说明

智能体在 AgnesHarness（AGH）上自主完成"数据体检 → 假设生成 → 参数拟合 → 三重验证 → 自我否定 → 结论落盘"的完整闭环，全程无人工干预。发现结果与公开标准答案逐项对照。

## 三重验证

| 检验 | 检验什么 | 为什么需要 |
|---|---|---|
| 留出集 | 未见采样点上的精度 | 排除记忆式拟合 |
| 外推区 | 数据支撑域之外的行为 | **区分"拟合"与"发现"** |
| 量纲/尺度 | 量纲齐次性与极限行为 | 排除数学上成立但物理上荒谬的表达式 |

## 目录结构

```
.
├── README.md                 本文件
├── requirements.txt          依赖
├── .env.example              环境变量样例（Agnes 模型配置）
├── config/
│   └── agent.yaml            智能体配置（迭代上限、阈值、工具开关）
├── src/
│   ├── main.py               入口：单任务运行
│   ├── batch.py              批量运行
│   ├── harness/              AGH 编排层：规划、工具注册、记忆
│   ├── tools/                工具实现
│   │   ├── data_audit.py     数据体检
│   │   ├── hypothesis.py     候选形式生成
│   │   ├── fit.py            参数拟合
│   │   ├── verify.py         三重验证
│   │   └── log_run.py        轨迹落盘
│   └── scoring/              与标准答案对照（**独立于智能体运行**）
├── tasks/                    公开数据任务（含来源与划分）
│   ├── README.md             数据卡
│   └── <task_id>/
│       ├── data.csv
│       └── meta.json
├── runs/                     运行输出（自动生成）
├── evidence/                 证据包（截图、图表、失败档案）
└── docs/                     项目说明、分工、素材来源清单
```

## 一键复现

```bash
# 1. 准备环境（Python 版本与依赖见 requirements.txt）
pip install -r requirements.txt

# 2. 配置 Agnes 模型访问
copy .env.example .env      # 填入你的密钥

# 3. 运行单个任务
python src/main.py --task tasks/<task_id> --run-id demo-01

# 4. 批量运行基础层任务
python src/batch.py --layer base --out runs/

# 5. 与标准答案对照（此步骤不属于智能体运行）
python src/scoring/compare.py --runs runs/ --ref tasks/
```

> **重要**：标准答案文件不参与智能体的任何输入。智能体只能看到 `data.csv` 与 `meta.json`。

## 输出说明

每次运行在 `runs/<run_id>/` 下生成：

| 文件 | 内容 |
|---|---|
| `command.txt` | 实际执行命令，可直接复现 |
| `env.txt` | AGH 版本、模型、依赖版本 |
| `trajectory.jsonl` | 每轮一行：假设 / 工具调用 / 指标 / 采纳或否决 / 理由 |
| `result.json` | 最终公式、参数、三重验证指标、最终判定 |
| `stdout.log` | 完整标准输出 |
| `figures/` | 生成的图表 |
| `checks/` | 三重验证的中间结果 |

## 合规声明

- 作品由本队三名成员在赛事期间独立完成；
- 所有模型调用仅使用 **Agnes 模型**；
- 使用的开源代码、公开数据集、第三方组件与素材均在 `docs/素材来源清单.md` 中逐项列明来源与使用方式。

## 许可

结果公布后按赛事要求开源。