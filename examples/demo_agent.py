# -*- coding: utf-8 -*-
# 自主闭环演示：智能体提出假设 -> 引擎三重验证 -> 被否决 -> 依据否决理由修正 -> 通过。
#
# 两种模式：
#   默认  内置假设生成器（无需模型账号，用于复现与录制脚本）
#   --llm 通过 AGH CLI 调用 Agnes 模型生成假设（需先构建并配置好 AGH）
#
# 输出：控制台逐轮实录 + runs/<run_id>/ 完整证据（含 trajectory.jsonl）
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.evidence import write_evidence
from formula_agh.settings import verify_settings
from formula_agh.verify import VerifyError, load_task, verify_formula

# 阈值与开关的唯一来源。改造前这里直接调用 verify_formula 不传参数，
# 于是演示用的是引擎默认值（留出集 0.08、外推区 0.15、不跑尺度检验），
# 与 config/agent.yaml 生效值（0.02 / 0.03 / 开启）不一致——
# 演示里"通过了"的公式，按正式配置可能并不通过。这属于判据被静默降级。
SETTINGS = verify_settings()


def emit(line):
    print(line, flush=True)


# ---- 假设生成：依据上一轮否决理由改形式，而不是改参数 ----
STRATEGIES = {
    'phys-pendulum-exact': [
        ('忽略振幅，先用经典小角度周期公式', '2*pi*sqrt(L/g)', []),
        ('上一轮被否决：域内误差过大。加入振幅的一阶修正项试试', '2*pi*sqrt(L/g)*(1 + a*theta0)', ['a']),
        ('否决理由提示修正项应为偶函数，改用平方项', '2*pi*sqrt(L/g)*(1 + a*theta0**2)', ['a']),
        ('系数拟合值偏离常见理论值，按参考理论系数 1/16 固定', '2*pi*sqrt(L/g)*(1 + theta0**2/16)', []),
    ],
    'phys-gravitation': [
        ('先假设引力与距离成正比', 'G*m1*m2*r', ['G']),
        ('否决：域内即失败。改为一次反比', 'G*m1*m2/r', ['G']),
        ('否决：仍不成立。改为三次反比看趋势', 'G*m1*m2/r**3', ['G']),
        ('两个方向都失败，回到二次反比（平方反比律）', 'G*m1*m2/r**2', ['G']),
    ],
}


def builtin_hypotheses(task_id):
    return STRATEGIES.get(task_id, [])


