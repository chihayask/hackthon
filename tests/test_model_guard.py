# -*- coding: utf-8 -*-
"""模型路由守卫的回归测试：通知五（二）要求模型调用仅限 Agnes。

这条控制的价值在于**拒绝**，而不在于文档里声明。所以测试的重点是负例：
非 Agnes 的路由必须被拒。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
EXAMPLES = os.path.join(ROOT, "examples")
sys.path.insert(0, EXAMPLES)


def _load():
    spec = importlib.util.spec_from_file_location(
        "model_guard", os.path.join(EXAMPLES, "model_guard.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_agnes_route_is_accepted():
    mod = _load()
    result = mod.check_routes(["main=agnes/agnes-3.0-flash"])
    assert result["ok"] is True, result
    assert result["routes"][0]["provider"] == "agnes"


def test_non_agnes_provider_is_rejected():
    mod = _load()
    result = mod.check_routes(["main=openai/gpt-4o"])
    assert result["ok"] is False, result
    assert "不是 Agnes" in result["reason"]


def test_non_agnes_model_on_agnes_provider_is_rejected():
    """provider 写成 agnes 但模型名不是 Agnes，同样要拒。"""
    mod = _load()
    result = mod.check_routes(["main=agnes/claude-3"])
    assert result["ok"] is False, result
    assert "非 Agnes" in result["reason"]


def test_route_without_slot_prefix_is_parsed():
    mod = _load()
    result = mod.check_routes(["openai/gpt-4o"])
    assert result["ok"] is False, result
    assert result["routes"][0]["provider"] == "openai"


def test_profile_config_is_agnes_only():
    """本机 AGH 配置必须只启用 Agnes 账号；配置不存在时跳过（他人机器上可能没装 AGH）。"""
    mod = _load()
    profile = os.environ.get("AGNES_PROFILE", "local-dev")
    path = mod.config_path(profile)
    if not os.path.isfile(path):
        return
    report = mod.check_accounts(profile)
    assert report["ok"] is True, report["reason"]
    for acc in report["accounts"]:
        if acc["enabled"]:
            assert acc["provider"].lower().startswith("agnes"), acc
            assert "agnes" in acc["baseUrlHost"], acc
