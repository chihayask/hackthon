# -*- coding: utf-8 -*-
# 生成演示视频的全套前期素材（M3 交付 · 10-13）。
#
# 说明白一件事：本脚本**不生产视频文件**，本机没有 ffmpeg，也不应该用动画冒充运行画面。
# 它生产的是"录制前一天就该准备好的东西"：
#
#   1. evidence/video/seg-self-negation.log.txt   真实运行日志（自我否定那一段的原始素材）
#   2. evidence/video/seg-self-negation-log.png   该日志的忠实渲染（仅作剪辑与字幕对齐参考）
#   3. evidence/video/title-open.png / title-close.png  片头 / 片尾卡
#   4. evidence/video/subtitle.srt                字幕文件，可直接导入剪辑软件
#   5. evidence/video/录制执行清单.md              逐时间码的录制指令与预期输出
#   6. evidence/video/storyboard.html             单页分镜，用于彩排与走位
#
# 画面诚实性纪律：渲染图内部带一条说明带，写明"真实输出版本 / 非屏幕录像"。
# 正式视频里的 2:30—3:05 仍必须使用真实屏幕录像，这份渲染只作为备用与剪辑参考。
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from formula_agh.figures import Chart, DEFAULT_COLORS as C

VIDEO = os.path.join(ROOT, 'evidence', 'video')
PY = sys.executable
BT = chr(96)  # 反引号：Markdown 行内代码用

# 演示运行：先用三重验证给出"拟合看着还行、域外崩了"，
# 再用尺度检验给出"结构本身就错了"的物理理由。
DEMO_STEPS = [
    ('演示运行 1/2：三重验证（数值判据）',
     [PY, '-m', 'formula_agh', 'verify', '--task', 'tasks/phys-gravitation',
      '--formula', 'G*m1*m2/r', '--params', 'G',
      '--run-id', 'demo-video-self-negation-01', '--out', 'runs']),
    ('演示运行 2/2：尺度一致性检验（物理判据）',
     [PY, '-m', 'formula_agh.scale_checks', '--task', 'tasks/phys-gravitation',
      '--formula', 'G*m1*m2/r', '--params', 'G=6.674e-11',
      '--run-id', 'demo-video-self-negation-02', '--out', 'runs']),
]

SUBTITLES = [
    (0, 2, '科学研究里最耗时的一步，常常不是做实验，'),
    (2, 5, '而是从数据里猜出支配它的那条公式。'),
    (5, 11, '我们用的全部是公开数据，每个任务都附带学界公认的标准公式——对错可以被客观判定。'),
    (11, 17, 'FORMULA-AGH 用 AgnesHarness 作为智能体底座，自主完成从数据到公式的闭环。'),
    (17, 24, '我们的判据分三层：量纲问单位对不对，误差问数值准不准，尺度判据问物理性质对不对。'),
    (24, 31, '现在开始一次完整运行，全程不碰键盘。它先给数据做体检。'),
    (31, 39, '接着生成候选形式、拟合参数，并把结果交给这几道门。'),
    (39, 50, '注意这里：G 乘 m1 乘 m2 除以 r，它在数据上拟合得不差。'),
    (50, 60, '但物理判据指出——距离加倍，引力应该变成四分之一，这个式子给出的是二分之一。'),
    (60, 66, '错的不是数值，是物理性质。于是它否决了自己。'),
    (66, 74, '这一句"我错了"，是这个项目最重要的输出。'),
    (74, 83, '第二轮换成平方反比，四道门全部通过，全过程自动写进轨迹档案。'),
    (83, 94, '这张图我们最想给评委看：小角度近似在窄窗内误差只有百分之一点七，走出窗口变成百分之十三点四。'),
    (94, 101, '域内几乎看不出来的错误，才是数值拟合最危险的地方。'),
    (101, 110, '我们做了双向对照：22 个标准公式全部通过，22 个结构错误式全部被拒。'),
    (110, 118, '把阈值换成四组不同的值重算，结论都是 22 比 22，零误杀。'),
    (118, 128, '我们还做了负对照：喂进纯噪声，它说"没有发现公式"，80 次尝试零次编造。'),
    (128, 136, '一个会推翻自己的智能体，比一个永远正确的答案更值得信任。'),
]

