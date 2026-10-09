# -*- coding: utf-8 -*-
# 公式表达式的安全求值。

# 智能体给出的公式是不可信输入：它可能语法错误，也可能（被提示注入后）包含
# 危险调用。本模块用 AST 白名单把可用语法限制成"初等数学表达式"，任何越界
# 构造一律抛 UnsafeExpression，绝不执行。
# 
from __future__ import annotations

import ast
import math
from typing import Dict, Iterable, Mapping

import numpy as np


class UnsafeExpression(ValueError):
    pass
    # 表达式含有白名单之外的语法或名称。


ALLOWED_FUNCS: Dict[str, object] = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "exp": np.exp, "log": np.log, "log10": np.log10,
    "sqrt": np.sqrt, "abs": np.abs, "sign": np.sign,
    "tanh": np.tanh,
}

ALLOWED_CONSTS: Dict[str, float] = {
    "pi": float(np.pi), "e": float(np.e),
}

ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def _check(node: ast.AST, variables: Iterable[str]) -> None:
    allowed_names = set(variables) | set(ALLOWED_FUNCS) | set(ALLOWED_CONSTS)
    for child in ast.walk(node):
        if isinstance(child, ast.Expression):
            continue
        if isinstance(child, ast.BinOp):
            if not isinstance(child.op, ALLOWED_BINOPS):
                raise UnsafeExpression("不支持的运算符: " + type(child.op).__name__)
            continue
        if isinstance(child, ast.UnaryOp):
            if not isinstance(child.op, ALLOWED_UNARYOPS):
                raise UnsafeExpression("不支持的一元运算: " + type(child.op).__name__)
            continue
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Name) or child.func.id not in ALLOWED_FUNCS:
                raise UnsafeExpression("不支持的函数调用")
            if child.keywords:
                raise UnsafeExpression("函数调用不允许关键字参数")
            continue
        if isinstance(child, ast.Name):
            if child.id not in allowed_names:
                raise UnsafeExpression("未知名称: " + child.id)
            continue
        if isinstance(child, ast.Constant):
            if not isinstance(child.value, (int, float)):
                raise UnsafeExpression("只允许数值常量")
            continue
        if isinstance(child, (ast.Load, ast.Store, ast.Del)):
            continue
        if isinstance(child, (ast.operator, ast.unaryop, ast.cmpop, ast.boolop, ast.expr_context)):
            # 运算符与上下文节点不含可执行内容；安全性由 BinOp / UnaryOp / Call 三个分支保证
            continue
        raise UnsafeExpression("不支持的语法节点: " + type(child).__name__)


def compile_formula(expr: str, variables: Iterable[str]):
    # 把公式字符串编译成可对 numpy 数组求值的函数。

#     返回 callable(env: Mapping[str, np.ndarray]) -> np.ndarray
# 
    if not isinstance(expr, str) or not expr.strip():
        raise UnsafeExpression("公式为空")
    if len(expr) > 2000:
        raise UnsafeExpression("公式过长")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression("公式语法错误: " + str(exc)) from exc
    _check(tree, variables)
    code = compile(tree, "<formula>", "eval")

    def evaluate(env: Mapping[str, np.ndarray]) -> np.ndarray:
        scope: Dict[str, object] = {}
        scope.update(ALLOWED_FUNCS)
        scope.update(ALLOWED_CONSTS)
        for key, value in env.items():
            if key not in variables:
                raise UnsafeExpression("环境包含未声明变量: " + key)
            scope[key] = value
        with np.errstate(all="ignore"):
            out = eval(code, {"__builtins__": {}}, scope)  # noqa: S307 - AST 已白名单校验
        return np.asarray(out, dtype=float)

    return evaluate


def parse_formula(expr: str, variables: Iterable[str]) -> ast.Expression:
    # 返回已通过白名单校验的 AST，供量纲分析复用。
    #
    # 缺陷修复（由 examples/adversarial_suite.py 的"语法错误公式"用例发现）：
    # 这里原来直接 ast.parse，语法错误会抛出**未捕获**的 SyntaxError，
    # 使整条验证流水线崩掉，而不是把这次调用判为"表达式不可用"。
    # compile_formula 一直都捕获 SyntaxError，parse_formula 漏了——两条路径行为不一致。
    if not isinstance(expr, str) or not expr.strip():
        raise UnsafeExpression("公式为空")
    if len(expr) > 2000:
        raise UnsafeExpression("公式过长")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression("公式语法错误: " + str(exc)) from exc
    _check(tree, variables)
    return tree


def is_safe(expr: str, variables: Iterable[str]) -> bool:
    try:
        parse_formula(expr, variables)
        return True
    except (UnsafeExpression, SyntaxError, ValueError):
        return False