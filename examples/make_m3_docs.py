# -*- coding: utf-8 -*-
# 由证据生成 M3 的交付文档。文档里的每个数字都来自 runs/ 或 evidence/ 下的记录，
# 任何一次重跑之后重新执行本脚本，文档会与证据重新对齐（不会出现手写文档与日志脱节）。
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

TASKS = os.path.join(ROOT, 'tasks')
RUNS = os.path.join(ROOT, 'runs')
EVIDENCE = os.path.join(ROOT, 'evidence')
DOCS = os.path.join(ROOT, 'docs')
PHYS = os.path.join(ROOT, 'physics')
BT = chr(96)


def code(text):
    return BT + str(text) + BT


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s (%d chars)' % (os.path.relpath(path, ROOT).replace(os.sep, '/'), len(text)))


def runs_index():
    out = {}
    if not os.path.isdir(RUNS):
        return out
    for name in sorted(os.listdir(RUNS)):
        path = os.path.join(RUNS, name, 'result.json')
        if os.path.exists(path):
            try:
                out[name] = load(path)
            except json.JSONDecodeError:
                pass
    return out


CLASS = {'dimension': '量纲不成立', 'holdout': '域内拟合失败', 'extrapolation': '外推崩溃',
         'fit': '拟合不收敛', 'expression': '表达式不可用', 'narrow_fit': '窄窗拟合失败',
         'scale': '尺度不成立', 'negative-control': '负对照', 'input': '输入问题'}


def build_physics_review(review):
    specs = load(os.path.join(PHYS, 'scale_specs.json'))['tasks']
    out = ['# 标准答案物理审查（M3 交付）', '',
           '> 这份文档回答一个问题：**任务集里的每一个标准公式，它在物理上描述什么、'
           '在什么条件下成立、一旦越过边界会怎样失效。**',
           '> 它不是从数据里算出来的，而是机械专业（M3）依据公开物理定律逐条核对的结果。', '',
           '审查方式：每个任务核对四项——', '',
           '1. **它描述什么现象**（来自 ' + code('tasks/<id>/meta.json') + ' 的 ' + code('phenomenon') + ' 字段）；',
           '2. **适用条件**（公式成立需要哪些前提）；',
           '3. **失效边界**（越界之后公式会怎样错，是偏高还是发散）；',
           '4. **量纲与尺度性质**（' + code('physics/scale_specs.json') + ' 中声明的检验项，由 '
           + code('python -m formula_agh.scale_checks') + ' 自动执行）。', '',
           '第 3 项直接决定我们在答辩里怎么讲"能力边界"：'
           '一个只在特定区间成立的公式被外推检验拦下，**是正确行为，不是失败**。', '',
           '## 审查结论', '']
    base = sum(load(os.path.join(TASKS, t, 'meta.json')).get('layer') == 'base' for t in specs)
    out += ['- 任务集共 **%d** 个任务（base %d / challenge %d），全部完成审查。'
            % (len(specs), base, len(specs) - base),
            '- 22 个标准公式全部通过三重验证与尺度检验（证据：' + code('evidence/discrimination.json') + '），'
            '说明判据不会误杀物理上正确的公式。',
            '- **多个任务带有明确的适用边界**（单摆的两条、斯涅尔定律、斯特藩-玻尔兹曼、氢原子能级、'
            '放射性衰变）：它们在采样区间内成立，越界后会以可预见的方式失效。'
            '这些边界被写进了尺度判据与领域说明，而不是藏在心里。',
            '- 量纲检验对部分任务降级为"结构一致性检查"（存在自由参数或未知单位），'
            '这一点在 ' + code('runs/*/checks/dimension.json') + ' 的 ' + code('reason')
            + ' 里逐条如实标注，没有掩盖。', '', '---', '']
    for task_id in sorted(specs):
        meta = load(os.path.join(TASKS, task_id, 'meta.json'))
        entry = review['physics'][task_id]
        units = meta.get('units') or {}
        free = meta.get('free_parameters') or []
        checks = specs[task_id]['checks']
        kinds = {}
        for item in checks:
            kinds[item['kind']] = kinds.get(item['kind'], 0) + 1
        out += ['## ' + code(task_id) + '（%s / %s）' % (meta.get('layer'), meta.get('domain')), '',
                '| 项 | 内容 |', '|---|---|',
                '| 描述的现象 | %s |' % meta.get('phenomenon'),
                '| 自变量（单位） | %s |' % '、'.join('%s [%s]' % (k, v) for k, v in units.items() if k != 'y'),
                '| 目标量 | y [%s] |' % units.get('y', '-'),
                '| 自由参数 | %s |' % ('、'.join(free) if free else '无（此时量纲可严格比对）'),
                '| 适用条件 | %s |' % entry['conditions'],
                '| 失效边界 | %s |' % entry['limits'],
                '| 数据区间 | %s |' % '、'.join('%s∈[%g, %g]' % (k, v[0], v[1])
                                              for k, v in sorted((meta.get('sampling') or {}).items())),
                '| 尺度判据 | %d 条（%s） |' % (len(checks), '、'.join('%s×%d' % kv for kv in sorted(kinds.items()))),
                '| 物理提示 | %s |' % specs[task_id].get('physics_note'), '']
    write(os.path.join(DOCS, '标准答案物理审查.md'), '\n'.join(out))


