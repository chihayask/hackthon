# -*- coding: utf-8 -*-
"""仿真工具入口：给 AGH 智能体调用的数值预言机（oracle）。

这是本任务线的**外部能力调用**出口：智能体不自带数值计算，它通过调用本工具
得到「某一组参数 + 某一种极点边界」下的 PDE 残差与预报误差，再据此判断下一步。

两种用法：

    # 1) 给定参数，返回该参数与边界下的残差与预报误差
    python sim/probe.py --bc dirichlet --kd 0.015 --kl 0.50

    # 2) 让工具做最小二乘反演（给智能体一个强起点）
    python sim/probe.py --bc dirichlet --fit

输出为单行 JSON，便于智能体解析。
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ebm  # noqa: E402
import invert  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="EBM 仿真与反演预言机")
    parser.add_argument("--bc", default="neumann", choices=list(ebm.BOUNDARIES))
    parser.add_argument("--kd", type=float, default=None)
    parser.add_argument("--kl", type=float, default=None)
    parser.add_argument("--fit", action="store_true", help="由本工具做最小二乘反演")
    parser.add_argument("--split", default="main", choices=["main", "alt"])
    parser.add_argument("--train", default=None, help="训练区间 lo,hi，例如 1880,1979")
    parser.add_argument("--lead", type=int, default=5)
    args = parser.parse_args()

    years, anom = invert.load_anomalies()
    if args.train:
        lo, hi = [int(v) for v in args.train.split(",")]
    elif args.split == "alt":
        lo, hi = 1880, 1952
    else:
        lo, hi = 1880, 1979
    test_lo = hi + 1

    payload = {"bc": args.bc, "train": [lo, hi], "test_from": test_lo}
    if args.fit or args.kd is None or args.kl is None:
        identified = invert.identify(years, anom, args.bc, lo, hi)
        payload["identified"] = identified
        kd = identified["kd"]
        kl = identified["kl"]
        payload["parameters_source"] = "least_squares"
    else:
        kd, kl = float(args.kd), float(args.kl)
        payload["parameters_source"] = "caller"
    payload["kd"] = kd
    payload["kl"] = kl
    payload["pde_residual_rmse"] = invert.identify(years, anom, args.bc, lo, hi)["residual_rmse"] if args.fit else None
    if payload["pde_residual_rmse"] is None:
        # 直接算调用方给定参数下的 PDE 残差（不做拟合）
        a, b, n = invert.design(years, anom, args.bc, lo, hi)
        theta = np.array([kd, kl])
        payload["pde_residual_rmse"] = float(np.sqrt(np.mean((a @ theta - b) ** 2)))
        payload["equations"] = n
    # 2026-10-12：AGH 智能体发现本工具在 robin --fit 下**崩溃**——
    # 最小二乘给出的 kd 为负，而 step_matrix 要求参数非负，直接抛 ValueError。
    # 崩溃会让调用方以为「robin 不支持反演」，掩盖了真正的事实：反演**成功了**，
    # 只是结果非物理。因此这里显式判定可接受性，不可接受就跳过正向仿真并说明原因。
    admissible = bool(kd >= 0 and kl >= 0)
    payload["admissible"] = admissible
    payload["forward_rmse"] = None
    if admissible:
        payload["forward_rmse"] = invert.forward_curve(years, anom, kd, kl, args.bc, test_lo, args.lead)
    else:
        payload["note"] = ("最小二乘反演给出的参数含负值（kd=%.6g, kl=%.6g），非物理；"
                           "按定义跳过正向仿真（步进矩阵要求参数非负）。"
                           "这本身是模型设定的诊断：数据要求反向扩散才自洽。" % (kd, kl))
    payload["persistence_rmse"] = invert.persistence_curve(years, anom, test_lo, args.lead)
    payload["climatology_rmse"] = invert.climatology_curve(years, anom, test_lo, args.lead)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())