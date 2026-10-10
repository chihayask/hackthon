# -*- coding: utf-8 -*-
"""工具类脚本的回归测试：文档一致性检查与 AGH 规则形状检查。

这两个脚本的作用是**拦住漂移**（文档与仓库不一致、AGH 预设规则形状不合法）。
对它们来说最要紧的是不误报——检查器自己先要能被信任，否则没人会看它的输出。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "examples"))
sys.path.insert(0, os.path.join(ROOT, "harness"))
BS = chr(92)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# 文档一致性检查
# --------------------------------------------------------------------------

def test_path_heuristic_accepts_repo_paths_and_rejects_noise():
    mod = _load("check_docs", "examples/check_docs.py")
    for good in ("README.md", "docs/数据卡.md", "examples/check_docs.py",
                 "src/formula_agh/verify.py", "runs/", "evidence/scoring/comparison.md"):
        assert mod.looks_like_repo_path(good), good
    # 第一版把这些全算成缺失文件，一次误报 84 条
    for noise in ("run.json", ".csv", "m/s^2", "RMSE/std(y)", "approvals.mode",
                  "meta.json", "~/.agh", "https://example.org/x",
                  "reference/answer/ground/solution/truth/label/golden"):
        assert not mod.looks_like_repo_path(noise), noise


def test_repo_documents_are_consistent():
    mod = _load("check_docs", "examples/check_docs.py")
    report = mod.check()
    assert report["ok"], report["problems"]
    assert report["tests_actual"] == mod.actual_test_count()
    assert report["steps_actual"] == mod.actual_step_count()


def test_step_and_test_counts_are_derived_not_hardcoded():
    mod = _load("check_docs", "examples/check_docs.py")
    assert mod.actual_test_count() > 50
    assert mod.actual_step_count() >= 15


def test_reviewer_docs_carry_no_role_labels():
    mod = _load("check_docs", "examples/check_docs.py")
    for rel in mod.REVIEWER_DOCS:
        if rel.endswith("独立完成声明.md"):
            continue  # 它本身就是通知要求的成员分工声明件
        text = mod._read(rel)
        assert not mod.ROLE_RE.findall(text), rel


# --------------------------------------------------------------------------
# AGH allow 规则形状
# --------------------------------------------------------------------------

def test_allow_rule_accepts_all_absolute_forms():
    mod = _load("check_agh_command_rule", "harness/check_agh_command_rule.py")
    good = ("^[Ee]:[" + BS + BS + "/]fagh[" + BS + BS + "/]harness[" + BS + BS +
            "/]run_verify" + BS + BS + ".cmd(?: [^&|;<>]*)?$")
    for pattern in (good, "^" + BS + BS, "^/usr/local/bin/x",
                    "^[" + BS + BS + "/]", "^[A-Za-z]:", "^C:" + BS + BS + "x"):
        ok, why = mod.check_argv(pattern)
        assert ok, (pattern, why)


def test_allow_rule_rejects_the_two_historical_mistakes():
    mod = _load("check_agh_command_rule", "harness/check_agh_command_rule.py")
    # 这两个正是当初真踩过的写法：都让 AGH 会话创建失败且不给可读错误
    for pattern in ("formula_agh|run_verify", "^(?:cmd /c)"):
        ok, _why = mod.check_argv(pattern)
        assert not ok, pattern


def test_allow_rule_rejects_invalid_regex():
    mod = _load("check_agh_command_rule", "harness/check_agh_command_rule.py")
    ok, why = mod.check_argv("^(" + BS + BS + "]]")
    assert not ok
    assert "不合法" in why or "路径形状" in why
