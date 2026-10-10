# -*- coding: utf-8 -*-
"""数据契约校验（M2 交付 2/8）：任务目录格式、字段完整性、答案泄漏。

设计立场
--------
"违规任务被拒绝并报错，不静默通过"是本模块唯一的目标。因此：

* 每条问题都带 severity：error 会让命令以非零码退出并阻断流水线；warn 只提示；
* 不做"猜测式修复"——发现 data.csv 列名与 meta.var_names 不一致就报错，不改数据；
* 泄漏扫描扩展到 reference/answer/ground/solution/truth/label/golden/key 九类文件名；
* 交叉校验 reference/ 与 tasks/ 的一一对应，两侧孤儿都报出来；
* 结果可落盘为 JSON（--report），供 M3 写入证据包与说明书。

契约定义文件：config/task.schema.json（供人阅读与第三方核对，非运行时依赖）。
"""
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .units import UNIT_TABLE, UnknownUnit, unit_dimension

# 智能体上下文绝不能出现的文件名模式（红线）
LEAK_PATTERN = re.compile(
    r"(reference|answer|ground[_\-]?truth|ground|solution|truth|label|golden|expected[_\-]?formula)",
    re.I,
)

ALLOWED_LAYERS = ("base", "challenge")
REQUIRED_META_FIELDS = {
    "task_id": str,
    "var_names": list,
    "layer": str,
    "source": (list, str),
}
ENGINE_MIN_SAMPLES = 50      # verify.split_columns 的硬下限
CONTRACT_MIN_SAMPLES = 200   # config/agent.yaml 的 data_audit.min_samples


@dataclass
class Finding:
    task_id: str
    severity: str          # error | warn
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _err(task_id, code, message) -> Finding:
    return Finding(task_id, "error", code, message)


def _warn(task_id, code, message) -> Finding:
    return Finding(task_id, "warn", code, message)


# --------------------------------------------------------------------------
# meta.json
# --------------------------------------------------------------------------

