# -*- coding: utf-8 -*-
"""量纲分析：判断一个公式在物理量纲上是否成立。

这是三重验证里"机械专业成员"的主场：拟合得再好，量纲不对就是荒谬公式。
本模块只做量纲（不是数值单位换算），采用 SI 七个基本量纲。
"""
from __future__ import annotations

import ast
import re
from fractions import Fraction
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .safe_eval import ALLOWED_FUNCS, UnsafeExpression, parse_formula

# 七个 SI 基本量纲
BASE_DIMS = ("L", "M", "T", "I", "Theta", "N", "J")
Dim = Tuple[Fraction, ...]

DIMENSIONLESS: Dim = tuple(Fraction(0) for _ in BASE_DIMS)


def dim(*pairs: Tuple[str, object]) -> Dim:
    vec = [Fraction(0) for _ in BASE_DIMS]
    for name, power in pairs:
        vec[BASE_DIMS.index(name)] = Fraction(power)
    return tuple(vec)


def _format(d: Dim) -> str:
    parts = []
    for name, power in zip(BASE_DIMS, d):
        if power != 0:
            parts.append(name if power == 1 else name + "^" + str(power))
    return "1" if not parts else "·".join(parts)


def _mul(a: Dim, b: Dim, sign: int = 1) -> Dim:
    return tuple(x + sign * y for x, y in zip(a, b))


def _scale(a: Dim, factor: object) -> Dim:
    f = Fraction(factor)
    return tuple(x * f for x in a)


# 常见单位 -> 量纲（够覆盖公开基准里的机械/热学/电磁公式）
UNIT_TABLE: Dict[str, Dim] = {
    "-": DIMENSIONLESS, "1": DIMENSIONLESS, "": DIMENSIONLESS,
    "m": dim(("L", 1)), "kg": dim(("M", 1)), "g": dim(("M", 1)),
    "s": dim(("T", 1)), "A": dim(("I", 1)), "K": dim(("Theta", 1)),
    "mol": dim(("N", 1)), "cd": dim(("J", 1)),
    "N": dim(("M", 1), ("L", 1), ("T", -2)),
    "J": dim(("M", 1), ("L", 2), ("T", -2)),
    "W": dim(("M", 1), ("L", 2), ("T", -3)),
    "Pa": dim(("M", 1), ("L", -1), ("T", -2)),
    "Hz": dim(("T", -1)), "rad": DIMENSIONLESS,
    "C": dim(("I", 1), ("T", 1)), "V": dim(("M", 1), ("L", 2), ("T", -3), ("I", -1)),
    "m/s": dim(("L", 1), ("T", -1)),
    "m/s^2": dim(("L", 1), ("T", -2)),
    "m/s2": dim(("L", 1), ("T", -2)),
    "kg/m^3": dim(("M", 1), ("L", -3)),
    "J/K": dim(("M", 1), ("L", 2), ("T", -2), ("Theta", -1)),
    "J/(kg*K)": dim(("L", 2), ("T", -2), ("Theta", -1)),
    "N/m": dim(("M", 1), ("T", -2)),
    "W/m^2": dim(("M", 1), ("T", -3)),
    # --- 以下为 2026-10 契约校验发现缺口后补充（原有 8 个任务的量纲检验被静默跳过）---
    # 电磁学常用导出单位
    "T": dim(("M", 1), ("T", -2), ("I", -1)),          # 特斯拉
    "Wb": dim(("M", 1), ("L", 2), ("T", -2), ("I", -1)),  # 韦伯
    "F": dim(("M", -1), ("L", -2), ("T", 4), ("I", 2)),   # 法拉
    "H": dim(("M", 1), ("L", 2), ("T", -2), ("I", -2)),   # 亨利
    "ohm": dim(("M", 1), ("L", 2), ("T", -3), ("I", -2)),  # 欧姆
    "\u03a9": dim(("M", 1), ("L", 2), ("T", -3), ("I", -2)),  # 欧姆（符号）
    "S": dim(("M", -1), ("L", -2), ("T", 3), ("I", 2)),   # 西门子
}


class UnknownUnit(KeyError):
    """单位字符串不在单位表内。"""


# --------------------------------------------------------------------------
# 复合单位解析
# --------------------------------------------------------------------------
# 背景（M2 契约校验发现的真实缺口）：改造前 unit_dimension 只做精确字符串查表，
# 于是 "m^3"、"F/m"、"H/m"、"m^2"、"ohm"、"T" 这些完全正常的单位会被判为
# "未知单位"，而 _check_dimension 遇到未知单位时会**静默跳过**该任务的量纲检验。
# 结果是 22 个任务里有 8 个的量纲门形同虚设——正是怀疑清单第 3 条
# "量纲检验会不会被绕过" 的真实案例。现改为：查表优先，落空则做复合单位解析。

_UNIT_TOKEN = re.compile(r"\s*(\^|\*|/|\(|\)|[A-Za-z_\u00b5\u03a9][A-Za-z_\u00b5\u03a9]*|-?\d+)")


def _tokenize_unit(text: str) -> List[str]:
    tokens: List[str] = []
    pos = 0
    while pos < len(text):
        match = _UNIT_TOKEN.match(text, pos)
        if match is None:
            raise UnknownUnit(text)
        tokens.append(match.group(1))
        pos = match.end()
    if not tokens:
        raise UnknownUnit(text)
    return tokens