CUES = [
    ('0:00—0:20', '黑底 + 公式浮现动画', '片头卡 title-open.png 直接叠化入场',
     '无需运行'),
    ('0:20—0:45', '数据卡与来源清单特写', '浏览器打开 docs/数据卡.md，滚动到任务清单表',
     '展示逐条可点击的维基来源链接'),
    ('0:45—1:05', '架构图缓慢推移', '用 01_项目说明书_定稿.md §4.1 的架构图',
     '注意架构图里已含"尺度判据 ×6 类"'),
    ('1:05—1:30', '三道门示意图', '用 evidence/figures/fig-discrimination.png 的前半段',
     '旁白与图同步，先只说"三层"'),
    ('1:30—2:00', '真实终端：数据体检', '录屏执行：python -m formula_agh validate-tasks --tasks tasks',
     '预期输出 ok: true，无 findings'),
    ('2:00—2:30', '真实终端：候选式与拟合指标', '录屏执行 examples/demo_agent.py --task phys-gravitation',
     '终端滚动，看到多轮假设'),
    ('2:30—3:05', '★ 自我否定（关键片段）',
     '录屏依次执行 segment 1 与 segment 2（详见执行清单下方命令）',
     '必须看到 scale-scaling-r 判 false；这段不能演，若未出现就换任务重跑'),
    ('3:05—3:25', '新假设通过 + 轨迹展开', '录屏执行 demo_agent.py --task phys-pendulum-exact',
     '展示 trajectory.jsonl 增长'),
    ('3:25—3:50', '外推崩溃图', '放映 evidence/figures/fig-extrap-phys-pendulum-exact-curve.png → -error.png',
     '两图切换，外推区红色高亮'),
    ('3:50—4:05', '判别力柱状图 + 决策平面', '放映 fig-discrimination.png → fig-error-plane.png',
     '柱子上的 22/22 数字要看清'),
    ('4:05—4:20', '负对照画面', '录屏执行 python examples/negative_control.py 的尾部输出',
     '看到"被采纳（= 编造）: 0 次"'),
    ('4:20—4:30', '片尾卡', 'title-close.png',
     '叠化收尾'),
]

SELF_NEGATION_COMMANDS = [
    ('python -m formula_agh verify --task tasks/phys-gravitation --formula "G*m1*m2/r" '
     '--params G --run-id demo-video-self-negation-01 --out runs'),
    ('python -m formula_agh.scale_checks --task tasks/phys-gravitation --formula "G*m1*m2/r" '
     '--params G=6.674e-11 --run-id demo-video-self-negation-02 --out runs'),
]


def run_demo():
    chunks = []
    for title, argv in DEMO_STEPS:
        chunks.append('=' * 78)
        chunks.append('# ' + title)
        chunks.append('# 命令： ' + ' '.join(_quote(a) for a in argv[1:]))
        chunks.append('=' * 78)
        env = dict(os.environ)
        env['PYTHONPATH'] = os.path.join(ROOT, 'src')
        env['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', env=env)
        chunks.append(proc.stdout.rstrip())
        if proc.stderr.strip():
            chunks.append('[stderr] ' + proc.stderr.strip()[:500])
        chunks.append('# 退出码： %d（1 = 该公式被否决，这是本次演示期望的结果）' % proc.returncode)
        chunks.append('')
    return chr(10).join(chunks)


def _quote(token):
    return '"%s"' % token if ' ' in token else token


