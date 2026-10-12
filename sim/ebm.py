# -*- coding: utf-8 -*-
"""一维能量平衡模型（EBM）仿真器。

模型（对纬度 x = sin(phi) 的能量平衡）：

    C dT/dt = d/dx[ D dT/dx ] - lambda*T + F(t)

本项目处理**距平**：状态取 T_i = (该纬度带温度异常) - (全球面积加权均值)。
减去全球均值后外强迫 F(t) 的一阶响应被消掉，方程变为齐次，参数才能在无强迫数据下辨识。

    dT/dt = kd * Lap_bc(T) - kl * T ，其中 kd = D/C、kl = lambda/C

两个可辨识参数：kd（扩散速率，1/年）、kl（反馈阻尼，1/年）。

数值：空间用 x = sin(lat) 上的非均匀网格（8 个纬度带），
时间用**隐式欧拉**（无条件稳定，1 年步长）：

    (I - dt*M) T(t+1) = T(t) ，M = kd*Lap - kl*I

极点边界条件三选一（本项目的对照变量）：

* neumann  ：零通量（绝热），极点不交换热量；
* dirichlet：极点温度钉在观测值上（最强约束）；
* robin    ：极点按牛顿冷却与外部交换，系数 h 由 `robin_h` 给出。
"""
import os

import numpy as np

# 8 个纬度带（自南向北）的边界与中心纬度（度）
BAND_EDGES = [(-90.0, -64.0), (-64.0, -44.0), (-44.0, -24.0), (-24.0, 0.0),
              (0.0, 24.0), (24.0, 44.0), (44.0, 64.0), (64.0, 90.0)]
BAND_NAMES = ["90S-64S", "64S-44S", "44S-24S", "24S-EQU",
              "EQU-24N", "24N-44N", "44N-64N", "64N-90N"]
CENTERS_DEG = [-77.0, -54.0, -34.0, -12.0, 12.0, 34.0, 54.0, 77.0]
BOUNDARIES = ("neumann", "dirichlet", "robin")
ROBIN_H = 1.0  # robin 边界的无量纲交换系数（按网格尺度归一）


def x_grid():
    return np.sin(np.deg2rad(np.asarray(CENTERS_DEG, dtype=float)))


def edges_x():
    """9 个纬度带边界的 x = sin(lat)，自南向北。有限体积单元用它，不用带中心的中点。"""
    lats = [low for low, _ in BAND_EDGES] + [BAND_EDGES[-1][1]]
    return np.sin(np.deg2rad(np.asarray(lats, dtype=float)))


def area_weights():
    """每带的面积权重 = sin(上边界) - sin(下边界)，即 x 方向上的单元宽度。"""
    w = np.diff(edges_x())
    return w / w.sum()


def laplacian(bc="neumann", robin_h=ROBIN_H):
    """经典 EBM 的扩散算子（North 1975 度量形式），非均匀网格有限体积离散。

        L T = d/dx[ g(x) dT/dx ] ,  g(x) = 1 - x^2 ,  x = sin(lat)

    九个面（0..8）在 edges_x() 处；面的度量系数 g 在极点恰为 0，
    所以**球面自带的极面零通量**是内建的（neumann）。

    关于极点边界的物理地位（必须说清）：
    球面上 x=±1 是**坐标奇点而不是真实边界**，g→0 使通量天然为零。
    因此这里比较的 robin / dirichlet 是在问一个敏感性问题是——
    「若人为规定极点与外部的交换方式，反演出的参数与预报误差会变多少」，
    而不是在解一个两端有真实物理边界的问题。文档中如实标注。
    """
    if bc not in BOUNDARIES:
        raise ValueError("未知边界条件: %s" % bc)
    x = x_grid()
    n = x.size
    ex = edges_x()
    widths = np.diff(ex)
    g_face = 1.0 - ex ** 2  # 9 个面的度量系数；两端恰为 0
    if bc == "robin":
        g_face[0] = robin_h
        g_face[-1] = robin_h
    lap = np.zeros((n, n), dtype=float)
    for i in range(n):
        # 上侧（+x 方向）的面：i<n-1 时是内部面，否则是北极面
        face = i + 1
        if i < n - 1:
            d = x[i + 1] - x[i]
            c = g_face[face] / (d * widths[i])
            lap[i, i + 1] += c
        else:
            d = 1.0 - x[i]  # 单元中心到极点
            c = g_face[face] / (d * widths[i])
        lap[i, i] -= c
        # 下侧（-x 方向）的面：i>0 时是内部面，否则是南极面
        face = i
        if i > 0:
            d = x[i] - x[i - 1]
            c = g_face[face] / (d * widths[i])
            lap[i, i - 1] += c
        else:
            d = x[i] - (-1.0)
            c = g_face[face] / (d * widths[i])
        lap[i, i] -= c
    return lap

def step_matrix(kd, kl, bc="neumann", dt=1.0, robin_h=ROBIN_H):
    """隐式欧拉：返回 A，使 T(t+1) = A @ T(t)（neumann 边界）。"""
    if kd < 0 or kl < 0:
        raise ValueError("参数必须非负")
    m = kd * laplacian(bc, robin_h) - kl * np.eye(len(CENTERS_DEG))
    return np.linalg.inv(np.eye(m.shape[0]) - dt * m)


def advance(state, kd, kl, bc="neumann", steps=1, dt=1.0, robin_h=ROBIN_H):
    """推进若干年。dirichlet 下极点保持在初始值（相当于固定外部温度）。"""
    a = step_matrix(kd, kl, bc, dt, robin_h)
    out = np.asarray(state, dtype=float).copy()
    for _ in range(int(steps)):
        nxt = a @ out
        if bc == "dirichlet":
            nxt[0], nxt[-1] = state[0], state[-1]
        out = nxt
    return out


def anomalies(bands):
    """把纬度带温度转成距平：减去全球面积加权均值。"""
    arr = np.asarray(bands, dtype=float)
    w = area_weights()
    if arr.ndim == 1:
        return arr - float(np.dot(w, arr))
    return arr - (arr @ w)[:, None]


def load_bands(path=None):
    """读 zonal_bands.csv，返回 (years, bands[N,8])。"""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "zonal_bands.csv")
    with open(path, encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
        years, rows = [], []
        for line in handle:
            parts = line.strip().split(",")
            if len(parts) != len(header):
                continue
            years.append(int(parts[0]))
            rows.append([float(v) for v in parts[1:]])
    return np.asarray(years), np.asarray(rows, dtype=float)