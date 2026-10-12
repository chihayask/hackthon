# -*- coding: utf-8 -*-
"""EBM 参数反演与评估：一步预测协议 + 按年份划分 + 基线对照。

评估协议（为什么是一步预测）
----------------------------
状态是**距平** T_i(t) = 纬度带温度 − 全球面积加权均值。任务定义为：

    给定 t 年的距平场，预测 t+1 年的距平场

这样有三点好处：①不需要外强迫序列（减均值已消去一阶响应）；
②每一年都产生一个独立样本，146 年得到 145 个预测；③与持久基线可比。

划分：训练 1880—1979，留出 1980—2025（**按时间切**，不是在样本里随机抽）。

参照物：
* 持久（persistence）：预测 t+1 = t 年的值；
* 零距平（climatology）：预测 t+1 为该时刻的距平均值 0。
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ebm  # noqa: E402

TRAIN = (1880, 1979)
HOLDOUT = (1980, 2025)


def load_anomalies(path=None):
    years, bands = ebm.load_bands(path)
    return years, ebm.anomalies(bands)


def predict(anom, kd, kl, bc):
    """对每个 t 给出一张 t+1 的预测图，返回预测矩阵 [n-1, 8]。"""
    a = ebm.step_matrix(kd, kl, bc)
    preds = anom[:-1] @ a.T
    if bc == "dirichlet":
        preds[:, 0] = anom[:-1, 0]
        preds[:, -1] = anom[:-1, -1]
    return preds


def score(years, anom, kd, kl, bc, lo, hi):
    """某年区间的一步预测 RMSE（对所有带、所有年取平方平均）。"""
    preds = predict(anom, kd, kl, bc)
    truth = anom[1:]
    y = years[:-1]
    sel = (y >= lo) & (y <= hi)
    if not sel.any():
        return float("nan"), 0
    diff = preds[sel] - truth[sel]
    return float(np.sqrt(np.mean(diff ** 2))), int(sel.sum())


def baseline_persistence(years, anom, lo, hi):
    truth = anom[1:]
    preds = anom[:-1]
    y = years[:-1]
    sel = (y >= lo) & (y <= hi)
    diff = preds[sel] - truth[sel]
    return float(np.sqrt(np.mean(diff ** 2)))


def baseline_climatology(years, anom, lo, hi):
    truth = anom[1:]
    y = years[:-1]
    sel = (y >= lo) & (y <= hi)
    return float(np.sqrt(np.mean(truth[sel] ** 2)))


def fit(years, anom, bc, lo, hi, kd_max=2.0, kl_max=1.0, n_kd=41, n_kl=41):
    """格点搜索 (kd, kl) 最小化训练区间的一步预测 RMSE，再局部加密三轮。"""
    best = (None, None, float("inf"))
    for kd in np.linspace(0.0, kd_max, n_kd):
        for kl in np.linspace(0.0, kl_max, n_kl):
            value, _ = score(years, anom, float(kd), float(kl), bc, lo, hi)
            if value < best[2]:
                best = (float(kd), float(kl), value)
    kd0, kl0, _ = best
    step_kd = kd_max / (n_kd - 1)
    step_kl = kl_max / (n_kl - 1)
    for _ in range(3):
        step_kd /= 3.0
        step_kl /= 3.0
        for dk in (-step_kd, 0.0, step_kd):
            for dl in (-step_kl, 0.0, step_kl):
                kd = min(max(kd0 + dk, 0.0), kd_max)
                kl = min(max(kl0 + dl, 0.0), kl_max)
                value, _ = score(years, anom, kd, kl, bc, lo, hi)
                if value < best[2]:
                    best = (kd, kl, value)
                    kd0, kl0 = kd, kl
    return best


def summarize(path=None):
    """跑完三种边界条件的反演与对照，返回结果字典。"""
    years, anom = load_anomalies(path)
    out = {"train_window": list(TRAIN), "holdout_window": list(HOLDOUT),
           "years": [int(years[0]), int(years[-1])], "boundaries": {}}
    for bc in ebm.BOUNDARIES:
        kd, kl, train_rmse = fit(years, anom, bc, TRAIN[0], TRAIN[1])
        hold_rmse, n_hold = score(years, anom, kd, kl, bc, HOLDOUT[0], HOLDOUT[1])
        out["boundaries"][bc] = {
            "kd": kd, "kl": kl,
            "train_rmse": train_rmse, "train_n": TRAIN[1] - TRAIN[0],
            "holdout_rmse": hold_rmse, "holdout_n": n_hold,
            "relax_years": (1.0 / kl) if kl > 0 else None,
        }
    out["baselines"] = {
        "persistence_train": baseline_persistence(years, anom, TRAIN[0], TRAIN[1]),
        "persistence_holdout": baseline_persistence(years, anom, HOLDOUT[0], HOLDOUT[1]),
        "climatology_train": baseline_climatology(years, anom, TRAIN[0], TRAIN[1]),
        "climatology_holdout": baseline_climatology(years, anom, HOLDOUT[0], HOLDOUT[1]),
    }
    return out

def design(years, anom, bc, lo, hi):
    """PDE 反演的设计矩阵：dT/dt = kd*(L T) - kl*T。"""
    lap = ebm.laplacian(bc)
    y = years[:-1]
    sel = (y >= lo) & (y <= hi)
    t0 = anom[:-1][sel]
    t1 = anom[1:][sel]
    lhs = (t1 - t0)  # dt = 1 年
    rhs_lap = t0 @ lap.T
    # 每个 (年, 纬度带) 是一个方程，未知量只有 (kd, kl) 两个：
    #   (dT)_j = kd * (Lap T)_j + kl * (-T_j)
    a = np.stack([rhs_lap.reshape(-1), (-t0).reshape(-1)], axis=1)
    b = lhs.reshape(-1)
    if bc == "dirichlet":
        # 极点带是被**规定**的边界，不是被预测的未知量：
        # 若把它们也放进最小二乘，等于强迫极点的 dT 由内部算子解释，
        # 而实际上那些行是人为约束。这里把极点带对应的方程剔除。
        keep = np.ones((t0.shape[0], t0.shape[1]), dtype=bool)
        keep[:, 0] = False
        keep[:, -1] = False
        a = a[keep.reshape(-1)]
        b = b[keep.reshape(-1)]
    return a, b, int(sel.sum())


def identify(years, anom, bc, lo, hi):
    """最小二乘反演 (kd, kl)：闭式解，两个参数同时辨识。

    对离散 PDE 的残差做线性最小二乘：
        (T(t+1) - T(t)) ~= kd * (Lap T)(t) - kl * T(t)
    未知量只有 (kd, kl)，是 2 列线性问题，用 lstsq 直接解，
    因此不存在「格点搜索会不会漏掉最优」的问题。
    """
    a, b, n = design(years, anom, bc, lo, hi)
    theta, *_ = np.linalg.lstsq(a, b, rcond=None)
    kd, kl = float(theta[0]), float(theta[1])
    resid = a @ theta - b
    return {"kd": kd, "kl": kl, "years": n,
            "residual_rmse": float(np.sqrt(np.mean(resid ** 2)))}


def forward_curve(years, anom, kd, kl, bc, start_year, lead_max):
    """从 start_year 起正向仿真的误差随预报时效曲线（对所有起报年取平均）。"""
    idx0 = int(np.where(years == start_year)[0][0])
    a = ebm.step_matrix(kd, kl, bc)
    curves = []
    for lead in range(1, lead_max + 1):
        errs = []
        for start in range(idx0, len(years) - lead):
            state = anom[start].copy()
            for _ in range(lead):
                state = a @ state
                if bc == "dirichlet":
                    state[0], state[-1] = anom[start][0], anom[start][-1]
            errs.append(state - anom[start + lead])
        if errs:
            curves.append(float(np.sqrt(np.mean(np.asarray(errs) ** 2))))
    return curves


def persistence_curve(years, anom, start_year, lead_max):
    """持久基线在同一协议下的误差曲线。"""
    idx0 = int(np.where(years == start_year)[0][0])
    curves = []
    for lead in range(1, lead_max + 1):
        errs = [anom[start] - anom[start + lead] for start in range(idx0, len(years) - lead)]
        if errs:
            curves.append(float(np.sqrt(np.mean(np.asarray(errs) ** 2))))
    return curves


def climatology_curve(years, anom, start_year, lead_max):
    """零距平基线：预测所有时效都是 0。"""
    idx0 = int(np.where(years == start_year)[0][0])
    curves = []
    for lead in range(1, lead_max + 1):
        errs = [anom[start + lead] for start in range(idx0, len(years) - lead)]
        if errs:
            curves.append(float(np.sqrt(np.mean(np.asarray(errs) ** 2))))
    return curves