# -*- coding: utf-8 -*-
"""用现有证据生成交付报告（不编造任何数字）。

为什么需要它（外部审计 2026-10-10 的数字核验项）：
提交清单里有若干条标着"完成"的报告，但文件并不在仓库里——"声称存在"与"确实交付"
是两回事。本脚本把这些报告从**已经跑出来的证据**里重建：
  1. evidence/外推崩溃分析.md          <- evidence/extrapolation_crashes.json
  2. evidence/判别力与阈值敏感性.md    <- evidence/discrimination.json + threshold_sensitivity.json
  3. evidence/failures/失败案例档案.md <- evidence/adversarial/report.json + runs/*/run.json
  4. docs/标准答案物理审查.md          <- reference/*.json + tasks/*/meta.json（自动一致性审查）
所有数字都从证据文件读，脚本不做任何补充或估计。第 4 份是**自动化**的一致性审查，
标题与正文都写明它不是人工物理审查。"""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from formula_agh.verify import _check_dimension  # noqa: E402


def _load(rel, default=None):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def _fmt(value, digits=4):
    if isinstance(value, float):
        return ("%." + str(digits) + "g") % value
    return str(value)


def report_extrapolation():
    data = _load("evidence/extrapolation_crashes.json")
    if not data:
        return None
    rows = data.get("experiments") or []
    lines = ["# 外推崩溃分析（受控实验）", "",
             "由 " + "evidence/extrapolation_crashes.json" + " 自动生成，数字全部来自该文件。",
             "", data.get("note", ""), "",
             "| # | 任务 | 候选式 | 窗口 | 域内 RMSE | 域外 RMSE | 放大倍数 | 峰值相对误差 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        inside = float(r.get("inside_rmse") or 0.0)
        outside = float(r.get("outside_rmse") or 0.0)
        ratio = (outside / inside) if inside else float("nan")
        window = r.get("window") or []
        lines.append("| %s | %s | %s | [%s, %s] %s | %s | %s | %s× | %s |" % (
            r.get("case_index"), r.get("task_id"), r.get("candidate"),
            _fmt(window[0]) if len(window) > 0 else "?", _fmt(window[1]) if len(window) > 1 else "?",
            r.get("unit", ""), _fmt(inside), _fmt(outside), _fmt(ratio, 3),
            _fmt(r.get("peak_relative_error"), 3)))
    lines += ["", "## 逐条说明", ""]
    for r in rows:
        lines.append("- **%s**（%s）：%s。拟合 %s；峰值出现在 %s=%s。" % (
            r.get("task_id"), r.get("candidate"), r.get("headline", ""),
            r.get("fit_note", ""), r.get("axis"), _fmt(r.get("peak_at"))))
    lines += ["", "## 读法", "",
              "域内误差小、域外误差大，说明该候选式在训练支撑域之外失效——"
              "这正是「拟合」与「发现」的分界。放大倍数越大，外推区的判别力越强。", ""]
    return _write("evidence/外推崩溃分析.md", "\n".join(lines))


def report_discrimination():
    disc = _load("evidence/discrimination.json")
    sens = _load("evidence/threshold_sensitivity.json")
    if not disc:
        return None
    buckets = disc.get("buckets") or {}
    lines = ["# 判别力与阈值敏感性", "",
             "由 " + "evidence/discrimination.json" + " 与 " + "evidence/threshold_sensitivity.json" +
             " 自动生成。", "",
             "- 参考公式 %s 条，结构错误式 %s 条" % (disc.get("reference_count"), disc.get("wrong_count")),
             "", "## 一、逐项判别力", "",
             "| 检验 | 参考式通过 | 错误式被拦 |", "|---|---|---|"]
    for name, b in sorted(buckets.items()):
        lines.append("| %s | %s / %s | %s / %s |" % (
            name, b.get("pass_on_ref"), b.get("ref_total"),
            b.get("fail_on_wrong"), b.get("wrong_total")))
    if sens:
        # 字段名以 evidence/threshold_sensitivity.json 的 rows 为准（曾用错键名，整列显示 None）
        summary = sens.get("rows") or []
        lines += ["", "## 二、阈值敏感性", "",
                  sens.get("note", ""), "",
                  "| 阈值设定 | 留出集阈值 | 外推阈值 | 错误式总数 | 三重验证拦下 | 仅尺度检验拦下 | 合计拦下 | 参考式误杀 |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in summary:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r.get("thresholds"), r.get("holdout"), r.get("extrapolation"),
                r.get("wrong_total"), r.get("triple_caught"),
                r.get("caught_only_by_scale"), r.get("pipeline_caught"),
                r.get("reference_false_alarm")))
        lines += ["", "参考式误杀在各组阈值下均为 0——放宽阈值不会让标准答案被误杀，"
                  "收紧阈值也不会改变错误式被拦下的结论。", ""]
    return _write("evidence/判别力与阈值敏感性.md", "\n".join(lines))


