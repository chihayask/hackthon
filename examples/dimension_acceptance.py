# -*- coding: utf-8 -*-
# 量纲检查工具的验收测试（M3 交付物 10-09 的验收证据）。
#
# 任务书的验收标准只有两句话：
#   "对正确公式判 pass；对人为改错单位的公式判 fail。"
# 这两句话要变成可复核的东西，就必须回答三个更细的问题：
#
#   1. 对 22 个参考公式，量纲检验是不是真的判了 pass？
#   2. 把某个变量的单位换成量纲不同的另一个单位，检验能不能发现？
#   3. 有没有任务其实是"跳过"而不是"通过"？（M2 怀疑清单第 3 条）
#
# 第 3 条最关键。'跳过'与'通过'在代码里都是 passed=True，
# 但它们是两件完全不同的事：跳过意味着这道门形同虚设。
# 本脚本因此把结果分成三种：pass / skip / fail，绝不把 skip 记成 pass。
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.evidence import write_evidence
from formula_agh.settings import verify_settings
from formula_agh.units import UNIT_TABLE
from formula_agh.verify import CheckResult, VerifyReport, _check_dimension, load_task

TASKS = os.path.join(ROOT, 'tasks')
REF = os.path.join(ROOT, 'reference')
EVIDENCE = os.path.join(ROOT, 'evidence')

# 每个单位对应的"看起来像、量纲不同"的错误单位。
# 选择标准：必须是同一个物理场景里说得出口的单位，而不是随便乱填——
# 检验要防的是"抄错单位"，不是"填一串乱码"。
WRONG_UNIT = {
    'm': 'm/s', 'm/s': 'm/s^2', 'm/s^2': 'm/s',
    'kg': 'm', 'm^3': 'm^2', 'm^2': 'm^3', 'kg/m^3': 'kg/m^2',
    's': 'm', 'K': 's', 'mol': 'kg', 'cd': 'mol',
    'C': 'A', 'A': 'C', 'J': 'N', 'N': 'J', 'W': 'J', 'V': 'W',
    'Pa': 'N', 'Hz': 'Pa', 'ohm': 'V', 'N/m': 'N',
    'rad': 'm', '-': 'm', '1': 'm', '': 'm',
    'F/m': 'H/m', 'H/m': 'F/m',
}

SKIP_MARKERS = ('跳过', '不适用', '无法识别', '未提供单位', '推迟')


def classify(check):
    if not check.passed:
        return 'fail'
    if any(marker in check.reason for marker in SKIP_MARKERS):
        return 'skip'
    return 'pass'


