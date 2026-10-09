# -*- coding: utf-8 -*-
"""隔离性测试（M2）：证明"标准答案"与"评分"被真正挡在智能体之外。

这些不是描述性声明，是机器判据：
1. formula_agh 的任何模块都不得 import 评分包；
2. 把 reference/ 整个拿掉，验证结论必须逐位不变；
3. 只有 src/scoring/ 一侧允许出现指向 reference/ 的路径。
"""
import ast
import json
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

PKG = os.path.join(ROOT, "src", "formula_agh")
SANDBOX = os.path.join(ROOT, "_isolation_tmp")


def _package_sources():
    for name in sorted(os.listdir(PKG)):
        if name.endswith(".py"):
            with open(os.path.join(PKG, name), encoding="utf-8") as fh:
                yield name, fh.read()


def test_formula_agh_never_imports_the_scoring_package():
    offenders = []
    for name, text in _package_sources():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "scoring" or alias.name.startswith("scoring."):
                        offenders.append(name + ": import " + alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "scoring"
                                    or node.module.startswith("scoring.")):
                    offenders.append(name + ": from " + node.module)
    assert not offenders, "智能体侧不得引用评分包: " + str(offenders)


def test_scoring_is_a_separate_top_level_package():
    assert os.path.isdir(os.path.join(ROOT, "src", "scoring"))
    assert not os.path.exists(os.path.join(PKG, "scoring")), \
        "评分包不能藏在 formula_agh 里面"


def _docstring_nodes(tree):
    """收集全部文档字符串节点。文档里当然可以解释红线，代码里不可以有路径。"""
    nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                nodes.add(id(body[0].value))
    return nodes


def test_only_scoring_side_mentions_a_reference_path():
    # 注释与文档字符串里可以解释红线；**代码里**的字符串字面量不行——
    # 只有后者会被拼进真正打开的文件路径。
    allowed = {"cli.py", "contract.py"}   # 这两个只把"reference 目录"写进给用户的提示语
    offenders = []
    for name, text in _package_sources():
        if name in allowed:
            continue
        tree = ast.parse(text)
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                lowered = node.value.lower()
                if "reference" in lowered and ("/" in lowered or ".json" in lowered):
                    offenders.append(name + ": " + node.value[:60])
    assert not offenders, "验证引擎的代码字符串里出现了标准答案路径: " + str(offenders)


def test_verification_is_identical_when_reference_directory_is_absent():
    """行为证明：把 reference/ 从环境里彻底拿掉，结论必须逐位不变。"""
    from formula_agh.verify import load_task, verify_formula

    task_id = "phys-gravitation"
    here = load_task(os.path.join(ROOT, "tasks", task_id))
    baseline = verify_formula("G*m1*m2/r**2", here[0], here[1], parameters=["G"]).to_json()

    shutil.rmtree(SANDBOX, ignore_errors=True)
    try:
        os.makedirs(SANDBOX)
        shutil.copytree(os.path.join(ROOT, "src"), os.path.join(SANDBOX, "src"))
        shutil.copytree(os.path.join(ROOT, "tasks"), os.path.join(SANDBOX, "tasks"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "config"), os.path.join(SANDBOX, "config"))
        assert not os.path.exists(os.path.join(SANDBOX, "reference"))
        assert not os.path.exists(os.path.join(SANDBOX, "sealed"))

        code = (
            "import json,sys;sys.path.insert(0,'src');"
            "from formula_agh.verify import load_task, verify_formula;"
            "c,m=load_task('tasks/phys-gravitation');"
            "print(verify_formula('G*m1*m2/r**2',c,m,parameters=['G']).to_json())"
        )
        import subprocess
        proc = subprocess.run([sys.executable, "-X", "utf8", "-c", code], cwd=SANDBOX,
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, proc.stderr[-800:]
        assert proc.stdout.strip() == baseline.strip(), \
            "去掉 reference/ 之后结论发生了变化，说明验证引擎读了标准答案"
    finally:
        shutil.rmtree(SANDBOX, ignore_errors=True)


def test_reference_directory_lives_outside_tasks():
    ref = os.path.join(ROOT, "reference")
    tasks = os.path.join(ROOT, "tasks")
    assert os.path.isdir(ref)
    assert not os.path.abspath(ref).startswith(os.path.abspath(tasks) + os.sep), \
        "标准答案不能放在 tasks/ 里面"
