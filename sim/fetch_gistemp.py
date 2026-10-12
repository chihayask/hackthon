# -*- coding: utf-8 -*-
"""取公开温度场数据：NASA GISTEMP 纬度带年平均温度异常（真实公开观测）。

为什么这份数据（2026-10-10）
--------------------------
赛题方向是「科学计算与仿真」，示例为「根据公开温度场或流场数据自动反演模型参数，
调用仿真工具复现过程，并对不同边界条件下的预测误差进行比较」。
GISTEMP 的 ZonAnn 表正是**公开温度场**：1880 年至今、按纬度带给出的温度异常，
既有空间结构也有时间演化，适合做「反演参数 → 仿真复现 → 边界条件对比」。

来源：NASA Goddard Institute for Space Studies, GISTEMP v4, ZonAnn.Ts+dSST.csv
      https://data.giss.nasa.gov/gistemp/

用法：python sim/fetch_gistemp.py
"""
import csv
import hashlib
import os
import sys
import urllib.request

URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/ZonAnn.Ts+dSST.csv"
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "ZonAnn.Ts+dSST.csv")
OUT = os.path.join(HERE, "data", "zonal_bands.csv")

# 取 8 个较细的纬度带，作为空间网格（自南向北）
BANDS = ["90S-64S", "64S-44S", "44S-24S", "24S-EQU",
         "EQU-24N", "24N-44N", "44N-64N", "64N-90N"]
# 各带中心纬度（度），用于 x = sin(lat)
CENTERS = [-77.0, -54.0, -34.0, -12.0, 12.0, 34.0, 54.0, 77.0]


def download():
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "formula-agh/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = response.read()
    with open(RAW, "wb") as handle:
        handle.write(payload)
    return payload


def parse(text):
    rows = list(csv.reader(text.splitlines()))
    header = rows[0]
    idx = {name: header.index(name) for name in BANDS}
    out = []
    for row in rows[1:]:
        if not row or not row[0].strip().isdigit():
            continue
        year = int(row[0])
        values = []
        for name in BANDS:
            raw = row[idx[name]].strip()
            if raw in ("", "***"):
                values = None
                break
            values.append(float(raw))
        if values is None:
            continue
        out.append([year] + values)
    return out


def main():
    if os.path.isfile(RAW):
        text = open(RAW, encoding="utf-8", errors="replace").read()
    else:
        text = download().decode("utf-8", errors="replace")
    rows = parse(text)
    if len(rows) < 100:
        raise SystemExit("解析出的行数过少：%d" % len(rows))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("year," + ",".join(BANDS) + "\n")
        for row in rows:
            handle.write("%d," % row[0] + ",".join("%.3f" % v for v in row[1:]) + "\n")
    digest = hashlib.sha256(open(RAW, "rb").read()).hexdigest()
    print("原始文件 sha256:", digest)
    print("年份范围: %d — %d（%d 年）" % (rows[0][0], rows[-1][0], len(rows)))
    print("纬度带:", ", ".join(BANDS))
    print("写出:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())