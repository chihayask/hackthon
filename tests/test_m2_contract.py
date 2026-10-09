# -*- coding: utf-8 -*-
"""M2 工程契约测试：划分可复现、违规即拒绝、证据可自校验、阈值单一来源。"""
import json
import os
import shutil
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from formula_agh.contract import validate_task, validate_taskset
from formula_agh.evidence import verify_manifest, write_evidence
from formula_agh.settings import default_config_path, load_config, verify_settings
from formula_agh.safe_eval import UnsafeExpression, parse_formula
from formula_agh.split import (SplitError, assert_no_indices, build_split, load_split,
                               check_split)
from formula_agh.units import parse_unit, unit_dimension
from formula_agh.verify import load_task, verify_formula

TASKS = os.path.join(ROOT, "tasks")
TMP = os.path.join(ROOT, "_contract_tmp")


def _task(task_id="phys-ohm"):
    return load_task(os.path.join(TASKS, task_id))


def _tmp_copy(task_id="phys-ohm", name="probe"):
    dest = os.path.join(TMP, name)
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    shutil.copytree(os.path.join(TASKS, task_id), dest)
    return dest


# --------------------------------------------------------------------------
# 划分
# --------------------------------------------------------------------------

def test_split_is_bitwise_reproducible():
    columns, meta = _task("phys-coulomb")
    first, _m1 = build_split(columns, meta, 0.2, 0.15, 20261008, task_id="phys-coulomb")
    second, _m2 = build_split(columns, meta, 0.2, 0.15, 20261008, task_id="phys-coulomb")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["fingerprint"] == second["fingerprint"]


def test_split_on_disk_matches_recomputation():
    columns, meta = _task("phys-ohm")
    stored = load_split(os.path.join(TASKS, "phys-ohm"))
    assert stored is not None, "先运行 formula_agh split"
    result = check_split(os.path.join(TASKS, "phys-ohm"), columns, meta, 0.2, 0.15, 20261008)
    assert result["identical"] is True, result


def test_split_manifest_carries_no_row_indices():
    columns, meta = _task("phys-weight")
    manifest, _masks = build_split(columns, meta, 0.2, 0.15, 20261008, task_id="phys-weight")
    assert_no_indices(manifest)          # 不抛异常即通过
    assert manifest["contains_row_indices"] is False
    for key in ("train", "holdout", "extrapolation"):
        assert isinstance(manifest["fingerprint"][key]["sha256"], str)
        assert len(manifest["fingerprint"][key]["sha256"]) == 64


def test_split_manifest_index_guard_actually_fires():
    columns, meta = _task("phys-weight")
    manifest, _masks = build_split(columns, meta, 0.2, 0.15, 20261008, task_id="phys-weight")
    manifest["fingerprint"]["train"]["indices"] = [1, 2, 3]
    with pytest.raises(SplitError):
        assert_no_indices(manifest)


def test_extrapolation_is_strictly_outside_training_support():
    for task_id in ("phys-ohm", "phys-coulomb"):
        columns, meta = _task(task_id)
        _manifest, masks = build_split(columns, meta, 0.2, 0.15, 20261008, task_id=task_id)
        var_names = [str(v) for v in meta["var_names"]]
        axis = int(masks["split_axis"])
        key = np.asarray(columns[var_names[axis]], dtype=float)
        lo = float(masks["support_lo"][axis])
        hi = float(masks["support_hi"][axis])
        ex = key[masks["extrapolation"]]
        ho = key[masks["holdout"]]
        assert np.all((ex < lo) | (ex > hi)), task_id + " 的外推区没有完全落在支撑域之外"
        assert np.all((ho >= lo) & (ho <= hi)), task_id + " 的留出区落在了支撑域之外"


# --------------------------------------------------------------------------
# 数据契约
# --------------------------------------------------------------------------

def test_clean_task_set_has_no_errors():
    result = validate_taskset(TASKS, reference_root=os.path.join(ROOT, "reference"))
    assert result["ok"] is True, result["findings"]
    assert result["checked"] == 22


