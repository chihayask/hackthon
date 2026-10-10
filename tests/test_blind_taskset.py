# -*- coding: utf-8 -*-
"""盲化任务集与提示泄漏审计的回归测试。

这两件事支撑 README 里的自我限定："带物理先验的已知定律恢复"。
它们一旦退化（盲化集又泄漏了真实 id / 现象文本，或审计不再报告泄漏），
文档里的限定就成了空话——所以用测试锁住。
"""
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from formula_agh.contract import validate_taskset

TMP = os.path.join(ROOT, "_blind_tmp")


def _load(rel):
    path = os.path.join(ROOT, rel)
    spec = importlib.util.spec_from_file_location(os.path.basename(rel)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fresh(name):
    d = os.path.join(TMP, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    return d


def _build(level):
    mod = _load("examples/make_blind_taskset.py")
    out = _fresh(level)
    result = mod.build(out, level)
    return mod, out, result


def test_blind_set_hides_identity_phenomenon_and_source():
    _mod, out, result = _build("metadata")
    assert result["tasks"] == 22, result
    mapping = json.load(open(os.path.join(out, "mapping.json"), encoding="utf-8"))
    assert len(mapping["map"]) == 22
    for anon, info in mapping["map"].items():
        meta_path = os.path.join(out, "tasks", anon, "meta.json")
        assert os.path.isfile(meta_path), meta_path
        raw = open(meta_path, encoding="utf-8").read()
        meta = json.loads(raw)
        assert meta["task_id"] == anon
        for field in ("phenomenon", "domain", "source_note"):
            assert field not in meta, (anon, field)
        # 真实 id 不得出现在盲化 meta 里（这是盲化的底线）
        assert info["real_id"] not in raw, "真实任务 id 泄漏: " + anon
        # source 必须是指向评审侧的占位，而不是可点击的定律条目
        source = meta.get("source")
        assert isinstance(source, list) and source, (anon, source)
        assert all("blind-set" in str(s) for s in source), (anon, source)


def test_blind_set_has_no_real_phenomenon_text():
    """原任务的现象描述不得以任何形式出现在盲化 meta 里。"""
    _mod, out, _result = _build("metadata")
    tasks_root = os.path.join(ROOT, "tasks")
    leaked = []
    for real in sorted(os.listdir(tasks_root)):
        src = os.path.join(tasks_root, real, "meta.json")
        if not os.path.isfile(src):
            continue
        original = json.load(open(src, encoding="utf-8"))
        text = str(original.get("phenomenon") or "").strip()
        if not text:
            continue
        for anon in os.listdir(os.path.join(out, "tasks")):
            raw = open(os.path.join(out, "tasks", anon, "meta.json"), encoding="utf-8").read()
            if text in raw:
                leaked.append((real, anon))
    assert not leaked, "现象原文泄漏进盲化集: " + str(leaked[:3])


def test_blind_set_passes_the_contract_without_errors():
    _mod, out, _result = _build("metadata")
    report = validate_taskset(os.path.join(out, "tasks"),
                              reference_root=os.path.join(out, "reference"),
                              require_split=False)
    # validate_taskset 返回的 findings 是字典（不是 Finding 对象），这里统一按字典读。
    findings = report.get("findings", [])
    errors = [f for f in findings if f.get("severity") == "error"]
    assert errors == [], errors[:3]
    assert report.get("ok") is True
    # 盲化集的 source 是评审侧占位串，预期每条给一个 SOURCE_NOT_URL 警告
    warns = [f for f in findings if f.get("severity") == "warn"]
    assert all(f.get("code") == "SOURCE_NOT_URL" for f in warns), warns[:3]


def test_strict_level_also_removes_units():
    _mod, out, result = _build("strict")
    assert "units" in result["removed"], result
    for anon in os.listdir(os.path.join(out, "tasks")):
        meta = json.load(open(os.path.join(out, "tasks", anon, "meta.json"), encoding="utf-8"))
        assert "units" not in meta, anon


def test_reference_and_scale_specs_are_remapped():
    _mod, out, _result = _build("metadata")
    refs = os.listdir(os.path.join(out, "reference"))
    assert len(refs) == 22, len(refs)
    assert not any(r.startswith("phys-") for r in refs), "盲化 reference 仍用真实 id"
    specs = json.load(open(os.path.join(out, "physics", "scale_specs.json"), encoding="utf-8"))
    keys = list((specs.get("tasks") or {}).keys())
    assert len(keys) == 22, len(keys)
    assert not any(k.startswith("phys-") for k in keys), "盲化 scale_specs 仍用真实 id"
    for spec in (specs.get("tasks") or {}).values():
        note = str(spec.get("physics_note") or "")
        assert "盲化" in note, "physics_note 未中性化: " + note[:60]


def test_hint_audit_reports_the_known_leakage():
    mod = _load("examples/hint_audit.py")
    tasks_root = os.path.join(ROOT, "tasks")
    rows = [mod.audit_task(os.path.join(tasks_root, n), n)
            for n in sorted(os.listdir(tasks_root))
            if os.path.isfile(os.path.join(tasks_root, n, "meta.json"))]
    assert len(rows) == 22
    # 22/22 都应在四个维度上有泄漏——这就是"带先验恢复"这一限定的依据
    for kind in ("task_id", "phenomenon", "source", "units"):
        hit = sum(1 for r in rows if any(l["kind"] == kind for l in r["leaks"]))
        assert hit == 22, (kind, hit)
    examples = mod._prompt_formula_examples()
    assert examples, "提示里的示例式应当被审计出来"


def test_no_temp_dirs_left_behind():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    assert not os.path.isdir(TMP)