def _check_meta(meta: Mapping[str, object], name: str, findings: List[Finding]) -> List[str]:
    for field, types in REQUIRED_META_FIELDS.items():
        if field not in meta:
            findings.append(_err(name, "MISSING_FIELD", "meta.json 缺少必备字段 " + field))
            continue
        if not isinstance(meta[field], types):
            findings.append(_err(name, "BAD_TYPE", "meta.json 字段 " + field + " 类型应为 "
                                 + str(types) + "，实际为 " + type(meta[field]).__name__))

    task_id = meta.get("task_id")
    if isinstance(task_id, str) and task_id and task_id != name:
        findings.append(_err(name, "TASK_ID_MISMATCH",
                             "meta.task_id=" + task_id + " 与目录名 " + name + " 不一致"))

    var_names = meta.get("var_names")
    var_list: List[str] = []
    if isinstance(var_names, list):
        var_list = [str(v) for v in var_names]
        if not var_list:
            findings.append(_err(name, "BAD_VAR_NAMES", "var_names 为空数组"))
        if len(set(var_list)) != len(var_list):
            findings.append(_err(name, "DUP_VAR", "var_names 含重复项: " + ",".join(var_list)))
        if "y" in var_list:
            findings.append(_err(name, "RESERVED_NAME", "var_names 不得包含目标列名 y"))
        if len(var_list) < 2:
            findings.append(_warn(name, "FEW_VARS",
                                  "只有 " + str(len(var_list)) + " 个自变量，不足以构成发现任务"))

    layer = meta.get("layer")
    if isinstance(layer, str) and layer not in ALLOWED_LAYERS:
        findings.append(_err(name, "BAD_LAYER", "layer 必须是 " + "/".join(ALLOWED_LAYERS)
                             + "，实际为 " + layer))

    source = meta.get("source")
    sources = source if isinstance(source, list) else ([source] if isinstance(source, str) else [])
    if not sources or not all(isinstance(s, str) and s.strip() for s in sources):
        findings.append(_err(name, "EMPTY_SOURCE", "source 必须是非空字符串或字符串数组（可追溯出处）"))
    else:
        for s in sources:
            if not re.match(r"^https?://", str(s).strip()):
                findings.append(_warn(name, "SOURCE_NOT_URL",
                                      "source 不是可点击链接: " + str(s)[:80]))

    # 先取自由参数：units 可能给自由参数声明单位（审计建议），那种键不算"未声明变量"。
    params_raw = meta.get("free_parameters")
    if not isinstance(params_raw, list):
        params_raw = []
    units = meta.get("units")
    if units is not None:
        if not isinstance(units, dict):
            findings.append(_err(name, "BAD_UNITS", "units 必须是对象 {变量: 单位}"))
        else:
            for key, value in units.items():
                declared_params = [str(p) for p in (params_raw or [])
                                   if isinstance(p, str)]
                if (var_list and str(key) not in var_list and str(key) != "y"
                        and str(key) not in declared_params):
                    findings.append(_warn(name, "UNKNOWN_UNIT_KEY",
                                          "units 含未声明变量或自由参数 " + str(key)))
                try:
                    unit_dimension(str(value))
                except UnknownUnit:
                    findings.append(_warn(name, "UNKNOWN_UNIT",
                                          "单位表未收录 " + str(key) + "=" + str(value)
                                          + "，量纲检验将跳过该任务"))
            if "y" not in units:
                findings.append(_warn(name, "MISSING_Y_UNIT",
                                      "units 未给出 y 的单位，量纲严格比对不可用"))

    params = meta.get("free_parameters")
    if params is not None:
        if not isinstance(params, list) or not all(isinstance(p, str) for p in params):
            findings.append(_err(name, "BAD_PARAMS", "free_parameters 必须是字符串数组"))
        else:
            collide = sorted(set(params) & set(var_list))
            if collide:
                findings.append(_err(name, "PARAM_COLLISION",
                                     "自由参数与自变量同名: " + ",".join(collide)))
            if len(set(params)) != len(params):
                findings.append(_err(name, "DUP_PARAM", "free_parameters 含重复项"))

    sampling = meta.get("sampling")
    if sampling is not None:
        if not isinstance(sampling, dict):
            findings.append(_err(name, "BAD_SAMPLING", "sampling 必须是对象 {变量: [lo, hi]}"))
        else:
            for key, value in sampling.items():
                if var_list and str(key) not in var_list:
                    findings.append(_err(name, "SAMPLING_UNKNOWN_VAR",
                                         "sampling 含未声明变量 " + str(key)))
                    continue
                if (not isinstance(value, (list, tuple)) or len(value) != 2
                        or not all(isinstance(v, (int, float)) for v in value)):
                    findings.append(_err(name, "SAMPLING_RANGE",
                                         "sampling." + str(key) + " 必须是 [lo, hi] 数值对"))
                elif not float(value[0]) < float(value[1]):
                    findings.append(_err(name, "SAMPLING_RANGE",
                                         "sampling." + str(key) + " 不满足 lo < hi"))
    return var_list


# --------------------------------------------------------------------------
# data.csv
# --------------------------------------------------------------------------

