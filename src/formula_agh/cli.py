# -*- coding: utf-8 -*-
    # formula-agh 命令行入口：AGH 通过命令工具调用它，读 stdout 的 JSON 作为执行反馈。

# 用法（示例）：

# python -m formula_agh verify --task tasks/mech-001 --formula "G*m1*m2/r**2" \
# --params G --run-id 20261008-mech001-01 --out runs

# python -m formula_agh batch --tasks tasks --out runs --layer base

# python -m formula_agh validate-tasks --tasks tasks

# 输出：stdout 打印 JSON（供智能体消费），证据同时写入 runs/<run_id>/。
# #
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

from .evidence import write_evidence
from .scale_checks import load_specs, run_scale_checks
from .settings import verify_settings
from .verify import VerifyError, load_task, verify_formula


DEFAULT_SPECS = os.path.join('physics', 'scale_specs.json')


def _parse_param_values(text: str) -> Dict[str, float]:
    # --params 支持两种写法：
    #   "G=6.674e-11,hbar=1.05e-34"  给出数值（尺度检验需要参数的量级与符号）
    #   "G,hbar"                     只给名字（回退到规格里的物理真值）
    out: Dict[str, float] = {}
    for chunk in (text or '').split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        if '=' in chunk:
            name, _, value = chunk.partition('=')
            out[name.strip()] = float(value)
        else:
            out[chunk] = float('nan')
    return out


REQUIRED_META = ("task_id", "var_names", "source")


def cmd_validate_tasks(args: argparse.Namespace) -> int:
    root = args.tasks
    problems: List[str] = []
    checked = 0
    for name in sorted(os.listdir(root)):
        task_dir = os.path.join(root, name)
        if not os.path.isdir(task_dir):
            continue
        checked += 1
        meta_path = os.path.join(task_dir, "meta.json")
        csv_path = os.path.join(task_dir, "data.csv")
        if not os.path.exists(meta_path):
            problems.append(name + ": 缺少 meta.json")
            continue
        if not os.path.exists(csv_path):
            problems.append(name + ": 缺少 data.csv")
            continue
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except json.JSONDecodeError as exc:
            problems.append(name + ": meta.json 不是合法 JSON (" + str(exc) + ")")
            continue
        for key in REQUIRED_META:
            if key not in meta:
                problems.append(name + ": meta.json 缺少字段 " + key)
        var_names = meta.get("var_names") or []
        if not isinstance(var_names, list) or not var_names:
            problems.append(name + ": var_names 必须是非空数组")
        header = open(csv_path, encoding="utf-8").readline().strip()
        columns = [c.strip() for c in header.split(",")]
        for var in var_names:
            if var not in columns:
                problems.append(name + ": data.csv 缺少列 " + str(var))
        if "y" not in columns:
            problems.append(name + ": data.csv 缺少目标列 y")
        leak = [f for f in os.listdir(task_dir) if re.search(r"reference|answer|ground", f, re.I)]
        if leak:
            problems.append(name + ": 任务目录出现疑似标准答案文件 " + ",".join(leak) +
                            "（必须移出 tasks/，避免进入智能体上下文）")
    result = {"checked": checked, "problems": problems, "ok": not problems}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


def _hypothesis_source(explicit: str = "") -> str:
    """假设来源三级优先：--hypothesis-source > FORMULA_AGH_HYPOTHESIS_SOURCE > cli。

    存在的理由（M2 真实运行暴露的缺陷 1）：AGH 通过 harness/run_verify.cmd 调用本 CLI 时，
    那条命令在引擎看来与"人在终端里敲"完全一样，于是模型自主提出的公式会被记成 cli，
    从而不计入评分脚本的"智能体发现"层——证据会在关键结论上说反话。
    包装脚本 export FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm，这条链把它接进来。
    """
    explicit = str(explicit or "").strip()
    if explicit:
        return explicit
    env = str(os.environ.get("FORMULA_AGH_HYPOTHESIS_SOURCE", "") or "").strip()
    if env:
        return env
    return "cli"