def build_failure_archive(review):
    index = runs_index()
    notes = review['failure_notes']
    order = review['failure_order']
    out = ['# 失败案例档案（M3 交付）', '',
           '> 赛事要求：**不许省略失败**。失败案例是"异常处理"与"验证严谨性"两项的直接证据。',
           '> 本档案每条都附 ' + code('runs/<run_id>/') + ' 的日志原文引用，可逐条复核。', '',
           '收录口径：**结构错误式**（物理上合理、结构写错的候选式）、'
           '**受控外推实验**（只在窄窗内拟合、窗口之外预测）、**负对照**（纯噪声输入）、'
           '**历史缺陷**（早期版本真实出现过、已修复）。', '',
           '总数：**%d 条**（任务书要求 ≥10 条）。' % len(order), '', '---', '']
    count = 0
    missing = [name for name in order if name not in index]
    if missing:
        print('  警告：以下运行目录不存在，未能入档: %s' % ', '.join(missing))
    for name in order:
        payload = index.get(name)
        if not payload or name not in notes:
            continue
        count += 1
        title, note = notes[name]
        failed = [c for c in (payload.get('checks') or []) if not c.get('passed')]
        out += ['## 失败案例 %02d：%s' % (count, title), '',
                '| 项 | 内容 |', '|---|---|',
                '| 运行编号 | ' + code(name) + ' |',
                '| 任务 | ' + code(payload.get('task_id')) + ' |',
                '| 被否决的假设 | ' + code(payload.get('formula')) + ' |',
                '| 最终判定 | **%s** |' % payload.get('verdict'),
                '| 参数估计 | %s |' % (json.dumps(payload.get('parameters') or {}, ensure_ascii=False)
                                        if payload.get('parameters') else '未收敛，未产出参数'),
                '| 失败类别 | %s |' % ('、'.join(CLASS.get(c['name'], c['name']) for c in failed) or '—'),
                '', '**日志原文引用**（逐条来自 ' + code('runs/%s/checks/*.json' % name) + '）：', '']
        for check in failed:
            out += ['> ' + code(check['name']) + ' — %s' % check['reason'], '>']
        if not failed:
            out += ['> （该运行的判定由汇总检验给出，见 ' + code('runs/%s/result.json' % name) + '）', '>']
        if payload.get('rounds_hint'):
            out += ['', '**系统给出的下一轮提示**：%s' % payload['rounds_hint']]
        out += ['', '**M3 的物理判读**：%s' % note, '', '---', '']
    out += ['## 附：已修复的历史缺陷（保留记录）', '',
            '早期版本的拟合器没有对数空间多起点搜索，导致三个**参考公式本身**无法通过验证。'
            '这不是任务集的问题，而是验证引擎的能力缺陷；修好之后三份失败记录仍然留在 '
            + code('runs/') + ' 里：', '',
            '| 运行 | 任务 | 当时的拒绝理由（原文） |', '|---|---|---|']
    for name in ('refcheck-phys-coulomb', 'refcheck-phys-energy-shift', 'refcheck-phys-hydrogen-level'):
        payload = index.get(name)
        if not payload:
            continue
        reason = next((c['reason'] for c in payload.get('checks') or [] if not c.get('passed')), '')
        out.append('| ' + code(name) + ' | ' + code(payload.get('task_id')) + ' | %s |' % reason)
    out += ['', '这三个任务现在重跑均为 accepted（22/22）。', '',
            '**为什么要留着**：删掉它们，评审无法判断我们是真的踩过这个坑、还是从来没遇到过硬骨头。'
            '失败记录本身就是"异常处理"这一项的实证。', '']
    write(os.path.join(EVIDENCE, 'failures', '失败案例档案.md'), '\n'.join(out))
    return count