def test_contract_rejects_non_numeric_and_missing_values():
    dest = _tmp_copy("phys-ohm")
    try:
        path = os.path.join(dest, "data.csv")
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        for index in range(3, 10):
            parts = lines[index].rstrip("\n").split(",")
            parts[-1] = ""
            lines[index] = ",".join(parts) + "\n"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(lines)
        findings = validate_task(dest, "probe")
        codes = {f.code for f in findings if f.severity == "error"}
        assert "CSV_NON_NUMERIC" in codes, codes
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_contract_rejects_reference_file_inside_task_dir():
    dest = _tmp_copy("phys-ohm")
    try:
        with open(os.path.join(dest, "reference.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        findings = validate_task(dest, "probe")
        assert any(f.code == "LEAK_FILE" and f.severity == "error" for f in findings)
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_contract_rejects_missing_declared_column():
    dest = _tmp_copy("phys-ohm")
    try:
        meta_path = os.path.join(dest, "meta.json")
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        meta["var_names"] = list(meta["var_names"]) + ["nonexistent_var"]
        with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(meta, fh, ensure_ascii=False)
        findings = validate_task(dest, "probe")
        assert any(f.code == "CSV_MISSING_COL" for f in findings)
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_contract_rejects_constant_column():
    dest = _tmp_copy("phys-ohm")
    try:
        path = os.path.join(dest, "data.csv")
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        header = lines[0].rstrip("\n").split(",")
        col = header.index("I")
        for index in range(1, len(lines)):
            parts = lines[index].rstrip("\n").split(",")
            parts[col] = "1.0"
            lines[index] = ",".join(parts) + "\n"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(lines)
        findings = validate_task(dest, "probe")
        assert any(f.code == "CONSTANT_COL" for f in findings)
    finally:
        shutil.rmtree(dest, ignore_errors=True)


# --------------------------------------------------------------------------
# 证据
# --------------------------------------------------------------------------

def test_evidence_manifest_covers_every_file_including_run_json():
    run_dir = os.path.join(TMP, "run-manifest")
    shutil.rmtree(run_dir, ignore_errors=True)
    columns, meta = _task("phys-ohm")
    report = verify_formula("I*R", columns, meta)
    write_evidence(run_dir, report, "pytest: manifest coverage")
    try:
        with open(os.path.join(run_dir, "manifest.sha256"), encoding="utf-8") as fh:
            listed = {line.rsplit("  ", 1)[0].strip() for line in fh if line.strip()}
        assert "run.json" in listed, "承载结论的 run.json 必须被防篡改清单覆盖"
        assert "result.json" in listed
        assert "checks/holdout.json" in listed
        result = verify_manifest(run_dir)
        assert result["ok"] is True, result
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_evidence_manifest_detects_tampering():
    run_dir = os.path.join(TMP, "run-tamper")
    shutil.rmtree(run_dir, ignore_errors=True)
    columns, meta = _task("phys-ohm")
    report = verify_formula("I*R", columns, meta)
    write_evidence(run_dir, report, "pytest: tamper detection")
    try:
        with open(os.path.join(run_dir, "result.json"), "a", encoding="utf-8") as fh:
            fh.write(" ")
        result = verify_manifest(run_dir)
        assert result["ok"] is False
        assert "result.json" in result["mismatched"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_evidence_records_free_parameter_names_even_when_fit_fails():
    columns, meta = _task("phys-ideal-gas")
    report = verify_formula("R*n*T", columns, meta, parameters=["R"])
    assert report.verdict == "rejected"
    assert report.parameters == {}, "这个式子本来就拟合不出来"
    assert report.free_parameters == ["R"], \
        "拟合失败也必须记住用户请求了哪些自由参数，否则独立复算会走错分支"


# --------------------------------------------------------------------------
# 阈值单一来源与判据
# --------------------------------------------------------------------------

def test_thresholds_come_from_a_single_config_file():
    config = load_config(default_config_path())
    settings = verify_settings(config)
    assert settings["holdout_threshold"] == float(config["verify"]["holdout_error_threshold"])
    assert settings["extrapolation_threshold"] == float(
        config["verify"]["extrapolation_error_threshold"])
    assert settings["seed"] == int(config["run"]["seed"])
    assert config["verify"]["error_criterion"] == "relative_error_median"


def test_cli_verify_and_batch_use_the_same_thresholds():
    """改造前 verify 用 0.05、batch 用 0.08，同一公式两个结论。这条测试锁死这个回归。"""
    import argparse
    from formula_agh.cli import build_parser
    parser = build_parser()
    verify_args = parser.parse_args(["verify", "--task", "t", "--formula", "f"])
    batch_args = parser.parse_args(["batch", "--tasks", "t"])
    assert verify_args.holdout_threshold is None, "verify 不得再有自己的默认阈值"
    assert verify_args.extrapolation_threshold is None
    assert not hasattr(batch_args, "holdout_threshold"), "batch 也不得自带阈值"


def test_decision_uses_median_relative_error():
    columns, meta = _task("phys-ohm")
    report = verify_formula("I*R", columns, meta)
    checks = {c.name: c for c in report.checks}
    for name in ("holdout", "extrapolation"):
        assert checks[name].metrics.get("criterion") == "relative_error_median"
        # 判定口径与七个诊断口径必须同时留证，评审可以换口径复核
        for key in ("relative_error_median", "relative_error_p75", "relative_error_p90",
                    "rmsre", "relative_rmse", "normalized_rmse", "max_relative_error"):
            assert key in checks[name].metrics, (name, key)


def test_hypothesis_source_chain_from_env(monkeypatch=None):
    """AGH 通过包装脚本调用引擎时，来源必须一路带到 run.json。

    真实事故：AGH 的 shell 调用 harness/run_verify.cmd，引擎看到的命令与人工敲的
    一模一样，于是模型自主提出的假设被记成 cli，**不计入「智能体发现」层**——
    证据在关键结论上说反了话。这条测试锁住修复。
    """
    from formula_agh.cli import _hypothesis_source

    old = os.environ.get("FORMULA_AGH_HYPOTHESIS_SOURCE")
    try:
        os.environ.pop("FORMULA_AGH_HYPOTHESIS_SOURCE", None)
        assert _hypothesis_source() == "cli", "没有环境变量时应退回 cli"
        assert _hypothesis_source("fixture-variant") == "fixture-variant", "显式参数优先"

        os.environ["FORMULA_AGH_HYPOTHESIS_SOURCE"] = "agh-llm"
        assert _hypothesis_source() == "agh-llm", "包装脚本设的环境变量必须生效"
        assert _hypothesis_source("cli") == "cli", "显式参数仍然优先于环境变量"
    finally:
        if old is None:
            os.environ.pop("FORMULA_AGH_HYPOTHESIS_SOURCE", None)
        else:
            os.environ["FORMULA_AGH_HYPOTHESIS_SOURCE"] = old


def test_scoring_classifies_agent_runs_by_provenance_not_by_name():
    """评分脚本必须按 hypothesis_source 判类，而不是按 run_id 命名。

    真实事故：AGH 产生的运行命名是 20261008-231054-phys-gravitation，
    不符合 <task>-candNN 的旧规则，于是被归到 other，
    一条货真价实的模型自主发现被排除在「智能体发现」层之外。
    """
    from scoring.compare import classify_run

    assert classify_run("20261008-231054-phys-gravitation", "phys-gravitation",
                        "agh-llm") == "agent-candidate"
    assert classify_run("refcheck-phys-ohm", "phys-ohm", "reference") == "gold-reference"
    assert classify_run("anything", "phys-ohm", "fixture-variant") == "wrong-variant"
    # 人工在命令行给出的候选式单独成层，不能算模型的发现能力
    assert classify_run("phys-ohm-cand01", "phys-ohm", "cli") == "cli-candidate"


def test_hypothesis_source_chain_from_env():
    """AGH 通过包装脚本调用引擎时，来源必须一路带到 run.json。

    真实事故：AGH 的 shell 调用 harness/run_verify.cmd，引擎看到的命令与人工敲的
    一模一样，于是模型自主提出的假设被记成 cli，**不计入「智能体发现」层**——
    证据在关键结论上说反了话。这条测试锁住修复。
    """
    from formula_agh.cli import _hypothesis_source

    old = os.environ.get("FORMULA_AGH_HYPOTHESIS_SOURCE")
    try:
        os.environ.pop("FORMULA_AGH_HYPOTHESIS_SOURCE", None)
        assert _hypothesis_source() == "cli", "没有环境变量时应退回 cli"
        assert _hypothesis_source("fixture-variant") == "fixture-variant", "显式参数优先"

        os.environ["FORMULA_AGH_HYPOTHESIS_SOURCE"] = "agh-llm"
        assert _hypothesis_source() == "agh-llm", "包装脚本设的环境变量必须生效"
        assert _hypothesis_source("cli") == "cli", "显式参数仍然优先于环境变量"
    finally:
        if old is None:
            os.environ.pop("FORMULA_AGH_HYPOTHESIS_SOURCE", None)
        else:
            os.environ["FORMULA_AGH_HYPOTHESIS_SOURCE"] = old


def test_scoring_classifies_agent_runs_by_provenance_not_by_name():
    """评分脚本必须按 hypothesis_source 判类，而不是按 run_id 命名。

    真实事故：AGH 产生的运行命名是 20261008-231054-phys-gravitation，
    不符合 <task>-candNN 的旧规则，于是被归到 other，
    一条货真价实的模型自主发现被排除在「智能体发现」层之外。
    """
    from scoring.compare import classify_run

    assert classify_run("20261008-231054-phys-gravitation", "phys-gravitation",
                        "agh-llm") == "agent-candidate"
    assert classify_run("refcheck-phys-ohm", "phys-ohm", "reference") == "gold-reference"
    assert classify_run("anything", "phys-ohm", "fixture-variant") == "wrong-variant"
    # 人工在命令行给出的候选式单独成层，不能算模型的发现能力
    assert classify_run("phys-ohm-cand01", "phys-ohm", "cli") == "cli-candidate"


def test_environment_differences_do_not_fail_reproduction():
    """换解释器不得把「结论一字不差」判成复现失败。

    真实事故：基线是在 python 3.12.14 / numpy 2.3.5 上固化的，照 README 用本机的
    python 3.13.5 / numpy 2.4.6 跑，15 步全部通过、指纹逐字段相同，却因为
    /environment/python 与 /environment/numpy 两行被判「复现失败」——把环境当结论。
    """
    sys.path.insert(0, ROOT)
    import reproduce

    with open(os.path.join(ROOT, "expected", "reproduction_baseline.json"),
              encoding="utf-8") as fh:
        baseline = json.load(fh)
    actual = json.loads(json.dumps(baseline))
    actual["environment"]["python"] = "9.9.9"
    actual["environment"]["numpy"] = "0.0.1"
    actual["environment"]["platform"] = "Linux"

    hard, env = reproduce.split_environment_diffs(
        reproduce.diff_fingerprints(baseline, actual))
    assert hard == [], "环境差异不得判成失败，实际：" + repr(hard)
    assert len(env) == 3, env

    # 结论差异必须仍然是失败——分开算不等于放水
    first_run = sorted(baseline["runs"])[0]
    actual["runs"][first_run]["verdict"] = "flipped"
    hard2, env2 = reproduce.split_environment_diffs(
        reproduce.diff_fingerprints(baseline, actual))
    assert len(hard2) == 1 and "verdict" in hard2[0], hard2
    assert len(env2) == 3, env2


def test_scale_check_switch_is_honoured():
    columns, meta = _task("phys-gravitation")
    off = verify_formula("G*m1*m2/r**2", columns, meta, parameters=["G"])
    on = verify_formula("G*m1*m2/r**2", columns, meta, parameters=["G"], scale_check=True)
    assert not [c for c in off.checks if c.name.startswith("scale-")]
    assert [c for c in on.checks if c.name.startswith("scale-")], \
        "打开 scale_check 后必须真的追加尺度检验"
    assert on.verdict == "accepted"


def test_disabled_dimension_check_is_visible_in_evidence():
    """关掉一项检验也要留痕：'没跑'和'跑过了'必须在证据里能分开。"""
    columns, meta = _task("phys-kinetic-energy")
    report = verify_formula("m*v/2", columns, meta, dimension_check=False)
    checks = {c.name: c for c in report.checks}
    assert checks["dimension"].passed is True
    assert checks["dimension"].metrics.get("disabled") is True
    assert "关闭" in checks["dimension"].reason


def test_scale_gate_catches_small_angle_without_any_threshold():
    """尺度门不依赖误差统计量：换口径、换阈值都不会影响这条结论。

    这正是 M3《交叉评审发现》发现 1 建议引用的那条证据。
    """
    columns, meta = _task("phys-pendulum-exact")
    report = verify_formula("2*pi*sqrt(L/g)", columns, meta, scale_check=True)
    failed = [c.name for c in report.checks if not c.passed]
    assert any(name.startswith("scale-") for name in failed), failed
    assert report.verdict == "rejected"


def test_every_entry_point_passes_all_switches():
    """入口漏传开关 = 判据被静默降级或用了错的阈值。这条测试把接线钉死。"""
    targets = [
        os.path.join(ROOT, "src", "formula_agh", "cli.py"),
        os.path.join(ROOT, "src", "formula_agh", "recheck.py"),
        os.path.join(ROOT, "examples", "reference_check.py"),
        os.path.join(ROOT, "examples", "variant_check.py"),
        os.path.join(ROOT, "examples", "adversarial_suite.py"),
        # 演示脚本的产出同样进证据包，因此同样不许绕过统一阈值
        os.path.join(ROOT, "examples", "demo_agent.py"),
    ]
    for path in targets:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert "scale_check=" in text, path + " 没有把 scale_check 传给 verify_formula"
        assert "dimension_check=" in text, path + " 没有把 dimension_check 传给 verify_formula"
        assert "fit_max_residual=" in text, path + " 没有把 fit_max_residual 传给 verify_formula"


def test_fit_threshold_comes_from_config_not_hardcoded():
    """拟合粗筛门槛曾经硬编码在 verify.py 里，属于"该进配置的没进"。"""
    config = load_config(default_config_path())
    assert "max_fit_residual" in config["verify"], "config/agent.yaml 必须声明 max_fit_residual"
    settings = verify_settings(config)
    assert settings["fit_max_residual"] == float(config["verify"]["max_fit_residual"])


def test_fit_check_records_training_diagnostics_under_all_criteria():
    columns, meta = _task("phys-gravitation")
    report = verify_formula("G*m1*m2/r**2", columns, meta, parameters=["G"])
    fit = {c.name: c for c in report.checks}["fit"]
    for key in ("train_relative_error_median", "train_normalized_rmse", "train_rmsre"):
        assert key in fit.metrics, (key, sorted(fit.metrics))


def test_scale_specs_cover_every_task():
    from formula_agh.scale_checks import _resolve_specs_path, list_spec_task_ids, load_specs
    specs = load_specs(_resolve_specs_path("physics/scale_specs.json"))
    covered = set(list_spec_task_ids(specs))
    tasks = {d for d in os.listdir(TASKS) if os.path.isdir(os.path.join(TASKS, d))}
    assert tasks <= covered, "以下任务没有尺度规格: " + str(sorted(tasks - covered))


def test_small_angle_approximation_is_rejected_under_current_thresholds():
    settings = verify_settings()
    columns, meta = _task("phys-pendulum-exact")
    exact = verify_formula("2*pi*sqrt(L/g)*(1 + theta0**2/16)", columns, meta,
                           holdout_threshold=settings["holdout_threshold"],
                           extrapolation_threshold=settings["extrapolation_threshold"])
    approx = verify_formula("2*pi*sqrt(L/g)", columns, meta,
                            holdout_threshold=settings["holdout_threshold"],
                            extrapolation_threshold=settings["extrapolation_threshold"])
    assert exact.verdict == "accepted"
    assert approx.verdict == "rejected", approx.to_json()


# --------------------------------------------------------------------------
# 量纲与表达式健壮性
# --------------------------------------------------------------------------

def test_compound_units_are_parsed_not_skipped():
    # 修复前这六个单位会导致 8 个任务的量纲检验被静默跳过
    assert parse_unit("m^3") != parse_unit("m^2")
    assert unit_dimension("T") != unit_dimension("m^3")
    from formula_agh.units import infer_from_source
    inferred = infer_from_source("1/sqrt(eps*mu)", {"eps": "F/m", "mu": "H/m"})
    assert inferred == unit_dimension("m/s")


def test_broken_formula_raises_unsafe_expression_not_syntax_error():
    # 修复前 parse_formula 会抛出未捕获的 SyntaxError，把整条流水线带崩
    with pytest.raises(UnsafeExpression):
        parse_formula("I*R*", ["I", "R"])
    with pytest.raises(UnsafeExpression):
        parse_formula("", ["I"])


def test_syntax_error_formula_is_rejected_not_crashing():
    columns, meta = _task("phys-ohm")
    report = verify_formula("I*R*", columns, meta)
    assert report.verdict == "rejected"


def test_wrong_unit_in_meta_is_caught_by_dimension_check():
    dest = _tmp_copy("phys-kinetic-energy", "badunit")
    try:
        meta_path = os.path.join(dest, "meta.json")
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        meta["units"]["v"] = "m/s^2"
        with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(meta, fh, ensure_ascii=False)
        columns, meta2 = load_task(dest)
        report = verify_formula("m*v**2/2", columns, meta2)
        checks = {c.name: c for c in report.checks}
        assert checks["dimension"].passed is False
        assert report.verdict == "rejected"
    finally:
        shutil.rmtree(dest, ignore_errors=True)