def cmd_verify(args: argparse.Namespace) -> int:
    settings = verify_settings()
    columns, meta = load_task(args.task)
    params = [p for p in (args.params or "").split(",") if p]
    holdout_threshold = (settings["holdout_threshold"]
                         if args.holdout_threshold is None else args.holdout_threshold)
    extrapolation_threshold = (settings["extrapolation_threshold"]
                               if args.extrapolation_threshold is None
                               else args.extrapolation_threshold)
    scale_specs = args.scale_specs or DEFAULT_SPECS
    report = verify_formula(
        args.formula,
        columns,
        meta,
        parameters=params,
        holdout_threshold=holdout_threshold,
        extrapolation_threshold=extrapolation_threshold,
        holdout_ratio=settings["holdout_ratio"],
        extrapolation_ratio=settings["extrapolation_ratio"],
        seed=settings["seed"],
        dimension_check=not args.no_dimension_check,
        scale_check=not args.no_scale_check,
        scale_specs_path=scale_specs,
        fit_max_residual=settings.get("fit_max_residual", 0.5),
    )
    run_id = args.run_id or (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + report.task_id)
    run_dir = os.path.join(args.out, run_id)
    command = "python -m formula_agh verify --task " + args.task + " --formula " + json.dumps(args.formula, ensure_ascii=False)
    if params:
        command += " --params " + ",".join(params)
    write_evidence(run_dir, report, command, inputs=[args.task],
                   settings_in=settings,
                   hypothesis_source=_hypothesis_source(args.hypothesis_source))
    payload = json.loads(report.to_json())
    payload["run_dir"] = run_dir.replace(os.sep, "/")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.verdict == "accepted" else 1


def cmd_batch(args: argparse.Namespace) -> int:
    summary = {"accepted": 0, "rejected": 0, "errors": 0, "runs": []}
    root = args.tasks
    for name in sorted(os.listdir(root)):
        task_dir = os.path.join(root, name)
        if not os.path.isdir(task_dir):
            continue
        meta_path = os.path.join(task_dir, "meta.json")
        cand_path = os.path.join(task_dir, "candidates.json")
        if not os.path.exists(meta_path) or not os.path.exists(cand_path):
            continue
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        if args.layer and str(meta.get("layer", "")) != args.layer:
            continue
        with open(cand_path, encoding="utf-8") as fh:
            candidates = json.load(fh)
        columns, meta2 = load_task(task_dir)
        for idx, cand in enumerate(candidates, 1):
            formula = cand["formula"] if isinstance(cand, dict) else str(cand)
            params = cand.get("parameters", []) if isinstance(cand, dict) else []
            run_id = name + "-cand%02d" % idx
            try:
                report = verify_formula(formula, columns, meta2, parameters=params)
            except VerifyError as exc:
                summary["errors"] += 1
                summary["runs"].append({"task": name, "run_id": run_id, "error": str(exc)})
                continue
            run_dir = os.path.join(args.out, run_id)
            write_evidence(run_dir, report, "batch: " + name, inputs=[task_dir],
                           hypothesis_source=_hypothesis_source(args.hypothesis_source))
            summary[report.verdict if report.verdict in ("accepted", "rejected") else "errors"] += 1
            summary["runs"].append({"task": name, "run_id": run_id, "verdict": report.verdict,
                                    "formula": formula})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="formula_agh", description="FORMULA-AGH 验证引擎")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="对单个公式执行三重验证")
    p_verify.add_argument("--task", required=True)
    p_verify.add_argument("--formula", required=True)
    p_verify.add_argument("--params", default="")
    p_verify.add_argument("--run-id", default="")
    p_verify.add_argument("--out", default="runs")
    # 默认值取 None：真正的阈值只有一个来源 config/agent.yaml（settings.verify_settings），
    # 命令行只在显式传入时才覆盖它。硬编码默认值会让"阈值只有一处"这条纪律失效。
    p_verify.add_argument("--holdout-threshold", type=float, default=None)
    p_verify.add_argument("--extrapolation-threshold", type=float, default=None)
    p_verify.add_argument("--hypothesis-source", default="",
                          help="假设来源（AGH 调用时应为 agh-llm）")
    p_verify.add_argument("--scale-specs", default="")
    p_verify.add_argument("--no-scale-check", action="store_true")
    p_verify.add_argument("--no-dimension-check", action="store_true")
    p_verify.set_defaults(func=cmd_verify)

    p_batch = sub.add_parser("batch", help="批量验证任务目录下的候选公式")
    p_batch.add_argument("--tasks", required=True)
    p_batch.add_argument("--out", default="runs")
    p_batch.add_argument("--layer", default="")
    p_batch.add_argument("--hypothesis-source", default="")
    p_batch.set_defaults(func=cmd_batch)

    p_val = sub.add_parser("validate-tasks", help="校验任务集格式与答案泄漏")
    p_val.add_argument("--tasks", required=True)
    p_val.set_defaults(func=cmd_validate_tasks)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except VerifyError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())