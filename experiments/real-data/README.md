# 真实数据负对照

## 这份实验回答什么问题

外部审计指出：项目的 22 个任务**全部是合成数据**，因此「能发现公式」这一主张缺少真实数据支撑。

把一条已知定律塞进真实数据**不能**回应它：

- 若数据是用该定律生成的 → 循环论证，什么也没证明；
- 若用真实观测 → 观测散布远大于合成数据的 0.4%，参考式会被自己的留出门拒绝，
  直接打破 22/22 的金标准不变式。

所以这里换一个更硬、且**不触碰已验证基准**的问题：

> 在一份确实没有闭式定律的真实数据上，引擎会不会给出 accepted？

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
    python experiments/real-data/run_control.py  # 跑负对照，写 results.json

关键设计：每个候选都配一个**量纲补齐**的自由参数 k。否则候选会先被量纲门拦住，
测到的是「单位不对」而不是「数据不支持定律」。

## 结果（2026-10-10）

| 候选函数族 | 判定 | 量纲档 | 失败项 |
|---|---|---|---|
| `k*velocity_ms**5*displacement_m` | rejected | skipped | 残差 16.144 > 0.500 |
| `k*velocity_ms**4` | rejected | skipped | 残差 12.384 > 0.500 |
| `k*velocity_ms**3*chord_m` | rejected | skipped | 残差 13.815 > 0.500 |
| `k*velocity_ms**2*chord_m*displacement_m` | rejected | skipped | 残差 14.990 > 0.500 |
| `k*velocity_ms*chord_m**2` | rejected | skipped | 残差 13.944 > 0.500 |
| `k*displacement_m` | rejected | skipped | 残差 13.922 > 0.500 |

**6 个候选，accepted 0 个**；残差是阈值的 **25—32 倍**。

## 边界（一并说明）

1. **量纲档是 skipped**：目标单位 `dB` 不在单位表里，量纲门跳过。这与
   `docs/尺度检验说明.md` 记录的档位一致；本条是它在真实数据上的一个实例：
   目标单位不可识别时，挡住建言的是拟合门而不是量纲门。
2. **没有跑智能体**。本实验检验的是**引擎**不会放过无定律的数据；
   「智能体不会编造」由 `evidence/负对照实验设计与结果.md` 的合成噪声实验
   （80 次尝试 0 次编造）支撑。两者互补：一个管「引擎不放水」，一个管「模型不硬凑」。
3. **这不是「发现公式」的证据**，它是**反证**：在没有定律的地方，本项目**不产出结论**。
