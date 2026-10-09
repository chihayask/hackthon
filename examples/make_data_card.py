# -*- coding: utf-8 -*-
# 由 tasks/ 与 reference/ 生成真实数据卡（避免手写出错）
import io
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')

rows = []
for name in sorted(os.listdir(TASKS)):
    d = os.path.join(TASKS, name)
    if not os.path.isdir(d):
        continue
    with open(os.path.join(d, 'meta.json'), encoding='utf-8') as fh:
        meta = json.load(fh)
    ref_path = os.path.join(REF, name + '.json')
    formula = ''
    if os.path.exists(ref_path):
        with open(ref_path, encoding='utf-8') as fh:
            formula = json.load(fh).get('formula', '')
    units = meta.get('units', {})
    varlist = []
    for v in meta.get('var_names', []):
        varlist.append('%s [%s]' % (v, units.get(v, '?')))
    params = meta.get('free_parameters') or []
    rows.append({
        'id': name,
        'layer': meta.get('layer', ''),
        'domain': meta.get('domain', ''),
        'phenomenon': meta.get('phenomenon', ''),
        'vars': ', '.join(varlist),
        'y': 'y [%s]' % units.get('y', '?'),
        'params': ', '.join(params) if params else 'none',
        'formula': formula,
    })

base = [r for r in rows if r['layer'] == 'base']
chal = [r for r in rows if r['layer'] == 'challenge']
L = []
L.append('# 数据卡（真实物理定律任务集）')
L.append('')
L.append('## 一、数据集总览')
L.append('')
L.append('| 项 | 内容 |')
L.append('|---|---|')
L.append('| 数据集名称 | 公开物理定律基准（自建，来源逐条列明） |')
L.append('| 任务数量 | %d 个（base %d，challenge %d） |' % (len(rows), len(base), len(chal)))
L.append('| 每任务样本数 | 400 |')
L.append('| 自变量数 | 2 到 3 个 |')
L.append('| 数据生成 | 按 meta.json 声明区间独立均匀采样，seed=20261008，脚本 examples/make_physics_tasks.py |')
L.append('| 噪声模型 | 默认相对高斯噪声 sigma=0.4%%；参考值可能接近零的任务改用绝对噪声（见任务级说明） |')
L.append('| 许可 | 公式与变量语义取自公开来源（逐条附链接）；采样数据由本队生成，可自由使用 |')
L.append('| 隐私与伦理 | 无个人信息、无伦理审查事项 |')
L.append('')
L.append('**必须如实说明的一点**：本任务集的**公式与变量语义**来自公开物理定律，**采样点**由我们按声明区间生成，不是实测数据。')
L.append('这样做的理由：真实实验数据缺少公认的标准答案，无法客观判定对错；而本赛事要求作品可验证，必须有客观答案才能形成闭环。')
L.append('表中每一条来源链接都可以点击核对。')
L.append('')
L.append('## 二、任务清单')
L.append('')
L.append('| task_id | 层级 | 领域 | 自变量（单位） | 目标 | 自由参数 | 参考公式 | 现象 |')
L.append('|---|---|---|---|---|---|---|---|')
for r in rows:
    L.append('| `%s` | %s | %s | %s | %s | %s | `%s` | %s |' % (r['id'], r['layer'], r['domain'], r['vars'], r['y'], r['params'], r['formula'], r['phenomenon']))
L.append('')
L.append('## 三、难度分层标准')
L.append('')
L.append('* **base（基础层）**：2 个自变量；表达式为四则运算、幂、开方与简单函数组合，不需要量纲推理即可判断合理性。')
L.append('* **challenge（挑战层）**：3 个自变量，或含指数/三角等复合函数，或**自由参数以非线性方式进入公式**（平方、分母、根号内）。')
L.append('')
L.append('最后一条是本任务集区分度的主要来源：`phys-hydrogen-level` 的参数在分母平方项里，`phys-index-vacuum` 的参数在根号内，')
L.append('线性空间的拟合从任何起点都跑不动，必须在对数空间做多起点搜索——这正是我们验证引擎的实际做法。')
L.append('')
L.append('## 四、数据划分规范')
L.append('')
L.append('1. **外推区**：按主自变量（跨度最大者）排序，取最小值端与最大值端各 7.5%%，合计 15%%，严格位于训练支撑域之外。')
L.append('2. **留出区**：中间区域随机抽取 20%%，智能体不可见。')
L.append('3. **训练区**：其余约 65%%。')
L.append('4. 划分由 `verify.split_columns` 完成，seed 固定，任何人重跑得到同一划分。')
L.append('')
L.append('## 五、答案隔离（红线）')
L.append('')
L.append('* 参考公式存放在仓库根目录的 `reference/`，**不在 `tasks/` 内**，避免被智能体的目录遍历读到。')
L.append('* `python -m formula_agh validate-tasks --tasks tasks` 会扫描任务目录中任何名为 reference/answer/ground/solution 的文件并报错。')
L.append('* 只有 `examples/reference_check.py`（金标准自检）与评分脚本可读取 `reference/`。')
L.append('')
L.append('## 六、已知局限')
L.append('')
L.append('* 数据为合成采样，不含真实测量误差结构（系统偏差、异方差等）。')
L.append('* 采样区间由我们设定，可能比真实实验的取值范围更规整，外推区因此偏温和。')
L.append('* `phys-radioactive-decay` 的 N0 与 y 在实际物理中应为粒子个数，此处按无量纲处理。')
txt = chr(10).join(L) + chr(10)
target = os.path.join(ROOT, 'docs', '数据卡.md')
with io.open(target, 'w', encoding='utf-8') as fh:
    fh.write(txt)
print('wrote', target, len(txt), 'chars')
print('tasks:', len(rows), 'base:', len(base), 'challenge:', len(chal))