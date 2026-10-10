# -*- coding: utf-8 -*-
"""从产物算出**权威数字**，供文档与检查器引用。

为什么需要它（2026-10-10）
--------------------------
这一轮里同一个数字在多份文档里漂过多次：智能体命中数在 16 与 17 之间、
消融结果在 14 与 13 之间、单元测试数 107/109/110、被拒运行 143/182。
每次都是人工同步，每次都漏。

本脚本不做判断，只做一件事：**把"当前产物里真的是几"算出来**，写成
evidence/关键数字.json 与 .md。文档引用这些数字，check_docs.py 再核对文档没有写错。

用法：
    python examples/key_numbers.py
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NL = chr(10)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _maybe(path):
    return _load(path) if os.path.isfile(path) else None


def run_counts():
    """跑当前 runs/ 数一遍来源与判定。"""
    runs_dir = os.path.join(ROOT, "runs")
    counts = {"runs_total": 0, "runs_rejected": 0, "runs_agh_llm": 0, "runs_bound": 0}
    if not os.path.isdir(runs_dir):
        return counts
    for run_id in os.listdir(runs_dir):
        path = os.path.join(runs_dir, run_id, "run.json")
        if not os.path.isfile(path):
            continue
        counts["runs_total"] += 1
        run = _maybe(path) or {}
        if run.get("verdict") == "rejected":
            counts["runs_rejected"] += 1
        if run.get("hypothesis_source") == "agh-llm":
            counts["runs_agh_llm"] += 1
        if run.get("provenance_bound"):
            counts["runs_bound"] += 1
    return counts


def test_count():
    total = 0
    tests_dir = os.path.join(ROOT, "tests")
    for name in sorted(os.listdir(tests_dir)):
        if name.startswith("test_") and name.endswith(".py"):
            text = open(os.path.join(tests_dir, name), encoding="utf-8").read()
            total += len(set(re.findall(r"^def (test_\w+)", text, re.M)))
    return total


def step_count():
    text = open(os.path.join(ROOT, "reproduce.py"), encoding="utf-8").read()
    return len(re.findall(re.escape("run_step(" + chr(34)), text.split("def main(")[-1]))


def main():
    numbers = {}
    numbers.update(run_counts())
    numbers["tests_total"] = test_count()
    numbers["pipeline_steps"] = step_count()

    scoring = _maybe(os.path.join(ROOT, "evidence", "scoring", "comparison.json"))
    if scoring:
        s = scoring.get("summary", {})
        for key in ("tasks_in_scope", "gold_reference_accepted", "wrong_variant_rejected",
                    "agent_candidates", "agent_accepted", "agent_matches_reference",
                    "agent_candidates_bound", "agent_candidates_unbound",
                    "agent_matches_reference_bound"):
            numbers[key] = s.get(key)

    ablation = _maybe(os.path.join(ROOT, "evidence", "ablation", "ablation_report.json"))
    if ablation:
        for arm in ablation.get("arms", []):
            numbers["ablation_" + str(arm.get("arm"))] = arm.get("any_run_match")

    adversarial = _maybe(os.path.join(ROOT, "evidence", "adversarial", "summary.json"))
    if adversarial:
        for key in ("cases_total", "cases_judged", "cases"):
            if key in adversarial:
                numbers[key] = adversarial[key]

    out_dir = os.path.join(ROOT, "evidence")
    with open(os.path.join(out_dir, "关键数字.json"), "w", encoding="utf-8") as fh:
        json.dump(numbers, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write(NL)

    labels = [
        ("tasks_in_scope", "任务总数"),
        ("pipeline_steps", "流水线步数"),
        ("tests_total", "单元测试数"),
        ("runs_total", "运行总数"),
        ("runs_rejected", "被拒运行数"),
        ("runs_agh_llm", "标注 agh-llm 的运行数"),
        ("runs_bound", "绑定 AGH 会话的运行数"),
        ("gold_reference_accepted", "金标准通过数"),
        ("wrong_variant_rejected", "结构错误式被拒数"),
        ("agent_candidates", "智能体候选数"),
        ("agent_candidates_bound", "其中绑定会话数"),
        ("agent_matches_reference_bound", "绑定层与标准答案一致"),
        ("ablation_先验辅助", "消融：先验辅助（门无关命中）"),
        ("ablation_盲化", "消融：盲化（门无关命中）"),
        ("ablation_纯数据", "消融：纯数据（门无关命中）"),
    ]
    lines = ["# 关键数字（由 examples/key_numbers.py 从产物算出）", "",
             "本表不写结论，只写「当前产物里是几」。文档引用这些数字，",
             "check_docs.py 会核对文档没有写错。", "",
             "| 数字 | 含义 |", "|---|---|"]
    for key, label in labels:
        if numbers.get(key) is not None:
            lines.append("| %s | %s |" % (numbers[key], label))
    with open(os.path.join(out_dir, "关键数字.md"), "w", encoding="utf-8", newline=NL) as fh:
        fh.write(NL.join(lines) + NL)

    for key, label in labels:
        if numbers.get(key) is not None:
            print("%-34s %s" % (label, numbers[key]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