def _check_csv(task_dir: str, name: str, var_list: Sequence[str],
               meta: Mapping[str, object], findings: List[Finding]) -> int:
    csv_path = os.path.join(task_dir, "data.csv")
    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            findings.append(_err(name, "EMPTY_CSV", "data.csv 为空文件"))
            return 0
        header = [c.strip() for c in header]
        if len(set(header)) != len(header):
            findings.append(_err(name, "CSV_DUP_COL", "data.csv 表头含重复列名"))
        if "y" not in header:
            findings.append(_err(name, "CSV_MISSING_Y", "data.csv 缺少目标列 y"))
        for var in var_list:
            if var not in header:
                findings.append(_err(name, "CSV_MISSING_COL", "data.csv 缺少列 " + var))

        bad_cells: List[str] = []
        nonfinite: List[str] = []
        rows = 0
        values: Dict[str, List[float]] = {c: [] for c in header}
        for lineno, row in enumerate(reader, start=2):
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) != len(header):
                findings.append(_err(name, "CSV_RAGGED",
                                     "第 %d 行列数 %d 与表头 %d 不一致"
                                     % (lineno, len(row), len(header))))
                continue
            rows += 1
            for col, cell in zip(header, row):
                text = cell.strip()
                if text == "":
                    if len(bad_cells) < 5:
                        bad_cells.append("r%d/%s 空值" % (lineno, col))
                    continue
                try:
                    value = float(text)
                except ValueError:
                    if len(bad_cells) < 5:
                        bad_cells.append("r%d/%s=%s" % (lineno, col, text[:20]))
                    continue
                if value != value or value in (float("inf"), float("-inf")):
                    if len(nonfinite) < 5:
                        nonfinite.append("r%d/%s" % (lineno, col))
                    continue
                values[col].append(value)

    if bad_cells:
        findings.append(_err(name, "CSV_NON_NUMERIC",
                             "data.csv 存在非数值/空单元格: " + "; ".join(bad_cells)))
    if nonfinite:
        findings.append(_err(name, "CSV_NONFINITE",
                             "data.csv 存在 NaN/Inf: " + "; ".join(nonfinite)))

    if rows < ENGINE_MIN_SAMPLES:
        findings.append(_err(name, "CSV_TOO_FEW",
                             "样本量 %d 低于验证引擎硬下限 %d" % (rows, ENGINE_MIN_SAMPLES)))
    elif rows < CONTRACT_MIN_SAMPLES:
        findings.append(_warn(name, "CSV_BELOW_MIN",
                              "样本量 %d 低于 config/agent.yaml 声明的下限 %d"
                              % (rows, CONTRACT_MIN_SAMPLES)))

    declared = meta.get("sample_count")
    if isinstance(declared, int) and declared != rows:
        findings.append(_err(name, "SAMPLE_COUNT_MISMATCH",
                             "meta.sample_count=%d 与 data.csv 实际行数 %d 不一致"
                             % (declared, rows)))

    for col, vals in values.items():
        if len(vals) < 2:
            continue
        lo, hi = min(vals), max(vals)
        if hi == lo:
            findings.append(_err(name, "CONSTANT_COL",
                                 "列 " + col + " 为常量（值=%r），拟合与检验均无意义" % lo))

    sampling = meta.get("sampling")
    if isinstance(sampling, dict):
        for key, rng in sampling.items():
            if key in values and isinstance(rng, (list, tuple)) and len(rng) == 2:
                lo, hi = min(values[key]), max(values[key])
                if lo < float(rng[0]) - 1e-9 or hi > float(rng[1]) + 1e-9:
                    findings.append(_warn(name, "SAMPLING_MISMATCH",
                                          "列 " + str(key) + " 实测范围 [%.6g, %.6g] 超出 meta 声明 [%s, %s]"
                                          % (lo, hi, rng[0], rng[1])))
    return rows


# --------------------------------------------------------------------------
# 泄漏与交叉引用
# --------------------------------------------------------------------------

def _check_leakage(task_dir: str, name: str, findings: List[Finding]) -> None:
    for entry in sorted(os.listdir(task_dir)):
        if entry in ("data.csv", "meta.json", "split.json", "data_train.csv",
                     "candidates.json", "README.md"):
            continue
        if LEAK_PATTERN.search(entry):
            findings.append(_err(name, "LEAK_FILE",
                                 "任务目录出现疑似标准答案文件 " + entry
                                 + "（必须移出 tasks/，否则会进入智能体上下文）"))


