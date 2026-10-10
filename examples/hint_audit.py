# -*- coding: utf-8 -*-
"""提示泄漏审计：智能体可见的那一面，到底泄漏了多少公式结构。

为什么需要它（外部审计 2026-10-10 指出的第 3 条）：
"自主发现"的主张强度取决于**模型能看到什么**。不读 reference/ 不等于无泄漏：
任务名、phenomenon 文本、source 链接、单位表都可能直接点名定律或暴露函数结构，
启动提示里还给了示例式。把这些当成不存在，会把"带先验的已知定律恢复"
说成"从数据中发现"。

本脚本不改变任何判定，只**如实清点**：把每个任务对智能体可见的表面的泄漏
分成几类，输出 evidence/hint_leak_audit.json，供文档与路演引用。
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 任务名里出现这些词，等于点名了定律或现象
NAME_HINTS = ["ohm", "coulomb", "gravitation", "grav", "kinetic", "elastic", "spring",
              "pendulum", "radioactive", "decay", "stefan", "boltzmann", "ideal-gas",
              "joule", "cyclotron", "snell", "index", "hydrogen", "buoyancy", "weight",
              "energy", "transit", "surface", "vacuum", "shift"]
# phenomenon 文本里出现这些词，等于把定律写在脸上
TEXT_LAW_WORDS = ["定律", "公式", "正比", "反比", "平方", "立方", "四次方", "成反比", "成正比",
                  "law", "proportional", "squared", "inverse"]


def _prompt_formula_examples():
    """从驱动脚本与技能文件里找出被当作示例给出的公式字面量。"""
    found = []
    for rel in ("harness/run_agent_discovery.ps1", "skills/formula-discovery-loop/SKILL.md"):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*\s*\*\*\s*\d+", text):
            found.append({"where": rel, "snippet": m.group(0)})
        for m in re.finditer(r"sigma\s*\*\s*A\s*\*\s*T", text):
            found.append({"where": rel, "snippet": m.group(0), "kind": "example-formula"})
    return found


def audit_task(task_dir, name):
    meta = json.load(open(os.path.join(task_dir, "meta.json"), encoding="utf-8"))
    leaks = []
    lower = name.lower()
    hit = [h for h in NAME_HINTS if h in lower]
    if hit:
        leaks.append({"kind": "task_id", "detail": "任务名含现象词: " + ",".join(sorted(set(hit)))})
    phenomenon = str(meta.get("phenomenon") or "")
    if phenomenon:
        words = [w for w in TEXT_LAW_WORDS if w in phenomenon]
        leaks.append({"kind": "phenomenon", "detail": phenomenon[:80],
                      "severity": "high" if words else "medium",
                      "matched": words})
    source = meta.get("source")
    urls = source if isinstance(source, list) else ([source] if source else [])
    urls = [str(u) for u in urls if u]
    if urls:
        leaks.append({"kind": "source", "detail": urls[0][:90],
                      "severity": "high",
                      "note": "链接通常直接指向定律条目（如 Wikipedia 的 Ohms_law）"})
    units = meta.get("units") or {}
    if units:
        leaks.append({"kind": "units", "detail": json.dumps(units, ensure_ascii=False),
                      "severity": "low",
                      "note": "单位本身是合法物理输入，但同时暴露量纲结构，会缩小搜索空间"})
    free = meta.get("free_parameters") or []
    if free:
        leaks.append({"kind": "free_parameters", "detail": ",".join(map(str, free)),
                      "severity": "low"})
    return {"task_id": name, "var_names": meta.get("var_names"), "leaks": leaks,
            "leak_count": len(leaks),
            "high": sum(1 for x in leaks if x.get("severity") == "high")}


def main():
    tasks_root = os.path.join(ROOT, "tasks")
    rows = []
    for name in sorted(os.listdir(tasks_root)):
        d = os.path.join(tasks_root, name)
        if os.path.isfile(os.path.join(d, "meta.json")):
            rows.append(audit_task(d, name))
    examples = _prompt_formula_examples()
    summary = {
        "tasks": len(rows),
        "tasks_with_phenomenon_text": sum(1 for r in rows
                                          if any(l["kind"] == "phenomenon" for l in r["leaks"])),
        "tasks_with_source_link": sum(1 for r in rows
                                      if any(l["kind"] == "source" for l in r["leaks"])),
        "tasks_with_name_hint": sum(1 for r in rows
                                    if any(l["kind"] == "task_id" for l in r["leaks"])),
        "tasks_with_units": sum(1 for r in rows
                                if any(l["kind"] == "units" for l in r["leaks"])),
        "high_severity_total": sum(r["high"] for r in rows),
        "prompt_formula_examples": examples,
        "note": ("这些泄漏都不是违规，但决定了主张的强度：存在 phenomenon 文本与 source 链接时，"
                 "更准确的表述是「带物理先验的已知定律恢复」，而不是「从数据中发现」。"
                 "hint_audit 只做清点，不改变任何判定。"),
    }
    out = {"summary": summary, "tasks": rows}
    os.makedirs(os.path.join(ROOT, "evidence"), exist_ok=True)
    path = os.path.join(ROOT, "evidence", "hint_leak_audit.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("任务数 %d" % summary["tasks"])
    print("  含 phenomenon 文本（点名现象/定律）: %d" % summary["tasks_with_phenomenon_text"])
    print("  含 source 链接（通常直指定律条目）  : %d" % summary["tasks_with_source_link"])
    print("  任务名本身含现象词                : %d" % summary["tasks_with_name_hint"])
    print("  含单位表（暴露量纲结构）          : %d" % summary["tasks_with_units"])
    print("  高严重度泄漏合计                  : %d" % summary["high_severity_total"])
    print("  提示中给出的示例式                : %d 处" % len(examples))
    for e in examples[:6]:
        print("      %s :: %s" % (e["where"], e["snippet"]))
    print("")
    print("wrote evidence/hint_leak_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