def llm_hypothesis(task_id, columns, meta, history, agh_entry, model):
    # 把历史失败作为上下文交给 Agnes 模型，请它给出下一个候选式。
    prompt = [
        '你在做符号回归。任务变量：' + ', '.join(meta.get('var_names', [])) + '，目标列 y。',
        '已尝试并被否决的假设如下（含否决理由），请据此给出一个新的候选公式，',
        '只用 + - * / ** 与 sin/cos/exp/log/sqrt 以及变量名，输出一行 JSON：',
        '{"formula": "...", "parameters": ["自由参数名"], "reason": "一句话依据"}',
    ]
    for h in history:
        prompt.append('候选 ' + h['formula'] + ' -> ' + h['verdict'] + '；理由：' + h.get('summary', ''))
    text = chr(10).join(prompt)
    try:
        proc = subprocess.run(['node', agh_entry, '-p', '--model', model, text],
                              capture_output=True, text=True, timeout=180)
        out = proc.stdout.strip()
        start = out.find('{')
        end = out.rfind('}')
        if start >= 0 and end > start:
            data = json.loads(out[start:end + 1])
            return data.get('formula'), data.get('parameters', []), data.get('reason', '')
    except Exception as exc:
        emit('   [llm 调用失败，回退到内置生成器] ' + str(exc)[:80])
    return None, None, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', default='phys-pendulum-exact')
    ap.add_argument('--run-id', default='')
    ap.add_argument('--llm', action='store_true', help='通过 AGH 调用 Agnes 模型生成假设')
    ap.add_argument('--agh-entry', default='')
    ap.add_argument('--model', default='main=agnes/agnes-3.0-flash')
    args = ap.parse_args()
    # 通知五（二）：作品中的所有模型调用仅限 Agnes 模型。这里**拒绝**非 Agnes 路由——
    # 外部审计（2026-10-10）指出：示例允许自由传 --model，却没有任何一处真正拒绝别家模型，
    # 于是"全程只用 Agnes"只能靠人记得别改参数，等于没有控制。
    try:
        from model_guard import check_routes
    except ImportError as exc:  # 失败关闭：校验不了就不运行
        print('拒绝运行：找不到模型路由守卫 examples/model_guard.py: %s' % exc)
        return 2
    _route_check = check_routes([args.model])
    if not _route_check.get('ok'):
        print('拒绝运行：' + str(_route_check.get('reason')))
        print('依据：通知五（二）——作品中的所有模型调用仅限 Agnes 模型。')
        return 2

    task_dir = os.path.join(ROOT, 'tasks', args.task)
    columns, meta = load_task(task_dir)
    run_id = args.run_id or ('demo-' + args.task)
    run_dir = os.path.join(ROOT, 'runs', run_id)
    os.makedirs(run_dir, exist_ok=True)
    traj_path = os.path.join(run_dir, 'trajectory.jsonl')
    # 轨迹必须"每次运行重写"，不能追加：改造前用 'a' 打开，同一个 run_id
    # 跑第二遍会把新的一轮追加在旧轮后面，文件里出现两套 round 1..N，
    # 且时间戳只有一份——它已经不能代表任何一次真实运行了。
    if os.path.exists(traj_path):
        os.remove(traj_path)

    emit('=' * 68)
    emit('任务: ' + args.task + '   |   变量: ' + ', '.join(meta.get('var_names', [])))
    emit('现象: ' + str(meta.get('phenomenon', '')))
    emit('来源: ' + str((meta.get('source') or [''])[0]))
    emit('=' * 68)

    history = []
    final = None
    rounds = builtin_hypotheses(args.task)
    max_rounds = len(rounds) if rounds else 6
    # 混合来源必须如实记录：只要有一轮回退到内置生成器，这条运行就不是纯模型发现。
    # 外部审计（2026-10-10）指出旧写法只按 --llm 开关标注，回退后仍记 agh-llm。
    used_fallback = False
    for idx in range(max_rounds):
        if args.llm and args.agh_entry:
            formula, params, reason = llm_hypothesis(args.task, columns, meta, history,
                                                    args.agh_entry, args.model)
            if formula is None:
                if idx >= len(rounds):
                    break
                _, formula, params = rounds[idx]
                reason = '内置生成器（LLM 不可用）'
                used_fallback = True
        else:
            if args.llm:
                used_fallback = True
            if idx >= len(rounds):
                break
            reason, formula, params = rounds[idx]

        emit('')
        emit('--- 第 %d 轮 ---------------------------------------------' % (idx + 1))
        emit('假设依据: ' + reason)
        emit('候选公式: ' + formula + ('   (自由参数: ' + ','.join(params) + ')' if params else ''))
        try:
            report = verify_formula(
                formula, columns, meta, parameters=params,
                holdout_threshold=SETTINGS['holdout_threshold'],
                extrapolation_threshold=SETTINGS['extrapolation_threshold'],
                holdout_ratio=SETTINGS['holdout_ratio'],
                extrapolation_ratio=SETTINGS['extrapolation_ratio'],
                seed=SETTINGS['seed'],
                dimension_check=SETTINGS['dimension_check'],
                scale_check=SETTINGS['scale_check'],
                fit_max_residual=SETTINGS['fit_max_residual'])
        except VerifyError as exc:
            emit('引擎结论: 无法评估 -> ' + str(exc))
            history.append({'formula': formula, 'verdict': 'error', 'summary': str(exc)})
            continue

        checks = {c.name: c for c in report.checks}
        for name in ('dimension', 'fit', 'holdout', 'extrapolation'):
            c = checks.get(name)
            if c is None:
                continue
            emit('   %-14s %s   %s' % (name, 'PASS' if c.passed else 'FAIL', c.reason))
        emit('引擎判定: ' + report.verdict)
        if report.verdict != 'accepted':
            emit('系统提示: ' + report.rounds_hint)

        note = ''
        if report.verdict != 'accepted':
            failed = [c for c in report.checks if not c.passed]
            if failed:
                note = failed[0].reason
        entry = {
            'round': idx + 1,
            'hypothesis_reason': reason,
            'formula': formula,
            'parameters': params,
            'verdict': report.verdict,
            'checks': [{'name': c.name, 'passed': c.passed, 'reason': c.reason, 'metrics': c.metrics}
                       for c in report.checks],
            'fitted_parameters': report.parameters,
            'engine_hint': report.rounds_hint,
        }
        with open(traj_path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + chr(10))
        history.append({'formula': formula, 'verdict': report.verdict, 'summary': note})

        if report.verdict == 'accepted':
            final = report
            emit('')
            emit('*** 通过三重验证，结论成立 ***')
            break

    emit('')
    emit('=' * 68)
    if final is None:
        emit('结论: 本轮未发现稳定公式（如实报告，不编造）')
        return 1
    emit('最终公式: ' + final.formula)
    if final.parameters:
        for k, v in final.parameters.items():
            emit('  拟合参数 %s = %.6g' % (k, v))
    emit('迭代轮数: %d（其中被自己否决 %d 次）' % (len(history), sum(1 for h in history if h['verdict'] != 'accepted')))
    write_evidence(run_dir, final,
                   'python examples/demo_agent.py --task ' + args.task + ' --run-id ' + run_id,
                   inputs=[task_dir],
                   # 来源必须如实标注：默认模式下每一条"假设"都是人手写在 STRATEGIES
                   # 表里的，不是模型提出的。不标注，这条运行看起来就像真实的自主闭环。
                   hypothesis_source=(
                       # 只有**每一轮**都由模型产出才算 agh-llm。请求了模型但中途回退，
                       # 记 fixture-fallback——它同样不计入评分脚本的智能体发现层。
                       'agh-llm' if (args.llm and not used_fallback)
                       else ('fixture-fallback' if args.llm else 'human-authored-fixture')),
                   notes=('假设每轮均由 Agnes 模型经 AGH 提出；轨迹见 trajectory.jsonl'
                          if (args.llm and not used_fallback) else
                          ('请求了 Agnes 模型，但至少有一轮回退到内置生成器；'
                           '混合来源不作为纯模型发现计入。轨迹见 trajectory.jsonl'
                           if args.llm else
                           '演示用固定装置：假设链由人工编写在本脚本的 STRATEGIES 表中；'
                           '调用的是真实验证引擎，但假设不是模型自主提出的，'
                           '不得用于支撑"智能体自主发现"的结论。轨迹见 trajectory.jsonl')))
    emit('证据目录: ' + os.path.relpath(run_dir, ROOT))
    emit('=' * 68)
    return 0


if __name__ == '__main__':
    sys.exit(main())