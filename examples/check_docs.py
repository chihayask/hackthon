# -*- coding: utf-8 -*-
"""文档一致性检查：把「文档说的」与「仓库里实际有的」对一遍。

为什么需要它（外部审计 2026-10-10 的数字与文档核验项）：
审计逐条核过文档里的声称，抓到多处矛盾——测试数在三个文件里分别写成 24/50/60、
提交清单把四份并不存在的报告标成「完成」、README 印着已经被删掉的包装脚本内容。
这些不是笔误，而是**没有机制**：文档只能靠人记得同步。本项目因为文档漂移
已经踩过八次以上，所以把它做成可执行的检查。

检查项：
  1. 反引号引用的仓库路径是否存在（同段落标注「未完成」的缺失可以接受）；
  2. 测试数声称是否等于 tests/ 下实际的 test 函数数；
  3. 流水线步数声称是否等于 reproduce.py 里 run_step 的调用数；
  4. 面向评审的文档里是否残留 M1/M2/M3 角色字样；
  5. 声称存在的目录缺失时，是否至少有一处明确标注未完成。"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NL = chr(10)
BT = chr(96)
BS = chr(92)

REVIEWER_DOCS = ["README.md", "01_项目说明书_定稿.md", "03_运行证据与提交清单_定稿.md",
                 "独立完成声明.md", "docs/数据卡.md", "docs/素材来源清单.md",
                 "docs/尺度检验说明.md", "docs/判据口径演进.md", "docs/自我怀疑与边界回应.md"]
SCAN_DOCS = REVIEWER_DOCS + ["AGENTS.md"]
ROLE_RE = re.compile(r"\bM[123]\b")
PATH_RE = re.compile(BT + "([^" + BT + NL + "]+?)" + BT)

TOP_LEVEL_FILES = {
    "README.md", "AGENTS.md", "reproduce.py", "run_tests.py", "requirements.txt",
    "独立完成声明.md", "01_项目说明书_定稿.md", "03_运行证据与提交清单_定稿.md",
}
ROOT_FILE_EXT = (".md", ".py", ".cmd", ".ps1", ".yaml", ".txt")
TOP_LEVEL_DIRS = {
    "blind", "config", "docs", "evidence", "examples", "expected", "harness",
    "packaging", "physics", "recheck", "reference", "runs", "sealed", "skills",
    "src", "superseded", "tasks", "tests", "experiments",
}
PENDING_MARKS = ("未完成", "待录制", "待补", "待本人完成", "尚未", "计划中")

# 这些路径**按设计不入库**（按需生成的中间产物、或 git 不跟踪的空占位目录），
# 文档提到它们是合理的。干净克隆里它们必然不存在——检查器若把它当缺失，
# 干净克隆的流水线第十八步就会误报（实测于 2026-10-10 的克隆验证）。
# 关键数字的**带标签**核对规则：(标签子串, 关键数字键, 取数正则, 取值组号)。
# 只对措辞明确的句子生效，避免把金标准 22/22、判别力 22/22 这类同形数字误伤。
CLAIM_RULES = [
    ("绑定层", "agent_matches_reference_bound", r"(\d+)\s*/\s*22", 1),
    ("绑定 AGH 会话", "agent_matches_reference_bound", r"(\d+)\s*/\s*22", 1),
    ("盲化（去现象/来源/任务名）", "ablation_盲化", r"(\d+)\s*/\s*22", 1),
    ("纯数据（再去掉尺度反馈）", "ablation_纯数据", r"(\d+)\s*/\s*22", 1),
    ("先验辅助（现象/来源/任务名齐全）", "ablation_先验辅助", r"(\d+)\s*/\s*22", 1),
    # 必须紧邻："14 条对抗用例 + 143 条被拒运行" 这种行里，紧邻匹配才不会取错数
    ("被拒运行", "runs_rejected", r"(\d+)\s*条\s*被拒运行", 1),
]


def load_key_numbers():
    path = os.path.join(ROOT, "evidence", "关键数字.json")
    if not os.path.isfile(path):
        return {}
    return _read_json(path)


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


NOT_COMMITTED = {
    "blind": "由 examples/make_blind_taskset.py 按需生成",
    "blind/tasks": "同上",
    "blind/reference": "同上",
    "blind/physics/scale_specs.json": "同上",
    "blind/mapping.json": "同上",
    "superseded/runs": "空占位目录（git 不跟踪空目录）",
}


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def looks_like_repo_path(text):
    """只认三种写法：已知顶层目录开头的路径、已知顶层文件、无歧义的相对路径。

    第一版没做这层过滤，把 run.json、.csv、m/s^2、RMSE/std(y)、approvals.mode
    这类普通标识符全算成缺失文件，一次误报 84 条——检查器自己先要能被信任。"""
    s = text.strip().rstrip("/")
    if not s or any(ch in s for ch in "<>*|()^" + " " + chr(9)):
        return False
    if s.startswith(("~", "http", "python", "set ", "git ", "cmd ", "-", "/", BS)):
        return False
    if s in TOP_LEVEL_FILES:
        return True
    parts = re.split("[" + "/" + BS + BS + "]", s)
    if len(parts) == 1 and parts[0] in TOP_LEVEL_DIRS:
        return True  # 裸目录名（如 runs、evidence）也是仓库路径
    if len(parts) == 1:
        return s.endswith(ROOT_FILE_EXT) and os.path.isfile(os.path.join(ROOT, s))
    if parts[0] not in TOP_LEVEL_DIRS:
        return False
    bare = [seg for seg in parts[1:] if seg and "." not in seg]
    if len(bare) > 3:
        return False
    return True


def actual_test_count():
    total = 0
    tests_dir = os.path.join(ROOT, "tests")
    for name in sorted(os.listdir(tests_dir)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        text = open(os.path.join(tests_dir, name), encoding="utf-8").read()
        total += len(set(re.findall(r"^def (test_\w+)", text, re.M)))
    return total


def actual_step_count():
    text = open(os.path.join(ROOT, "reproduce.py"), encoding="utf-8").read()
    body = text.split("def main(")[-1]
    return len(re.findall(re.escape('run_step("'), body))


def check(scan_docs=None):
    problems = []
    stats = {"docs_scanned": 0, "paths_checked": 0, "numbers_checked": 0,
             "acknowledged_missing": []}
    tests = actual_test_count()
    steps = actual_step_count()
    texts = {}

    for rel in (scan_docs or SCAN_DOCS):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            problems.append({"doc": rel, "kind": "missing-doc", "detail": "文档不存在"})
            continue
        text = _read(rel)
        texts[rel] = text
        stats["docs_scanned"] += 1

        for line in text.split(NL):
            pending = any(mark in line for mark in PENDING_MARKS)
            for raw in PATH_RE.findall(line):
                candidate = raw.strip()
                if not looks_like_repo_path(candidate):
                    continue
                clean = candidate.split("#")[0].strip().rstrip("/")
                if not clean:
                    continue
                stats["paths_checked"] += 1
                normalised = clean.replace("\\", "/").rstrip("/")
                if normalised in NOT_COMMITTED:
                    stats["acknowledged_missing"].append(normalised)
                    continue
                if os.path.exists(os.path.join(ROOT, clean.replace("/", os.sep))):
                    continue
                if pending:
                    stats["acknowledged_missing"].append(clean)
                    continue
                problems.append({"doc": rel, "kind": "missing-path", "detail": candidate})

        for line in text.split(NL):
            if not any(k in line for k in ("测试", "run_tests", "passing")):
                continue
            for m in re.finditer(r"(\d+)\s*/\s*(\d+)", line):
                a, b = int(m.group(1)), int(m.group(2))
                if a != b or a < 10:
                    continue
                stats["numbers_checked"] += 1
                if a != tests:
                    problems.append({"doc": rel, "kind": "test-count",
                                     "detail": "文档写 %d，实际 %d" % (a, tests)})

        for m in re.finditer(r"(\d+)\s*步", text):
            claimed = int(m.group(1))
            if claimed <= 5:
                continue
            stats["numbers_checked"] += 1
            if claimed != steps:
                problems.append({"doc": rel, "kind": "step-count",
                                 "detail": "文档写 %d 步，实际 %d 步" % (claimed, steps)})

        if rel in REVIEWER_DOCS and rel != "独立完成声明.md":
            hits = ROLE_RE.findall(text)
            if hits:
                problems.append({"doc": rel, "kind": "role-label",
                                 "detail": "出现角色字样: " + ",".join(sorted(set(hits)))})

    for rel in ("evidence/video",):
        if os.path.exists(os.path.join(ROOT, rel)):
            continue
        acknowledged = False
        for text in texts.values():
            for line in text.split(NL):
                if rel in line and any(mark in line for mark in PENDING_MARKS):
                    acknowledged = True
        if not acknowledged:
            problems.append({"doc": "(全局)", "kind": "missing-dir",
                             "detail": rel + " 被引用但没有任何一处标注未完成"})

    # 带标签的关键数字核对：文档写的必须等于产物算出来的。
    numbers = load_key_numbers()
    if numbers:
        for rel, text in texts.items():
            for line in text.split(NL):
                for label, key, pattern, group in CLAIM_RULES:
                    if label not in line:
                        continue
                    match = re.search(pattern, line)
                    if not match:
                        continue
                    claimed = int(match.group(group))
                    actual = numbers.get(key)
                    if actual is None:
                        continue
                    stats["numbers_checked"] += 1  # 计"核对过的数字"，不是"错了几处"
                    if claimed == actual:
                        continue
                    problems.append({"doc": rel, "kind": "claim-mismatch",
                                     "detail": "%s：文档写 %d，产物是 %s" % (label, claimed, actual)})

    return {"tests_actual": tests, "steps_actual": steps, "stats": stats,
            "problems": problems, "ok": not problems}


def main(argv=None):
    ap = argparse.ArgumentParser(description="文档一致性检查")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default="evidence/doc_check.json")
    ap.add_argument("--fix", action="store_true",
                    help="把文档里的测试数与步数改写为实测值（这项同步以前要人工做三次，已错过三轮）")
    args = ap.parse_args(argv)
    report = check()
    if args.fix:
        fixed = 0
        for rel in SCAN_DOCS:
            path = os.path.join(ROOT, rel)
            if not os.path.isfile(path):
                continue
            text = _read(rel)
            next_text = text
            # 只改"同一行同时出现测试字样与 N / N"的数字，避免误伤 22/22 这类金标准比值
            for line in text.split(NL):
                if not any(k in line for k in ("测试", "run_tests", "passing")):
                    continue
                for m in re.finditer(r"(\d+)\s*/\s*(\d+)", line):
                    a, b = int(m.group(1)), int(m.group(2))
                    if a != b or a < 10 or a == report["tests_actual"]:
                        continue
                    next_text = next_text.replace(m.group(0), "%d / %d" % (report["tests_actual"], report["tests_actual"]))
            for m in re.finditer(r"(\d+)\s*步", text):
                claimed = int(m.group(1))
                if claimed <= 5 or claimed == report["steps_actual"]:
                    continue
                next_text = next_text.replace(m.group(0), "%d 步" % report["steps_actual"])
            if next_text != text:
                with open(path, "w", encoding="utf-8", newline=NL) as fh:
                    fh.write(next_text)
                fixed += 1
        if fixed:
            print("已同步 %d 份文档的测试数/步数" % fixed)
        report = check()
    out_path = os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline=NL) as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write(NL)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("文档一致性检查：扫描 %d 份文档，核对 %d 条路径、%d 处数字"
              % (report["stats"]["docs_scanned"], report["stats"]["paths_checked"],
                 report["stats"]["numbers_checked"]))
        print("  实际测试数 %d，实际流水线步数 %d"
              % (report["tests_actual"], report["steps_actual"]))
        ack = report["stats"].get("acknowledged_missing") or []
        if ack:
            print("  已声明未交付（接受）：" + ", ".join(sorted(set(ack))))
        if report["ok"]:
            print("  结论：文档与仓库一致。")
        else:
            print("  发现 %d 处不一致：" % len(report["problems"]))
            for p in report["problems"][:40]:
                print("    [%s] %s :: %s" % (p["kind"], p["doc"], p["detail"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
