# -*- coding: utf-8 -*-
"""叭啦品牌资产移植：PNG 瘦身入包 / 裁标志透明底 / tabBar 图标换品牌紫"""
from PIL import Image
import os
import colorsys

SRC = 'F:/Zima Institute/Project Y/叭啦-品牌全案_assets/'
DST = 'F:/Zima Institute/Project Y/bala-miniapp/miniprogram/assets/'
os.makedirs(DST + 'brand', exist_ok=True)

def prepare(name, src_file, width):
    im = Image.open(SRC + src_file).convert('RGB')
    w, h = im.size
    im = im.resize((width, int(h * width / w)), Image.LANCZOS)
    im.save(DST + 'brand/' + name, optimize=True)
    print('brand:', name, im.size, os.path.getsize(DST + 'brand/' + name) // 1024, 'KB')

LOCKUP = '78dcca38-miora_edit_image-1792324923164-0-e83678958688.png'
prepare('logo-primary.png', LOCKUP, 512)
prepare('logo-secondary.png', '28f59747-miora_edit_image-1792324920179-0-63808bbe85f9.png', 512)
prepare('spark.png', 'c8c49567-miora_edit_image-1792324921176-0-6fe76cb72fe7.png', 512)
prepare('brush.png', 'fe9c9f19-miora_edit_image-1792324919499-0-526b80f7000c.png', 512)
prepare('ribbon.png', '467e893c-miora_edit_image-1792324920228-0-a1ff700fe30a.png', 512)

# ---- 从主组合裁纯标志，背景转透明 ----
im = Image.open(SRC + LOCKUP).convert('RGB')
w, h = im.size
bg = im.getpixel((6, 6))
px = im.load()
minx, miny, maxx, maxy = w, h, 0, 0
for y in range(0, int(h * 0.45)):
    for x in range(w):
        p = px[x, y]
        if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 60:
            minx = min(minx, x); maxx = max(maxx, x)
            miny = min(miny, y); maxy = max(maxy, y)
crop = im.crop((minx, miny, maxx + 1, maxy + 1)).convert('RGBA')
d = crop.load()
cw, ch = crop.size
for y in range(ch):
    for x in range(cw):
        p = d[x, y]
        dist = abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2])
        a = min(255, max(0, int((dist - 24) * 4)))
        d[x, y] = (p[0], p[1], p[2], a)
crop.save(DST + 'brand/logo-mark.png', optimize=True)
print('mark:', crop.size, os.path.getsize(DST + 'brand/logo-mark.png') // 1024, 'KB')

# ---- tabBar 选中图标：旧蓝 -> 品牌紫 #8B5CF6 ----
def recolor(path):
    im = Image.open(path).convert('RGBA')
    d = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = d[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hh = (hh + 33.0 / 360.0) % 1.0
            ss = ss * 0.90
            vv = min(1.0, vv * 1.04)
            nr, ng, nb = colorsys.hsv_to_rgb(hh, ss, vv)
            d[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
    im.save(path, optimize=True)

for f in ['home_active.png', 'vote_active.png', 'club_active.png', 'calendar_active.png', 'profile_active.png']:
    p = DST + 'tabbar/' + f
    recolor(p)
    im = Image.open(p).convert('RGBA')
    op = [q for q in im.getdata() if q[3] > 200]
    print(f, '->', op[0] if op else None, os.path.getsize(p) // 1024, 'KB')

total = sum(os.path.getsize(DST + r + '/' + f) for r, _, fs in os.walk(DST) for f in fs)
print('assets total:', total // 1024, 'KB')