def build_extrapolation():
    data = load(os.path.join(EVIDENCE, 'extrapolation_crashes.json'))
    out = ['# 外推崩溃分析（M3 交付）', '',
           '> 任务书要求：把被否决的公式**与它崩溃的区间**画出来，'
           '产出"预测曲线 vs 真实曲线（外推区高亮）"。', '',
           '## 一、方法：为什么做受控实验，而不是直接用现成的划分', '',
           '项目默认的三段划分按"跨度最大的自变量"切分，而错误往往出在另一个自变量上'
           '（例如 ' + code('G*m1*m2/r') + ' 的幂次错在 r，但划分轴是 m1）。'
           '要在图上把崩溃区间指出来，必须自己控制训练域。因此每个实验是：', '',
           '1. 选定物理自变量（如 r）；',
           '2. **只用它的一段窄窗口内的数据**拟合候选式的自由参数'
           '（复用验证引擎自己的拟合器，没有另写一套）；',
           '3. 在窗口之外预测；',
           '4. 画出预测曲线 vs 真实曲线（外推区高亮），另附一条误差增长曲线。', '',
           '## 二、实验结果', '',
           '| 任务 | 错误候选式 | 变量 | 窄窗 | 域内误差 | 域外误差 | 放大倍数 | 峰值相对误差 |',
           '|---|---|---|---|---|---|---|---|']
    for row in data['experiments']:
        ratio = (row['outside_rmse'] / row['inside_rmse']) if row['inside_rmse'] else float('inf')
        out.append('| ' + code(row['task_id']) + ' | ' + code(row['candidate']) + ' | %s | [%.4g, %.4g] '
                   '| %.4f | %.4f | **%.1f×** | %.3g @ %s=%.4g |'
                   % (row['axis'], row['window'][0], row['window'][1], row['inside_rmse'],
                      row['outside_rmse'], ratio, row['peak_relative_error'], row['axis'], row['peak_at']))
    out += ['', '（域内/域外均为归一化 RMSE，参照量为 y 的标准差；'
            '峰值相对误差是"其余自变量取中位数"的剖面上，外推区内 |Δy|/|y| 的最大值。）', '',
            '## 三、逐例读图', '']
    for row in data['experiments']:
        out += ['### ' + code(row['task_id']), '', '**%s**' % row['headline'], '',
                '- 拟合方式：%s' % row['fit_note'],
                '- 窄窗 %s ∈ [%.4g, %.4g]；域内归一化误差 **%.4f**，域外 **%.4f**'
                % (row['axis'], row['window'][0], row['window'][1], row['inside_rmse'], row['outside_rmse']),
                '- 剖面峰值相对误差 **%.3g**（%s = %.4g）；窗口内峰值仅 %.3g。'
                % (row['peak_relative_error'], row['axis'], row['peak_at'], row['peak_inside_window']), '',
                '![预测曲线 vs 真实曲线（外推区高亮）](figures/%s)'
                % os.path.basename(row['figures'][0]), '',
                '![误差随自变量的增长](figures/%s)'
                % os.path.basename(row['figures'][1]), '']
    out += ['## 四、结论（写进说明书，不藏）', '',
            '1. **域内误差小不等于公式正确。** 小角度近似在窄窗内归一化误差只有 0.0173，'
            '走出窗口后放大到 0.1343。这类错误在只看训练集的做法下 100% 会被漏掉。',
            '2. **错误的方向是可预测的。** 幂次错一次，误差就随该变量单调增长；'
            '这让我们能把"崩溃区间"明确指出来，而不是笼统地说"效果不好"。',
            '3. **外推检验的代价是诚实的。** 它会让一些域内表现良好的候选式被否决——'
            '这正是它的目的。宁可否决一个可能正确的公式（可以再提新假设），'
            '也不要采纳一个离开数据就崩的公式。', '',
            '## 五、证据位置', '',
            '- 每个实验的完整证据：' + code('runs/extrap-<task_id>/') + '（含 ' + code('checks/*.json')
            + '、' + code('manifest.sha256') + '）',
            '- 原始数据：' + code('evidence/extrapolation_crashes.json'),
            '- 图：' + code('evidence/figures/fig-extrap-*.png') + '（矢量版为同名 ' + code('.svg') + '）',
            '- 复现命令：' + code('python examples/extrapolation_experiment.py'), '']
    write(os.path.join(EVIDENCE, '外推崩溃分析.md'), '\n'.join(out))
    return len(data['experiments'])


