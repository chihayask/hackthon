# -*- coding: utf-8 -*-
    # 证据包生成：把一次验证落成可归档、可复核的目录。

# 对应赛事要求的"运行与验证证据"。原则：

# * 只记录事实（公式、指标、判定、理由），不做任何美化；
# * 判定为 rejected 的结果同样归档——失败案例本身就是评分项；
# * 每条证据带时间戳与 SHA256，方便第三方核对未被篡改。
# #
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import __version__
from .settings import verify_settings
from .verify import VerifyReport


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def environment_snapshot() -> Mapping[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# 假设来源词表。存在的理由：赛事要求"证明全程零人工干预"，
# 而证据包里同时躺着三类完全不同的运行——
#   * 模型真的自己提的假设（agh-llm）
#   * 人工写在代码里的假设链（human-authored-fixture，演示用）
#   * 标准答案或人为构造的错误式（reference / fixture-*）
# 如果不在证据里区分，评审无法判断哪一条能支持"自主发现"这句话。
# 因此 write_evidence 强制记录来源；评分脚本只把 agh-llm 计入"智能体发现"层。
HYPOTHESIS_SOURCES = {
    "agh-llm": "假设由 Agnes 模型经 AGH 命令工具提出（可用于支撑自主闭环）",
    "agnes-api-direct": ("假设由 Agnes 模型经 HTTP API 直接提出，运行底座不是 AGH"
                         "（AGH 未构建）。可用来证明模型能提出并自我否定，"
                         "但不得用来声称在 AGH 上完成了自主闭环）"),
    "cli": "公式由人在命令行给出",
    "reference": "标准答案原样送回引擎（金标准自检）",
    "fixture-variant": "人为构造的结构错误候选式（判别力测试）",
    "fixture-experiment": "受控实验装置（负对照 / 窄域外推 / 量纲验收）",
    "human-authored-fixture": "假设由人工编写的策略表给出（演示用，不是自主发现）",
    "unclassified": "未标注来源——不计入任何能力声明，需补齐",
}


def write_evidence(run_dir: str,
                   report: VerifyReport,
                   command: str,
                   inputs: Optional[Sequence[str]] = None,
                   notes: str = "",
                   settings_in: Optional[Mapping[str, object]] = None,
                   hypothesis_source: str = "unclassified") -> str:
    # 把一次验证写入 runs/<run_id>/，返回 run_dir。
    os.makedirs(run_dir, exist_ok=True)
    checks_dir = os.path.join(run_dir, "checks")
    figures_dir = os.path.join(run_dir, "figures")
    os.makedirs(checks_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as fh:
        fh.write(report.to_json())

    with open(os.path.join(run_dir, "command.txt"), "w", encoding="utf-8") as fh:
        fh.write(command.rstrip() + "\n")

    with open(os.path.join(run_dir, "env.json"), "w", encoding="utf-8") as fh:
        json.dump(environment_snapshot(), fh, ensure_ascii=False, indent=2)

    # 重名检验会把 checks/<name>.json 覆盖掉，证据里只剩最后一份，而 result.json 里
    # 还留着两份——两者不一致，独立复算就会报 stale-metrics。这里显式记下来，
    # 让"证据里有两个同名但取值不同的结果"永远不是静默发生的。
    name_counts: Dict[str, int] = {}
    for check in report.checks:
        name_counts[check.name] = name_counts.get(check.name, 0) + 1
    duplicate_names = sorted(name for name, count in name_counts.items() if count > 1)

    for check in report.checks:
        payload = {
            "name": check.name,
            "passed": check.passed,
            "reason": check.reason,
            "metrics": check.metrics,
        }
        path = os.path.join(checks_dir, check.name + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    if duplicate_names:
        with open(os.path.join(checks_dir, "_duplicate_check_names.json"), "w",
                  encoding="utf-8", newline="\n") as fh:
            json.dump({
                "duplicate_names": duplicate_names,
                "counts": name_counts,
                "note": ("本次报告里出现了重名检验。checks/<name>.json 只保留最后一份，"
                         "而 result.json 保存全部——两者不一致。上游应去重，"
                         "否则独立复算必然报 stale-metrics。"),
            }, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    if hypothesis_source not in HYPOTHESIS_SOURCES:
        raise ValueError("未知的假设来源: " + str(hypothesis_source)
                         + "；可选值见 evidence.HYPOTHESIS_SOURCES")
    settings = dict(settings_in if settings_in is not None else verify_settings())
    meta = {
        "task_id": report.task_id,
        "verdict": report.verdict,
        "formula": report.formula,
        "parameters": report.parameters,
        # free_parameters 记录自由参数的**名字**（不是拟合值）：
        # 独立复算必须自己重新拟合，不能复用本次结果，否则复算失去意义。
        # 优先用报告里显式记录的请求参数；只有旧版报告没有该字段时才从拟合值反推
        # （拟合失败时拟合值为空，反推会丢失信息——这是已修复的缺陷）。
        "free_parameters": (sorted(report.free_parameters)
                            if getattr(report, "free_parameters", None)
                            else sorted(report.parameters.keys())),
        # 实际生效的阈值与种子。缺了这一段，第三方就无法解释"为什么换台机器结论不同"。
        "verify_settings": settings,
        "engine_version": __version__,
        # 假设从哪来：决定这条运行能不能用来支撑"智能体自主发现"。
        "hypothesis_source": hypothesis_source,
        "hypothesis_source_note": HYPOTHESIS_SOURCES.get(hypothesis_source, ""),
        "rounds_hint": report.rounds_hint,
        "inputs": list(inputs or []),
        "notes": notes,
        "duplicate_check_names": duplicate_names,
    }
    # run.json 必须在清单之前落盘：否则"防篡改清单"覆盖不到承载结论的文件（已修复的缺陷）。
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    manifest_path = os.path.join(run_dir, "manifest.sha256")
    index_lines = []
    for root, _dirs, files in os.walk(run_dir):
        for name in sorted(files):
            full = os.path.join(root, name)
            if os.path.abspath(full) == os.path.abspath(manifest_path):
                continue  # 清单不把自己写进去
            rel = os.path.relpath(full, run_dir).replace(os.sep, "/")
            index_lines.append(rel + "  " + _sha256_file(full))
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(index_lines) + "\n")
    return run_dir

def verify_manifest(run_dir: str) -> Dict[str, object]:
    """校验 runs/<run_id>/manifest.sha256：逐文件比对 SHA256。

    这是"证据可复核"的机器判据——第三方拿到证据目录，先跑这一步，
    确认没有任何文件在事后被改动，再谈复现结论。
    """
    manifest_path = os.path.join(run_dir, "manifest.sha256")
    if not os.path.exists(manifest_path):
        return {"run_dir": run_dir, "status": "missing-manifest", "ok": False,
                "checked": 0, "mismatched": [], "missing": [], "untracked": []}
    expected: Dict[str, str] = {}
    with open(manifest_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            rel, _, digest = line.rpartition("  ")
            expected[rel.strip()] = digest.strip()

    mismatched: List[str] = []
    missing: List[str] = []
    for rel, digest in sorted(expected.items()):
        full = os.path.join(run_dir, rel.replace("/", os.sep))
        if not os.path.exists(full):
            missing.append(rel)
            continue
        if _sha256_file(full) != digest:
            mismatched.append(rel)

    present = set()
    for root, _dirs, files in os.walk(run_dir):
        for name in files:
            full = os.path.join(root, name)
            if os.path.abspath(full) == os.path.abspath(manifest_path):
                continue
            present.add(os.path.relpath(full, run_dir).replace(os.sep, "/"))
    untracked = sorted(present - set(expected))

    ok = not (mismatched or missing or untracked)
    return {
        "run_dir": run_dir,
        "status": "ok" if ok else "tampered-or-incomplete",
        "ok": ok,
        "checked": len(expected),
        "mismatched": mismatched,
        "missing": missing,
        "untracked": untracked,
    }
