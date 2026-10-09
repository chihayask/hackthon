# -*- coding: utf-8 -*-
# 由 Markdown 初稿生成 Word 版参赛材料。
# 用法: python examples/build_docx.py
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'FORMULA-AGH_参赛材料.docx')

SOURCES = [
    ('第一部分  项目说明书', '01_项目说明书_定稿.md'),
    ('第二部分  执行计划与分工', '02_执行计划与分工_初稿.md'),
    ('第三部分  运行证据与提交清单', '03_运行证据与提交清单_定稿.md'),
    ('第四部分  视频脚本与路演提纲', '04_视频脚本与路演提纲_定稿.md'),
    ('第五部分  AGH 事实核对与路线修正', '06_AGH事实核对与路线修正.md'),
    ('第六部分  路演提纲与讲稿', '05_路演提纲与讲稿_定稿.md'),
]
APPENDIX = [
    ('附录A  数据卡', os.path.join('docs', '数据卡.md')),
    ('附录B  运行与验证说明', os.path.join('docs', '运行与验证.md')),
    ('附录C  素材来源清单', os.path.join('docs', '素材来源清单.md')),
    ('附录D  AGH Skill 正文', os.path.join('skills', 'formula-discovery-loop', 'SKILL.md')),
    # 以下五项是 M3（机械专业成员）的交付物
    ('附录E  标准答案物理审查', os.path.join('docs', '标准答案物理审查.md')),
    ('附录F  外推崩溃分析', os.path.join('evidence', '外推崩溃分析.md')),
    ('附录G  负对照实验设计与结果', os.path.join('evidence', '负对照实验设计与结果.md')),
    ('附录H  判别力对照与阈值敏感性', os.path.join('evidence', '判别力与阈值敏感性.md')),
    ('附录I  失败案例档案', os.path.join('evidence', 'failures', '失败案例档案.md')),
    ('附录J  交叉评审发现', os.path.join('evidence', '交叉评审发现.md')),
    ('附录K  尺度检验说明', os.path.join('docs', '尺度检验说明.md')),
    ('附录L  量纲检查工具验收报告', os.path.join('evidence', '量纲检验验收.md')),
    ('附录M  交叉评审意见（M3 → M1/M2）', os.path.join('evidence', '交叉评审_M3意见.md')),
]

doc = Document()


def set_style(name, ascii_font, ea_font, size=None, bold=None):
    st = doc.styles[name]
    st.font.name = ascii_font
    if size is not None:
        st.font.size = Pt(size)
    if bold is not None:
        st.font.bold = bold
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = rpr.makeelement(qn('w:rFonts'), {})
        rpr.append(rf)
    rf.set(qn('w:ascii'), ascii_font)
    rf.set(qn('w:hAnsi'), ascii_font)
    rf.set(qn('w:eastAsia'), ea_font)


set_style('Normal', 'Times New Roman', '宋体', 11)
for lvl, sz in ((1, 16), (2, 14), (3, 12), (4, 11)):
    set_style('Heading %d' % lvl, 'Times New Roman', '黑体', sz, True)
    doc.styles['Heading %d' % lvl].font.color.rgb = RGBColor(0x1F, 0x28, 0x37)
sec = doc.sections[0]
sec.left_margin = Cm(2.0)
sec.right_margin = Cm(2.0)
sec.top_margin = Cm(2.4)
sec.bottom_margin = Cm(2.4)

ZWS = chr(0x200B)


def soften(t):
    # 在长串中插入零宽空格，帮助换行，避免表格被撑宽
    t = t.replace('/', '/' + ZWS)
    for tok in ('AgnesHarness', 'formula_agh', 'reference.json', 'make_physics_tasks'):
        if len(tok) > 6:
            t = t.replace(tok, tok[:4] + ZWS + tok[4:])
    return t


def add_runs(p, text):
    for part in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**') and len(part) > 4:
            r = p.add_run(soften(part[2:-2]))
            r.bold = True
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            r = p.add_run(soften(part[1:-1]))
            r.font.name = 'Consolas'
            r.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        else:
            p.add_run(soften(part))


def para(text='', indent=None, space_after=4, italic=False):
    p = doc.add_paragraph()
    if indent is not None:
        p.paragraph_format.left_indent = Cm(indent)
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        add_runs(p, text)
    for r in p.runs:
        r.italic = italic
    return p


def code_block(lines):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(chr(10).join(lines))
    r.font.name = 'Consolas'
    r.font.size = Pt(8.5)
    r.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')


def set_widths(t, widths):
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = tblPr.makeelement(qn('w:tblLayout'), {qn('w:type'): 'fixed'})
    tblPr.append(layout)
    for tag in ('w:tblW', 'w:tblInd'):
        old = tblPr.find(qn(tag))
        if old is not None:
            tblPr.remove(old)
    total = int(sum(widths) * 567)
    tblPr.append(tblPr.makeelement(qn('w:tblW'), {qn('w:type'): 'dxa', qn('w:w'): str(total)}))
    tblPr.append(tblPr.makeelement(qn('w:tblInd'), {qn('w:type'): 'dxa', qn('w:w'): '0'}))
    for row in t.rows:
        for i, c in enumerate(row.cells):
            if i < len(widths):
                c.width = Cm(widths[i])
    for i, col in enumerate(t.columns):
        if i < len(widths):
            col.width = Cm(widths[i])


