# -*- coding: utf-8 -*-
"""从 sim/results.json 生成 sim/RESULTS.md。

为什么由 JSON 生成而不是手写报告：本项目已经多次出现同一数字在文档与产物之间漂移。
报告里的每个数都从 results.json 取，重跑任务线即自动同步。

用法：python sim/make_report.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.json")
OUT = os.path.join(HERE, "RESULTS.md")
BC_LABEL = {"neumann": "neumann（极面零通量，球面自带）",
            "dirichlet": "dirichlet（极点带钉在观测值）",
            "robin": "robin（极点与外部储库交换）"}


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        out.append("| " + " | ".join(str(v) for v in row) + " |")
    return out


def build(data):
    main = data["splits"]["主划分"]
    lines = ["# 仿真任务线结果（由 results.json 生成，请勿手改）", ""]
    lines += ["## 一、数据与模型", ""]
    lines += table([
        ["数据源", data["data"]["source"]],
        ["下载地址", data["data"]["url"]],
        ["原始文件 sha256", data["data"]["raw_sha256"] or "（未保留原始文件）"],
        ["纬度带", "%d 个：%s" % (len(data["data"]["bands"]), " / ".join(data["data"]["bands"]))],
        ["年份", "%d—%d" % tuple(data["data"]["years"])],
        ["模型方程", data["model"]["equation"]],
        ["状态量", data["model"]["state"]],
        ["待反演参数", "、".join(data["model"]["parameters"])],
        ["离散", data["model"]["discretization"]],
    ], ["项", "值"])
    lines += ["", "## 二、参数反演（训练 %s）" % str(main["train"]), ""]
    rows = []
    for bc in ("neumann", "dirichlet", "robin"):
        v = main["boundaries"][bc]
        rows.append([BC_LABEL[bc], "%.4f" % v["ls"]["kd"], "%.4f" % v["ls"]["kl"],
                     "%.4f" % v["ls"]["residual_rmse"],
                     "可接受" if v["ls"]["kd"] >= 0 else "**kd<0，不可接受**"])
    lines += table(rows, ["极点边界", "kd（最小二乘）", "kl", "PDE 残差 RMSE", "参数是否非负"])
    lines += ["", "非负约束下的最优（格点搜索，kd,kl ≥ 0）：", ""]
    rows = []
    for bc in ("neumann", "dirichlet", "robin"):
        v = main["boundaries"][bc]["constrained"]
        rows.append([BC_LABEL[bc], "%.4f" % v["kd"], "%.4f" % v["kl"], "%.4f" % v["train_rmse"]])
    lines += table(rows, ["极点边界", "kd", "kl", "训练 RMSE"])
    lines += ["", "## 三、正向仿真复现：误差随预报时效", ""]
    lead = main["lead_max"]
    rows = []
    for bc in ("neumann", "dirichlet", "robin"):
        c = main["boundaries"][bc]["forward_rmse"]
        rows.append([BC_LABEL[bc]] + ["%.3f" % x for x in c])
    rows.append(["持久基线"] + ["%.3f" % x for x in main["baselines"]["persistence"]])
    rows.append(["零距平基线"] + ["%.3f" % x for x in main["baselines"]["climatology"]])
    lines += table(rows, ["方法"] + ["第 %d 年" % k for k in range(1, lead + 1)])
    lines += ["", "## 四、对照划分（训练 1880—1952 / 留出 1953—2025）", ""]
    alt = data["splits"]["对照划分"]
    rows = []
    for bc in ("neumann", "dirichlet", "robin"):
        v = alt["boundaries"][bc]
        rows.append([BC_LABEL[bc], "%.4f" % v["ls"]["kd"], "%.4f" % v["ls"]["kl"],
                     "%.4f" % v["ls"]["residual_rmse"]])
    lines += table(rows, ["极点边界", "kd（最小二乘）", "kl", "PDE 残差 RMSE"])
    return lines


def main():
    with open(RESULTS, encoding="utf-8") as handle:
        data = json.load(handle)
    lines = build(data)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("已写出", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())