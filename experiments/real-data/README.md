# 真实数据负对照

## 这份实验回答什么问题

外部审计指出：项目的 22 个任务**全部是合成数据**，因此「能发现公式」这一主张缺少真实数据支撑。

把一条已知定律塞进真实数据**不能**回应它：

- 若数据是用该定律生成的 → 循环论证，什么也没证明；
- 若用真实观测 → 观测散布远大于合成数据的 0.4%，参考式会被自己的留出门拒绝，
  直接打破 22/22 的金标准不变式。

所以这里换一个更硬、且**不触碰已验证基准**的问题：

> 在一份确实没有闭式定律的真实数据上，**引擎**与**智能体**会不会给出 accepted？

## 数据

| 项 | 值 |
|---|---|
| 来源 | UCI Machine Learning Repository，Airfoil Self-Noise（id 291） |
| 内容 | NACA 0012 翼型的**真实风洞测量**，1503 行 |
| 列 | 频率 / 攻角 / 弦长 / 来流速度 / 位移厚度 → scaled sound pressure level |
| sha256 | `74c75fd71783f1e6b71f8a622b993dc592897a97cd689c5090a07147a1b097b3` |
| 许可 | UCI 公开数据集；原始出处 Brooks, Pope & Marcolini, NASA RP-1218 (1989) |

这份数据与自变量之间确有工程经验关系，但**不存在量纲封闭的精确公式**——正适合检验「是否会编造」。

## 怎么做

    python experiments/real-data/fetch.py        # 下载并校验哈希
    python experiments/real-data/run_control.py  # 第一臂：引擎直接跑 6 个候选
    # 第二臂：把智能体的运行目录传进来（运行方式见第七节）
    $env:REAL_DATA_AGENT_RUNS='E:\fagh-realdata-root\runs'
    python experiments/real-data/run_control.py

第一臂的关键设计：每个候选都配一个**量纲补齐**的自由参数 k。否则候选会先被量纲门拦住，
测到的是「单位不对」而不是「数据不支持定律」。

## 结果一：引擎（6 个函数族，2026-10-10）

| 候选函数族 | 判定 | 量纲档 | 失败项 |
|---|---|---|---|
| `k*velocity_ms**5*displacement_m` | rejected | skipped | 残差 16.144 > 0.500 |
| `k*velocity_ms**4` | rejected | skipped | 残差 12.384 > 0.500 |
| `k*velocity_ms**3*chord_m` | rejected | skipped | 残差 13.815 > 0.500 |
| `k*velocity_ms**2*chord_m*displacement_m` | rejected | skipped | 残差 14.990 > 0.500 |
| `k*velocity_ms*chord_m**2` | rejected | skipped | 残差 13.944 > 0.500 |
| `k*displacement_m` | rejected | skipped | 残差 13.922 > 0.500 |

**6 个候选，accepted 0 个**；残差是阈值的 **25—32 倍**。

## 结果二：智能体（3 轮，2026-10-10）

用 `harness/run_agent_discovery.ps1` 让 Agnes 模型在这个任务上自主循环 3 轮
（捆绑协议与正式支路一致：来源 `agh-llm`、会话绑定）。

| 轮次 | 模型给出的公式 | 判定 | 被拦在哪 |
|---|---|---|---|
| 1 | `A + B*log10(v) + C*log10(f) + D*(k*c)*log10(c)` | rejected | 未知名称 A（只允许已声明的自由参数） |
| 2 | `k*log10(v)+k*log10(f)` | rejected | 未知名称 frequency_hz（该列未被纳入本任务） |
| 3 | `k*log10(v/c)+k*log10(d*v)` | rejected | log10 参数须无量纲；残差 5.300 |

**3 轮，accepted 0 个**，且三条运行全部 `provenance_bound=true`，可核对。
结果由 `run_control.py --summarize` 从 `runs/` 复算，写入 `agent_results.json`。

## 边界（一并说明）

1. **量纲档是 skipped**：目标单位 `dB` 不在单位表里，量纲门跳过。这与
   `docs/尺度检验说明.md` 记录的档位一致；本条是它在真实数据上的一个实例：
   目标单位不可识别时，挡住建言的是拟合门而不是量纲门。
2. **表达式语言的表达力边界（本轮最重要的发现）**：模型三轮都试了**对数形式**——
   而声压级恰恰是对数律的典型量。引擎没能接受它们，原因有三个，其中两个属于语言限制而非数据问题：
   - 只允许**已声明**的自由参数（模型写了 A/B/C/D，被拒）；
   - 只允许**已导入**的变量（模型想要频率，而本任务只暴露了 3 列）；
   - `log10` 的参数必须无量纲，因此无法表达工程上常见的 `log10(v)` 型经验式。
   也就是说：**这类数据的正确形式本身就在语言的表达范围之外**，拒绝它是对的，
   但不能据此说「模型没找到」——它找的方向是对的。这条限制应写进自我怀疑清单。
3. **这不是「发现公式」的证据**，它是**反证**：在没有定律的地方，本项目**不产出结论**。
4. 第二臂的 3 轮与正式 22 任务支路的 3 轮设置相同；但本任务没有尺度规格，
   因此尺度门未参与（与前一条相关）。
