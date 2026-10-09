# -*- coding: utf-8 -*-
"""数据划分（M2 交付 1/8）：训练 / 留出 / 外推三段的唯一实现与落盘规范。

职责边界
--------
* 本模块是"三段划分"的唯一落盘出口；实际切分算法复用 verify.split_columns，
  不复制第二份实现，避免"验证脚本的划分"与"归档的划分"漂移。
* 落盘的 tasks/<task_id>/split.json 只含规则、计数、支撑域与指纹，
  不含任何行号索引——这样智能体即便读到它，也无法反推哪些点是留出点。
* 真正被封印的留出集/外推集数据点写到 sealed/<task_id>/*.csv（与 reference/ 同级，
  位于 tasks/ 之外），智能体遍历任务目录时读不到。
* 种子固定，任何人在任何机器上重跑得到同样的指纹；--check 就是这条验收标准。

验收标准（对应分工表 10-08）
---------------------------
"重跑两次划分结果完全一致" —— 由 split.json 中的 SHA256 指纹保证，
并由 tests/test_split.py::test_split_is_bitwise_reproducible 自动校验。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .verify import VerifyError, split_columns

RULE_VERSION = "split-v1"
DEFAULT_SEED = 20261008
DEFAULT_HOLDOUT_RATIO = 0.2
DEFAULT_EXTRAPOLATION_RATIO = 0.15

RULE_TEXT = {
    "extrapolation": "按主自变量（极差最大者）升序排列后，取最小端与最大端各占样本量 7.5% 的点，"
                     "合计 15%，严格位于训练支撑域之外",
    "holdout": "中间区域内均匀随机抽取 20%（种子固定）",
    "train": "其余点；支撑域 [support_lo, support_hi] 只由训练点决定",
    "main_axis": "取值范围极差最大的自变量",
}


class SplitError(ValueError):
    """划分无法建立（样本量不足、数据退化等）。"""


# --------------------------------------------------------------------------
# 指纹
# --------------------------------------------------------------------------

def _rows_digest(columns: Mapping[str, np.ndarray], var_names: Sequence[str],
                 y_name: str, indices: np.ndarray) -> str:
    """对一组数据点做规范化哈希：先按字典序排序行，再拼接精确浮点表示。

    排序保证「同一集合、不同顺序」得到同一指纹；repr(float) 是 Python 的
    最短往返表示，跨机器稳定。
    """
    keys = list(var_names) + [y_name]
    rows: List[Tuple[str, ...]] = []
    for i in indices:
        rows.append(tuple(repr(float(columns[k][i])) for k in keys))
    rows.sort()
    blob = "\n".join(",".join(r) for r in rows)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _mask_digest(columns, var_names, y_name, mask: np.ndarray) -> Dict[str, object]:
    idx = np.nonzero(mask)[0]
    y = np.asarray(columns[y_name], dtype=float)[idx]
    return {
        "sha256": _rows_digest(columns, var_names, y_name, idx),
        "n": int(idx.size),
        "y_min": float(np.min(y)) if idx.size else None,
        "y_max": float(np.max(y)) if idx.size else None,
    }


# --------------------------------------------------------------------------
# 划分
# --------------------------------------------------------------------------

def build_split(columns: Mapping[str, np.ndarray],
                meta: Mapping[str, object],
                holdout_ratio: float = DEFAULT_HOLDOUT_RATIO,
                extrapolation_ratio: float = DEFAULT_EXTRAPOLATION_RATIO,
                seed: int = DEFAULT_SEED,
                task_id: Optional[str] = None) -> Tuple[Dict[str, object], Dict[str, np.ndarray]]:
    """建立三段划分并返回 (manifest, masks)。

    masks 供本进程直接复用；manifest 是可落盘、可分发给队友的划分说明。
    """
    var_names = [str(v) for v in (meta.get("var_names") or [])]
    if not var_names:
        raise SplitError("meta.json 缺少 var_names，无法确定主自变量")
    try:
        masks = split_columns(dict(columns), var_names, "y",
                              holdout_ratio, extrapolation_ratio, seed)
    except VerifyError as exc:
        raise SplitError(str(exc)) from exc

    n = int(np.asarray(columns["y"]).shape[0])
    axis = int(masks["split_axis"])
    support_lo = np.asarray(masks["support_lo"], dtype=float)
    support_hi = np.asarray(masks["support_hi"], dtype=float)

    manifest: Dict[str, object] = {
        "task_id": str(task_id if task_id is not None else meta.get("task_id", "unknown")),
        "rule_version": RULE_VERSION,
        "rule": {
            "main_axis": {
                "index": axis,
                "name": var_names[axis] if axis < len(var_names) else "?",
                "criterion": RULE_TEXT["main_axis"],
            },
            "extrapolation": RULE_TEXT["extrapolation"],
            "holdout": RULE_TEXT["holdout"],
            "train": RULE_TEXT["train"],
            "holdout_ratio": float(holdout_ratio),
            "extrapolation_ratio": float(extrapolation_ratio),
            "seed": int(seed),
        },
        "n_total": n,
        "counts": {
            "train": int(masks["train"].sum()),
            "holdout": int(masks["holdout"].sum()),
            "extrapolation": int(masks["extrapolation"].sum()),
        },
        "support": {
            "var_names": list(var_names),
            "lo": [float(v) for v in support_lo],
            "hi": [float(v) for v in support_hi],
        },
        "fingerprint": {
            "train": _mask_digest(columns, var_names, "y", masks["train"]),
            "holdout": _mask_digest(columns, var_names, "y", masks["holdout"]),
            "extrapolation": _mask_digest(columns, var_names, "y", masks["extrapolation"]),
        },
        "contains_row_indices": False,
        "note": "本文件不含留出集/外推集的行号，只有规则、计数、支撑域与集合指纹；"
                "留出与外推数据点同时被封印到 sealed/<task_id>/，位于 tasks/ 之外。",
    }
    return manifest, masks


def _walk_manifest(node, forbidden, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in forbidden and isinstance(value, list) and value:
                raise SplitError("split.json 出现疑似行号字段 " + path + "/" + str(key))
            _walk_manifest(value, forbidden, path + "/" + str(key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _walk_manifest(value, forbidden, path + "[%d]" % i)


def assert_no_indices(manifest: Mapping[str, object]) -> None:
    """自检：split.json 里绝不能出现行号索引数组（防止把留出集告诉智能体）。"""
    forbidden = ("indices", "index", "idx", "rows", "members", "holdout_idx", "train_idx")
    _walk_manifest(manifest, forbidden)


# --------------------------------------------------------------------------
# 落盘
# --------------------------------------------------------------------------

def split_path(task_dir: str) -> str:
    return os.path.join(task_dir, "split.json")


def write_split(task_dir: str, manifest: Mapping[str, object]) -> str:
    assert_no_indices(manifest)
    path = split_path(task_dir)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def load_split(task_dir: str) -> Optional[Dict[str, object]]:
    path = split_path(task_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _read_header(csv_path: str) -> List[str]:
    with open(csv_path, encoding="utf-8") as fh:
        line = fh.readline().strip()
    return [c.strip() for c in line.split(",")]


def _write_subset(path: str, header: Sequence[str], columns, mask: np.ndarray) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    idx = np.nonzero(mask)[0]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(list(header))
        for i in idx:
            writer.writerow(["%.17g" % float(columns[name][i]) for name in header])


def seal_split(task_dir: str,
               sealed_root: str,
               columns: Mapping[str, np.ndarray],
               masks: Mapping[str, np.ndarray],
               manifest: Mapping[str, object]) -> Dict[str, str]:
    """把三段划分物理分离：

    * tasks/<id>/data_train.csv —— 智能体可见的工作集（只有训练点）；
    * sealed/<id>/holdout.csv / extrapolation.csv —— 位于 tasks/ 之外，
      智能体按目录遍历读不到；评分与独立复算从这里取"未见点"。

    这一步正面回答 M2 怀疑清单第 1 条：留出集不是"口头说没看过"，而是文件系统上分开的。
    """
    task_id = str(manifest["task_id"])
    header = _read_header(os.path.join(task_dir, "data.csv"))
    sealed_dir = os.path.join(sealed_root, task_id)
    os.makedirs(sealed_dir, exist_ok=True)

    train_rel = "tasks/" + task_id + "/data_train.csv"
    sealed_rel = {
        "holdout": "sealed/" + task_id + "/holdout.csv",
        "extrapolation": "sealed/" + task_id + "/extrapolation.csv",
    }
    _write_subset(os.path.join(task_dir, "data_train.csv"), header, columns, masks["train"])
    _write_subset(os.path.join(sealed_dir, "holdout.csv"), header, columns, masks["holdout"])
    _write_subset(os.path.join(sealed_dir, "extrapolation.csv"), header, columns,
                  masks["extrapolation"])

    sealed_manifest = {
        "task_id": task_id,
        "rule_version": manifest["rule_version"],
        "seed": manifest["rule"]["seed"],
        "files": {
            "train": train_rel,
            "holdout": sealed_rel["holdout"],
            "extrapolation": sealed_rel["extrapolation"],
        },
        "counts": dict(manifest["counts"]),
        "fingerprint": dict(manifest["fingerprint"]),
        "access_policy": {
            "train": "智能体可见：AGH 只应读取 data_train.csv（或由验证引擎内部切分 data.csv）",
            "holdout": "智能体不可见：仅验证引擎与评分脚本读取",
            "extrapolation": "智能体不可见：仅验证引擎与评分脚本读取",
        },
    }
    with open(os.path.join(sealed_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(sealed_manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")

    rel = {"train": train_rel}
    rel.update(sealed_rel)
    return rel


def check_split(task_dir: str, columns, meta, holdout_ratio, extrapolation_ratio,
                seed) -> Dict[str, object]:
    """重算划分并与已落盘的 split.json 逐项比对——"重跑两次完全一致"的机器判据。"""
    stored = load_split(task_dir)
    fresh, _masks = build_split(columns, meta, holdout_ratio, extrapolation_ratio, seed)
    if stored is None:
        return {"task_id": fresh["task_id"], "status": "missing",
                "identical": False, "detail": "尚未落盘 split.json"}
    diffs: List[str] = []
    for key in ("counts", "support", "fingerprint"):
        if stored.get(key) != fresh.get(key):
            diffs.append(key)
    if stored.get("rule") != fresh.get("rule"):
        diffs.append("rule")
    return {
        "task_id": fresh["task_id"],
        "status": "ok" if not diffs else "drift",
        "identical": not diffs,
        "differing_fields": diffs,
        "stored_fingerprint": stored.get("fingerprint"),
        "recomputed_fingerprint": fresh.get("fingerprint"),
    }
