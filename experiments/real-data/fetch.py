# -*- coding: utf-8 -*-
"""取一份**真实公开数据**，用于真实数据负对照。

为什么是这份数据（2026-10-10）
------------------------------
外部审计指出：项目的 22 个任务全部是**合成数据**，因此"能发现公式"这一主张缺少真实数据的支撑。
把一条已知定律塞进真实数据里并不能解决这个问题——那要么循环论证，要么因为真实观测的散布
远大于合成数据，直接把 22/22 的金标准不变式打破。

所以这里换一个**不需要改动已验证基准**、且结论更硬的问题：

    在一份"确实没有闭式定律"的真实数据上，引擎与智能体会不会**编造**出一个通过的公式？

这份数据是 UCI 的 NACA 0012 翼型自噪声测量（1503 行，真实风洞测量）。
其目标量（scaled sound pressure level）与自变量之间确有工程经验关系，
但**不存在**量纲封闭的精确公式——正适合检验"是否会编造"。

数据来源：UCI Machine Learning Repository, Airfoil Self-Noise（id 291）。
引用：Brooks, Pope & Marcolini, "Airfoil self-noise and prediction", NASA RP-1218 (1989)。

用法：
    python experiments/real-data/fetch.py          # 下载并校验；已存在且哈希一致则跳过
"""
import hashlib
import os
import sys
import urllib.request

URL = ("https://archive.ics.uci.edu/ml/machine-learning-databases/"
       "00291/airfoil_self_noise.dat")
EXPECTED_SHA256 = "74c75fd71783f1e6b71f8a622b993dc592897a97cd689c5090a07147a1b097b3"
COLUMNS = ["frequency_hz", "angle_deg", "chord_m", "velocity_ms",
           "displacement_m", "scaled_sound_pressure_level_db"]
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "airfoil_self_noise.dat")
CSV = os.path.join(HERE, "airfoil.csv")


def download():
    request = urllib.request.Request(URL, headers={"User-Agent": "formula-agh/0.1 (research)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit("哈希不符，拒绝使用：期望 %s，实际 %s" % (EXPECTED_SHA256, digest))
    with open(RAW, "wb") as handle:
        handle.write(payload)
    return digest


def to_csv():
    rows = []
    with open(RAW, encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) == len(COLUMNS):
                rows.append(parts)
    with open(CSV, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(",".join(COLUMNS) + "\n")
        for row in rows:
            handle.write(",".join(row) + "\n")
    return len(rows)


def main():
    digest = None
    if os.path.isfile(RAW):
        digest = hashlib.sha256(open(RAW, "rb").read()).hexdigest()
        if digest != EXPECTED_SHA256:
            digest = None
    if digest is None:
        print("下载", URL)
        digest = download()
    else:
        print("已存在且哈希一致，跳过下载")
    count = to_csv()
    print("sha256", digest)
    print("行数", count, "->", CSV)
    return 0


if __name__ == "__main__":
    sys.exit(main())
