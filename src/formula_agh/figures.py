# -*- coding: utf-8 -*-
# 零依赖绘图：把"预测曲线 vs 真实曲线（外推区高亮）"这类物理图直接画出来。
#
# 为什么自己写而不用 matplotlib：
#   本机环境没有 scipy / matplotlib 且无法安装（见 docs/运行与验证.md）。
#   比赛机器上也未必有。整条证据链不能因为缺一个绘图库就断掉。
#   这里只依赖 Python 标准库 + Pillow（Pillow 仅用于输出 PNG；SVG 纯文本生成）。
#
# 输出两种格式，各有明确用途：
#   SVG  矢量，进浏览器/HTML 证据页，任意放大不失真；
#   PNG  位图，进 Word 文档与视频截帧（python-docx 不接受 SVG）。
#
# 坐标轴支持线性与对数两种刻度——物理量常跨若干数量级，对数轴是必需品而不是装饰。
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

SVG_FONT = "Microsoft YaHei, Segoe UI, PingFang SC, sans-serif"
PNG_FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/arial.ttf",
)

DEFAULT_COLORS = {
    'truth': '#1f77b4',
    'reference': '#2ca02c',
    'candidate': '#d62728',
    'rejected': '#8c564b',
    'neutral': '#7f7f7f',
    'accent': '#ff7f0e',
    'grid': '#e6e6e6',
    'axis': '#333333',
    'text': '#222222',
}


@dataclass
class Rect:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0


def _nice_ticks(lo: float, hi: float, count: int = 6) -> List[float]:
    # 1-2-5 刻度：让标注落在人眼习惯的数值上。
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        return [lo]
    raw = (hi - lo) / max(1, count)
    exp = math.floor(math.log10(raw))
    base = raw / (10 ** exp)
    for step in (1.0, 2.0, 2.5, 5.0, 10.0):
        if base <= step:
            step_size = step * (10 ** exp)
            break
    else:
        step_size = 10.0 ** (exp + 1)
    start = math.ceil(lo / step_size) * step_size
    ticks = []
    value = start
    while value <= hi + step_size * 1e-6:
        ticks.append(0.0 if abs(value) < step_size * 1e-9 else value)
        value += step_size
    return ticks


def _log_ticks(lo: float, hi: float) -> List[float]:
    lo, hi = max(lo, 1e-300), max(hi, 1e-299)
    out = []
    for exponent in range(int(math.floor(math.log10(lo))), int(math.ceil(math.log10(hi))) + 1):
        for mantissa in (1.0, 2.0, 5.0):
            value = mantissa * (10.0 ** exponent)
            if lo * 0.999 <= value <= hi * 1.001:
                out.append(value)
    return out or [lo, hi]


def _format_tick(value: float, scale: str) -> str:
    if scale == 'log' or (value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e5)):
        return '%.3g' % value
    if abs(value - round(value)) < 1e-9:
        return '%d' % round(value)
    return '%.3g' % value


