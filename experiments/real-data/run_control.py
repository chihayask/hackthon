# -*- coding: utf-8 -*-
"""真实数据负对照：在没有闭式定律的真实数据上，引擎会不会编造出"通过"的公式。

设计（2026-10-10）
-----------------
外部审计指出项目的 22 个任务全部是合成数据。把一条已知定律塞进真实数据并不能回应它：
真实观测的散布远大于合成数据，要么循环论证（定律本身就是生成数据用的），
要么直接打破 22/22 的金标准不变式。

所以这里换一个更硬、且**不触碰已验证基准**的问题：

    在一份确实没有闭式定律的真实数据上，引擎会不会给出 accepted？

数据：UCI Airfoil Self-Noise（id 291），NACA 0012 翼型的真实风洞测量，1503 行。
目标量是 scaled sound pressure level；它与频率、攻角、弦长、来流速度、位移厚度之间
确有工程经验关系，但**不存在**量纲封闭的精确公式。

做法：每个候选函数族都配一个**量纲补齐**的自由参数 k（否则会先被量纲门拦住，
测到的是"单位不对"而不是"数据不支持定律"），让判定落到拟合/留出/外推门。

用法：
    python experiments/real-data/run_control.py
    # 第二臂（智能体）：把它的运行目录传进来
    REAL_DATA_AGENT_RUNS=E:\fagh-realdata-root\runs python experiments/real-data/run_control.py
输出：results.json + 终端表格。可由 fetch.py 先取数。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from formula_agh.importer import convert          # noqa: E402
from formula_agh.verify import load_task, verify_formula  # noqa: E402

SOURCE = os.path.join(HERE, "airfoil.csv")
TASKS = os.path.join(HERE, "tasks")
REFERENCE = os.path.join(HERE, "reference")
TASK_ID = "real-airfoil-noise"
URL = ("https://archive.ics.uci.edu/ml/machine-learning-databases/"
       "00291/airfoil_self_noise.dat")

VARIABLES = ["velocity_ms", "displacement_m", "chord_m"]
# (候选公式, 让该式量纲补齐所需的 k 单位)
CANDIDATES = [
    ("k*velocity_ms**5*displacement_m", "s^5/m^6"),
    ("k*velocity_ms**4", "s^4/m^4"),
    ("k*velocity_ms**3*chord_m", "s^3/m^4"),
    ("k*velocity_ms**2*chord_m*displacement_m", "s^2/m^4"),
    ("k*velocity_ms*chord_m**2", "s/m^3"),
    ("k*displacement_m", "1/m"),
]


def _field(item, name, default=None):
    """CheckResult 是 dataclass；早期版本按 dict 取值，结果失败项与残差全丢。"""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _reason(item):
    return str(_field(item, "reason", "") or "")[:110]


def run_candidate(formula, unit):
    report = convert(
        SOURCE, TASK_ID, target="scaled_sound_pressure_level_db",
        variables=VARIABLES,
        units={"velocity_ms": "m/s", "displacement_m": "m", "chord_m": "m",
               "y": "dB", "k": unit},
        free_parameters=["k"], source_url=URL, tasks_root=TASKS,
        reference_root=REFERENCE, phenomenon="NACA 0012 翼型自噪声的风洞测量（真实数据）",
        force=True)
    if report.get("errors"):
        return {"formula": formula, "k_unit": unit, "error": str(report["errors"])}
    columns, meta = load_task(os.path.join(TASKS, TASK_ID))
    result = verify_formula(formula, columns, meta, parameters=["k"],
                            dimension_check=True, fit_max_residual=0.5)
    checks = list(getattr(result, "checks", []) or [])
    dimension = next((c for c in checks if _field(c, "name") == "dimension"), None)
    failed, metrics, reasons = [], {}, {}
    for c in checks:
        name = _field(c, "name")
        if _field(c, "passed") is False:
            failed.append(name)
            reasons[name] = _reason(c)
        if name in ("fit", "holdout", "extrapolation"):
            metrics[name] = (_field(c, "metrics", {}) or {}).get("normalized_rmse")
    return {"formula": formula, "k_unit": unit, "verdict": result.verdict,
            "dimension_mode": (_field(dimension, "metrics", {}) or {}).get("mode"),
            "failed_checks": failed, "failure_reasons": reasons, "metrics": metrics}


def summarize_runs(runs_dir, out_name="agent_results.json"):
    """汇总智能体在本任务上的运行（第二臂：模型会不会硬凑）。"""
    rows = []
    if os.path.isdir(runs_dir):
        for run_id in sorted(os.listdir(runs_dir)):
            path = os.path.join(runs_dir, run_id, "run.json")
            if not os.path.isfile(path):
                continue
            run = json.load(open(path, encoding="utf-8"))
            failed = []
            checks_dir = os.path.join(runs_dir, run_id, "checks")
            if os.path.isdir(checks_dir):
                for name in sorted(os.listdir(checks_dir)):
                    if not name.endswith(".json"):
                        continue
                    check = json.load(open(os.path.join(checks_dir, name), encoding="utf-8"))
                    if check.get("passed") is False:
                        failed.append({"check": check.get("name"),
                                       "reason": str(check.get("reason", ""))[:120]})
            rows.append({"run_id": run_id, "source": run.get("hypothesis_source"),
                         "provenance_bound": bool(run.get("provenance_bound")),
                         "formula": run.get("formula"), "verdict": run.get("verdict"),
                         "failed": failed})
    payload = {"runs": rows, "accepted_count": sum(1 for r in rows if r["verdict"] == "accepted"),
               "run_count": len(rows)}
    with open(os.path.join(HERE, out_name), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for r in rows:
        print("%-34s %-9s %s" % (r["run_id"], r["verdict"], r["formula"]))
        for f in r["failed"]:
            print("    %s: %s" % (f["check"], f["reason"]))
    print("\n%d 条智能体运行，accepted %d 条 —— 写入 %s" % (len(rows), payload["accepted_count"], out_name))
    return payload


def main():
    if not os.path.isfile(SOURCE):
        raise SystemExit("先运行 fetch.py 取数")
    runs_dir = os.environ.get("REAL_DATA_AGENT_RUNS", "")
    if runs_dir:
        summarize_runs(runs_dir)
        return 0
    rows = [run_candidate(f, u) for f, u in CANDIDATES]
    accepted = [r for r in rows if r.get("verdict") == "accepted"]
    payload = {"dataset": "UCI Airfoil Self-Noise (id 291)", "source_url": URL,
               "task_id": TASK_ID, "candidates": rows,
               "accepted_count": len(accepted), "candidate_count": len(rows)}
    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("%-42s %-9s %-8s %s" % ("候选公式", "判定", "量纲档", "失败项"))
    for r in rows:
        detail = "; ".join(r.get("failure_reasons", {}).values())
        print("%-42s %-9s %-8s %s" % (r["formula"], r.get("verdict", "-"),
                                      r.get("dimension_mode", "-"), detail or "-"))
    print("\n%d 个候选，accepted %d 个" % (len(rows), len(accepted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
