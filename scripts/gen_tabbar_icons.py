# -*- coding: utf-8 -*-
"""
生成小程序自定义 TabBar 图标（81x81 PNG，普通态 / 选中态各一套）。

纯标准库实现：4x 超采样光栅化后降采样，得到带抗锯齿的图标。
运行：python scripts/gen_tabbar_icons.py
输出：miniprogram/assets/tabbar/*.png
"""

import math
import os
import struct
import zlib

SIZE = 81
SS = 4                      # 超采样倍数
N = SIZE * SS               # 超采样画布边长

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'miniprogram', 'assets', 'tabbar')

COLOR_NORMAL = (0x9D, 0x96, 0xB8)   # 品牌 · 次文字
COLOR_TOP = (0x8B, 0x5C, 0xF6)      # 品牌 · 叭啦紫
COLOR_BOTTOM = (0xF9, 0x73, 0x16)   # 品牌 · 星芒橙


# ------------------------------------------------------------------ 光栅化

def new_mask():
    return [0.0] * (N * N)


def fill(mask, inside):
    for i in range(N * N):
        if inside(i % N, i // N):
            mask[i] = 1.0


def erase(mask, inside):
    for i in range(N * N):
        if inside(i % N, i // N):
            mask[i] = 0.0


def P(v):
    """归一化坐标 → 超采样像素坐标"""
    return v * N


def circle(cx, cy, r):
    cx, cy, r = P(cx), P(cy), P(r)
    r2 = r * r
    return lambda x, y: (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r2


def ring(cx, cy, r, th):
    inner, outer = circle(cx, cy, r - th / 2.0), circle(cx, cy, r + th / 2.0)
    return lambda x, y: outer(x, y) and not inner(x, y)


def ring_segment(cx, cy, r, th, a0, a1):
    """环形片段，角度制：90° 表示正下方"""
    base = ring(cx, cy, r, th)
    lo, hi = math.radians(a0), math.radians(a1)

    def f(x, y):
        if not base(x, y):
            return False
        ang = math.atan2(y + 0.5 - P(cy), x + 0.5 - P(cx))
        return lo <= ang <= hi

    return f


def rect(x0, y0, x1, y1):
    x0, y0, x1, y1 = P(x0), P(y0), P(x1), P(y1)
    return lambda x, y: x0 <= x + 0.5 <= x1 and y0 <= y + 0.5 <= y1


def rounded_rect(x0, y0, x1, y1, r):
    x0, y0, x1, y1, r = P(x0), P(y0), P(x1), P(y1), P(r)

    def f(x, y):
        px, py = x + 0.5, y + 0.5
        if not (x0 <= px <= x1 and y0 <= py <= y1):
            return False
        cx = min(max(px, x0 + r), x1 - r)
        cy = min(max(py, y0 + r), y1 - r)
        return (px - cx) ** 2 + (py - cy) ** 2 <= r * r

    return f


def polygon(pts):
    poly = [(P(a), P(b)) for a, b in pts]

    def f(x, y):
        px, py = x + 0.5, y + 0.5
        hit = False
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if (y1 > py) != (y2 > py):
                xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if px < xi:
                    hit = not hit
        return hit

    return f


# ------------------------------------------------------------------ 图标定义

def icon_home():
    m = new_mask()
    fill(m, ring(0.5, 0.5, 0.36, 0.075))                       # 表盘外圈
    fill(m, polygon([(0.5, 0.22), (0.61, 0.5), (0.5, 0.78), (0.39, 0.5)]))  # 指针
    return m


def icon_vote():
    m = new_mask()
    for x0, x1, top in ((0.20, 0.36, 0.44), (0.42, 0.58, 0.26), (0.64, 0.80, 0.54)):
        fill(m, rounded_rect(x0, top, x1, 0.78, 0.035))
    fill(m, rounded_rect(0.14, 0.80, 0.86, 0.845, 0.022))      # 基线
    return m


def icon_club():
    m = new_mask()
    fill(m, circle(0.5, 0.31, 0.145))
    fill(m, circle(0.27, 0.60, 0.125))
    fill(m, circle(0.73, 0.60, 0.125))
    return m


def icon_calendar():
    m = new_mask()
    fill(m, rounded_rect(0.16, 0.20, 0.84, 0.82, 0.09))
    erase(m, rounded_rect(0.235, 0.275, 0.765, 0.745, 0.04))
    fill(m, rect(0.16, 0.20, 0.84, 0.33))                       # 顶部标题条
    for cx in (0.36, 0.64):
        for cy in (0.50, 0.66):
            fill(m, circle(cx, cy, 0.052))
    return m


def icon_profile():
    m = new_mask()
    fill(m, circle(0.5, 0.33, 0.155))                           # 头部
    fill(m, ring_segment(0.5, 0.33, 0.33, 0.085, 38, 142))      # 肩部
    return m


ICONS = {
    'home': icon_home,
    'vote': icon_vote,
    'club': icon_club,
    'calendar': icon_calendar,
    'profile': icon_profile,
}


# ------------------------------------------------------------------ 输出

def write_png(path, rgba):
    raw = bytearray()
    stride = SIZE * 4
    for y in range(SIZE):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')

    with open(path, 'wb') as fp:
        fp.write(png)


def render(mask, active):
    """降采样 + 上色；选中态使用纵向渐变"""
    buf = bytearray(SIZE * SIZE * 4)
    step = SS * SS
    for y in range(SIZE):
        t = y / (SIZE - 1.0)
        if active:
            r = COLOR_TOP[0] + (COLOR_BOTTOM[0] - COLOR_TOP[0]) * t
            g = COLOR_TOP[1] + (COLOR_BOTTOM[1] - COLOR_TOP[1]) * t
            b = COLOR_TOP[2] + (COLOR_BOTTOM[2] - COLOR_TOP[2]) * t
        else:
            r, g, b = COLOR_NORMAL
        for x in range(SIZE):
            acc = 0.0
            for dy in range(SS):
                row = (y * SS + dy) * N + x * SS
                for dx in range(SS):
                    acc += mask[row + dx]
            a = acc / step
            i = (y * SIZE + x) * 4
            buf[i] = int(round(r))
            buf[i + 1] = int(round(g))
            buf[i + 2] = int(round(b))
            buf[i + 3] = int(round(min(a, 1.0) * 255))
    return buf


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in ICONS.items():
        mask = fn()
        write_png(os.path.join(OUT_DIR, '%s.png' % name), render(mask, False))
        write_png(os.path.join(OUT_DIR, '%s_active.png' % name), render(mask, True))
    print('generated %d icons -> %s' % (len(ICONS) * 2, OUT_DIR))


if __name__ == '__main__':
    main()
