# -*- coding: utf-8 -*-
"""与标准答案对照（M2 交付 5/8）。

一键产出对照表
--------------
    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring

产出：
    comparison.json   机器可读的完整对照
    comparison.csv    便于贴进表格工具
    comparison.md     人可读的对照表（直接进说明书/视频）

对照分三层，避免"自说自话"
--------------------------
1. 金标准自检（refcheck）：把标准答案原样送进验证引擎，必须 accepted。
   —— 证明判据本身没把正确答案误杀。
2. 判别力（variant）：物理上合理但结构错误的候选，必须 rejected。
   —— 证明判据不是"什么都说对"。
3. 智能体发现（cand）：智能体给出的公式与标准答案逐项对照，
   包括"公式结构是否相同"与"数值是否等价"两个独立判据。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, ".."))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from formula_agh.safe_eval import UnsafeExpression, compile_formula  # noqa: E402

PROBE_SEED = 20261008
PROBE_N = 256
EQUIVALENCE_TOL = 1e-6
TICK = chr(96)  # 反引号，Markdown 行内代码用


# --------------------------------------------------------------------------
# 公式等价性
# --------------------------------------------------------------------------

def normalize_formula(text: str) -> str:
    """把公式规范成可比较的字符串：去掉空白、统一幂运算符。"""
    out = str(text or "").strip().lower()
    out = out.replace("**", "^")
    out = re.sub(r"\s+", "", out)
    return out


def _probe_points(task_dir: str, var_names: Sequence[str]) -> Optional[np.ndarray]:
    """在训练支撑域内取确定性探针点（种子固定，任何人重跑同一组点）。"""
    split_file = os.path.join(task_dir, "split.json")
    if not os.path.exists(split_file):
        return None
    with open(split_file, encoding="utf-8") as fh:
        split = json.load(fh)
    support = split.get("support") or {}
    lo = support.get("lo")
    hi = support.get("hi")
    if not lo or not hi or len(lo) != len(var_names):
        return None
    rng = np.random.default_rng(PROBE_SEED)
    lo_arr = np.asarray(lo, dtype=float)
    hi_arr = np.asarray(hi, dtype=float)
    points = lo_arr + rng.random((PROBE_N, len(var_names))) * (hi_arr - lo_arr)
    edges = np.vstack([lo_arr, hi_arr, (lo_arr + hi_arr) / 2.0])
    return np.vstack([points, edges])


def numeric_equivalence(agent_formula: str,
                        agent_params: Mapping[str, float],
                        reference_formula: str,
                        reference_params: Mapping[str, float],
                        task_dir: str,
                        var_names: Sequence[str]) -> Dict[str, object]:
    """在支撑域探针点上比较两条公式的数值输出。

    两边都用各自的参数：智能体用它拟合出的参数，标准答案用它自己的真值。
    这检验的是"是不是同一条物理定律"，而不是"参数是否恰好一样"。
    """
    points = _probe_points(task_dir, var_names)
    if points is None:
        return {"available": False, "reason": "缺少 split.json，无法确定探针范围"}
    env: Dict[str, np.ndarray] = {}
    for index, name in enumerate(var_names):
        env[str(name)] = points[:, index]
    try:
        agent_fn = compile_formula(agent_formula, list(var_names) + list(agent_params))
        ref_fn = compile_formula(reference_formula, list(var_names) + list(reference_params))
    except UnsafeExpression as exc:
        return {"available": False, "reason": "公式无法求值: " + str(exc)}

    agent_env = dict(env)
    for name, value in agent_params.items():
        agent_env[name] = np.full(points.shape[0], float(value))
    ref_env = dict(env)
    for name, value in reference_params.items():
        ref_env[name] = np.full(points.shape[0], float(value))
    try:
        with np.errstate(all="ignore"):
            agent_values = np.asarray(agent_fn(agent_env), dtype=float)
            ref_values = np.asarray(ref_fn(ref_env), dtype=float)
    except Exception as exc:  # noqa: BLE001 - 求值失败必须如实报告，不掩盖
        return {"available": False, "reason": "求值异常: " + type(exc).__name__ + ": " + str(exc)}

    finite = np.isfinite(agent_values) & np.isfinite(ref_values)
    scale = float(np.max(np.abs(ref_values[finite]))) if finite.any() else 0.0
    if scale == 0.0:
        scale = 1.0
    if not finite.all():
        max_scaled = float("inf")
    else:
        max_scaled = float(np.max(np.abs(agent_values - ref_values))) / scale
    relative = None
    if finite.all():
        denom = np.maximum(np.abs(ref_values), 1e-300)
        relative = float(np.max(np.abs(agent_values - ref_values) / denom))
    return {
        "available": True,
        "probe_points": int(points.shape[0]),
        "probe_seed": PROBE_SEED,
        "max_scaled_deviation": max_scaled,
        "max_relative_deviation": relative,
        "all_finite": bool(finite.all()),
        "equivalent": bool(finite.all() and max_scaled <= EQUIVALENCE_TOL),
    }


# --------------------------------------------------------------------------
# 运行收集
# --------------------------------------------------------------------------

def _read_json(path: str) -> Optional[Mapping[str, object]]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def classify_run(run_id: str, task_id: str, source: str = "") -> str:
    """按**假设来源**判类，run_id 命名只作兜底。

    为什么改成这样（真实 AGH 运行暴露出来的缺陷）：
    原来只看 run_id 是不是 <task>-candNN，于是 AGH 产生的运行
    （命名形如 20261008-231054-phys-gravitation）被归到 other，
    **一条货真价实的"模型自主发现"被排除在「智能体发现」层之外**，
    对照表反而显示该层为空。命名是运输层的偶然属性，来源才是我们要判的事实。
    """
    if source == "agh-llm":
        return "agent-candidate"
    if source == "reference" or run_id == "refcheck-" + task_id:
        return "gold-reference"
    if source == "fixture-variant" or run_id == "variant-" + task_id:
        return "wrong-variant"
    if re.match(r"^" + re.escape(task_id) + r"-cand\d+$", run_id):
        return "cli-candidate"
    return "other"


def collect_runs(runs_root: str) -> Dict[str, List[Dict[str, object]]]:
    by_task: Dict[str, List[Dict[str, object]]] = {}
    if not os.path.isdir(runs_root):
        return by_task
    for entry in sorted(os.listdir(runs_root)):
        run_dir = os.path.join(runs_root, entry)
        if not os.path.isdir(run_dir):
            continue
        meta = _read_json(os.path.join(run_dir, "run.json"))
        if not meta:
            continue
        task_id = str(meta.get("task_id") or "")
        if not task_id:
            continue
        checks: Dict[str, object] = {}
        checks_dir = os.path.join(run_dir, "checks")
        if os.path.isdir(checks_dir):
            for name in sorted(os.listdir(checks_dir)):
                payload = _read_json(os.path.join(checks_dir, name))
                if payload and "name" in payload:
                    checks[str(payload["name"])] = payload
        by_task.setdefault(task_id, []).append({
            "run_id": entry,
            "run_dir": run_dir.replace(os.sep, "/"),
            "kind": classify_run(entry, task_id,
                                 str(meta.get("hypothesis_source") or "")),
            "verdict": meta.get("verdict"),
            "formula": meta.get("formula"),
            "parameters": meta.get("parameters") or {},
            "free_parameters": meta.get("free_parameters"),
            "hypothesis_source": meta.get("hypothesis_source") or "unclassified",
            # 溯源绑定：agh-llm 是自报标签，session_id 才是可核对物。外部审计
            # （2026-10-10）指出只信标签等于把"自称"当成"证据"。
            "provenance_bound": bool(meta.get("provenance_bound")),
            "session_id": meta.get("session_id") or "",
            "checks": checks,
        })
    return by_task


# --------------------------------------------------------------------------
# 对照
# --------------------------------------------------------------------------

def build_comparison(runs_root: str, tasks_root: str, reference_root: str) -> Dict[str, object]:
    by_task = collect_runs(runs_root)
    rows: List[Dict[str, object]] = []
    notes: List[str] = []

    reference_ids = []
    if os.path.isdir(reference_root):
        reference_ids = sorted(os.path.splitext(f)[0] for f in os.listdir(reference_root)
                               if f.endswith(".json"))
    task_ids = []
    if os.path.isdir(tasks_root):
        task_ids = sorted(d for d in os.listdir(tasks_root)
                          if os.path.isdir(os.path.join(tasks_root, d)))
    # 只统计"有任务目录或标准答案"的 id：runs/ 里可能残留指不到任务的运行，
    # 把它们混进分层统计会凭空造出一个 unknown 桶，虚增任务数。
    all_ids = sorted(set(reference_ids) | set(task_ids))

    for task_id in all_ids:
        task_dir = os.path.join(tasks_root, task_id)
        ref = _read_json(os.path.join(reference_root, task_id + ".json"))
        meta = _read_json(os.path.join(task_dir, "meta.json")) or {}
        runs = by_task.get(task_id, [])
        gold = [r for r in runs if r["kind"] == "gold-reference"]
        wrong = [r for r in runs if r["kind"] == "wrong-variant"]
        # 只有"假设由模型提出"的运行才算智能体发现层。
        # 人写的候选式（hypothesis_source 不是 agh-llm）单独成层，
        # 否则对照表会把人工固定装置算成模型的能力。
        cands = [r for r in runs if r["kind"] == "agent-candidate"]
        # 人在命令行给出的候选式（runs/<task>-candNN）单独成层，
        # 不能算成模型的发现能力。
        fixtures = [r for r in runs if r["kind"] == "cli-candidate"]

        row: Dict[str, object] = {
            "task_id": task_id,
            "layer": meta.get("layer"),
            "domain": meta.get("domain"),
            "var_names": meta.get("var_names"),
            "reference_formula": (ref or {}).get("formula"),
            "reference_source": (ref or {}).get("source"),
            "has_reference": ref is not None,
            "has_task_dir": os.path.isdir(task_dir),
            "gold_reference": None,
            "wrong_variant": None,
            "agent": None,
            "agent_fixture": None,
        }

        if gold:
            best = gold[0]
            row["gold_reference"] = {
                "run_id": best["run_id"],
                "formula": best["formula"],
                "verdict": best["verdict"],
                "as_expected": best["verdict"] == "accepted",
                "holdout": _metric(best, "holdout", "normalized_rmse"),
                "extrapolation": _metric(best, "extrapolation", "normalized_rmse"),
                "dimension": _passed(best, "dimension"),
            }
        if wrong:
            best = wrong[0]
            row["wrong_variant"] = {
                "run_id": best["run_id"],
                "formula": best["formula"],
                "verdict": best["verdict"],
                "as_expected": best["verdict"] == "rejected",
                "failed_checks": sorted(n for n, c in (best["checks"] or {}).items()
                                        if not c.get("passed")),
            }
        if fixtures:
            best_fixture = fixtures[0]
            row["agent_fixture"] = {
                "run_id": best_fixture["run_id"],
                "formula": best_fixture["formula"],
                "verdict": best_fixture["verdict"],
                "hypothesis_source": best_fixture.get("hypothesis_source"),
            }
        if cands:
            accepted = [c for c in cands if c["verdict"] == "accepted"]
            # 选代表运行时**优先已绑定会话的**。理由（2026-10-10 实测）：
            # 同一任务在历史上有过"标了 agh-llm 但没有会话号"的运行，按目录名排序
            # 会把那条旧运行选成代表，绑定层于是显示 1/22——而实际上 22 个任务
            # 都已经有绑定过的运行。这里把绑定当作第一权重，accepted 第二，run_id 第三。
            # 绑定是**第一**优先级：绑定层要回答的是"可核验的运行里有多少命中"。
            # 只看 accepted 会漏掉这种情况（实测 phys-pendulum-period）：新的绑定运行被判
            # rejected，而绑定机制之前有一条 accepted 的旧运行，于是代表被选成旧的、任务
            # 在绑定层显示为命中——那是拿不可核验的旧运行给绑定层充数。
            bound = [c for c in cands if c.get("provenance_bound")]
            group = bound if bound else cands
            accepted_in_group = [c for c in group if c["verdict"] == "accepted"]
            best = (accepted_in_group or group)[0]
            comparison: Dict[str, object] = {
                "run_id": best["run_id"],
                "formula": best["formula"],
                "verdict": best["verdict"],
                "provenance_bound": bool(best.get("provenance_bound")),
                "session_id": best.get("session_id") or "",
                "parameters": best["parameters"],
                "holdout": _metric(best, "holdout", "normalized_rmse"),
                "extrapolation": _metric(best, "extrapolation", "normalized_rmse"),
                "dimension": _passed(best, "dimension"),
                "candidates_tried": len(cands),
                "candidates_accepted": len(accepted),
            }
            if ref and os.path.isdir(task_dir):
                comparison["structural_match"] = (
                    normalize_formula(str(best["formula"])) ==
                    normalize_formula(str(ref.get("formula"))))
                ref_params = dict(ref.get("true_constants") or {})
                param_source = "reference.true_constants"
                if not ref_params and ref.get("free_parameters"):
                    fitted = _load_parameters(os.path.join(runs_root, "refcheck-" + task_id))
                    ref_params = {k: v for k, v in (fitted or {}).items()
                                  if k in (ref.get("free_parameters") or [])}
                    param_source = "refcheck 拟合值（reference 未给出真值）"
                comparison["reference_parameter_source"] = param_source
                var_names = [str(v) for v in (meta.get("var_names") or [])]
                if var_names:
                    equivalence = numeric_equivalence(
                        str(best["formula"]), dict(best["parameters"] or {}),
                        str(ref.get("formula")), ref_params, task_dir, var_names)
                    comparison["numeric_equivalence"] = equivalence
                    comparison["matches_reference"] = bool(
                        equivalence.get("equivalent") or comparison["structural_match"])
                else:
                    comparison["matches_reference"] = comparison["structural_match"]
            row["agent"] = comparison
        rows.append(row)

    summary = _summarize(rows, notes)
    return {
        "runs_root": runs_root.replace(os.sep, "/"),
        "tasks_root": tasks_root.replace(os.sep, "/"),
        "reference_root": reference_root.replace(os.sep, "/"),
        "isolation": {
            "reference_reader": "src/scoring/compare.py（唯一读取标准答案的组件）",
            "agent_side": "formula_agh 不持有任何指向 reference/ 的路径",
            "probe_seed": PROBE_SEED,
        },
        "summary": summary,
        "rows": rows,
        "notes": notes,
    }


def _load_parameters(run_dir: str) -> Optional[Mapping[str, object]]:
    meta = _read_json(os.path.join(run_dir, "run.json"))
    return (meta or {}).get("parameters")


def _metric(run: Mapping[str, object], check: str, metric: str) -> Optional[float]:
    payload = (run.get("checks") or {}).get(check) or {}
    value = (payload.get("metrics") or {}).get(metric)
    return float(value) if isinstance(value, (int, float)) else None


def _passed(run: Mapping[str, object], check: str) -> Optional[bool]:
    payload = (run.get("checks") or {}).get(check)
    return None if payload is None else bool(payload.get("passed"))


def _summarize(rows: Sequence[Mapping[str, object]], notes: List[str]) -> Dict[str, object]:
    gold = [r for r in rows if r.get("gold_reference")]
    wrong = [r for r in rows if r.get("wrong_variant")]
    agent = [r for r in rows if r.get("agent")]
    tasks = [r for r in rows if r.get("has_task_dir")]

    gold_ok = sum(1 for r in gold if r["gold_reference"]["as_expected"])
    wrong_ok = sum(1 for r in wrong if r["wrong_variant"]["as_expected"])
    agent_match = sum(1 for r in agent if r["agent"].get("matches_reference"))
    agent_accepted = sum(1 for r in agent if r["agent"].get("verdict") == "accepted")
    # 已绑定 = agh-llm 且带 AGH 会话号。未绑定的单独汇报，不与已绑定的混为一谈。
    agent_bound = [r for r in agent if r["agent"].get("provenance_bound")]
    agent_unbound = [r for r in agent if not r["agent"].get("provenance_bound")]
    agent_match_bound = sum(1 for r in agent_bound if r["agent"].get("matches_reference"))

    by_layer: Dict[str, Dict[str, int]] = {}
    for row in rows:
        layer = str(row.get("layer") or "unknown")
        bucket = by_layer.setdefault(layer, {"tasks": 0, "gold_ok": 0, "wrong_ok": 0,
                                             "agent_match": 0, "agent_total": 0})
        if row.get("has_task_dir"):
            bucket["tasks"] += 1
        if row.get("gold_reference") and row["gold_reference"]["as_expected"]:
            bucket["gold_ok"] += 1
        if row.get("wrong_variant") and row["wrong_variant"]["as_expected"]:
            bucket["wrong_ok"] += 1
        if row.get("agent"):
            bucket["agent_total"] += 1
            if row["agent"].get("matches_reference"):
                bucket["agent_match"] += 1

    if agent and agent_unbound:
        notes.append("有 %d 个候选式运行标了 agh-llm 但**没有** AGH 会话号（provenance_bound=false），"
                     "已单列不计入绑定层：标签是自报的，只有绑定到真实会话才可核对。"
                     "请让调用方设置 FORMULA_AGH_SESSION_ID（见 harness/run_agent_discovery.ps1）。"
                     % len(agent_unbound))
    if len(gold) < len(tasks):
        notes.append("有 %d 个任务缺少 refcheck 运行（金标准自检未覆盖），"
                     "先运行 examples/reference_check.py。" % (len(tasks) - len(gold)))
    if len(wrong) < len(tasks):
        notes.append("有 %d 个任务缺少 variant 运行（判别力未覆盖），"
                     "先运行 examples/variant_check.py。" % (len(tasks) - len(wrong)))
    fixtures = [r for r in rows if r.get("agent_fixture")]
    if not agent:
        if fixtures:
            # 有候选式运行、但来源不是模型：如实说清楚，别让读者以为"跑都没跑"。
            notes.append("有 %d 个任务存在候选式运行，但其 hypothesis_source 不是 agh-llm"
                         "（现为人工提供或命令行给出），因此**不计入**「智能体发现」层。"
                         "对照表第 3 层为空，不能据此声称发现能力。" % len(fixtures))
        else:
            notes.append("没有任何候选式运行（runs/<task>-candNN）。"
                         "对照表第 3 层为空，不能据此声称发现能力；"
                         "当前可支撑的结论只有金标准自检与判别力两层。")

    return {
        "tasks_in_scope": len(tasks),
        "gold_reference_checked": len(gold),
        "gold_reference_accepted": gold_ok,
        "gold_reference_rate": (gold_ok / len(gold)) if gold else None,
        "wrong_variant_checked": len(wrong),
        "wrong_variant_rejected": wrong_ok,
        "wrong_variant_rate": (wrong_ok / len(wrong)) if wrong else None,
        "agent_candidates": len(agent),
        "agent_fixture_tasks": len([r for r in rows if r.get("agent_fixture")]),
        "agent_accepted": agent_accepted,
        "agent_matches_reference": agent_match,
        "agent_match_rate": (agent_match / len(agent)) if agent else None,
        # 绑定层：只统计带 AGH 会话号的候选式运行
        "agent_candidates_bound": len(agent_bound),
        "agent_candidates_unbound": len(agent_unbound),
        "agent_matches_reference_bound": agent_match_bound,
        "agent_match_rate_bound": (agent_match_bound / len(agent_bound)) if agent_bound else None,
        "by_layer": by_layer,
    }


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------

def write_outputs(payload: Mapping[str, object], out_dir: str) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    paths: Dict[str, str] = {}
    json_path = os.path.join(out_dir, "comparison.json")
    with open(json_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    paths["json"] = json_path

    csv_path = os.path.join(out_dir, "comparison.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["task_id", "layer", "kind", "formula", "verdict",
                         "holdout_rmse", "extrapolation_rmse", "dimension",
                         "reference_formula", "matches_reference"])
        for row in payload.get("rows") or []:
            wrote = False
            for key, kind in (("gold_reference", "gold-reference"),
                              ("wrong_variant", "wrong-variant"),
                              ("agent", "agent-candidate")):
                entry = row.get(key)
                if not entry:
                    continue
                writer.writerow([
                    row.get("task_id"), row.get("layer"), kind,
                    entry.get("formula") or row.get("reference_formula"),
                    entry.get("verdict"),
                    _fmt(entry.get("holdout")), _fmt(entry.get("extrapolation")),
                    entry.get("dimension"),
                    row.get("reference_formula"),
                    entry.get("matches_reference"),
                ])
                wrote = True
            if not wrote:
                writer.writerow([row.get("task_id"), row.get("layer"), "no-run", "", "",
                                 "", "", "", row.get("reference_formula"), ""])
    paths["csv"] = csv_path

    md_path = os.path.join(out_dir, "comparison.md")
    with open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_markdown(payload))
    paths["md"] = md_path
    return paths


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return "%.6g" % value
    return str(value)


def _markdown(payload: Mapping[str, object]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# 与标准答案对照表（M2 评分脚本产出）",
        "",
        "生成方式：",
        "",
        "    python src/scoring/compare.py --runs runs --tasks tasks --reference reference --out evidence/scoring",
        "",
        "标准答案只被本脚本读取。智能体侧（formula_agh）不持有任何指向 reference/ 的路径；",
        "证据是：把 reference/ 改名后，全部验证结论逐位不变（tests/test_isolation.py）。",
        "",
        "## 一、总览",
        "",
        "| 层次 | 检查数 | 符合预期 | 通过率 |",
        "|---|---|---|---|",
        "| 金标准自检（标准答案必须被接受） | %s | %s | %s |" % (
            summary.get("gold_reference_checked"),
            summary.get("gold_reference_accepted"),
            _pct(summary.get("gold_reference_rate"))),
        "| 判别力（结构错误的候选必须被拒绝） | %s | %s | %s |" % (
            summary.get("wrong_variant_checked"),
            summary.get("wrong_variant_rejected"),
            _pct(summary.get("wrong_variant_rate"))),
        "| 智能体发现（与标准答案一致，仅计 hypothesis_source=agh-llm） | %s | %s | %s |" % (
            summary.get("agent_candidates"),
            summary.get("agent_matches_reference"),
            _pct(summary.get("agent_match_rate"))),
        "| （参考）人工提供的候选式，不计入上行 | %s | - | - |" % (
            summary.get("agent_fixture_tasks"),),
        "",
        "## 二、按难度分层",
        "",
        "| 层级 | 任务数 | 金标准通过 | 错误式拒绝 | 智能体命中 |",
        "|---|---|---|---|---|",
    ]
    for layer in sorted((summary.get("by_layer") or {}).keys()):
        bucket = summary["by_layer"][layer]
        lines.append("| %s | %d | %d | %d | %d/%d |" % (
            layer, bucket["tasks"], bucket["gold_ok"], bucket["wrong_ok"],
            bucket["agent_match"], bucket["agent_total"]))
    lines += [
        "",
        "## 三、逐任务对照",
        "",
        "| 任务 | 层级 | 标准公式 | 智能体公式 | 留出集 | 外推区 | 量纲 | 与答案一致 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in payload.get("rows") or []:
        agent = row.get("agent") or {}
        mark = "-"
        if agent:
            equivalence = agent.get("numeric_equivalence") or {}
            if agent.get("structural_match"):
                mark = "结构相同"
            elif equivalence.get("equivalent"):
                mark = "数值等价"
            elif equivalence.get("available"):
                mark = "不一致 (偏差 %.3g)" % float(
                    equivalence.get("max_scaled_deviation") or 0.0)
            else:
                mark = "不可判定"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row.get("task_id"), row.get("layer") or "-",
            TICK + str(row.get("reference_formula") or "-") + TICK,
            (TICK + str(agent.get("formula")) + TICK) if agent.get("formula") else "-",
            _fmt(agent.get("holdout")), _fmt(agent.get("extrapolation")),
            _dim(agent.get("dimension")), mark))
    lines.append("")
    notes = payload.get("notes") or []
    if notes:
        lines.append("## 四、如实说明（不掩盖空缺）")
        lines.append("")
        for note in notes:
            lines.append("- " + str(note))
        lines.append("")
    return "\n".join(lines) + "\n"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return "%.1f%%" % (100.0 * float(value))


def _dim(value: object) -> str:
    if value is None:
        return "n/a"
    return "pass" if value else "fail"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="与标准答案对照（评分，独立于智能体）")
    parser.add_argument("--runs", default="runs")
    parser.add_argument("--tasks", default="tasks")
    parser.add_argument("--reference", default="reference")
    parser.add_argument("--out", default="evidence/scoring")
    args = parser.parse_args(argv)

    payload = build_comparison(args.runs, args.tasks, args.reference)
    paths = write_outputs(payload, args.out)
    print(json.dumps({
        "outputs": {k: v.replace(os.sep, "/") for k, v in paths.items()},
        "summary": payload["summary"],
        "notes": payload["notes"],
    }, ensure_ascii=False, indent=2))
    summary = payload["summary"]
    failed = 0
    if summary["gold_reference_checked"]:
        failed += summary["gold_reference_checked"] - summary["gold_reference_accepted"]
    if summary["wrong_variant_checked"]:
        failed += summary["wrong_variant_checked"] - summary["wrong_variant_rejected"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
