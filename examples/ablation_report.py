# -*- coding: utf-8 -*-
"""去提示消融汇总：把多条支路放在**同一口径**下比较，并留下可复算的证据。

为什么需要这个脚本（2026-10-10）：
消融第一版只报了评分器的"代表运行"数字，结果纯数据支路显示 17/20、比带尺度反馈的
14/20 还高，看起来"去掉尺度反馈反而更好"。追下去发现是**混杂因素**——去掉尺度检验等于
少一道门，更多运行进入 accepted，而评分器取"第一个 accepted 运行"作代表，
于是"门更少"被误读成"发现得更好"。

当时我是在命令行里临时写了几行 Python 算出门无关指标，用完就删了。那等于把结论建立在
一次不可复算的操作上。本脚本就是把它固化下来：任何人在任何支路上都能重跑。

两种口径：
  * any_run_match（主指标）：该任务**是否曾有任一次**给出与标准答案一致的公式。
    与判定门数无关，因此跨支路可比。
  * scorer：直接读该支路 evidence/scoring/comparison.json 的摘要，受门数影响，仅作对照。

用法：
    python examples/ablation_report.py \
        --arm 先验辅助=. \
        --arm 盲化=E:\fagh-blind-root \
        --arm 纯数据=E:\fagh-noprior-root \
        --out evidence/ablation
"""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from scoring.compare import normalize_formula  # noqa: E402


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _reference_formula(ref_dir, task_id, alias):
    """任务目录名可能是匿名 id，参考文件则可能按真实 id 命名。"""
    for candidate in (task_id, alias):
        if not candidate:
            continue
        path = os.path.join(ref_dir, candidate + ".json")
        if os.path.isfile(path):
            return _load(path).get("formula")
    return None


def any_run_match(arm_root, alias_of=None):
    """门无关主指标：每个任务是否曾有任一次运行给出与标准答案一致的公式。"""
    runs_dir = os.path.join(arm_root, "runs")
    ref_dir = os.path.join(arm_root, "reference")
    if not os.path.isdir(runs_dir):
        return {}, 0
    hits, total = {}, 0
    for run_id in sorted(os.listdir(runs_dir)):
        run_path = os.path.join(runs_dir, run_id, "run.json")
        if not os.path.isfile(run_path):
            continue
        total += 1
        run = _load(run_path)
        if run.get("hypothesis_source") != "agh-llm":
            continue
        task_id = str(run.get("task_id"))
        ref_formula = _reference_formula(ref_dir, task_id, (alias_of or {}).get(task_id))
        if ref_formula is None:
            continue
        try:
            if normalize_formula(str(run.get("formula"))) == normalize_formula(str(ref_formula)):
                hits[task_id] = hits.get(task_id, 0) + 1
        except Exception:  # 解析不了的表达式不计命中
            continue
    return hits, total


def provenance_counts(arm_root):
    runs_dir = os.path.join(arm_root, "runs")
    bound = total = 0
    if not os.path.isdir(runs_dir):
        return 0, 0
    for run_id in os.listdir(runs_dir):
        path = os.path.join(runs_dir, run_id, "run.json")
        if not os.path.isfile(path):
            continue
        total += 1
        if _load(path).get("provenance_bound"):
            bound += 1
    return bound, total


