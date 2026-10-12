# -*- coding: utf-8 -*-
"""把项目说明书 Markdown 转成 docx（再由 LibreOffice 转 PDF）。

为什么自己写而不是找现成工具：本机只有 numpy/python-docx 等办公库，没有 pandoc；
说明书里只有标题、表格、列表、引用与内联标记这几种结构，自己解析比装工具的代价小，
且能控制中文字体（只设 font.name 对中文不起作用，必须同时设 w:eastAsia）。

用法：python packaging/make_spec_pdf.py --source 01_项目说明书_定稿.md --out <目录>
"""
import argparse
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

BODY = "宋体"
HEAD = "黑体"
MONO = "Consolas"
TEXT_WIDTH_CM = 17.0

TICK = chr(96)
CODE_RE = re.compile(TICK + "([^" + TICK + "]+)" + TICK)
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
TOKEN_RE = re.compile("(" + TICK + "[^" + TICK + "]+" + TICK + "|\\*\\*[^*]+\\*\\*)")
# 缩进式代码块：Markdown 里 4 空格缩进即预格式。本项目用它画 ASCII 架构图，
# 图中夹着只缩进 2 空格的行，所以"续行"门槛放宽到 2 空格，并在遇到空行/顶格行时结束。
INDENT_START = re.compile(r"^ {4,}\S")
INDENT_CONT = re.compile(r"^ {2,}\S")
BOX_CHARS = "┌┐└┘├┤┬┴┼│─▼▲◄►"
MONO_CJK = "NSimSun"


def cjk(run, name, size, bold=False, italic=False, mono=False):
    run.font.name = MONO if mono else name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def add_runs(paragraph, text, size=10.5, base_bold=False):
    """把 **粗体** 与 `代码` 拆成多个 run，保留内联格式。"""
    for piece in TOKEN_RE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            cjk(paragraph.add_run(piece[2:-2]), BODY, size, True)
        elif piece.startswith(TICK) and piece.endswith(TICK) and len(piece) > 2:
            cjk(paragraph.add_run(piece[1:-1]), BODY, size - 0.5, base_bold, mono=True)
        else:
            cjk(paragraph.add_run(piece), BODY, size, base_bold)
    return paragraph


def para(document, text, size=10.5, bold=False, font=BODY, style=None, before=0, after=6,
         indent=0.0, align=None):
    paragraph = document.add_paragraph(style=style)
    add_runs(paragraph, text, size, bold) if not bold else cjk(paragraph.add_run(text), font, size, True)
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    if indent:
        paragraph.paragraph_format.left_indent = Cm(indent)
    if align is not None:
        paragraph.alignment = align
    return paragraph


def heading(document, text, level):
    sizes = {1: 18, 2: 14, 3: 12}
    paragraph = document.add_paragraph()
    cjk(paragraph.add_run(text), HEAD, sizes.get(level, 12), True)
    paragraph.paragraph_format.space_before = Pt(12 if level > 1 else 0)
    paragraph.paragraph_format.space_after = Pt(6)
    # 标题不许成为页尾孤行（"4.1 总体架构"曾独自留在上一页）。
    paragraph.paragraph_format.keep_with_next = True
    if level == 1:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return paragraph


def add_table(document, rows):
    """rows[0] 是表头；按各列文本长度分配列宽，总和不超过正文宽度。"""
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    lengths = []
    for index in range(cols):
        longest = max(len(r[index]) for r in rows)
        lengths.append(max(longest, 4))
    total = sum(lengths)
    widths = [max(1.8, TEXT_WIDTH_CM * value / total) for value in lengths]
    scale = TEXT_WIDTH_CM / sum(widths)
    widths = [w * scale for w in widths]

    table = document.add_table(rows=0, cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].width = Cm(widths[index])
            paragraph = cells[index].paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            if row_index == 0:
                cjk(paragraph.add_run(value.strip()), HEAD, 10, True)
            else:
                add_runs(paragraph, value.strip(), 9.5)
    document.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def parse_table(lines, start):
    rows = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        raw = lines[index].strip().strip("|")
        cells = [c.strip() for c in raw.split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c or "---") for c in cells):
            rows.append(cells)
        index += 1
    return rows, index


def add_pre(document, block):
    """等宽预格式：ASCII 图必须逐字对齐，字号按最长行自动收缩。"""
    longest = max(len(line) for line in block)
    # 17cm 正文宽；CJK 等宽下取 0.62em 作保守估计
    size = min(8.8, TEXT_WIDTH_CM * 28.35 / (longest * 0.62))
    size = max(6.5, round(size, 1))
    first = True
    for line in block:
        paragraph = document.add_paragraph()
        run = paragraph.add_run(line.rstrip())
        run.font.name = MONO_CJK
        run.font.size = Pt(size)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO_CJK)
        paragraph.paragraph_format.space_before = Pt(4 if first else 0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        # 图不能跨页拆开：整块与下一行同页（末行除外，末尾另加空段收尾）。
        paragraph.paragraph_format.keep_with_next = True
        first = False
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def build(markdown_path, out_path):
    lines = open(markdown_path, encoding="utf-8").read().split("\n")
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = BODY
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY)
    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)

    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if INDENT_START.match(line):
            block = []
            while index < len(lines):
                current = lines[index]
                if current.strip() and INDENT_CONT.match(current):
                    block.append(current)
                    index += 1
                elif current.strip() and any(ch in current for ch in BOX_CHARS):
                    block.append(current)
                    index += 1
                else:
                    break
            if block:
                add_pre(document, block)
            continue
        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            if rows:
                add_table(document, rows)
            continue
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading(document, stripped.lstrip("#").strip(), min(level, 3))
            index += 1
            continue
        if stripped.startswith(">"):
            para(document, stripped.lstrip(">").strip(), size=9.5, indent=0.6, after=4)
            index += 1
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        numbered = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if bullet:
            paragraph = para(document, bullet.group(1), indent=0.75, after=3)
            paragraph.paragraph_format.first_line_indent = Cm(-0.4)
            paragraph.runs[0].text = "• " + paragraph.runs[0].text if paragraph.runs else paragraph.runs
            index += 1
            continue
        if numbered:
            paragraph = para(document, numbered.group(2), indent=0.75, after=3)
            paragraph.paragraph_format.first_line_indent = Cm(-0.4)
            if paragraph.runs:
                paragraph.runs[0].text = numbered.group(1) + ". " + paragraph.runs[0].text
            index += 1
            continue
        if stripped == "---":
            index += 1
            continue
        para(document, stripped)
        index += 1

    document.save(out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", default="项目说明书")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, args.name + ".docx")
    build(args.source, out_path)
    print("已生成:", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())