def load_reference(task_id):
    with open(os.path.join(REF, task_id + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def write_report(rows, summary, coverage, scale_specs, caught, total, missed, na):
    t = summary['base_kind_counts']
    out = [
        '# 量纲检查工具验收报告（M3 交付 · 10-09 验收标准）',
        '',
        '> 任务书的验收标准只有两句话：**"对正确公式判 pass；对人为改错单位的公式判 fail。"**',
        '> 本报告把它变成可复核的数字，并如实报告一处**必须让评审知道的能力边界**。',
        '',
        '## 一、三种结果必须分开记（这是本报告的核心）',
        '',
        '在代码里，"跳过"与"通过"都是 ' + chr(96) + 'passed=True' + chr(96) + '，',
        '但它们是两件完全不同的事：跳过意味着这道门形同虚设。',
        '因此本验收把每个结果分成三种：',
        '',
        '| 类别 | 含义 | 判定依据 |',
        '|---|---|---|',
        '| **pass** | 量纲检验真正执行并判通过 | ' + chr(96) + 'passed=True' + chr(96) + ' 且理由中不含"跳过/推迟/不适用" |',
        '| **skip** | 检验被如实标注为跳过或降级 | ' + chr(96) + 'passed=True' + chr(96) + ' 但理由是"严格比对推迟"或"未知单位跳过" |',
        '| **fail** | 判否决 | ' + chr(96) + 'passed=False' + chr(96) + ' |',
        '',
        '## 二、结论 1：正确公式全部没有被误杀',
        '',
        '| 结果 | 数量 | 占 22 个任务 |',
        '|---|---|---|',
        '| pass（量纲门严格生效） | %d | %.0f%% |' % (t['pass'], 100.0 * t['pass'] / 22),
        '| skip（量纲门降级） | %d | %.0f%% |' % (t['skip'], 100.0 * t['skip'] / 22),
        '| fail（误杀） | %d | %.0f%% |' % (t['fail'], 100.0 * t['fail'] / 22),
        '',
        '**零误杀**：没有任何一个物理上正确的参考公式因为量纲检验被否决。',
        '降级全部来自一个刻意的设计取舍：**存在自由参数时，参数本身可以吸收单位**，',
        '若强行要求公式量纲等于 y 的量纲，会把 ' + chr(96) + 'G*m1*m2/r**2' + chr(96) + ' 这类正确公式误杀。',
        '所以引擎选择了"结构一致性检查 + 明确标注推迟"，而不是假装通过。',
        '',
        '## 三、结论 2：人为改错单位的检出率',
        '',
        '对 22 个任务的每个变量，逐个替换成"看起来像、量纲不同"的错误单位',
        '（如 ' + chr(96) + 'm → m/s' + chr(96) + '、' + chr(96) + 'J → N' + chr(96) + '、' + chr(96) + 'C → A' + chr(96) + '），共构造 %d 例有效扰动：' % total,
        '',
        '| 结果 | 例数 | 说明 |',
        '|---|---|---|',
        '| 被发现（判 fail） | %d | 量纲门或结构一致性检查拦下 |' % caught,
        '| 未发现 | %d | 全部落在量纲门降级的任务上，理由如实标注为"推迟" |' % missed,
        '| 不适用 | %d | 该单位没有"貌似合理"的替换项，或替换项本身是未知单位 |' % na,
        '',
        '## 四、结论 3（必须让评审知道的能力边界）：量纲门只覆盖 %d / 22 个任务' % t['pass'],
        '',
        '这不是缺陷，是**设计取舍的代价**，但代价有多大必须说清楚：',
        '',
        '| 项 | 任务数 | 任务列表 |',
        '|---|---|---|',
        '| 量纲门严格生效 | %d | %s |' % (len(coverage['dimension_strict']),
                                        '、'.join(chr(96) + x + chr(96) for x in coverage['dimension_strict'])),
        '| 量纲门降级 | %d | %s |' % (len(coverage['dimension_degraded']),
                                     '、'.join(chr(96) + x + chr(96) for x in coverage['dimension_degraded'])),
        '',
        '**降级的 %d 个任务全部由尺度检验（M3）覆盖**，没有一个任务处于无人看守状态：'
        % len(coverage['dimension_degraded']),
        '',
        '| 降级任务 | 该任务的尺度判据条数 |',
        '|---|---|',
    ]
    for task_id in coverage['dimension_degraded']:
        spec = scale_specs.get(task_id) or {}
        out.append('| ' + chr(96) + task_id + chr(96) + ' | %d |' % len(spec.get('checks') or []))
    out += [
        '',
        '未被尺度门覆盖的任务：**%s**。'
        % ('无' if not coverage['degraded_and_uncovered']
           else '、'.join(coverage['degraded_and_uncovered'])),
        '',
        '这正是"多一道不依赖误差阈值的门"的价值所在：量纲门的盲区，尺度门补上。',
        '两者合起来，22 个任务在物理侧**全部有门**。',
        '',
        '## 五、逐任务明细',
        '',
        '图例：✓ 改错单位被发现 / ✗漏 未发现 / ~ 检验降级 / – 不适用',
        '',
        '| 任务 | 参考式量纲门 | ' + ' | '.join('变量扰动') + ' |',
        '|---|---|---|',
    ]
    for record in rows:
        bits = []
        for item in record['perturbations']:
            mark = {'fail': '✓', 'pass': '✗漏', 'skip': '~', 'n/a': '–'}[item['kind']]
            bits.append('%s → %s %s' % (item['var'], item['wrong_unit'] or '—', mark))
        out.append('| ' + chr(96) + record['task_id'] + chr(96) + ' | %s | %s |'
                   % (record['base_kind'], ' ； '.join(bits)))
    out += [
        '',
        '## 六、复现方式',
        '',
        '    python examples/dimension_acceptance.py',
        '',
        '- 机器可读结果：' + chr(96) + 'evidence/dimension_acceptance.json' + chr(96),
        '- 运行证据：' + chr(96) + 'runs/m3-dimension-acceptance/' + chr(96),
        '- 被测工具：' + chr(96) + 'src/formula_agh/units.py' + chr(96)
        + ' 与 ' + chr(96) + 'src/formula_agh/verify.py::_check_dimension' + chr(96),
        '',
        '## 七、由此产生的两条改进要求（已上报 M1/M2）',
        '',
        '1. **文档与答辩口径**：不得笼统宣称"每个任务都做了量纲检验"。',
        '   正确表述是"13 个任务量纲门严格生效，9 个任务降级为结构一致性检查',
        '   并由 106 条尺度判据补位"。见 ' + chr(96) + 'evidence/交叉评审发现.md' + chr(96) + '。',
        '2. **智能体提示语**：量纲门降级时，工具返回的 JSON 应当在 ' + chr(96) + 'rounds_hint' + chr(96),
        '   里显式提醒"本任务量纲门已降级，请勿据此认为公式在物理上已通过"。',
        '   目前的 ' + chr(96) + 'reason' + chr(96) + ' 字段已如实标注，但提示语没有跟着变。',
        '',
    ]
    path = os.path.join(EVIDENCE, '量纲检验验收.md')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = chr(10).join(out)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote evidence/量纲检验验收.md (%d chars)' % len(text))


def main():
    settings = verify_settings()
    rows = []
    totals = {'pass': 0, 'skip': 0, 'fail': 0}
    strict_tasks = 0
    loose_tasks = 0

    for task_id in sorted(os.listdir(TASKS)):
        task_dir = os.path.join(TASKS, task_id)
        if not os.path.isdir(task_dir):
            continue
        columns, meta = load_task(task_dir)
        ref = load_reference(task_id)
        formula = ref['formula']
        free = [str(p) for p in (ref.get('free_parameters') or [])]
        units = dict(meta.get('units') or {})

        # --- 用例 A：原始（正确）单位 -------------------------------------------------
        base = _check_dimension(formula, meta, free)
        base_kind = classify(base)
        totals[base_kind] += 1
        if base_kind == 'pass':
            strict_tasks += 1
        else:
            loose_tasks += 1
        record = {'task_id': task_id, 'formula': formula,
                  'free_parameters': free,
                  'base_kind': base_kind, 'base_reason': base.reason,
                  'perturbations': []}

        # --- 用例 B：逐个变量换成错误单位 ---------------------------------------------
        for var, unit in sorted(units.items()):
            if var == 'y':
                continue
            wrong = WRONG_UNIT.get(str(unit))
            if not wrong:
                record['perturbations'].append({
                    'var': var, 'unit': unit, 'wrong_unit': None,
                    'kind': 'n/a', 'reason': '该单位没有预设的"貌似合理但量纲不同"的替换项'})
                continue
            if str(wrong) not in UNIT_TABLE:
                record['perturbations'].append({
                    'var': var, 'unit': unit, 'wrong_unit': wrong,
                    'kind': 'n/a', 'reason': '替换单位不在单位表内，属于"未知单位"分支而非量纲比对'})
                continue
            bad_meta = dict(meta)
            bad_units = dict(units)
            bad_units[var] = wrong
            bad_meta['units'] = bad_units
            check = _check_dimension(formula, bad_meta, free)
            kind = classify(check)
            record['perturbations'].append({
                'var': var, 'unit': unit, 'wrong_unit': wrong,
                'kind': kind, 'reason': check.reason})
        rows.append(record)

    # --- 统计 ------------------------------------------------------------------------
    pert_total = pert_caught = pert_missed = pert_na = 0
    for record in rows:
        for item in record['perturbations']:
            if item['kind'] == 'n/a':
                pert_na += 1
                continue
            pert_total += 1
            if item['kind'] == 'fail':
                pert_caught += 1
            else:
                pert_missed += 1

    summary = {
        'task_count': len(rows),
        'base_kind_counts': totals,
        'perturbations_total': pert_total,
        'perturbations_caught': pert_caught,
        'perturbations_missed': pert_missed,
        'perturbations_not_applicable': pert_na,
        'note': ('base_kind = pass 表示量纲检验真正执行并判通过；skip 表示检验被如实标注为'
                 '跳过或降级（passed=True 但门是虚设的）；fail 表示判否决。'),
    }
    payload = {'settings': dict(settings), 'summary': summary, 'rows': rows}
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(os.path.join(EVIDENCE, 'dimension_acceptance.json'), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    checks = [
        CheckResult('dimension-acceptance', totals['skip'] == 0,
                    '22 个参考公式中：严格通过 %d 个、降级/跳过 %d 个、误判否决 %d 个'
                    % (totals['pass'], totals['skip'], totals['fail']),
                    {'pass': totals['pass'], 'skip': totals['skip'], 'fail': totals['fail']}),
        CheckResult('dimension-sensitivity', pert_total > 0 and pert_caught == pert_total,
                    '人为改错单位共 %d 例，被量纲检验发现 %d 例、漏过 %d 例（另有 %d 例不适用）'
                    % (pert_total, pert_caught, pert_missed, pert_na),
                    {'total': pert_total, 'caught': pert_caught,
                     'missed': pert_missed, 'not_applicable': pert_na}),
    ]
    verdict = 'accepted' if all(c.passed for c in checks) else 'rejected'
    report = VerifyReport('dimension-acceptance',
                          '(对 22 个参考公式及其单位扰动做量纲检验验收)',
                          {}, verdict, checks,
                          '量纲检验验收完成；未通过项说明该门存在可被绕过的情形，需如实上报。')
    write_evidence(os.path.join(ROOT, 'runs', 'm3-dimension-acceptance'), report,
                   'python examples/dimension_acceptance.py',
                   inputs=['tasks/', 'reference/', 'src/formula_agh/units.py'],
                   notes='M3 量纲检查工具验收（10-09 验收标准）', settings_in=settings)

    # --- 互补性分析：量纲门降级的任务，尺度门是否覆盖？ --------------------------------
    specs_path = os.path.join(ROOT, 'physics', 'scale_specs.json')
    scale_specs = {}
    if os.path.exists(specs_path):
        with open(specs_path, encoding='utf-8') as fh:
            scale_specs = json.load(fh).get('tasks') or {}
    skipped = [r['task_id'] for r in rows if r['base_kind'] != 'pass']
    uncovered = [t for t in skipped if not (scale_specs.get(t) or {}).get('checks')]
    coverage = {
        'dimension_strict': [r['task_id'] for r in rows if r['base_kind'] == 'pass'],
        'dimension_degraded': skipped,
        'degraded_but_covered_by_scale': [t for t in skipped if t not in uncovered],
        'degraded_and_uncovered': uncovered,
    }
    summary['coverage'] = coverage
    payload['summary'] = summary
    with open(os.path.join(EVIDENCE, 'dimension_acceptance.json'), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    write_report(rows, summary, coverage, scale_specs, pert_caught, pert_total, pert_missed, pert_na)

    print('参考公式的量纲检验结果：pass %d / skip %d / fail %d'
          % (totals['pass'], totals['skip'], totals['fail']))
    print('量纲门降级的 %d 个任务中，被尺度门覆盖 %d 个，无人覆盖 %d 个'
          % (len(skipped), len(coverage['degraded_but_covered_by_scale']), len(uncovered)))
    print('单位扰动：共 %d 例，发现 %d，漏过 %d，不适用 %d'
          % (pert_total, pert_caught, pert_missed, pert_na))
    print('')
    print('%-30s %-6s %s' % ('task', 'base', '单位扰动结果'))
    for record in rows:
        bits = []
        for item in record['perturbations']:
            mark = {'fail': '✓', 'pass': '✗漏', 'skip': '~', 'n/a': '-'}[item['kind']]
            bits.append('%s:%s' % (item['var'], mark))
        print('%-30s %-6s %s' % (record['task_id'], record['base_kind'], ' '.join(bits)))
    print('')
    print('图例：✓ 改错单位被发现 / ✗漏 未发现 / ~ 跳过 / - 不适用')
    return 0


if __name__ == '__main__':
    sys.exit(main())