class _UnitParser:
    """受限文法： expr := term (('*'|'/') term)* ; term := factor ('^' int)? ;

    factor := NAME | '(' expr ')' | 数字
    """

    def __init__(self, tokens: List[str], original: str) -> None:
        self.tokens = tokens
        self.original = original
        self.pos = 0

    def _peek(self) -> Optional[str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> str:
        token = self._peek()
        if token is None:
            raise UnknownUnit(self.original)
        self.pos += 1
        return token

    def parse(self) -> Dim:
        value = self._expr()
        if self._peek() is not None:
            raise UnknownUnit(self.original)
        return value

    def _expr(self) -> Dim:
        value = self._term()
        while self._peek() in ("*", "/"):
            operator = self._next()
            right = self._term()
            value = _mul(value, right, 1 if operator == "*" else -1)
        return value

    def _term(self) -> Dim:
        value = self._factor()
        if self._peek() == "^":
            self._next()
            exponent = self._next()
            try:
                value = _scale(value, Fraction(exponent))
            except (ValueError, ZeroDivisionError):
                raise UnknownUnit(self.original)
        return value

    def _factor(self) -> Dim:
        token = self._peek()
        if token == "(":
            self._next()
            value = self._expr()
            if self._next() != ")":
                raise UnknownUnit(self.original)
            return value
        token = self._next()
        if token in UNIT_TABLE:
            return UNIT_TABLE[token]
        if token.lstrip("-").isdigit():
            return DIMENSIONLESS
        raise UnknownUnit(token)


def parse_unit(text: str) -> Dim:
    """把单位字符串解析成量纲：先查表（快路径），再按复合表达式解析。"""
    key = (text or "").strip()
    if key in UNIT_TABLE:
        return UNIT_TABLE[key]
    if key == "":
        return DIMENSIONLESS
    return _UnitParser(_tokenize_unit(key), key).parse()


def unit_dimension(unit: str) -> Dim:
    return parse_unit(unit)


class DimensionError(ValueError):
    """公式在量纲上不成立。"""


def infer(node: ast.AST, var_dims: Mapping[str, Dim]) -> Dim:
    """对表达式做量纲推断；不成立时抛 DimensionError。"""
    if isinstance(node, ast.Expression):
        return infer(node.body, var_dims)
    if isinstance(node, ast.Constant):
        return DIMENSIONLESS
    if isinstance(node, ast.Name):
        if node.id in var_dims:
            return var_dims[node.id]
        if node.id in ("pi", "e"):
            return DIMENSIONLESS
        raise DimensionError("未知符号: " + node.id)
    if isinstance(node, ast.UnaryOp):
        return infer(node.operand, var_dims)
    if isinstance(node, ast.BinOp):
        left = infer(node.left, var_dims)
        right = infer(node.right, var_dims)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if left != right:
                raise DimensionError("加减法两侧量纲不同: " + _format(left) + " vs " + _format(right))
            return left
        if isinstance(node.op, ast.Mult):
            return _mul(left, right, 1)
        if isinstance(node.op, ast.Div):
            return _mul(left, right, -1)
        if isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or not isinstance(node.right.value, (int, float)):
                raise DimensionError("指数必须是数值常量")
            return _scale(left, node.right.value)
        raise DimensionError("不支持的运算")
    if isinstance(node, ast.Call):
        fname = node.func.id
        if fname not in ALLOWED_FUNCS:
            raise DimensionError("不支持的函数: " + fname)
        args = node.args
        if len(args) != 1:
            raise DimensionError(fname + " 只接受一个参数")
        inner = infer(args[0], var_dims)
        if fname == "sqrt":
            return _scale(inner, Fraction(1, 2))
        if inner != DIMENSIONLESS:
            raise DimensionError(fname + " 的参数必须无量纲，实际为 " + _format(inner))
        return DIMENSIONLESS
    if isinstance(node, ast.Compare) or isinstance(node, ast.BoolOp):
        raise DimensionError("公式不允许比较或逻辑运算")
    raise DimensionError("不支持的语法节点: " + type(node).__name__)


def infer_from_source(expr: str, variable_units: Mapping[str, str],
                       free_parameters: Optional[Sequence[str]] = None) -> Dim:
    """推断公式的量纲。

    自由参数在 meta.json 里没有声明单位（它们的物理身份由拟合决定，例如万有引力常数
    的指数/量级），所以按**无量纲占位**进入推断：这样仍然能抓住"长度加时间"这类
    结构性错误，但不会因为参数可吸收单位而误杀正确公式。调用方在有自由参数时只
    使用这一次推断的**结构一致性**结论，不使用返回值做严格比对。
    """
    var_dims: Dict[str, Dim] = {}
    for name, unit in variable_units.items():
        var_dims[name] = unit_dimension(unit)
    allowed = list(variable_units.keys())
    for raw in (free_parameters or []):
        name = str(raw)
        if name in var_dims:
            continue
        var_dims[name] = dim()
        allowed.append(name)
    tree = parse_formula(expr, allowed)
    return infer(tree, var_dims)


def expected_dimension(y_unit: Optional[str]) -> Optional[Dim]:
    if y_unit is None or not str(y_unit).strip():
        return None
    try:
        return unit_dimension(str(y_unit))
    except UnknownUnit:
        return None