# -*- coding: utf-8 -*-
"""仿真任务线：从公开温度场反演 EBM 参数、仿真复现、比较不同边界条件。

跑完写出 sim/results.json 与 sim/RESULTS.md。全部为确定性计算，不调用模型。

    模型：C dT/dt = d/dx[(1-x^2) D dT/dx] - lambda T      x = sin(lat)
    距平：T_i = 纬度带温度 - 全球面积加权均值（消去外强迫一阶响应）
    反演：最小二乘辨识 (kd, kl)，kd = D/C，kl = lambda/C；另给非负约束解
    复现：以辨识参数正向仿真，误差随预报时效；对照持久 / 零距平两条基线

用法：python sim/run_task.py
"""
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ebm  # noqa: E402
import invert  # noqa: E402

RAW = os.path.join(HERE, "data", "ZonAnn.Ts+dSST.csv")
LEAD_MAX = 10
SPLITS = [(1880, 1979, 1980, 2025, "主划分"), (1880, 1952, 1953, 2025, "对照划分")]


def sha256(path):
    if not os.path.isfile(path):
        return None
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run_split(years, anom, train_lo, train_hi, test_lo, test_hi):
    out = {"train": [train_lo, train_hi], "test": [test_lo, test_hi], "boundaries": {}}
    for bc in ebm.BOUNDARIES:
        unconstrained = invert.identify(years, anom, bc, train_lo, train_hi)
        kd, kl, train_rmse = invert.fit(years, anom, bc, train_lo, train_hi)
        # 可用的预报时效上限 = 留出期长度（年份差，不是 len(years) 减年份——这里踩过一次）
        span = int(test_hi - test_lo)
        curve = invert.forward_curve(years, anom, kd, kl, bc, test_lo, min(LEAD_MAX, span))
        out["boundaries"][bc] = {
            "ls": unconstrained,
            "constrained": {"kd": kd, "kl": kl, "train_rmse": train_rmse},
            "forward_rmse": curve,
            "admissible": bool(kd >= 0 and kl >= 0 and unconstrained["kd"] >= 0),
        }
    lead = len(next(iter(out["boundaries"].values()))["forward_rmse"])
    out["lead_max"] = lead
    out["baselines"] = {
        "persistence": invert.persistence_curve(years, anom, test_lo, lead),
        "climatology": invert.climatology_curve(years, anom, test_lo, lead),
    }
    return out


def main():
    years, anom = invert.load_anomalies()
    result = {
        "data": {
            "source": "NASA GISTEMP v4 ZonAnn.Ts+dSST.csv",
            "url": "https://data.giss.nasa.gov/gistemp/tabledata_v4/ZonAnn.Ts+dSST.csv",
            "raw_sha256": sha256(RAW),
            "bands": ebm.BAND_NAMES,
            "years": [int(years[0]), int(years[-1])],
        },
        "model": {
            "equation": "C dT/dt = d/dx[(1-x^2) D dT/dx] - lambda T",
            "state": "距平：纬度带温度 - 全球面积加权均值",
            "parameters": ["kd = D/C", "kl = lambda/C"],
            "discretization": "有限体积（9 个带边界），隐式欧拉，dt = 1 年",
        },
        "splits": {},
    }
    for train_lo, train_hi, test_lo, test_hi, label in SPLITS:
        result["splits"][label] = run_split(years, anom, train_lo, train_hi, test_lo, test_hi)

    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print("已写出 sim/results.json")
    main_split = result["splits"]["主划分"]
    print("主划分 训练 %s 留出 %s" % (main_split["train"], main_split["test"]))
    print("%-10s %10s %10s %12s %10s" % ("边界", "kd(LS)", "kl(LS)", "PDE残差", "可用?"))
    for bc, v in main_split["boundaries"].items():
        print("%-10s %10.4f %10.4f %12.4f %10s" % (bc, v["ls"]["kd"], v["ls"]["kl"],
              v["ls"]["residual_rmse"], "是" if v["admissible"] else "否"))
    return 0


if __name__ == "__main__":
    sys.exit(main())