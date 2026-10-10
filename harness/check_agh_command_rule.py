# -*- coding: utf-8 -*-
"""校验 AGH 预设里 allow 规则的形状。

为什么需要它：AGH 的命令策略校验器要求**每一条 allow 规则的 argv 必须以
"绝对路径形状"开头**（源码见 packages/host/src/command-policy.ts 的 checkCommandRule）。
不满足时会话根本创建不起来，而且守护进程**故意不把异常消息写进日志**，
客户端只看到 INTERNAL_ERROR (-32603)。这个坑当初花了几小时定位：
先试 argv: 'formula_agh|run_verify'（报"未锚定在路径开头"），
再试 argv: '^(?:cmd ...)'（报"allow 规则必须要求绝对路径"）。

本脚本把那条规则固化成可执行的检查：**改预设之后先跑它，再重建**。

用法：
    python harness/check_agh_command_rule.py <preset.yaml> [...]
    python harness/check_agh_command_rule.py --argv "^[Ee]:[\\/]fagh[\\/]harness[\\/]run_verify\\.cmd(?: [^&|;<>]*)?$"

注意 argv 是**正则**而不是字面路径，所以判断的是"去掉前导 ^ 之后是否以绝对路径形状开头"。
"""
import argparse
import re
import sys

_BS = chr(92)                      # 反斜杠：用 chr() 构造，避免源码里的转义地狱
SLASH = "/"

# "绝对路径形状"的四种写法（正则前缀，用来匹配 argv 正则去掉 ^ 之后的正文）
_BS = chr(92)
SLASH = chr(47)
CMDNAME_RE = '^[A-Za-z][A-Za-z0-9_' + _BS + '-]*'
DRIVE_RE = '^[A-Za-z]:'
# AGH 认可的「绝对路径形状」。argv 本身是正则，所以这里判断的是去掉前导 ^ 之后的正文：
#   /...   \\server   X:...   [Ee]:...   [\\/]...
LITERAL_ABS = (SLASH, _BS + _BS)
DRIVE_CLASS_RE = '^' + _BS + '[[^' + _BS + ']]+' + _BS + ']:'  # 允许 [A-Za-z] 这种带范围的字符类
SEP_CLASS_RE = '^' + _BS + '[' + '[' + _BS + _BS + SLASH + ']+' + _BS + ']'


def starts_with_absolute(body):
    if body.startswith(LITERAL_ABS):
        return True
    if re.match(DRIVE_RE, body):
        return True
    if re.match(DRIVE_CLASS_RE, body):
        return True
    if re.match(SEP_CLASS_RE, body):
        return True
    return False


def check_argv(pattern):
    """返回 (ok, 说明)。"""
    errors = []
    if pattern.startswith("^("):
        errors.append("以 ^(...) 分组开头，不是路径形状")
    body = pattern[1:] if pattern.startswith("^") else pattern
    if re.match(CMDNAME_RE, body) and not re.match(DRIVE_RE, body):
        errors.append("以命令名开头，不是路径形状")
    if not starts_with_absolute(body):
        errors.append("没有以绝对路径形状开头（需 /、" + _BS + "、X:、[Xx]: 或 [\\/]）")
    try:
        re.compile(pattern)
    except re.error as exc:
        errors.append("正则本身不合法: %s" % exc)
    if errors:
        return False, "；".join(errors)
    return True, "形状合法"


def parse_presets(paths):
    """朴素解析 preset yaml 的 allow 规则：找 tool / argv / action 三项。"""
    rules = []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        tool = argv = None
        for idx, raw in enumerate(lines, 1):
            line = raw.rstrip()
            m = re.search("^" + _BS + "s*-?" + _BS + "s*tool:" + _BS + "s*'?([A-Za-z0-9_-]+)'?", line)
            if m:
                tool = m.group(1)
            m = re.search("^" + _BS + "s*argv:" + _BS + "s*'?([^'" + _BS + "n]+?)'?" + _BS + "s*$", line)
            if m:
                argv = m.group(1)
            m = re.search("^" + _BS + "s*action:" + _BS + "s*'?([a-z-]+)'?", line)
            if m:
                rules.append((path, idx, tool, argv, m.group(1)))
                tool = argv = None
    return rules


def main(argv=None):
    ap = argparse.ArgumentParser(description="校验 AGH allow 规则的绝对路径形状要求")
    ap.add_argument("presets", nargs="*", help="preset yaml 文件")
    ap.add_argument("--argv", action="append", default=[], help="直接校验一个 argv 正则")
    args = ap.parse_args(argv)

    problems = []
    checked = 0
    for pattern in args.argv:
        checked += 1
        ok, why = check_argv(pattern)
        print(("OK   " if ok else "FAIL ") + pattern[:60] + "  :: " + why)
        if not ok:
            problems.append(pattern)
    for path, lineno, tool, pattern, action in parse_presets(args.presets):
        if action != "allow" or not pattern:
            continue
        checked += 1
        ok, why = check_argv(pattern)
        print(("OK   " if ok else "FAIL ") + "%s:%d tool=%s" % (path, lineno, tool) + "  :: " + why)
        if not ok:
            problems.append(pattern)

    if not checked:
        print("没有可校验的规则：请给出 preset 文件，或用 --argv 指定一个正则。")
        return 0
    print("")
    if problems:
        print("结论：%d 条规则不合法。AGH 会在会话创建时失败，且不给可读错误。" % len(problems))
        return 2
    print("结论：全部 %d 条 allow 规则的 argv 形状合法。" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