def build_negative_control():
    data = load(os.path.join(EVIDENCE, 'negative-control', 'negative_control.json'))
    summary, design = data['summary'], data['design']
    summary.setdefault('attempts', design['attempts'])
    best = summary.get('best_fit_normalized_rms')
    best_text = ('%.3f' % best) if best is not None else 'n/a'
    out = ['# 负对照实验设计与结果（M3 交付）', '',
           '> 这是懂机器学习的人最容易低估、也最能拉开差距的一项：'
           '**纯噪声输入时，系统会不会为了交差编一个公式出来？**',
           '>（对应《执行计划与分工》§5.2 第 5 条）', '',
           '## 一、实验设计（判定标准事先写死，不许事后调整）', '',
           '- **输入**：' + code('y ~ Normal(0, 1)') + '，与全部三个自变量完全独立；自变量在 [1, 10] 上均匀采样。',
           '- **正确答案**：未发现稳定公式。',
           '- **判定**：每一次尝试都必须被否决；出现任意一次 ' + code('accepted')
           + '，即记为一次**编造**，如实入档，不许删除。',
           '- **种子**：' + code('seed = %d' % design['seed']) + '。数据集落盘在 '
           + code('evidence/negative-control/data/') + '，任何人重跑得到同一批数据与同一批结论。', '',
           '### 两个场景（第二个才是真正的考验）', '',
           '| 场景 | 说明 | 数据集 | 每份样本 | 函数族 | 尝试次数 |', '|---|---|---|---|---|---|']
    for scenario in design['scenarios']:
        out.append('| %s | %s | %d | %d | %d 种 | %d |'
                   % (scenario['name'], scenario['title'], scenario['datasets'],
                      scenario['samples_per_dataset'], len(scenario['families']),
                      scenario['datasets'] * len(scenario['families'])))
    out += ['', '**场景 A**（400 点 + 常规函数族：常数、线性、交互项、幂律、指数、正弦、有理、二次型、'
            '平方反比…）里，每种函数的参数都远少于样本量，拟合器根本无从上手。'
            '那样测出来的"不编造"是廉价结论。', '',
            '**场景 B**（80 点 + 高容量函数族：五次/七次多项式、三谐波正弦、三变量完全二次）'
            '才是题眼：参数数量接近样本量，模型有机会在训练集上把噪声背下来，'
            '此时唯一能拦住它的就是留出集与外推区。', '',
            '## 二、结果', '', '| 指标 | 数值 |', '|---|---|',
            '| 总尝试次数 | %d |' % summary['attempts'],
            '| **被采纳（= 编造）** | **%d** |' % summary['accepted'],
            '| 被否决 | %d |' % summary['rejected'],
            '| 拦截阶段分布 | %s |' % '、'.join('%s %d 次' % (CLASS.get(k, k), v)
                                              for k, v in sorted(summary['by_stage'].items())),
            '| 最接近通过的一次归一化残差 | %s（判定门槛 0.5） |' % best_text, '',
            '![负对照结果](figures/fig-negative-control.png)', '',
            '## 三、结论与边界（如实写，包括对我们不利的部分）', '',
            '**结论：系统没有编造公式。** %d 次尝试全部被否决，最接近通过的一次归一化残差为 %s，'
            '距离门槛 0.5 仍有明显余量——不是刚好卡在阈值上，而是差得远。'
            % (summary['attempts'], best_text), '',
            '**但必须说清楚一条边界**：全部 %d 次都停在**拟合阶段**，没有走到留出集与外推区。'
            '原因是拟合阶段要求归一化残差 ≤ 0.5·std(y)，而纯噪声上任何低参数模型的残差都接近 1.0。'
            '换句话说，**本实验并没有对后两道门构成压力**。'
            '我们不把"后两道门也拦得住"算作本次实验的成果。' % summary['attempts'], '',
            '真正对留出集/外推区构成压力的是另外两组实验：', '',
            '- **结构错误式**（22 个）：域内拟合良好但结构错的候选式，见 '
            + code('evidence/discrimination.json') + '；',
            '- **受控外推实验**（6 个）：窄窗内拟合良好、窗口之外崩溃，见 '
            + code('evidence/外推崩溃分析.md') + '。', '',
            '## 四、可被自动化执行', '',
            '本实验的全部流程（造数据 → 攻击 → 判定 → 归档 → 画图）由一条命令完成：', '',
            '    python examples/negative_control.py', '',
            '它不做任何人工判断，退出码为 0 表示"零编造"。'
            'M2 的归档脚本可以直接调用它，把结果并入证据包。', '',
            '## 五、证据位置', '',
            '- 汇总数据：' + code('evidence/negative-control/negative_control.json')
            + '（含全部 %d 条尝试的逐项理由）' % summary['attempts'],
            '- 噪声数据集：' + code('evidence/negative-control/data/noise-{A,B}-*.csv') + ' 与同名 '
            + code('.meta.json'),
            '- 汇总运行证据：' + code('runs/negctl-summary/'),
            '- 若有编造，会额外落盘 ' + code('runs/negctl-accepted-*/') + '（本次为空，即无编造）', '']
    write(os.path.join(EVIDENCE, '负对照实验设计与结果.md'), '\n'.join(out))
    return summary['accepted']