class Chart:
    # 极简单坐标系图表：足够画"物理曲线 + 区域高亮 + 图例"，不做多余的事。
    def __init__(self, width: int = 1080, height: int = 620, supersample: int = 2):
        self.width = int(width)
        self.height = int(height)
        self.ss = max(1, int(supersample))
        self.rect = Rect(96, 64, width - 40, height - 78)
        self.title = ''
        self.xlabel = ''
        self.ylabel = ''
        self.xscale = 'linear'
        self.yscale = 'linear'
        self._items: List[dict] = []
        self._xlim: Optional[Tuple[float, float]] = None
        self._ylim: Optional[Tuple[float, float]] = None
        self.legend_loc = 'upper right'
        self.legend_on = True
        self.show_xticks = True
        self.show_yticks = True

    # ---- 数据 -> 坐标变换 ------------------------------------------------
    def _tx(self, value: float) -> float:
        return math.log10(value) if self.xscale == 'log' else float(value)

    def _ty(self, value: float) -> float:
        return math.log10(value) if self.yscale == 'log' else float(value)

    def _px(self, x: float) -> float:
        tx0, tx1 = self._tx(self._xr[0]), self._tx(self._xr[1])
        return self.rect.x0 + (self._tx(x) - tx0) / (tx1 - tx0) * self.rect.w if tx1 > tx0 else self.rect.x0

    def _py(self, y: float) -> float:
        ty0, ty1 = self._ty(self._yr[0]), self._ty(self._yr[1])
        return self.rect.y1 - (self._ty(y) - ty0) / (ty1 - ty0) * self.rect.h if ty1 > ty0 else self.rect.y1

    @property
    def _xr(self) -> Tuple[float, float]:
        if self._xlim:
            return self._xlim
        values = []
        for item in self._items:
            kind = item['kind']
            if kind == 'band':
                values.extend([item['x0'], item['x1']])
            elif kind == 'bar':
                values.extend([item['x0'], item['x1']])
            elif kind == 'vline':
                values.append(item['x'])
            elif kind in ('line', 'scatter'):
                values.extend([v for v in item['xs'] if math.isfinite(v)])
        if not values:
            return (0.0, 1.0)
        return self._pad(min(values), max(values), self.xscale)

    @property
    def _yr(self) -> Tuple[float, float]:
        if self._ylim:
            return self._ylim
        values = []
        for item in self._items:
            kind = item['kind']
            if kind in ('line', 'scatter'):
                values.extend([v for v in item['ys'] if math.isfinite(v)])
            elif kind == 'hline':
                values.append(item['y'])
            elif kind == 'bar':
                values.extend([item['base'], item['height']])
        if not values:
            return (0.0, 1.0)
        return self._pad(min(values), max(values), self.yscale)

    def _pad(self, lo: float, hi: float, scale: str = 'linear') -> Tuple[float, float]:
        # 对数轴必须按倍数留边。线性留边会把 10 变成 -6000，直接让 log10 越界。
        if scale == 'log':
            if lo <= 0:
                positives = [v for v in (lo, hi) if v > 0]
                lo = min(positives) / 10.0 if positives else 1e-3
            if hi <= lo:
                return (lo / 2.0, max(hi, lo) * 2.0)
            factor = (hi / lo) ** 0.05
            return (lo / factor, hi * factor)
        if hi <= lo:
            delta = abs(lo) * 0.1 or 1.0
            return (lo - delta, hi + delta)
        margin = (hi - lo) * 0.06
        return (lo - margin, hi + margin)

    # ---- 绘制指令 --------------------------------------------------------
    def set_title(self, text: str) -> 'Chart':
        self.title = text
        return self

    def set_axes(self, xlabel: str = '', ylabel: str = '', xscale: str = 'linear',
                 yscale: str = 'linear', xlim=None, ylim=None,
                 xticks: bool = True, yticks: bool = True) -> 'Chart':
        self.xlabel, self.ylabel = xlabel, ylabel
        self.xscale, self.yscale = xscale, yscale
        self._xlim = tuple(xlim) if xlim else None
        self._ylim = tuple(ylim) if ylim else None
        # 类目轴（柱子）不需要数值刻度，关掉可以少一层噪声。
        self.show_xticks = bool(xticks)
        self.show_yticks = bool(yticks)
        return self

    def line(self, xs: Sequence[float], ys: Sequence[float], color: str = '#1f77b4',
             width: float = 2.4, label: str = '', dash: Optional[Sequence[float]] = None,
             alpha: float = 1.0) -> 'Chart':
        self._items.append({'kind': 'line', 'xs': list(xs), 'ys': list(ys), 'color': color,
                            'width': width, 'label': label, 'dash': list(dash) if dash else None,
                            'alpha': alpha})
        return self

    def scatter(self, xs: Sequence[float], ys: Sequence[float], color: str = '#1f77b4',
                size: float = 3.0, label: str = '', alpha: float = 0.6) -> 'Chart':
        self._items.append({'kind': 'scatter', 'xs': list(xs), 'ys': list(ys), 'color': color,
                            'size': size, 'label': label, 'alpha': alpha})
        return self

    def band(self, x0: float, x1: float, color: str = '#ffcccc', alpha: float = 0.45,
             label: str = '') -> 'Chart':
        self._items.insert(0, {'kind': 'band', 'x0': x0, 'x1': x1, 'color': color,
                               'alpha': alpha, 'label': label})
        return self

    def hline(self, y: float, color: str = '#999999', width: float = 1.4,
              dash: Sequence[float] = (6, 4), label: str = '') -> 'Chart':
        self._items.append({'kind': 'hline', 'y': y, 'color': color, 'width': width,
                            'dash': list(dash), 'label': label, 'alpha': 1.0})
        return self

    def vline(self, x: float, color: str = '#999999', width: float = 1.4,
              dash: Sequence[float] = (6, 4), label: str = '') -> 'Chart':
        self._items.append({'kind': 'vline', 'x': x, 'color': color, 'width': width,
                            'dash': list(dash), 'label': label, 'alpha': 1.0})
        return self

    def bar_rect(self, x0: float, x1: float, height: float, label: str = '',
                 color: str = '#1f77b4', alpha: float = 0.92, base: float = 0.0) -> 'Chart':
        # 柱状图用：数据坐标下的矩形，从 base 长到 height。
        self._items.append({'kind': 'bar', 'x0': x0, 'x1': x1, 'base': base,
                            'height': height, 'color': color, 'label': label,
                            'alpha': alpha})
        return self

    def text(self, x: float, y: float, s: str, color: str = '#222222', size: float = 15.0,
             anchor: str = 'start') -> 'Chart':
        self._items.append({'kind': 'text', 'x': x, 'y': y, 's': s, 'color': color,
                            'size': size, 'anchor': anchor})
        return self

    # ---- 图例 ------------------------------------------------------------
    def _legend_entries(self):
        seen, entries = set(), []
        for item in self._items:
            label = item.get('label')
            if label and label not in seen:
                seen.add(label)
                entries.append((label, item.get('color', '#333333'), item['kind']))
        return entries

    # ---- SVG 后端 --------------------------------------------------------
    def _svg(self) -> str:
        w, h = self.width, self.height
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
                 'viewBox="0 0 %d %d" font-family="%s">' % (w, h, w, h, SVG_FONT),
                 '<rect width="%d" height="%d" fill="#ffffff"/>' % (w, h)]
        parts.append('<text x="%d" y="34" font-size="22" font-weight="600" fill="%s" '
                     'text-anchor="middle">%s</text>'
                     % (w // 2, DEFAULT_COLORS['text'], _escape(self.title)))
        parts.extend(self._svg_frame())
        for item in self._items:
            kind = item['kind']
            if kind == 'band':
                x0, x1 = self._px(item['x0']), self._px(item['x1'])
                parts.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                             'fill-opacity="%.2f"/>'
                             % (min(x0, x1), self.rect.y0, abs(x1 - x0), self.rect.h,
                                item['color'], item['alpha']))
            elif kind == 'line':
                d = _polyline_path([(self._px(x), self._py(y))
                                    for x, y in zip(item['xs'], item['ys'])
                                    if math.isfinite(x) and math.isfinite(y)])
                dash = (' stroke-dasharray="%s"' % ' '.join('%.1f' % v for v in item['dash'])
                        if item.get('dash') else '')
                parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" '
                             'stroke-linejoin="round" stroke-linecap="round" '
                             'stroke-opacity="%.2f"%s/>'
                             % (d, item['color'], item['width'], item['alpha'], dash))
            elif kind == 'scatter':
                for x, y in zip(item['xs'], item['ys']):
                    if math.isfinite(x) and math.isfinite(y):
                        parts.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" '
                                     'fill-opacity="%.2f"/>'
                                     % (self._px(x), self._py(y), item['size'] / 2.0,
                                        item['color'], item['alpha']))
            elif kind == 'hline':
                y = self._py(item['y'])
                dash = ' stroke-dasharray="%s"' % ' '.join('%.1f' % v for v in item['dash'])
                parts.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                             'stroke-width="%.2f"%s/>'
                             % (self.rect.x0, y, self.rect.x1, y, item['color'],
                                item['width'], dash))
            elif kind == 'vline':
                x = self._px(item['x'])
                dash = ' stroke-dasharray="%s"' % ' '.join('%.1f' % v for v in item['dash'])
                parts.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                             'stroke-width="%.2f"%s/>'
                             % (x, self.rect.y0, x, self.rect.y1, item['color'],
                                item['width'], dash))
            elif kind == 'bar':
                x0, x1 = self._px(item['x0']), self._px(item['x1'])
                y0, y1 = self._py(item['base']), self._py(item['height'])
                parts.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                             'fill-opacity="%.2f"/>'
                             % (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0),
                                item['color'], item['alpha']))
            elif kind == 'text':
                parts.append('<text x="%.2f" y="%.2f" font-size="%.1f" fill="%s" '
                             'text-anchor="%s">%s</text>'
                             % (self._px(item['x']), self._py(item['y']), item['size'],
                                item['color'], item['anchor'], _escape(item['s'])))
        parts.extend(self._svg_legend())
        parts.append('</svg>')
        return '\n'.join(parts)

    def _svg_legend(self) -> List[str]:
        if not self.legend_on:
            return []
        entries = self._legend_entries()
        if not entries:
            return []
        x, y = self.rect.x1 - 16, self.rect.y0 + 12
        out = []
        for index, (label, color, kind) in enumerate(entries):
            ly = y + index * 22
            if kind == 'band':
                out.append('<rect x="%.2f" y="%.2f" width="26" height="12" fill="%s" '
                           'fill-opacity="0.5"/>' % (x - 210, ly - 10, color))
            elif kind == 'scatter':
                out.append('<circle cx="%.2f" cy="%.2f" r="4" fill="%s"/>'
                           % (x - 197, ly - 4, color))
            else:
                out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                           'stroke-width="2.4"/>' % (x - 210, ly - 4, x - 184, ly - 4, color))
            out.append('<text x="%.2f" y="%.2f" font-size="15" fill="%s" '
                       'text-anchor="end">%s</text>' % (x, ly, DEFAULT_COLORS['text'],
                                                        _escape(label)))
        return out

    # ---- PNG 后端 --------------------------------------------------------
    def _png(self, path: str) -> None:
        from PIL import Image, ImageDraw, ImageFont

        ss = self.ss
        image = Image.new('RGB', (self.width * ss, self.height * ss), 'white')
        draw = ImageDraw.Draw(image, 'RGBA')

        def font(size: float, bold: bool = False):
            for candidate in PNG_FONT_CANDIDATES:
                if os.path.exists(candidate):
                    try:
                        return ImageFont.truetype(candidate, int(size * ss))
                    except OSError:
                        continue
            return ImageFont.load_default(int(size * ss))

        self._png_frame(draw, font, image, Image, ImageDraw)
        draw.text((self.width * ss / 2, 34 * ss), self.title, fill=DEFAULT_COLORS['text'],
                  font=font(22, True), anchor='mm')

        for item in self._items:
            kind = item['kind']
            if kind == 'band':
                x0, x1 = self._px(item['x0']) * ss, self._px(item['x1']) * ss
                alpha = int(255 * item['alpha'])
                draw.rectangle([min(x0, x1), self.rect.y0 * ss, max(x0, x1), self.rect.y1 * ss],
                               fill=_rgba(item['color'], alpha))
            elif kind == 'line':
                points = [(self._px(x) * ss, self._py(y) * ss)
                          for x, y in zip(item['xs'], item['ys'])
                          if math.isfinite(x) and math.isfinite(y)]
                _draw_polyline(draw, points, _rgba(item['color'], int(255 * item['alpha'])),
                               max(1, int(round(item['width'] * ss))), item.get('dash'), ss)
            elif kind == 'scatter':
                radius = max(1.0, item['size'] / 2.0 * ss)
                fill = _rgba(item['color'], int(255 * item['alpha']))
                for x, y in zip(item['xs'], item['ys']):
                    if math.isfinite(x) and math.isfinite(y):
                        px, py = self._px(x) * ss, self._py(y) * ss
                        draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=fill)
            elif kind == 'hline':
                y = self._py(item['y']) * ss
                _draw_polyline(draw, [(self.rect.x0 * ss, y), (self.rect.x1 * ss, y)],
                               _rgba(item['color'], 255), max(1, int(item['width'] * ss)),
                               item.get('dash'), ss)
            elif kind == 'vline':
                x = self._px(item['x']) * ss
                _draw_polyline(draw, [(x, self.rect.y0 * ss), (x, self.rect.y1 * ss)],
                               _rgba(item['color'], 255), max(1, int(item['width'] * ss)),
                               item.get('dash'), ss)
            elif kind == 'bar':
                x0, x1 = self._px(item['x0']) * ss, self._px(item['x1']) * ss
                y0, y1 = self._py(item['base']) * ss, self._py(item['height']) * ss
                draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)],
                               fill=_rgba(item['color'], int(255 * item['alpha'])))
            elif kind == 'text':
                draw.text((self._px(item['x']) * ss, self._py(item['y']) * ss), item['s'],
                          fill=item['color'], font=font(item['size']),
                          anchor={'start': 'lm', 'middle': 'mm', 'end': 'rm'}.get(item['anchor'], 'lm'))

        if self.legend_on:
            entries = self._legend_entries()
            x = (self.rect.x1 - 16) * ss
            for index, (label, color, kind) in enumerate(entries):
                ly = (self.rect.y0 + 12 + index * 22) * ss
                if kind == 'band':
                    draw.rectangle([x - 210 * ss, ly - 10 * ss, x - 184 * ss, ly + 2 * ss],
                                   fill=_rgba(color, 128))
                elif kind == 'scatter':
                    draw.ellipse([x - 201 * ss, ly - 8 * ss, x - 193 * ss, ly], fill=color)
                else:
                    draw.line([x - 210 * ss, ly - 4 * ss, x - 184 * ss, ly - 4 * ss],
                              fill=color, width=max(1, int(2.4 * ss)))
                draw.text((x, ly - 4 * ss), label, fill=DEFAULT_COLORS['text'],
                          font=font(15), anchor='rm')

        image = image.resize((self.width, self.height), Image.LANCZOS)
        image.save(path)

        # 顺便落一份 SVG：同一张图在 HTML 证据页里可以无损放大。
        if path.lower().endswith('.png'):
            with open(path[:-4] + '.svg', 'w', encoding='utf-8') as fh:
                fh.write(self._svg())

    # ---- 坐标框、刻度、轴标签 -------------------------------------------
    def _ticks(self):
        xr, yr = self._xr, self._yr
        ticks_x = _log_ticks(*xr) if self.xscale == 'log' else _nice_ticks(*xr)
        ticks_y = _log_ticks(*yr) if self.yscale == 'log' else _nice_ticks(*yr)
        return ticks_x, ticks_y

    def _svg_frame(self) -> List[str]:
        out: List[str] = []
        rect = self.rect
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" '
                   'stroke="%s" stroke-width="1.2"/>'
                   % (rect.x0, rect.y0, rect.w, rect.h, DEFAULT_COLORS['axis']))
        ticks_x, ticks_y = self._ticks()
        for value in (ticks_x if self.show_xticks else []):
            px = self._px(value)
            if not (rect.x0 - 1 <= px <= rect.x1 + 1):
                continue
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                       'stroke-width="0.8"/>'
                       % (px, rect.y1, px, rect.y1 + 6, DEFAULT_COLORS['axis']))
            out.append('<text x="%.2f" y="%.2f" font-size="15" fill="%s" '
                       'text-anchor="middle">%s</text>'
                       % (px, rect.y1 + 24, DEFAULT_COLORS['text'],
                          _escape(_format_tick(value, self.xscale))))
        for value in (ticks_y if self.show_yticks else []):
            py = self._py(value)
            if not (rect.y0 - 1 <= py <= rect.y1 + 1):
                continue
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                       'stroke-width="0.8"/>'
                       % (rect.x0 - 6, py, rect.x0, py, DEFAULT_COLORS['axis']))
            out.append('<text x="%.2f" y="%.2f" font-size="15" fill="%s" '
                       'text-anchor="end">%s</text>'
                       % (rect.x0 - 12, py + 5, DEFAULT_COLORS['text'],
                          _escape(_format_tick(value, self.yscale))))
        if self.xlabel:
            out.append('<text x="%.2f" y="%d" font-size="16" fill="%s" '
                       'text-anchor="middle">%s</text>'
                       % (rect.x0 + rect.w / 2, self.height - 26,
                          DEFAULT_COLORS['text'], _escape(self.xlabel)))
        if self.ylabel:
            cx, cy = 26.0, rect.y0 + rect.h / 2
            out.append('<text x="%.2f" y="%.2f" font-size="16" fill="%s" '
                       'text-anchor="middle" transform="rotate(-90 %.2f %.2f)">%s</text>'
                       % (cx, cy, DEFAULT_COLORS['text'], cx, cy, _escape(self.ylabel)))
        return out

    def _png_frame(self, draw, font, image, Image, ImageDraw) -> None:
        ss = self.ss
        rect = self.rect
        axis = _rgba(DEFAULT_COLORS['axis'], 255)
        text_color = DEFAULT_COLORS['text']
        draw.rectangle([rect.x0 * ss, rect.y0 * ss, rect.x1 * ss, rect.y1 * ss],
                       outline=axis, width=max(1, ss))
        ticks_x, ticks_y = self._ticks()
        tick_width = max(1, int(round(0.8 * ss)))
        for value in (ticks_x if self.show_xticks else []):
            px = self._px(value)
            if not (rect.x0 - 1 <= px <= rect.x1 + 1):
                continue
            draw.line([px * ss, rect.y1 * ss, px * ss, (rect.y1 + 6) * ss],
                      fill=axis, width=tick_width)
            draw.text((px * ss, (rect.y1 + 10) * ss), _format_tick(value, self.xscale),
                      fill=text_color, font=font(15), anchor='ma')
        for value in (ticks_y if self.show_yticks else []):
            py = self._py(value)
            if not (rect.y0 - 1 <= py <= rect.y1 + 1):
                continue
            draw.line([(rect.x0 - 6) * ss, py * ss, rect.x0 * ss, py * ss],
                      fill=axis, width=tick_width)
            draw.text(((rect.x0 - 10) * ss, py * ss), _format_tick(value, self.yscale),
                      fill=text_color, font=font(15), anchor='rm')
        if self.xlabel:
            draw.text(((rect.x0 + rect.w / 2) * ss, (self.height - 34) * ss), self.xlabel,
                      fill=text_color, font=font(16), anchor='ma')
        if self.ylabel:
            # Pillow 不支持旋转绘制文本，先画在小图上再整体旋转 90 度贴回去。
            band_w = int(rect.h * ss) + 8 * ss
            band_h = 30 * ss
            band = Image.new('RGB', (band_w, band_h), 'white')
            band_draw = ImageDraw.Draw(band)
            band_draw.text((band_w // 2, band_h // 2), self.ylabel,
                           fill=text_color, font=font(16), anchor='mm')
            band = band.rotate(90, expand=True)
            image.paste(band, (10 * ss, int(rect.y0 * ss)))

    # ---- 对外接口 --------------------------------------------------------
    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        if path.lower().endswith('.svg'):
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(self._svg())
            return path
        self._png(path)
        return path


def _escape(text: str) -> str:
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def _rgba(color: str, alpha: int):
    color = color.lstrip('#')
    if len(color) == 3:
        color = ''.join(ch * 2 for ch in color)
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), max(0, min(255, alpha)))


def _polyline_path(points: Sequence[Tuple[float, float]]) -> str:
    if not points:
        return ''
    parts = ['M %.2f %.2f' % points[0]]
    for px, py in points[1:]:
        parts.append('L %.2f %.2f' % (px, py))
    return ' '.join(parts)


def _draw_polyline(draw, points, fill, width: int, dash, ss: int) -> None:
    if len(points) < 2:
        return
    if not dash:
        draw.line(points, fill=fill, width=width, joint='curve')
        return
    pattern = [max(1.0, d * ss) for d in dash]
    index, remaining, on = 0, pattern[0], True
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg <= 0:
            continue
        travelled = 0.0
        while travelled < seg:
            step = min(remaining, seg - travelled)
            t0, t1 = travelled / seg, (travelled + step) / seg
            if on:
                draw.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0),
                           (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=fill, width=width)
            travelled += step
            remaining -= step
            if remaining <= 1e-9:
                index = (index + 1) % len(pattern)
                remaining = pattern[index]
                on = not on
