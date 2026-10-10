# -*- coding: utf-8 -*-
"""把 独立完成声明.md 生成一份 .docx（提交用）。

为什么单独写脚本而不是手工做一份：
提交件必须与仓库里的声明一致。手工编辑出来的 docx 一旦与 md 分叉，就无人知道哪份是准的——
本会话已经因为这类"同一事实两处写法"返工多次。脚本可重跑，内容以参数表为准。

用法：
    python packaging/make_declaration_docx.py --out <目录>
"""
import argparse
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt  # noqa: F401

BODY_FONT = "宋体"
HEAD_FONT = "黑体"

TITLE = "独立完成声明"

BASIS = ("依据《关于举办 2026 年江苏省 AI+科学与工程创新大赛黑客松（高校组）的通知》"
         "（苏智会〔2026〕60 号）六、作品提交与评审与九、注意事项："
         "参赛作品须由学生团队独立完成，并提交成员分工和独立完成声明；"
         "使用既有代码、第三方组件、数据及其他素材的，须如实说明来源和使用方式。")

NOTE = ("填写说明：姓名、学号、学校 / 学院与签名处由三名成员各自填写并手写签名；"
        "打印后签字，扫描件随作品一并提交。未签名前本声明不视为有效。")

SECTIONS = [
    ("一、作品信息", ["项", "内容"], [
        ["作品名称", "FORMULA-AGH · 可验证公式发现智能体"],
        ["组别", "本科生组"],
        ["报名方向", "AI4S 与科学实验 / 数学 AI 与算法发现 / Agent 与 Harness 工程"],
        ["运行底座", "Agnes Harness（AGH）"],
        ["模型调用", "仅使用 Agnes 模型（agnes-3.0-flash），未接入其他厂商模型"],
    ]),
    ("二、成员分工", ["成员", "姓名", "学号", "学校 / 学院", "专业", "承担工作"], [
        # 6 列在 A4 竖排下必须限宽，否则"承担工作"会被挤成一条窄缝
        ["成员一", "", "", "", "人工智能",
         "智能体底座与编排：AGH 接入、任务规划与工具调用接线、运行轨迹与证据导出"],
        ["成员二", "", "", "", "计算机科学与技术",
         "验证引擎与工程可靠性：三重验证、划分与评分脚本、一键复现、证据归档"],
        ["成员三", "", "", "", "机械设计制造及其自动化",
         "物理正确性与任务设计：任务集与难度分层、量纲/尺度检查、外推分析、文档与演示视频"],
    ]),
    ("四、第三方素材与来源（详见 docs/素材来源清单.md）", ["素材", "来源", "许可 / 使用方式"], [
        ["Agnes Harness（AGH）", "github.com/AgnesAI-Labs/agnes-harness",
         "Apache-2.0；作为运行底座使用，未修改其核心源码"],
        ["物理公式与变量语义", "各 tasks/<id>/meta.json 的 source 字段所列公开来源",
         "公开知识；公式为标准物理定律"],
        ["任务数据（22 个合成任务）", "由本队 examples/make_physics_tasks.py 依 meta 声明区间采样生成",
         "自产，可复现（SEED=20261008，N=400）"],
        ["真实公开数据（负对照）", "UCI Airfoil Self-Noise（id 291），NASA RP-1218",
         "UCI 公开数据集；仅用于负对照实验，脚本内含 sha256 校验"],
        ["numpy", "numpy.org", "BSD-3-Clause；唯一的第三方 Python 依赖"],
    ]),
    ("五、签名", ["成员", "姓名（正楷）", "签名", "日期"], [
        # 签名表留出手写空间
        ["成员一（人工智能）", "", "", ""],
        ["成员二（计算机科学与技术）", "", "", ""],
        ["成员三（机械设计制造及其自动化）", "", "", ""],
    ]),
]

STATEMENTS = [
    "本作品由上述三名队员在赛事期间独立完成，不存在代做、抄袭或挂名；",
    "每名成员均实际参与并承担上表所列职责；",
    "作品中的模型调用仅使用 Agnes 模型；",
    "作品使用 Agnes Harness（AGH）作为智能体运行与执行底座，由 AGH 连接数据、调用验证代码，"
    "形成「任务规划 → 能力调用 → 执行反馈 → 结果验证 → 异常处理」的完整闭环；",
    "使用既有代码、第三方组件、数据及其他素材的情况已逐条列明于 docs/素材来源清单.md，无隐瞒；",
    "提交的全部个人信息与学籍信息真实、准确、完整，接受赛事工作组的在校学生身份核验；",
    "已知悉：如存在信息不实、冒用身份、代做、抄袭或隐瞒第三方素材来源等情况，"
    "同意被取消参赛或获奖资格。",
]


def cjk(run, name, size, bold=False):
    """同时设置 ascii 与 eastAsia 字体：只设 run.font.name 对中文不起作用。"""
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def add_paragraph(document, text, size=10.5, bold=False, font=BODY_FONT, style=None,
                  space_after=6, indent=False):
    paragraph = document.add_paragraph(style=style)
    run = paragraph.add_run(text)
    cjk(run, font, size, bold)
    paragraph.paragraph_format.space_after = Pt(space_after)
    if indent:
        paragraph.paragraph_format.left_indent = Pt(18)
    return paragraph


def add_table(document, header, rows, widths=None):
    table = document.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, title in enumerate(header):
        cell = table.rows[0].cells[index]
        cell.text = ""
        cjk(cell.paragraphs[0].add_run(title), HEAD_FONT, 10.5, True)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = ""
            cjk(cells[index].paragraphs[0].add_run(str(value)), BODY_FONT, 10.5)
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = width
    document.add_paragraph()
    return table


def build(out_path):
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    # 提交件用 A4（python-docx 默认是 Letter，中文打印会走形）。
    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)

    title = document.add_heading("", level=0)
    cjk(title.add_run(TITLE), HEAD_FONT, 20, True)
    title.paragraph_format.space_after = Pt(10)

    add_paragraph(document, BASIS, size=9, space_after=8)
    add_paragraph(document, NOTE, size=10.5, bold=True, space_after=12)

    # 章节顺序必须与 md 一致：三（声明正文）夹在二与四之间。
    WIDTHS = {
        2: [Cm(4.2), Cm(12.4)],
        6: [Cm(1.9), Cm(2.6), Cm(2.6), Cm(3.0), Cm(2.6), Cm(4.1)],
        3: [Cm(4.4), Cm(6.6), Cm(5.6)],
    }
    for section_title, header, rows in SECTIONS:
        add_paragraph(document, section_title, size=13, bold=True, font=HEAD_FONT, space_after=6)
        add_table(document, header, rows, WIDTHS.get(len(header)))
        if section_title.startswith("二"):
            add_paragraph(document, "三、独立完成声明", size=13, bold=True,
                          font=HEAD_FONT, space_after=6)
            add_paragraph(document, "我们郑重声明：", space_after=4)
            for index, text in enumerate(STATEMENTS, start=1):
                add_paragraph(document, "%d. %s" % (index, text), space_after=4, indent=True)

    document.save(out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="生成 独立完成声明.docx")
    parser.add_argument("--out", required=True, help="输出目录")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    # 声明正文在第三节，插在第二节之后：按 SECTIONS 顺序输出，第三节单独处理。
    out_path = os.path.join(args.out, "独立完成声明.docx")
    build(out_path)
    print("已生成:", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