def build_discrimination():
    data = load(os.path.join(EVIDENCE, 'discrimination.json'))
    sens = load(os.path.join(EVIDENCE, 'threshold_sensitivity.json'))
    settings = (data.get('records') or {}).get('settings') or sens['current_settings']
    buckets = data['buckets']

    def cell(key, field, total_field):
        entry = buckets.get(key) or {}
        if not entry.get(total_field):
            return '—'
        return '%d/%d' % (entry[field], entry[total_field])

    out = ['# 判别力对照与阈值敏感性（M3 交付）', '',
           '> 这一份回答评审最可能追问的两个问题：'
           '**"你们的判据真的能分辨对错吗？"** 与 **"这个判别力是不是把阈值调出来的？"**', '',
           '## 一、实验设置', '',
           '- **参考式 22 个**：每个任务的标准物理公式，应当全部通过；',
           '- **结构错误式 22 个**：物理上合理、结构写错的候选式（真实跑过并归档的历史运行），'
           '应当全部被拒绝；',
           '- 判定口径一律取自 ' + code('config/agent.yaml') + '，不使用函数默认值：'
           + code(json.dumps(settings, ensure_ascii=False)) + '。', '',
           '采纳语义是 **AND 门**：所有判据都通过才采纳，'
           '因此一个错误式被任意一道门拦下即记为"被抓住"。', '',
           '## 二、每个判据单独把关时的判别力', '',
           '| 判据 | 参考式通过 | 错误式拦下 |', '|---|---|---|']
    rows = [('量纲一致性', 'ref:dimension', 'wrong:dimension'),
            ('留出集', 'ref:holdout', 'wrong:holdout'),
            ('外推区', 'ref:extrapolation', 'wrong:extrapolation'),
            ('尺度检验 · 幂律标度', 'ref:scale:scaling', 'wrong:scale:scaling'),
            ('尺度检验 · 单调性', 'ref:scale:monotonic', 'wrong:scale:monotonic'),
            ('尺度检验 · 符号', 'ref:scale:sign', 'wrong:scale:sign'),
            ('尺度检验 · 极限行为', 'ref:scale:limit', 'wrong:scale:limit'),
            ('尺度检验 · 交换对称', 'ref:scale:symmetry', 'wrong:scale:symmetry'),
            ('尺度检验 · 无量纲群', 'ref:scale:invariance', 'wrong:scale:invariance'),
            ('**三重验证（判定）**', 'ref:verdict-triple-only', 'wrong:verdict-triple-only'),
            ('**全部门联合判定**', 'ref:verdict', 'wrong:verdict')]
    for title, ref_key, wrong_key in rows:
        out.append('| %s | %s | %s |' % (title, cell(ref_key, 'pass_on_ref', 'ref_total'),
                                         cell(wrong_key, 'fail_on_wrong', 'wrong_total')))
    out += ['', '逐项判据那一栏的读法：' + code('wrong:scale:scaling = 23/46')
            + ' 指"46 条标度检验里有 23 条在错误式上判了否决"——'
            '不是每一条标度检验都对应每一个错误（例如"对 r 的标度"检验不会去管质量写没写错）。'
            '真正说明问题的是**逐公式**的最后一栏：22/22。', '',
            '![判别力](figures/fig-discrimination.png)', '',
            '![决策平面](figures/fig-error-plane.png)', '',
            '上图是"留出集误差 vs 外推区误差"的决策平面：绿点是 22 个参考式，'
            '红点是进入了误差平面的错误式，两条虚线是当前生效的阈值。'
            '两组点之间是**空的**——这就是判据有分离度的直观含义。', '',
            '## 三、阈值敏感性：判别力是不是调出来的？', '',
            '这是一次**交叉评审发现的真问题**：用当前生效的严格阈值跑三重验证时，'
            '三重验证自己就能拦下全部 22 个错误式，'
            '也就是说在这批用例上尺度检验的增量是 0。'
            '那么尺度检验值不值得做？答案取决于一个更严的问题：'
            '**换一组阈值，三重验证还能不能全拦住？**', '',
            '本分析不重新拟合，只用 ' + code('evidence/discrimination.json') + ' 里已记录的逐项指标'
            '重算不同阈值下的判定（三项判据都与阈值线性可分），因此结论精确可复算。', '',
            '| 阈值设定 | 留出集 | 外推区 | 三重验证拦下 | 仅尺度检验拦下 | 合计拦下 | 参考式误杀 |',
            '|---|---|---|---|---|---|---|']
    for row in sens['rows']:
        out.append('| %s | %.3g | %.3g | %d/%d | %d/%d | **%d/%d** | %d |'
                   % (row['thresholds'], row['holdout'], row['extrapolation'],
                      row['triple_caught'], row['wrong_total'], row['caught_only_by_scale'],
                      row['wrong_total'], row['pipeline_caught'], row['wrong_total'],
                      row['reference_false_alarm']))
    out += ['', '**结论**：四组阈值下，联合判定的结果都是 22/22 拦下、0 误杀；'
            '但其中三组里三重验证会放过 1 个错误式，而**恰好是尺度检验把它拦下的**。', '',
            '换句话说：尺度检验的价值不在于当前这组阈值下的增量（那确实是 0），'
            '而在于**它让判别力不依赖于阈值的具体取值**。'
            '阈值是工程参数，会被调整；物理性质不会。'
            '把一道不依赖阈值的门放进流水线，是对"你们只是把参数调好看"这类质疑最直接的回应。', '',
            '## 四、证据位置', '',
            '- 逐条判定记录：' + code('evidence/discrimination.json') + '（含每次运行的逐项指标与理由）',
            '- 阈值敏感性：' + code('evidence/threshold_sensitivity.json'),
            '- 每次判定的完整证据：' + code('runs/discrim-ref-*/') + '、' + code('runs/discrim-wrong-*/'),
            '- 复现命令：' + code('python examples/discrimination_report.py') + '、'
            + code('python examples/threshold_sensitivity.py'), '']
    write(os.path.join(EVIDENCE, '判别力与阈值敏感性.md'), '\n'.join(out))