def add_table(rows):
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncols)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j in range(ncols):
            txt = row[j] if j < len(row) else ''
            cp = cells[j].paragraphs[0]
            cp.paragraph_format.space_after = Pt(2)
            add_runs(cp, txt)
            for r in cp.runs:
                r.font.size = Pt(9)
                if i == 0:
                    r.bold = True
    total = 17.0
    if ncols == 2:
        widths = [4.4, total - 4.4]
    elif ncols == 3:
        widths = [3.6, 5.4, total - 9.0]
    elif ncols == 4:
        widths = [3.0, 4.6, 4.2, total - 11.8]
    elif ncols == 5:
        widths = [2.6, 2.2, 4.6, 2.2, total - 11.6]
    else:
        widths = [total / ncols] * ncols
    set_widths(t, widths)
    para('', space_after=2)


def emit_markdown(text, base_dir=None):
    lines = text.split(chr(10))
    base_dir = base_dir or ROOT
    i = 0
    in_code = False
    buf = []
    tbl = []
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith('```'):
            if in_code:
                code_block(buf)
                buf = []
                in_code = False
            else:
                if tbl:
                    add_table(tbl)
                    tbl = []
                in_code = True
            i += 1
            continue
        if in_code:
            buf.append(ln)
            i += 1
            continue
        s = ln.strip()
        if s.startswith('|'):
            cells = [c.strip() for c in s.strip('|').split('|')]
            if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c != ''):
                i += 1
                continue
            tbl.append(cells)
            i += 1
            continue
        if tbl:
            add_table(tbl)
            tbl = []
        if s == '':
            i += 1
            continue
        if s == '---':
            para('_' * 40, space_after=6)
            i += 1
            continue
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', s)
        if m:
            # 图片路径相对于它所在的 Markdown 文件，不是仓库根目录。
            img = os.path.join(base_dir, m.group(2))
            if os.path.exists(img):
                doc.add_picture(img, width=Cm(16.0))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap = doc.add_paragraph()
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap.paragraph_format.space_after = Pt(8)
                r = cap.add_run(m.group(1))
                r.italic = True
                r.font.size = Pt(9)
            else:
                para('[缺图] ' + m.group(2), indent=0.7)
            i += 1
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            doc.add_heading(re.sub(r'[*`]', '', m.group(2)), level=min(len(m.group(1)) + 1, 4))
            i += 1
            continue
        if s.startswith('>'):
            para(s.lstrip('> ').strip(), indent=0.7, space_after=3, italic=True)
            i += 1
            continue
        m = re.match(r'^[-*]\s+(.*)$', s)
        if m:
            para('· ' + m.group(1), indent=0.7, space_after=2)
            i += 1
            continue
        m = re.match(r'^(\d+)\.\s+(.*)$', s)
        if m:
            para(m.group(1) + '. ' + m.group(2), indent=0.7, space_after=2)
            i += 1
            continue
        if s.startswith('- [ ]'):
            para('□ ' + s[5:].strip(), indent=0.7, space_after=2)
            i += 1
            continue
        para(s)
        i += 1
    if tbl:
        add_table(tbl)
    if in_code and buf:
        code_block(buf)


def cover():
    lines = [
        '2026年江苏省AI+科学与工程',
        '创新实践黑客松（高校组）',
        '参赛材料',
    ]
    for idx, t in enumerate(lines):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(t)
        r.bold = True
        r.font.size = Pt(14 if idx < 2 else 11)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run('FORMULA-AGH')
    r.bold = True
    r.font.size = Pt(20)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run('面向公开科学数据的可验证公式发现智能体')
    r.font.size = Pt(12)
    info = [
        ('主赛道', 'B. 数学计算与科研智能体'),
        ('具体方向', 'B3. 科学计算与仿真（辅 B2 算法发现与组合优化）'),
        ('组别', '本科生组'),
        ('队伍', '3 人（人工智能 / 计算机 / 机械 各 1 名）'),
        ('智能体底座', 'AgnesHarness（AGH）'),
        ('模型调用', '仅使用 Agnes 模型'),
        ('数据来源', '公开物理定律基准，逐条附来源'),
        ('任务集规模', '22 个任务（基础 13 / 挑战 9）'),
        ('当前验证', '自测 24/24；参考式 22/22；结构错误式 22/22 被拒；'
                     '物理尺度判据 106 条；负对照 80 次尝试零编造'),
        ('提交截止', '2026-10-15 12:00'),
    ]
    for k, v in info:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(k + '：')
        r.bold = True
        p.add_run(soften(v))


def main():
    cover()
    doc.add_page_break()
    for title, rel in SOURCES + APPENDIX:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print('skip (missing):', rel)
            continue
        doc.add_heading(title, level=1)
        with open(path, encoding='utf-8') as fh:
            emit_markdown(fh.read(), base_dir=os.path.dirname(path))
        doc.add_page_break()
    doc.save(OUT)
    print('saved', OUT)
    print('paragraphs', len(doc.paragraphs), 'tables', len(doc.tables))
    return 0


if __name__ == '__main__':
    sys.exit(main())