def terminal_frame(text, path, width=1600, height=900, title='终端'):
    from PIL import Image, ImageDraw, ImageFont
    # 宋体（simsun.ttc）的 ASCII 宽度正好是汉字的一半，是最接近中文终端等宽效果的
    # 系统字体；Consolas 没有汉字字形，会把所有中文渲染成方框。
    size = 17
    font = bold = None
    for candidate in ('C:/Windows/Fonts/simsun.ttc', 'C:/Windows/Fonts/msyh.ttc',
                      'C:/Windows/Fonts/consola.ttf'):
        if not os.path.exists(candidate):
            continue
        try:
            font = ImageFont.truetype(candidate, size)
            # 说明带也用它：系统里的"粗体"变体未必带汉字字形，
            # 用错字体会把最关键的诚实声明渲染成方框。
            bold = font
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default(size)
        bold = font
    bg = (18, 22, 28)
    fg = (222, 230, 238)
    dim = (130, 145, 160)
    accent = (255, 150, 120)
    banner = (60, 45, 20)

    def columns(s):
        # 汉字占两列，ASCII 占一列——按显示宽度而不是字符个数折行。
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in s)

    lines = []
    for raw in text.split(chr(10)):
        while columns(raw) > 116:
            cut = 0
            col = 0
            for index, ch in enumerate(raw):
                col += 2 if ord(ch) > 0x2E80 else 1
                if col > 116:
                    break
                cut = index + 1
            lines.append(raw[:cut])
            raw = '    ' + raw[cut:]
        lines.append(raw)
    line_h = size + 6

    img = Image.new('RGB', (width, height), bg)
    draw = ImageDraw.Draw(img)
    # 顶部说明带：明确这不是屏幕录像，避免被误当成运行画面
    draw.rectangle([0, 0, width, 40], fill=banner)
    draw.text((16, 20), '真实 stdout 的忠实渲染 · 非屏幕录像 · 正式视频请使用真实录屏',
              fill=(255, 205, 150), font=bold, anchor='lm')
    draw.text((width - 16, 20), 'segment: ' + title, fill=(255, 205, 150), font=font, anchor='rm')
    y = 56
    visible = int((height - 70) / line_h)
    for line in lines[:visible]:
        colour = fg
        if line.startswith('#') or line.startswith('='):
            colour = dim
        if '"passed": false' in line or '"verdict": "rejected"' in line:
            colour = accent
        draw.text((16, y), line, fill=colour, font=font)
        y += line_h
    if len(lines) > visible:
        draw.text((16, height - 24), '……（完整日志见 seg-self-negation.log.txt，共 %d 行）'
                  % len(lines), fill=dim, font=font)
    img.save(path)