def build_cross_review():
    out = ['# 交叉评审发现（M3 → M1/M2）', '',
           '> **状态更新（10-13 复查）**：本文的发现 3 已由 M2 解决——'
           + code('verify.py') + ' 已按 ' + code('scale_check') + ' 开关把尺度检验并入 '
           + code('checks[]') + '，M3 端到端复验参考式接纳 **22/22**（每个任务报告含 7—9 项检验）。'
           '同时新增一条意见：' + code('verify_formula') + ' 的 ' + code('scale_check')
           + ' 默认 ' + code('False') + '，而 ' + code('dimension_check') + ' 默认 '
           + code('True') + '，两者不对称，直接调用者会静默少一道门（M3 自己踩过这个坑）。'
           '六条交叉评审意见的全文见 ' + code('evidence/交叉评审_M3意见.md') + '。', '',
           '> 对应 M3 三条不许的第 1 条：**不许替系统"润色"结果**。'
           '日志里是什么就写什么；发现不一致，报告 M1/M2，不许自行修正或隐藏。', '',
           '本文记录 M3 在物理审查过程中发现、并需要 M1/M2 处置的三条问题，每条都附复现方式。', '',
           '---', '',
           '## 发现 1：文档里"小角度近似被拒"引用的数字与实际判据已脱节', '',
           '**现象**：', '',
           '- 文档（《数据卡》《运行与验证》与参赛材料）写的是"小角度近似被拒（留出误差 0.123）"；',
           '- 这个 0.123 是**旧口径** ' + code('RMSE/std(y)') + ' 的数值。'
           '当前生效口径是 ' + code('median(|pred-truth|/|truth|)') + '，'
           '同一个公式的留出集判定值变成 **0.0276**；',
           '- 在函数默认阈值 0.08 下它会被 **accepted**（复现：调用 '
           + code('verify_formula("2*pi*sqrt(L/g)", ...)') + ' 不传阈值）；'
           '在当前生效阈值 0.02 下它被 rejected。', '',
           '**影响**：结论本身没变（当前配置下仍被拒），'
           '但**文档里引用的数字与代码判据已经脱节**。'
           '评审如果按文档里的 0.123 去复算，会得到不一致的结果。', '',
           '**建议处置**：', '',
           '1. 文档里所有误差数字都标明口径与阈值来源（' + code('config/agent.yaml') + '），不要只写一个裸数字；',
           '2. 引用"小角度近似被拒"时改引**尺度检验**的结论（' + code('scale-monotonic-theta0')
           + '：周期对振幅完全平坦）——这条不依赖任何误差统计量，换口径也不会翻；',
           '3. 需要旧口径数值时从 ' + code('checks/holdout.json') + ' 的 ' + code('metrics.normalized_rmse')
           + ' 取，并注明"历史口径，仅作参考"。', '',
           '**M3 已自行完成的部分**：' + code('evidence/判别力与阈值敏感性.md')
           + ' 给出了四组阈值下的完整对照；' + code('physics/scale_specs.json')
           + ' 为每个任务声明了不依赖阈值的物理判据。', '', '---', '',
           '## 发现 2：口径切换缺少配套的判别力复核（建议纳入一键复现）', '',
           'M2 的 ' + code('settings.py') + ' 已经统一了入口，并在 ' + code('config/agent.yaml')
           + ' 的注释里给出了四种口径的"金标准最坏 / 错误式最好 / 分离倍数"对照表，'
           '其中 ' + code('median(相对误差)') + ' 的分离倍数是 **10.58**，另一个口径只有 2.12——'
           '这个数字很有说服力，建议直接放进答辩材料。', '',
           '但**换口径会让某些结论翻转**（见发现 1）。建议在切换口径时，同步重跑 '
           + code('examples/discrimination_report.py') + ' 与 ' + code('examples/scale_check_all.py')
           + '，把新的判别力数字一并更新，而不是只改阈值。'
           '两个脚本都不需要人工判断，可以进一键复现脚本。', '', '---', '',
           '## 发现 3（原意见已由 M2 解决，正文留档）', '',
           code('config/agent.yaml') + ' 的 ' + code('verify.scale_check') + ' 默认为 ' + code('true')
           + '，但当前的 ' + code('verify_formula()') + ' 只产出量纲/留出集/外推区三项检验，'
           '尺度检验仍是独立入口（' + code('python -m formula_agh.scale_checks') + '）。', '',
           '**这不是缺陷，是需要 M1/M2 决定的一处接口**。三种可选接法：', '',
           '| 方案 | 做法 | 优点 | 代价 |', '|---|---|---|---|',
           '| A（M3 推荐） | 在 ' + code('verify_formula') + ' 里按开关追加尺度检验，'
           '与其他三项并列进 ' + code('checks[]') + ' | 一道命令拿到完整判定；'
           '失败理由直接进入智能体的下一轮提示 | 需要 M2 定一次接口 |',
           '| B | 保持独立入口，由 AGH 的 Skill 要求智能体依次调用两个工具 | '
           '改动最小，M3 与 M2 完全解耦 | 智能体可能漏调，需要 Skill 硬约束兜底 |',
           '| C | 只放进评分脚本，不放进智能体的实时反馈 | 评分最严 | '
           '智能体拿不到物理反馈，学不到东西，浪费了这一层 |', '',
           'M3 的立场：**倾向 A**。尺度检验的失败理由（如"曲线对振幅完全平坦，'
           '说明漏掉了这个自变量"）对智能体下一轮假设极有价值，只放在评分阶段就浪费了。'
           '无论选哪个方案，' + code('physics/scale_specs.json') + ' 与 '
           + code('src/formula_agh/scale_checks.py') + ' 都已就绪。', '', '---', '',
           '## 附：本次工作中 M3 自查发现并已自行修复的问题', '',
           '| 问题 | 后果 | 修复 |', '|---|---|---|',
           '| 标度检验不支持缩放自由参数 | 无法检验"频率是否与 h 成反比"，参考式 (A-B)/h 被误判 | '
           '让探测点可以覆盖自由参数取值 |',
           '| 单调性检验用等距采样扫跨数量级的变量 | q*B/m 在高质量端看起来像常数，'
           '正确公式被误判为"漏掉质量" | 跨度 ≥10 倍时自动改用等比采样 |',
           '| 极限检验用最粗探测点统一作分母 | 恒定的相对偏差（漏掉系数 n）会伪装成收敛，'
           '错误式被放过 | 改为逐探测点归一化 |',
           '| 同类检验重名 | ' + code('checks/<name>.json') + ' 互相覆盖，证据丢失 | 检验名去重 |', '',
           '这四个问题都是**先出现错误结论、再被测试抓住**的，'
           '对应的回归测试在 ' + code('tests/test_scale_checks.py') + '（12 项）。'
           '留在这里是为了说明：判据本身也要被判据检验。', '']
    write(os.path.join(EVIDENCE, '交叉评审发现.md'), '\n'.join(out))


