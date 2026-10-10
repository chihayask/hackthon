# -*- coding: utf-8 -*-
"""溯源绑定、覆盖留痕与量纲分档——外部审计（2026-10-10）整改项的回归测试。

这三条都是"证据可信度"问题，不是功能问题：标签自报、覆盖静默、
量纲门笼统报 PASS。它们一旦回归，评分结论会在关键处说反话。
"""
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from formula_agh.evidence import write_evidence
from formula_agh.verify import (CheckResult, VerifyReport, _check_dimension,
                                load_task, verify_formula)

TMP = os.path.join(ROOT, "_prov_tmp")


def _fresh(name):
    d = os.path.join(TMP, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    return d


def _report(task_id="phys-ohm", verdict="accepted"):
    return VerifyReport(task_id=task_id, formula="I*R", parameters={},
                        verdict=verdict,
                        checks=[CheckResult("dimension", True, "量纲一致（严格比对）", {})],
                        rounds_hint="")


# --------------------------------------------------------------------------
# 溯源绑定
# --------------------------------------------------------------------------

def test_provenance_bound_requires_both_label_and_session():
    root = _fresh("bound")
    run = os.path.join(root, "r1")
    write_evidence(run, _report(), "test", hypothesis_source="agh-llm",
                   session_id="sess-abc", agent_workspace="E:/ws/task")
    meta = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
    assert meta["session_id"] == "sess-abc"
    assert meta["agent_workspace"] == "E:/ws/task"
    assert meta["provenance_bound"] is True


def test_agh_llm_without_session_is_not_bound():
    """自报标签不算证据：标了 agh-llm 但没有会话号，provenance_bound 必须为 False。"""
    root = _fresh("unbound")
    run = os.path.join(root, "r2")
    write_evidence(run, _report(), "test", hypothesis_source="agh-llm")
    meta = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
    assert meta["session_id"] == ""
    assert meta["provenance_bound"] is False


def test_non_agent_source_is_never_bound():
    root = _fresh("cli")
    run = os.path.join(root, "r3")
    write_evidence(run, _report(), "test", hypothesis_source="cli",
                   session_id="sess-xyz")
    meta = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
    assert meta["provenance_bound"] is False


def test_demo_fallback_label_is_a_known_source():
    from formula_agh.evidence import HYPOTHESIS_SOURCES
    assert "fixture-fallback" in HYPOTHESIS_SOURCES


# --------------------------------------------------------------------------
# 覆盖留痕
# --------------------------------------------------------------------------

def test_rewriting_a_run_leaves_an_overwrite_record():
    root = _fresh("overwrite")
    run = os.path.join(root, "r4")
    write_evidence(run, _report(verdict="rejected"), "first",
                   hypothesis_source="agh-llm", session_id="sess-1")
    assert not os.path.exists(os.path.join(run, "overwritten_from.json"))
    write_evidence(run, _report(verdict="accepted"), "second",
                   hypothesis_source="agh-llm", session_id="sess-2")
    path = os.path.join(run, "overwritten_from.json")
    assert os.path.exists(path), "覆盖已有 run 必须留痕"
    rec = json.load(open(path, encoding="utf-8"))
    assert rec["verdict"] == "rejected"
    assert rec["session_id"] == "sess-1"
    # 覆盖留痕必须在清单里，否则它自己可以被悄悄删掉
    manifest = open(os.path.join(run, "manifest.sha256"), encoding="utf-8").read()
    assert "overwritten_from.json" in manifest


# --------------------------------------------------------------------------
# 量纲分档
# --------------------------------------------------------------------------

def _meta(units, free_parameters=None):
    return {"task_id": "probe", "var_names": ["x", "k"],
            "units": units, "free_parameters": free_parameters or []}


def test_dimension_mode_strict_without_free_parameters():
    meta = _meta({"x": "m", "k": "N/m", "y": "J"})
    res = _check_dimension("0.5*k*x**2", meta, [])
    assert res.passed is True
    assert res.metrics.get("mode") == "strict", res.metrics


def test_dimension_mode_structural_when_parameter_has_no_units():
    meta = _meta({"x": "m", "k": "N/m", "y": "J"})
    res = _check_dimension("sigma*x**2", meta, ["sigma"])
    assert res.passed is True
    assert res.metrics.get("mode") == "structural", res.metrics


def test_dimension_mode_is_strict_when_parameter_units_are_declared():
    """给自由参数声明单位后，它不再是"可吸收单位的未知量"，严格比对就能做。"""
    meta = _meta({"x": "m", "k": "N/m", "y": "J", "sigma": "N/m"})
    res = _check_dimension("sigma*x**2", meta, ["sigma"])
    assert res.passed is True
    assert res.metrics.get("mode") == "strict", res.metrics
    assert res.metrics.get("free_parameters_with_units") == ["sigma"]


def test_dimension_mode_skipped_without_units():
    meta = {"task_id": "probe", "var_names": ["x", "k"]}
    res = _check_dimension("k*x", meta, [])
    assert res.passed is True
    assert res.metrics.get("mode") == "skipped", res.metrics


def test_dimension_mismatch_is_reported_in_strict_mode():
    meta = _meta({"x": "m", "k": "N/m", "y": "J"})
    res = _check_dimension("k*x", meta, [])
    assert res.passed is False
    assert res.metrics.get("mode") == "strict", res.metrics


def test_real_tasks_declare_a_dimension_mode():
    """全部 22 个任务的量纲检验都必须带上 mode，不能有无档位的"通过"。"""
    tasks = os.path.join(ROOT, "tasks")
    missing = []
    seen = set()
    for name in sorted(os.listdir(tasks)):
        meta_path = os.path.join(tasks, name, "meta.json")
        ref_path = os.path.join(ROOT, "reference", name + ".json")
        if not (os.path.isfile(meta_path) and os.path.isfile(ref_path)):
            continue
        meta = json.load(open(meta_path, encoding="utf-8"))
        ref = json.load(open(ref_path, encoding="utf-8"))
        res = _check_dimension(str(ref.get("formula")), meta,
                               list(ref.get("free_parameters") or []))
        mode = res.metrics.get("mode")
        if mode not in ("strict", "structural", "skipped"):
            missing.append(name)
        seen.add(mode)
    assert not missing, "以下任务的量纲检验缺少 mode: " + ",".join(missing)
    assert seen & {"strict", "structural"}, "至少应出现严格或结构档位"


def test_no_temp_dirs_left_behind():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    assert not os.path.isdir(TMP)