def summarize_arm(name, arm_root, tasks_total, alias_of=None):
    hits, run_total = any_run_match(arm_root, alias_of)
    bound, _ = provenance_counts(arm_root)
    entry = {
        "arm": name,
        "root": arm_root,
        "tasks_total": tasks_total,
        "any_run_match": len(hits),
        "any_run_match_ratio": round(len(hits) / tasks_total, 4) if tasks_total else 0.0,
        "tasks_with_a_match": sorted(hits),
        "runs_total": run_total,
        "runs_bound": bound,
    }
    scoring_path = os.path.join(arm_root, "evidence", "scoring", "comparison.json")
    if os.path.isfile(scoring_path):
        summary = _load(scoring_path).get("summary", {})
        entry["scorer"] = {k: summary.get(k) for k in (
            "agent_candidates", "agent_accepted", "agent_candidates_bound",
            "agent_matches_reference", "agent_match_rate",
            "agent_matches_reference_bound", "agent_match_rate_bound")}
        entry["scorer_note"] = "受判定门数影响，仅作对照；跨支路比较请用 any_run_match"
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser(description="去提示消融汇总（门无关口径为主）")
    ap.add_argument("--arm", action="append", required=True,
                    metavar="名字=路径", help="可重复；路径是含 tasks/ reference/ runs/ 的支路根")
    ap.add_argument("--mapping", default="", help="可选：盲化映射 json（匿名 id → 真实 id）")
    ap.add_argument("--out", default="evidence/ablation")
    ap.add_argument("--force", action="store_true",
                    help="允许覆盖已有的汇总（默认拒绝，避免单臂运行悄悄顶掉归档的多臂结果）")
    args = ap.parse_args(argv)

    alias_of = {}
    if args.mapping and os.path.isfile(args.mapping):
        payload = _load(args.mapping)
        alias_of = {anon: info.get("real_id") for anon, info in (payload.get("map") or {}).items()}

    arms = []
    for item in args.arm:
        if "=" not in item:
            print("--arm 需要写成 名字=路径: " + item, file=sys.stderr)
            return 2
        name, path = item.split("=", 1)
        arm_root = path if os.path.isabs(path) else os.path.abspath(os.path.join(os.getcwd(), path))
        tasks_dir = os.path.join(arm_root, "tasks")
        tasks_total = len([d for d in os.listdir(tasks_dir)
                           if os.path.isfile(os.path.join(tasks_dir, d, "meta.json"))]) \
            if os.path.isdir(tasks_dir) else 0
        arms.append(summarize_arm(name, arm_root, tasks_total, alias_of))

    report = {"primary_metric": "any_run_match（该任务是否曾有任一次给出正确公式，与门无关）",
              "arms": arms}
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    # 不静默覆盖：仓库里归档的是三条支路的汇总，若有人只带一条支路就跑，
    # 默认拒绝，免得把归档结果顶掉却没人注意（本项目的证据纪律）。
    archive = os.path.join(out_dir, "ablation_report.json")
    if os.path.isfile(archive) and not args.force:
        try:
            previous = _load(archive).get("arms") or []
        except Exception:
            previous = []
        if len(previous) > len(arms):
            print("拒绝覆盖：%s 已有 %d 条支路的汇总，本次只提供了 %d 条。"
                  % (archive, len(previous), len(arms)), file=sys.stderr)
            print("要覆盖请显式加 --force。", file=sys.stderr)
            return 3
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ablation_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    lines = ["# 去提示消融汇总", "",
             "主指标：该任务**是否曾有任一次**给出与标准答案一致的公式（与判定门数无关）。", "",
             "| 支路 | 曾有任一次正确 | 占比 | 任务总数 | 运行数 | 绑定运行 | 评分器口径命中 |",
             "|---|---|---|---|---|---|---|"]
    for a in arms:
        scorer = a.get("scorer") or {}
        lines.append("| %s | %d | %.1f%% | %d | %d | %d | %s |" % (
            a["arm"], a["any_run_match"], a["any_run_match_ratio"] * 100, a["tasks_total"],
            a["runs_total"], a["runs_bound"],
            ("%s / %s" % (scorer.get("agent_matches_reference_bound"), scorer.get("agent_candidates_bound")))
            if scorer else "—"))
    lines += ["",
              "评分器口径优先取 accepted 运行作代表，**受门数影响**：少一道门会显得发现得更好。",
              "跨支路比较请用左起第二列。", ""]
    with open(os.path.join(out_dir, "消融汇总.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))

    for a in arms:
        print("%-10s 门无关命中 %2d / %d  绑定 %d / %d 运行" % (
            a["arm"], a["any_run_match"], a["tasks_total"], a["runs_bound"], a["runs_total"]))
    print("汇总写入:", os.path.join(out_dir, "消融汇总.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
