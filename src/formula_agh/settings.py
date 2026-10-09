# -*- coding: utf-8 -*-
"""阈值与运行参数的唯一来源（M2 交付 3/8 的一部分）。

为什么需要这个模块（这是本次工程审查发现的一个真实缺陷）
--------------------------------------------------------
改造前：

* cli.cmd_verify   用 holdout_threshold=0.05（argparse 默认值）
* cli.cmd_batch    直接调用 verify_formula()，用的是 0.08（函数默认值）

也就是说同一个公式，走 verify 与走 batch 会得到**不同判定**，而证据包里
没有任何地方记录当时用的是哪组阈值——复现时无法解释差异。这违反本项目的
根本纪律（"阈值统一在 config/agent.yaml"，见 AGH Skill 硬约束第 6 条）。

改造后：所有入口都从 config/agent.yaml 读取同一组阈值，并把实际生效的
参数写进证据（run.json.verify_settings），任何一次运行都可被独立复算。

依赖说明：不引入 pyyaml（本机不可安装），自带一个受限 YAML 子集解析器，
覆盖 config/agent.yaml 实际用到的语法（嵌套映射、标量、内联列表、注释）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Mapping, Optional

DEFAULTS: Dict[str, Any] = {
    "run": {
        "max_rounds": 6,
        "max_rejected_before_restart": 3,
        "timeout_per_tool_sec": 120,
        "seed": 20261008,
    },
    "verify": {
        "holdout_ratio": 0.2,
        "holdout_error_threshold": 0.05,
        "extrapolation_ratio": 0.15,
        "extrapolation_error_threshold": 0.15,
        "dimension_check": True,
        "scale_check": True,
        "max_fit_residual": 0.5,
    },
    "data_audit": {
        "missing_ratio_warn": 0.02,
        "outlier_sigma": 4,
        "min_samples": 200,
    },
    "limits": {
        "max_variables": 5,
    },
}


# --------------------------------------------------------------------------
# 受限 YAML 子集解析器
# --------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    out: List[str] = []
    quote: Optional[str] = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text: str) -> Any:
    text = text.strip()
    if text == "":
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in inner.split(",")]
    low = text.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~"):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def parse_yaml_subset(text: str) -> Dict[str, Any]:
    """解析 config/agent.yaml 用到的 YAML 子集：嵌套映射 + 标量 + 内联列表。

    不支持锚点、多行字符串、块序列——用到了会显式报错，绝不静默错读。
    """
    root: Dict[str, Any] = {}
    stack: List[Any] = [(-1, root)]
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if line.lstrip().startswith("- "):
            raise ValueError("config/agent.yaml 第 %d 行使用了块序列，本解析器不支持" % lineno)
        if "\t" in line[:len(line) - len(line.lstrip())]:
            raise ValueError("config/agent.yaml 第 %d 行用了制表符缩进" % lineno)
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if ":" not in body:
            raise ValueError("config/agent.yaml 第 %d 行不是 key: value 形式" % lineno)
        key, _, value = body.partition(":")
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError("config/agent.yaml 第 %d 行缩进异常" % lineno)
        parent = stack[-1][1]
        if value == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value)
    return root


# --------------------------------------------------------------------------
# 装载与合并
# --------------------------------------------------------------------------

def _deep_merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _deep_merge(dict(out[key]), value)
        else:
            out[key] = value
    return out


def default_config_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.join(root, "config", "agent.yaml")


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """读取 config/agent.yaml 并与内置默认值合并；文件缺失时退回默认值。"""
    config_path = path or default_config_path()
    if not os.path.exists(config_path):
        return json.loads(json.dumps(DEFAULTS))
    with open(config_path, encoding="utf-8") as fh:
        loaded = parse_yaml_subset(fh.read())
    if not isinstance(loaded, dict):
        raise ValueError("config/agent.yaml 顶层必须是映射")
    return _deep_merge(DEFAULTS, loaded)


def verify_settings(config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """返回三重验证真正生效的参数（写进证据包，供独立复算）。"""
    cfg = dict(config or load_config())
    run = dict(cfg.get("run") or {})
    verify = dict(cfg.get("verify") or {})
    return {
        "holdout_ratio": float(verify.get("holdout_ratio", 0.2)),
        "holdout_threshold": float(verify.get("holdout_error_threshold", 0.05)),
        "extrapolation_ratio": float(verify.get("extrapolation_ratio", 0.15)),
        "extrapolation_threshold": float(verify.get("extrapolation_error_threshold", 0.15)),
        "dimension_check": bool(verify.get("dimension_check", True)),
        "scale_check": bool(verify.get("scale_check", True)),
        "fit_max_residual": float(verify.get("max_fit_residual", 0.5)),
        "seed": int(run.get("seed", 20261008)),
    }
