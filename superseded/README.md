# superseded —— 已隔离的历史证据

本目录存放**不可复现**的历史运行：它们的任务目录已经不存在（例如任务被改名或下线），
因此既不能重跑，也无法用 `runs/<run_id>/manifest.sha256` 之一致性来核对
——它们的清单引用的 `checks/`、`result.json` 等文件在恢复过程中已经丢失。

**为什么留在这里而不是删掉**：删掉会抹掉"这个 run_id 曾经存在过"这一事实；
留在 `runs/` 里又会让读者以为它是可核验的证据。隔离是本项目对这类文件的态度：
不隐藏、不冒充，单独放一处并写明它为什么不可核验。

## 当前内容

| 运行 | 任务 | 为什么被隔离 |
|---|---|---|
| `runs/demo-accepted-01` | `mech-gravity`（已不存在） | 任务目录已下线；清单列出 7 个文件，恢复后只剩 `run.json`，清单校验必然失败 |

## 与 `runs/` 的区别

`runs/` 里的每条运行都必须能通过 `evidence.verify_manifest`；
`superseded/runs/` 的不保证这一点，且不参与评分与复现指纹
（`reproduce.py` 的 `EXCLUDE_DIRS` 已排除 `superseded`）。
