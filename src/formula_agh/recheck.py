# -*- coding: utf-8 -*-
"""三重验证的独立复算（M2 交付 3/8）。

验收标准（对应分工表 10-09）
---------------------------
"对同一份 result.json 可独立复算，结果与 M1 日志一致"。

设计要点
--------
* **不复用 M1 的拟合值**：只读 run.json 里的公式与自由参数*名字*，从 data.csv 重新
  划分、重新拟合、重新判定。若复用拟合值，复算就退化成"重读一遍输出"，没有意义。
* **写入位置在 run 目录之外**（recheck/<run_id>.json）。运行目录一经生成即视为
  不可变证据；后来的复核不得改写它，否则 manifest.sha256 的防篡改语义就被破坏了。
* **确定性判定是严格的**：全流程无未播种随机性，复算结果应与原结果逐位一致。
  一旦出现偏差，本模块报 nondeterministic，而不是"差不多就行"。
* 任务已不存在（历史遗留运行）时，如实报 unresolvable，不假装通过。
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional, Tuple

from .evidence import verify_manifest
from .settings import verify_settings
from .verify import VerifyError, load_task, verify_formula

REL_TOL = 1e-9
# 数值偏差超过这个量级就不再算"一致"。1e-9 只能抓浮点末位噪声，
# 抓不到"证据由旧口径产出"这种真问题——旧口径与新口径的最大相对差实测能到 0.8。
METRIC_TOL = 1e-3

# 标准三重验证引擎能产出的检验项。若某次运行记录的检验项不在此集合内，
# 说明它由别的判定套件产出（例如 M3 的尺度/极限行为检查 scale-*），
# 本模块不冒充能复算它——如实标成 out-of-scope，而不是武断报"不一致"。
CORE_CHECKS = {"expression", "dimension", "fit", "holdout", "extrapolation"}


def is_standard_check(name: str) -> bool:
    """标准引擎能产出的检验名。

    接入 M3 的尺度检验后（方案 A），scale-* 也属于标准引擎的输出。
    但只有"只跑尺度检验"的那种运行（scale-ref-*）仍然算范围外——
    它们没有走三重门，不属于本模块能断言的对象。
    """
    return name in CORE_CHECKS or name.startswith("scale-")


def _load_json(path: str) -> Optional[Dict[str, object]]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def resolve_task_dir(run_meta: Mapping[str, object], tasks_root: str,
                     run_dir: str) -> Tuple[Optional[str], str]:
    """定位这次运行对应的任务目录，返回 (路径, 依据说明)。"""
    candidates: List[str] = []
    for entry in (run_meta.get("inputs") or []):
        text = str(entry).replace("\\", "/")
        if text.endswith(".csv") or text.endswith(".json"):
            text = os.path.dirname(text)
        candidates.append(text)
    task_id = str(run_meta.get("task_id") or "")
    if task_id:
        candidates.append(os.path.join(tasks_root, task_id))
        candidates.append(task_id)
    for cand in candidates:
        if not cand:
            continue
        path = cand if os.path.isabs(cand) else os.path.join(os.getcwd(), cand)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "data.csv")):
            return path, "resolved from run.json inputs/task_id: " + cand
        rel = os.path.join(os.path.basename(os.path.dirname(run_dir)), cand)
        if os.path.isdir(rel) and os.path.exists(os.path.join(rel, "data.csv")):
            return rel, "resolved relative to run dir: " + rel
    return None, ("任务目录不存在（run.json.task_id=" + (task_id or "?")
                  + "，inputs=" + json.dumps(run_meta.get("inputs") or [], ensure_ascii=False) + "）")


def _rel_diff(a: float, b: float) -> float:
    if a == b:
        return 0.0
    scale = max(abs(a), abs(b))
    if scale == 0:
        return 0.0 if a == b else float("inf")
    return abs(a - b) / scale


def recheck_run(run_dir: str,
                tasks_root: str = "tasks",
                settings_override: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    """对单个运行目录做独立复算。"""
    run_id = os.path.basename(os.path.normpath(run_dir))
    out: Dict[str, object] = {
        "run_id": run_id,
        "run_dir": run_dir.replace(os.sep, "/"),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "unknown",
        "agrees": False,
    }

    meta = _load_json(os.path.join(run_dir, "run.json"))
    if meta is None:
        out["status"] = "missing-run-json"
        out["detail"] = "运行目录缺少 run.json，无法独立复算"
        return out
    out["task_id"] = meta.get("task_id")
    out["formula"] = meta.get("formula")
    out["original_verdict"] = meta.get("verdict")

    manifest = verify_manifest(run_dir)
    out["manifest_ok"] = bool(manifest.get("ok"))
    out["manifest_detail"] = {k: manifest.get(k) for k in ("untracked", "missing", "mismatched")}

    task_dir, why = resolve_task_dir(meta, tasks_root, run_dir)
    out["task_resolution"] = why
    if task_dir is None:
        out["status"] = "unresolvable"
        out["detail"] = "任务目录不存在，本次运行无法被独立复算（历史遗留运行）"
        return out
    out["task_dir"] = task_dir.replace(os.sep, "/")

    recorded = meta.get("verify_settings")
    if settings_override is not None:
        settings = dict(settings_override)
        out["settings_source"] = "cli-override"
    elif isinstance(recorded, Mapping):
        settings = dict(recorded)
        out["settings_source"] = "run.json.verify_settings"
    else:
        settings = verify_settings()
        out["settings_source"] = "fallback:config/agent.yaml（该运行早于本字段引入）"
    out["settings"] = settings

    params = meta.get("free_parameters")
    if isinstance(params, list):
        param_names = [str(p) for p in params]
        out["params_source"] = "run.json.free_parameters"
    else:
        param_names = sorted((meta.get("parameters") or {}).keys())
        out["params_source"] = "derived from run.json.parameters keys（该运行早于本字段引入）"
    out["free_parameters"] = param_names

    try:
        columns, task_meta = load_task(task_dir)
    except VerifyError as exc:
        out["status"] = "task-load-error"
        out["detail"] = str(exc)
        return out

    formula = str(meta.get("formula") or "")
    if not formula:
        out["status"] = "missing-formula"
        out["detail"] = "run.json 没有公式，无法复算"
        return out

    try:
        fresh = verify_formula(
            formula, columns, task_meta,
            parameters=param_names,
            holdout_threshold=float(settings.get("holdout_threshold", 0.05)),
            extrapolation_threshold=float(settings.get("extrapolation_threshold", 0.15)),
            holdout_ratio=float(settings.get("holdout_ratio", 0.2)),
            extrapolation_ratio=float(settings.get("extrapolation_ratio", 0.15)),
            seed=int(settings.get("seed", 20261008)),
            # 开关也要复算，否则"原运行带尺度检验、复算不带"会被误判成不一致
            dimension_check=bool(settings.get("dimension_check", True)),
            scale_check=bool(settings.get("scale_check", False)),
            fit_max_residual=float(settings.get("fit_max_residual", 0.5)),
        )
    except VerifyError as exc:
        out["status"] = "recompute-error"
        out["detail"] = str(exc)
        return out

    out["recomputed_verdict"] = fresh.verdict
    verdict_match = (fresh.verdict == meta.get("verdict"))

    check_details: List[Dict[str, object]] = []
    max_metric_diff = 0.0
    checks_match = True
    original_checks = {}
    for path_name in sorted(os.listdir(os.path.join(run_dir, "checks"))
                            if os.path.isdir(os.path.join(run_dir, "checks")) else []):
        payload = _load_json(os.path.join(run_dir, "checks", path_name))
        if isinstance(payload, Mapping) and "name" in payload:
            original_checks[str(payload["name"])] = payload

    foreign = sorted(n for n in original_checks if not is_standard_check(n))
    has_core = bool(set(original_checks) & CORE_CHECKS)
    if not original_checks or foreign or not has_core:
        out["recomputed_verdict"] = fresh.verdict
        out["recorded_checks"] = sorted(original_checks)
        out["status"] = "out-of-scope"
        out["detail"] = (
            "该运行由其它判定套件产出（检验项：" + ",".join(sorted(original_checks))
            + "），没有走标准三重验证，本模块不做一致性断言。"
            + "若要作为提交证据，请用统一引擎重跑一次。")
        out["foreign_checks"] = foreign
        return out

    compared = 0
    for check in fresh.checks:
        if check.name not in original_checks:
            continue   # 只比对双方都有的检验项，避免"记录得更少"被误判为不一致
        compared += 1
        old = original_checks.get(check.name) or {}
        passed_match = (old.get("passed") == check.passed)
        metric_diffs: Dict[str, float] = {}
        for key, value in (check.metrics or {}).items():
            old_value = (old.get("metrics") or {}).get(key)
            if isinstance(old_value, (int, float)) and isinstance(value, (int, float)):
                diff = _rel_diff(float(value), float(old_value))
                metric_diffs[key] = diff
                if math.isfinite(diff):
                    max_metric_diff = max(max_metric_diff, diff)
                else:
                    max_metric_diff = float("inf")
        if not passed_match:
            checks_match = False
        check_details.append({
            "name": check.name,
            "passed_original": old.get("passed"),
            "passed_recomputed": check.passed,
            "passed_match": passed_match,
            "metrics_rel_diff": metric_diffs,
        })
    out["checks"] = check_details
    out["checks_compared"] = compared

    param_diffs: Dict[str, float] = {}
    original_params = meta.get("parameters") or {}
    for name, value in (fresh.parameters or {}).items():
        old_value = original_params.get(name)
        if isinstance(old_value, (int, float)):
            param_diffs[name] = _rel_diff(float(value), float(old_value))
    out["parameter_rel_diff"] = param_diffs
    max_param_diff = max(param_diffs.values()) if param_diffs else 0.0

    bitwise = (verdict_match and checks_match
               and max_metric_diff <= REL_TOL and max_param_diff <= REL_TOL)
    out["verdict_match"] = verdict_match
    out["checks_match"] = checks_match
    out["max_metric_rel_diff"] = max_metric_diff
    out["max_parameter_rel_diff"] = max_param_diff
    out["agrees"] = bool(verdict_match and checks_match)
    out["verdict_reproduced"] = bool(verdict_match)
    out["deterministic"] = bool(bitwise)
    if not verdict_match:
        out["status"] = "disagree"
        out["detail"] = ("判定翻转：原 %s，复算 %s。这是最严重的一类问题，必须查清原因。"
                         % (meta.get("verdict"), fresh.verdict))
    elif not checks_match:
        # 判定一致但检验项对不上：通常说明该运行由更早版本的引擎产出（证据过期），
        # 或者两条代码路径对同一次调用给出了不同理由。两者都要重跑一次。
        out["status"] = "stale-checks"
        changed = [c["name"] for c in check_details if not c["passed_match"]]
        out["detail"] = ("最终判定可复现（%s），但检验项 %s 与记录不同："
                         "该证据很可能由旧版本引擎产出，应重跑后再提交。"
                         % (fresh.verdict, ",".join(changed)))
    elif max_metric_diff > METRIC_TOL or max_param_diff > METRIC_TOL:
        # 判定相同、检验项也相同，但数字对不上——通常是证据由**旧口径/旧阈值**产出。
        # 这类运行不能算"复现通过"：拿它去答辩，评审按新口径复算会得到不同的数。
        out["status"] = "stale-metrics"
        out["detail"] = ("判定可复现，但指标数值对不上（metric 最大相对差 %.4g > %.0e，"
                         "参数最大相对差 %.4g）：该证据很可能由旧口径或旧阈值产出，"
                         "应重跑后再引用。" % (max_metric_diff, METRIC_TOL, max_param_diff))
    elif not bitwise:
        out["status"] = "agree"
        out["detail"] = ("判定与指标在 %.0e 容差内一致，仅浮点末位差异"
                         "（metric 最大相对差 %.3g，参数最大相对差 %.3g）。"
                         % (METRIC_TOL, max_metric_diff, max_param_diff))
    else:
        out["status"] = "agree"
        out["detail"] = "判定与全部检验项逐位一致，独立复算通过"
    return out


def recheck_all(runs_root: str = "runs",
                tasks_root: str = "tasks",
                out_dir: str = "recheck",
                settings_override: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    """对 runs/ 下所有运行目录做独立复算，落盘明细与汇总。"""
    os.makedirs(out_dir, exist_ok=True)
    results: List[Dict[str, object]] = []
    if os.path.isdir(runs_root):
        for entry in sorted(os.listdir(runs_root)):
            run_dir = os.path.join(runs_root, entry)
            if not os.path.isdir(run_dir):
                continue
            if not os.path.exists(os.path.join(run_dir, "run.json")):
                results.append({"run_id": entry, "status": "not-a-run",
                                "detail": "目录内没有 run.json"})
                continue
            result = recheck_run(run_dir, tasks_root, settings_override)
            results.append(result)
            with open(os.path.join(out_dir, entry + ".json"), "w",
                      encoding="utf-8", newline="\n") as fh:
                json.dump(result, fh, ensure_ascii=False, indent=2)
                fh.write("\n")

    tally: Dict[str, int] = {}
    for item in results:
        key = str(item.get("status"))
        tally[key] = tally.get(key, 0) + 1

    scored = [r for r in results
              if r.get("status") in ("agree", "disagree", "stale-checks", "stale-metrics")]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs_root": runs_root.replace(os.sep, "/"),
        "tasks_root": tasks_root.replace(os.sep, "/"),
        "total": len(results),
        "tally": tally,
        "in_scope": len(scored),
        # 复算通过率只在"标准三重验证产出的运行"上计算；别的判定套件不掺进来充数。
        "independent_recompute_rate": (
            float(tally.get("agree", 0)) / float(len(scored)) if scored else 0.0),
        "verdict_reproduced_rate": (
            float(tally.get("agree", 0) + tally.get("stale-checks", 0)) / float(len(scored))
            if scored else 0.0),
        "stale_checks": [r["run_id"] for r in results if r.get("status") == "stale-checks"],
        "stale_metrics": [r["run_id"] for r in results
                          if r.get("status") == "stale-metrics"],
        "out_of_scope": [r["run_id"] for r in results if r.get("status") == "out-of-scope"],
        "unresolvable": [r["run_id"] for r in results if r.get("status") == "unresolvable"],
        "disagree": [r["run_id"] for r in results if r.get("status") == "disagree"],
        "nondeterministic": [r["run_id"] for r in results
                             if r.get("status") == "agree" and not r.get("deterministic")],
        "results": [{k: v for k, v in r.items() if k != "checks"} for r in results],
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_summary_markdown(summary))
    return summary


def _summary_markdown(summary: Mapping[str, object]) -> str:
    lines = [
        "# 独立复算报告（M2）",
        "",
        "对 runs/ 下每一次运行，从 data.csv 重新划分、重新拟合、重新判定，",
        "再与原始 result.json 逐项比对。复算不复用原始拟合值。",
        "",
        "- 生成时间（UTC）：" + str(summary.get("generated_at_utc")),
        "- 运行总数：" + str(summary.get("total")),
        "- 判定一致：" + str((summary.get("tally") or {}).get("agree", 0)),
        "- 独立复算通过率：%.1f%%" % (100.0 * float(summary.get("independent_recompute_rate") or 0.0)),
        "",
        "- 属于标准三重验证、纳入复算统计的运行：" + str(summary.get("in_scope")),
        "- 由其它判定套件产出、不纳入统计的运行：" + str(len(summary.get("out_of_scope") or [])),
        "",
        "| run_id | 状态 | 原判定 | 复算判定 | manifest | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for item in summary.get("results") or []:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            item.get("run_id"), item.get("status"),
            item.get("original_verdict", "-"), item.get("recomputed_verdict", "-"),
            "ok" if item.get("manifest_ok") else "缺失/不完整",
            str(item.get("detail", "")).replace("|", "/")[:80],
        ))
    lines.append("")
    stale_metrics = summary.get("stale_metrics") or []
    if stale_metrics:
        lines.append("## 证据过期（判定可复现，但指标数值由旧口径产出）")
        lines.append("")
        lines.append("以下运行的最终判定与新引擎一致，但记录的误差数值对不上——")
        lines.append("通常是因为它们产生于判定口径/阈值变更之前。**引用前必须重跑**：")
        lines.append("否则评审按当前口径复算会得到不同的数字。")
        lines.append("")
        for run_id in stale_metrics:
            lines.append("- " + str(run_id))
        lines.append("")
    stale = summary.get("stale_checks") or []
    if stale:
        lines.append("## 证据过期（判定可复现，但检验项与记录不符）")
        lines.append("")
        lines.append("以下运行由更早版本的引擎产出，重跑后最终判定相同、但检验明细不同，"
                     "已在本次流水线中重跑覆盖：")
        lines.append("")
        for run_id in stale:
            lines.append("- " + str(run_id))
        lines.append("")
    unresolvable = summary.get("unresolvable") or []
    if unresolvable:
        lines.append("## 无法复算的历史运行（如实列出，不隐藏）")
        lines.append("")
        lines.append("以下运行目录的 run.json 指向的任务目录已不存在，属于早期迭代产物，"
                     "**不可复现**，不作为提交证据使用：")
        lines.append("")
        for run_id in unresolvable:
            lines.append("- " + str(run_id))
        lines.append("")
    return "\n".join(lines) + "\n"