def validate_task(task_dir: str, name: Optional[str] = None,
                  require_split: bool = False) -> List[Finding]:
    name = name or os.path.basename(os.path.normpath(task_dir))
    findings: List[Finding] = []
    meta_path = os.path.join(task_dir, "meta.json")
    csv_path = os.path.join(task_dir, "data.csv")
    if not os.path.exists(meta_path):
        findings.append(_err(name, "MISSING_META", "缺少 meta.json"))
    if not os.path.exists(csv_path):
        findings.append(_err(name, "MISSING_CSV", "缺少 data.csv"))
    if findings:
        return findings

    try:
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    except json.JSONDecodeError as exc:
        findings.append(_err(name, "BAD_JSON", "meta.json 不是合法 JSON: " + str(exc)))
        return findings
    if not isinstance(meta, dict):
        findings.append(_err(name, "BAD_JSON", "meta.json 顶层必须是对象"))
        return findings

    var_list = _check_meta(meta, name, findings)
    _check_csv(task_dir, name, var_list, meta, findings)
    _check_leakage(task_dir, name, findings)

    if require_split and not os.path.exists(os.path.join(task_dir, "split.json")):
        findings.append(_err(name, "SPLIT_MISSING", "缺少 split.json（先运行 formula_agh split）"))
    return findings


def validate_taskset(tasks_root: str,
                     reference_root: Optional[str] = None,
                     require_split: bool = False,
                     sealed_root: Optional[str] = None) -> Dict[str, object]:
    """校验整个任务集，并交叉核对 reference/ 与 sealed/ 的一致性。"""
    findings: List[Finding] = []
    tasks: List[str] = []
    if not os.path.isdir(tasks_root):
        findings.append(_err("<taskset>", "MISSING_TASKS_ROOT", "任务根目录不存在: " + tasks_root))
        return _summarize(tasks_root, tasks, findings)

    for entry in sorted(os.listdir(tasks_root)):
        task_dir = os.path.join(tasks_root, entry)
        if not os.path.isdir(task_dir):
            continue
        tasks.append(entry)
        findings.extend(validate_task(task_dir, entry, require_split))

    if not tasks:
        findings.append(_err("<taskset>", "NO_TASKS", "任务根目录下没有任何任务子目录"))

    # 任务 id 重复（大小写不敏感，Windows 上尤其危险）
    lowered: Dict[str, int] = {}
    for t in tasks:
        lowered[t.lower()] = lowered.get(t.lower(), 0) + 1
    for key, count in sorted(lowered.items()):
        if count > 1:
            findings.append(_err("<taskset>", "DUP_TASK_ID",
                                 "任务 id 大小写不敏感重复: " + key + " x" + str(count)))

    if reference_root and os.path.isdir(reference_root):
        refs = {os.path.splitext(f)[0] for f in os.listdir(reference_root)
                if f.endswith(".json")}
        for task in tasks:
            if task not in refs:
                findings.append(_err(task, "MISSING_REFERENCE",
                                     "reference/ 缺少 " + task + ".json，无法与标准答案对照"))
        for ref in sorted(refs - set(tasks)):
            findings.append(_err(ref, "ORPHAN_REFERENCE",
                                 "reference/" + ref + ".json 没有对应任务目录"))
    elif reference_root:
        findings.append(_err("<taskset>", "MISSING_REFERENCE_ROOT",
                             "reference 根目录不存在: " + reference_root))

    if sealed_root is not None:
        missing = [t for t in tasks
                   if not os.path.exists(os.path.join(sealed_root, t, "manifest.json"))]
        for task in missing:
            findings.append(_warn(task, "SEALED_MISSING",
                                  "sealed/" + task + "/ 未生成（先运行 formula_agh split --seal）"))
    return _summarize(tasks_root, tasks, findings)


def _summarize(root: str, tasks: Sequence[str], findings: Sequence[Finding]) -> Dict[str, object]:
    errors = [f for f in findings if f.severity == "error"]
    warns = [f for f in findings if f.severity == "warn"]
    by_code: Dict[str, int] = {}
    for f in findings:
        by_code[f.code] = by_code.get(f.code, 0) + 1
    return {
        "tasks_root": os.path.abspath(root).replace(os.sep, "/"),
        "checked": len(tasks),
        "tasks": list(tasks),
        "errors": len(errors),
        "warnings": len(warns),
        "ok": not errors,
        "by_code": by_code,
        "findings": [f.to_dict() for f in findings],
    }