def title_card(path, heading, sub, footer, accent):
    from PIL import Image, ImageDraw, ImageFont
    width, height = 1920, 1080
    img = Image.new('RGB', (width, height), (16, 20, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, height - 14, width, height], fill=accent)
    try:
        big = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc', 96)
        mid = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 44)
        small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
    except OSError:
        big = mid = small = ImageFont.load_default(48)
    draw.text((width // 2, 400), heading, fill=(255, 255, 255), font=big, anchor='mm')
    draw.text((width // 2, 520), sub, fill=accent, font=mid, anchor='mm')
    draw.text((width // 2, 620), footer, fill=(160, 175, 190), font=small, anchor='mm')
    img.save(path)


def write_srt(path):
    out = []
    for index, (start, end, text) in enumerate(SUBTITLES, 1):
        out.append(str(index))
        out.append('%s --> %s' % (_ts(start), _ts(end)))
        out.append(text)
        out.append('')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(chr(10).join(out))


def _ts(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return '%02d:%02d:%02d,000' % (h, m, s)


def write_cue_sheet(path, log_name, frame_name):
    out = [
        '# 演示视频录制执行清单（M3 · 定稿）',
        '',
        '**目标时长 4 分 30 秒** ｜ **硬性要求**：含真实运行画面与一次自我否定片段。',
        '',
        '本清单把分镜表翻译成"每个时间码上具体做什么"。录屏时按顺序执行即可，',
        '不需要临场判断。字幕文件 ' + BT + 'subtitle.srt' + BT + ' 可直接导入剪辑软件。',
        '',
        '## 零、录制前必须确认的三件事',
        '',
        '1. **终端字号 ≥ 18pt，窗口大小固定**（录屏中不要调窗口）。',
        '2. **画面里不得出现** ' + BT + 'reference/' + BT + ' 或 ' + BT + 'physics/scale_specs.json' + BT,
        '   的路径——它们是评分侧资源，出现在画面里会误导评审以为答案进了智能体输入。',
        '3. **2:30—3:05 的自我否定必须真实发生。** 若录屏时没有出现否决，换一个更难的任务重跑，',
        '   直到出现。这段不能演，也不能用渲染图替代。',
        '',
        '## 一、逐时间码执行表',
        '',
        '| 时间码 | 画面 | 具体动作 | 预期看到什么 | 负责 |',
        '|---|---|---|---|---|',
    ]
    for timecode, visual, action, expect in CUES:
        out.append('| %s | %s | %s | %s | M3 |' % (timecode, visual, action, expect))
    out += [
        '',
        '## 二、2:30—3:05 自我否定片段的精确命令',
        '',
        '按顺序在同一个终端里执行这两条（第二条才是关键）：',
        '',
        '    1) ' + SELF_NEGATION_COMMANDS[0],
        '    2) ' + SELF_NEGATION_COMMANDS[1],
        '',
        '第二条必须出现下面这行（这是本段唯一的"通过标准"）：',
        '',
        '    "reason": "缩放 r×2 倍后 y 变为 0.5 倍，物理预期 0.25 倍（相对偏差 5.00e-01，容差 1e-04）"',
        '',
        '它的含义是：**距离加倍，引力应该变成四分之一，而这个式子给出的是二分之一。**',
        '这句话不依赖任何误差阈值，画面与旁白完全对应，是整段视频最有力的一句。',
        '',
        '## 三、备用素材（若演示环境临时故障）',
        '',
        '| 素材 | 文件 | 用途与限制 |',
        '|---|---|---|',
        '| 真实运行日志 | ' + BT + log_name + BT + ' | 本次演示两条命令的完整 stdout，含退出码 |',
        '| 日志忠实渲染 | ' + BT + frame_name + BT + ' | **仅作剪辑参考与字幕对齐**；',
        '   图内自带"非屏幕录像"说明带，不得作为运行画面直接使用 |',
        '| 片头 / 片尾卡 | ' + BT + 'title-open.png' + BT + ' / ' + BT + 'title-close.png' + BT + ' | 可直接使用 |',
        '| 分镜单页 | ' + BT + 'storyboard.html' + BT + ' | 彩排走位用 |',
        '',
        '## 四、录制后立刻要做的核对',
        '',
        '- [ ] 导出的视频时长在 3—5 分钟之间',
        '- [ ] 2:30—3:05 段落含真实否决画面（不是渲染图）',
        '- [ ] 画面中未出现 ' + BT + 'reference/' + BT + ' 与 ' + BT + 'physics/scale_specs.json' + BT,
        '- [ ] 视频中引用的每个数字都能在 ' + BT + 'runs/' + BT + ' 或 ' + BT + 'evidence/' + BT + ' 中找到',
        '- [ ] 字幕已加载且无错别字（对照 ' + BT + 'subtitle.srt' + BT + '）',
        '- [ ] 1080p 导出，文件名 ' + BT + 'evidence/video/final.mp4' + BT,
        '',
    ]
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(chr(10).join(out))


def write_storyboard(path, log_name, frame_name):
    cards = []
    for timecode, visual, action, expect in CUES:
        cards.append(
            '<section class="card"><div class="tc">%s</div><h3>%s</h3>'
            '<p class="act">%s</p><p class="exp">预期：%s</p></section>'
            % (timecode, visual, action, expect))
    html = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>FORMULA-AGH 演示视频分镜（4 分 30 秒）</title>
<style>
 body{font-family:"Microsoft YaHei",system-ui,sans-serif;margin:0;background:#0f1116;color:#e8eef5}
 header{padding:28px 40px;border-bottom:1px solid #26303c}
 h1{margin:0 0 6px;font-size:26px}
 header p{margin:0;color:#93a4b8;font-size:14px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;padding:24px 40px}
 .card{background:#161b23;border:1px solid #26303c;border-radius:10px;padding:14px 16px}
 .tc{color:#ff9a63;font-weight:700;font-size:14px;letter-spacing:.5px}
 .card h3{margin:6px 0 8px;font-size:16px}
 .act{margin:0 0 8px;font-size:13px;color:#c6d3e0;line-height:1.6}
 .exp{margin:0;font-size:12px;color:#8ea0b4}
 .note{margin:0 40px 32px;padding:14px 16px;border-left:3px solid #ff9a63;
       background:#1a1410;color:#ffd0b0;font-size:13px;line-height:1.7}
 code{background:#0b0e13;padding:2px 5px;border-radius:4px;font-family:Consolas,monospace}
</style></head><body>
<header>
  <h1>FORMULA-AGH 演示视频分镜</h1>
  <p>目标 4 分 30 秒 ｜ 含真实运行画面与一次自我否定片段 ｜ M3 主导录制与剪辑</p>
</header>
<p class="note">关键片段 2:30—3:05 必须来自真实录屏。本次已归档的真实日志见
<code>''' + log_name + '''</code>，其忠实渲染 <code>''' + frame_name + '''</code>
仅用于剪辑参考与字幕对齐，<b>不得替代运行画面</b>。</p>
<div class="grid">''' + ''.join(cards) + '''</div>
</body></html>'''
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)


def main():
    os.makedirs(VIDEO, exist_ok=True)

    log = run_demo()
    log_path = os.path.join(VIDEO, 'seg-self-negation.log.txt')
    with open(log_path, 'w', encoding='utf-8') as fh:
        fh.write(log)
    print('wrote %s (%d chars)' % (os.path.relpath(log_path, ROOT), len(log)))

    frame_path = os.path.join(VIDEO, 'seg-self-negation-log.png')
    terminal_frame(log, frame_path, title='2:30—3:05 自我否定')
    print('wrote %s' % os.path.relpath(frame_path, ROOT))

    title_card(os.path.join(VIDEO, 'title-open.png'), 'FORMULA-AGH',
               '面向公开科学数据的可验证公式发现智能体',
               'B3. 科学计算与仿真 ｜ 2026 江苏省 AI+科学与工程创新实践黑客松',
               (255, 122, 60))
    title_card(os.path.join(VIDEO, 'title-close.png'),
               '一个会推翻自己的智能体，',
               '比一个永远正确的答案更值得信任。',
               'FORMULA-AGH ｜ 22 个物理定律任务 ｜ 22/22 参考式通过 ｜ 22/22 错误式被拒 ｜ 负对照零编造',
               (60, 170, 120))
    print('wrote title cards')

    srt_path = os.path.join(VIDEO, 'subtitle.srt')
    write_srt(srt_path)
    print('wrote %s (%d 条字幕)' % (os.path.relpath(srt_path, ROOT), len(SUBTITLES)))

    write_cue_sheet(os.path.join(VIDEO, '录制执行清单.md'),
                    'seg-self-negation.log.txt', 'seg-self-negation-log.png')
    write_storyboard(os.path.join(VIDEO, 'storyboard.html'),
                     'seg-self-negation.log.txt', 'seg-self-negation-log.png')
    print('wrote 录制执行清单.md / storyboard.html')

    with open(os.path.join(VIDEO, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump({
            'generated_at': datetime.now().isoformat(timespec='seconds'),
            'target_duration_sec': 270,
            'subtitles': len(SUBTITLES),
            'demo_commands': SELF_NEGATION_COMMANDS,
            'note': ('本目录不含视频文件：本机无 ffmpeg，且纪律禁止用动画冒充运行画面。'
                     '这里提供的是录制前一天应准备好的全套素材与指令。'),
        }, fh, ensure_ascii=False, indent=2)
    print('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