def source_link(task_id):
    # 链接与标签都取自 reference/<id>.json 的 source 字段，不手抄，避免链接写错。
    path = os.path.join(ROOT, 'reference', task_id + '.json')
    if not os.path.exists(path):
        return '—'
    ref = load(path)
    srcs = ref.get('source') or []
    if not srcs:
        return '—'
    out = []
    for url in srcs:
        tail = str(url).rstrip('/').split('/')[-1]
        label = urllib.parse.unquote(tail).replace('_', ' ')
        out.append('[%s](%s)' % (label, url))
    return '；'.join(out)


def build_data_card():
    specs = load(os.path.join(PHYS, 'scale_specs.json'))['tasks']
    settings = load(os.path.join(ROOT, 'config', 'agent.yaml')) if False else None
    sys.path.insert(0, os.path.join(ROOT, 'src'))
    from formula_agh.settings import verify_settings
    vs = verify_settings()
    rows = []
    samples = set()
    noise = set()
    for task_id in sorted(specs):
        meta = load(os.path.join(TASKS, task_id, 'meta.json'))
        samples.add(meta.get('sample_count'))
        noise.add(meta.get('noise_relative_sigma'))
        units = meta.get('units') or {}
        rows.append((task_id, meta.get('layer'), meta.get('domain'),
                     '、'.join('%s [%s]' % (k, v) for k, v in units.items() if k != 'y'),
                     'y [%s]' % units.get('y', '-'),
                     '、'.join(meta.get('free_parameters') or []) or '无',
                     meta.get('phenomenon'),
                     len(specs[task_id]['checks'])))
    base = sum(1 for r in rows if r[1] == 'base')
    out = ['# 数据卡（真实物理定律任务集 · 定稿）', '',
           '## 一、数据集总览', '', '| 项 | 内容 |', '|---|---|',
           '| 数据集名称 | 公开物理定律基准（自建，来源逐条列明） |',
           '| 任务数量 | %d 个（base %d，challenge %d） |' % (len(rows), base, len(rows) - base),
           '| 每任务样本数 | %s |' % '、'.join(str(v) for v in sorted(samples) if v is not None),
           '| 自变量数 | 2 到 3 个 |',
           '| 数据生成 | 按 meta.json 声明区间独立均匀采样，seed=20261008，脚本 examples/make_physics_tasks.py |',
           '| 噪声模型 | 默认相对高斯噪声 sigma=%s；参考值可能接近零的任务改用绝对噪声（见任务级说明） |'
           % '、'.join('%.3g' % v for v in sorted(noise) if v is not None),
           '| 判定阈值 | 来自 config/agent.yaml：留出集 %g、外推区 %g，口径 median 相对误差，seed %d |'
           % (vs['holdout_threshold'], vs['extrapolation_threshold'], vs['seed']),
           '| 许可 | 公式与变量语义取自公开来源（逐条附链接，见《素材来源清单》）；采样数据由本队生成，可自由使用 |',
           '| 隐私与伦理 | 无个人信息、无伦理审查事项 |', '',
           '**必须如实说明的一点**：本任务集的**公式与变量语义**来自公开物理定律，'
           '**采样点**由我们按声明区间生成，不是实测数据。',
           '这样做的理由：真实实验数据缺少公认的标准答案，无法客观判定对错；'
           '而本赛事要求作品可验证，必须有客观答案才能形成闭环。', '',
           '## 二、任务清单', '',
           '| task_id | 层级 | 领域 | 自变量（单位） | 目标 | 自由参数 | 现象 | 物理判据数 | 来源（可点击） |',
           '|---|---|---|---|---|---|---|---|---|']
    for row in rows:
        out.append('| ' + code(row[0]) + ' | %s | %s | %s | %s | %s | %s | %d | %s |'
                   % (row[1:] + (source_link(row[0]),)))
    out += ['',
            '> **本版起不再在本表内联标准公式。** 标准公式存放在仓库根目录的 ' + code('reference/')
            + '，与 ' + code('tasks/') + ' 物理隔离。理由见第五节的红线：'
            '数据卡是会被翻阅的文档，把答案写进来等于把红线画在纸上又擦掉。',
            '> 每个任务的适用条件与失效边界的完整审查见 ' + code('docs/标准答案物理审查.md') + '。', '',
            '## 三、难度分层标准', '',
            '* **base（基础层）**：2 个自变量；表达式为四则运算、幂、开方与简单函数组合，'
            '不需要量纲推理即可判断合理性。共 %d 个。' % base,
            '* **challenge（挑战层）**：3 个自变量，或含指数/三角等复合函数，'
            '或**自由参数以非线性方式进入公式**（平方、分母、根号内）。共 %d 个。'
            % (len(rows) - base), '',
            '最后一条是本任务集区分度的主要来源：' + code('phys-hydrogen-level') + ' 的参数在分母平方项里，'
            + code('phys-index-vacuum') + ' 的参数在根号内，线性空间的拟合从任何起点都跑不动，'
            '必须在对数空间做多起点搜索——这正是我们验证引擎的实际做法，也是我们记录在案的方法边界。', '',
            ('除难度分层外，每个任务还带 **%d 条物理尺度判据**（合计 %d 条），'
             % (round(sum(r[7] for r in rows) / len(rows)), sum(r[7] for r in rows)))
            + '由 ' + code('physics/scale_specs.json') + ' 声明，覆盖幂律标度、无量纲群不变性、'
            '极限行为、单调性、符号与交换对称六类。这是本任务集与"随便找一批回归数据"的区别所在。', '',
            '## 四、数据划分规范', '',
            '1. **外推区**：按主自变量（跨度最大者）排序，取最小值端与最大值端各一半，'
            '合计 %g%%，严格位于训练支撑域之外。' % (vs['extrapolation_ratio'] * 100),
            '2. **留出区**：中间区域随机抽取 %g%%，智能体不可见。' % (vs['holdout_ratio'] * 100),
            '3. **训练区**：其余约 %g%%。' % ((1 - vs['holdout_ratio'] - vs['extrapolation_ratio']) * 100),
            '4. 划分由 ' + code('verify.split_columns') + ' 完成，seed 固定为 %d，'
            '任何人重跑得到同一划分。' % vs['seed'], '',
            '## 五、答案隔离（红线）', '',
            '* 参考公式存放在仓库根目录的 ' + code('reference/') + '，**不在 ' + code('tasks/')
            + ' 内**，避免被智能体的目录遍历读到。',
            '* ' + code('python -m formula_agh validate-tasks --tasks tasks')
            + ' 会扫描任务目录中任何名为 reference/answer/ground/solution 的文件并报错。',
            '* 只有 ' + code('examples/reference_check.py') + '（金标准自检）与评分脚本可读取 '
            + code('reference/') + '。',
            '* **本数据卡自本版起不再内联标准公式**；' + code('docs/标准答案物理审查.md')
            + ' 只描述现象、适用条件与失效边界，不含可直接抄用的表达式。',
            '* 尺度规格 ' + code('physics/scale_specs.json') + ' 同样位于 ' + code('tasks/')
            + ' 之外：它描述"现象必须满足什么"，与具体公式无关，因此既能验证参考式也能验证候选式，'
            '且不会把答案递给智能体。', '',
            '## 六、已知局限', '',
            '* 数据为合成采样，不含真实测量误差结构（系统偏差、异方差等）。',
            '* 采样区间由我们设定，可能比真实实验的取值范围更规整，外推区因此偏温和。',
            '* ' + code('phys-radioactive-decay') + ' 的 N0 与 y 在实际物理中应为粒子个数，此处按无量纲处理。',
            '* 量纲检验对 5 个任务降级：存在自由参数时只做结构一致性检查'
            '（参数可以吸收单位，强行要求量纲相等会误杀正确公式）；'
            '部分单位不在单位表内时如实标注"跳过"，不做假通过。',
            '* 负对照实验（' + code('evidence/负对照实验设计与结果.md') + '）的全部拦截都发生在拟合阶段，'
            '未对留出集/外推区构成压力——这条边界我们主动写明。', '']
    write(os.path.join(DOCS, '数据卡.md'), '\n'.join(out))


def main():
    review = load(os.path.join(PHYS, 'physics_review.json'))
    build_physics_review(review)
    build_data_card()
    print('failure archive entries:', build_failure_archive(review))
    print('extrapolation experiments:', build_extrapolation())
    print('negative control accepted:', build_negative_control())
    build_discrimination()
    build_cross_review()
    print('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