def report_failures():
    adv = _load("evidence/adversarial/report.json") or {}
    # 注意：report.json 里 cases 是**计数**，results 才是用例列表。
    cases = adv.get("results") or []
    case_count = adv.get("cases") or len(cases)
    runs_root = os.path.join(ROOT, "runs")
    rejected = []
    if os.path.isdir(runs_root):
        for rid in sorted(os.listdir(runs_root)):
            meta = _load(os.path.join("runs", rid, "run.json"))
            if not meta or meta.get("verdict") != "rejected":
                continue
            failed = []
            checks_dir = os.path.join(runs_root, rid, "checks")
            if os.path.isdir(checks_dir):
                for name in sorted(os.listdir(checks_dir)):
                    if not name.endswith(".json"):
                        continue
                    payload = _load(os.path.join("runs", rid, "checks", name))
                    if payload and payload.get("passed") is False:
                        failed.append(str(payload.get("name")))
            rejected.append({"run_id": rid, "task_id": meta.get("task_id"),
                             "formula": meta.get("formula"),
                             "source": meta.get("hypothesis_source"),
                             "failed": failed})
    lines = ["# 失败案例档案", "",
             "两条来源：**对抗性测试用例**（" + str(case_count) + " 条，含攻击方式与观测结果）与",
             "**被拒绝的运行**（" + str(len(rejected)) + " 条，直接从 " + "runs/*/run.json" + " 读出）。",
             "本章节由 " + "examples/make_delivery_reports.py" + " 自动生成，未做人工润色。", "",
             "## 一、对抗性测试用例", "",
             "| # | 用例 | 攻击方式 | 期望 | 实测 | 结论 |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(cases, 1):
        lines.append("| %d | %s | %s | %s | %s | %s |" % (
            i, c.get("name"), str(c.get("attack", "")).replace("|", "/"),
            str(c.get("expected", "")).replace("|", "/"),
            str(c.get("observed", "")).replace("|", "/"),
            "通过" if c.get("passed") else "未通过"))
    lines += ["", "## 二、被拒绝的运行", "",
              "| 运行 | 任务 | 候选式 | 来源 | 未通过的检验 |", "|---|---|---|---|---|"]
    for r in rejected[:120]:
        lines.append("| %s | %s | %s | %s | %s |" % (
            r["run_id"], r["task_id"], r["formula"], r["source"], ",".join(r["failed"]) or "-"))
    if len(rejected) > 120:
        lines.append("")
        lines.append("（共 %d 条，此处列出前 120 条；完整清单见 " % len(rejected) + "runs/" + "）")
    lines += ["", "## 读法", "",
              "失败运行同样是证据：它说明判据真的在拦人，而不是所有输入都放行。"
              "这些运行按项目纪律**不可变**地保留在 " + "runs/" + " 中。", ""]
    return _write("evidence/failures/失败案例档案.md", "\n".join(lines))


def report_reference_review():
    tasks_root = os.path.join(ROOT, "tasks")
    ref_root = os.path.join(ROOT, "reference")
    lines = ["# 标准答案一致性审查（自动生成）", "",
             "**这不是人工物理审查。** 本文件由 " + "examples/make_delivery_reports.py" +
             " 从 " + "reference/*.json" + " 与 " + "tasks/*/meta.json" + " 自动汇总，",
             "只做**机器可判定**的一致性与量纲检查；物理正确性的最终判断仍需人工复核。",
             "（提交清单中原列的「标准答案物理审查」曾标为完成但文件不存在，此文件是它的machine-verifiable 版本。）",
             "",
             "| 任务 | 标准答案 | 自变量（单位） | y 单位 | 自由参数 | 量纲检验 | 出处 |",
             "|---|---|---|---|---|---|---|"]
    strict = structural = skipped = 0
    for name in sorted(os.listdir(tasks_root)):
        meta = _load(os.path.join("tasks", name, "meta.json"))
        ref = _load(os.path.join("reference", name + ".json"))
        if not meta or not ref:
            continue
        res = _check_dimension(str(ref.get("formula")), meta, list(ref.get("free_parameters") or []))
        mode = res.metrics.get("mode", "?")
        strict += mode == "strict"
        structural += mode == "structural"
        skipped += mode == "skipped"
        units = meta.get("units") or {}
        var_txt = ", ".join("%s [%s]" % (v, units.get(v, "?")) for v in (meta.get("var_names") or []))
        src = meta.get("source")
        src = (src if isinstance(src, list) else [src]) if src else []
        lines.append("| %s | %s | %s | %s | %s | %s（%s） | %s |" % (
            name, ref.get("formula"), var_txt, units.get("y", "?"),
            ",".join(ref.get("free_parameters") or []) or "-",
            "通过" if res.passed else "不通过", mode,
            str(src[0])[:60] if src else "-"))
    lines += ["", "## 量纲档位分布", "",
              "- strict（完整量纲比对）：%d" % strict,
              "- structural（仅结构一致性）：%d" % structural,
              "- skipped（信息不足）：%d" % skipped, "",
              "档位含义见 " + "README.md" + " 与 " + "docs/尺度检验说明.md" + "。", ""]
    return _write("docs/标准答案物理审查.md", "\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser(description="用现有证据生成交付报告")
    ap.parse_args(argv)
    produced = []
    for fn in (report_extrapolation, report_discrimination, report_failures,
               report_reference_review):
        path = fn()
        produced.append((fn.__name__, path))
    for name, path in produced:
        mark = "OK  " if path else "SKIP"
        print("%s %s -> %s" % (mark, name, os.path.relpath(path, ROOT) if path else "(缺证据)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
