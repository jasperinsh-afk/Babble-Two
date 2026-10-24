# -*- coding: utf-8 -*-
"""
生成叭啦 Babble 品牌分享卡（小程序 onShareAppMessage 用，5:4 = 1080x864）

合成要素：
  - 品牌标准渐变底（135deg #8B5CF6 → #F97316）
  - 柔光：白 / 深紫 / 浅橙三层径向光晕
  - 中央：透明标志（logo-mark）+ 「叭啦」+ 「Babble」+ 品牌三点
  - 角落：星芒 / 飘带软圆徽章（浅底资产裁圆 + 提白）

仅使用现有品牌资产本地合成，不调用 AI 生图。
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINI = os.path.join(ROOT, "miniprogram")
BRAND = os.path.join(MINI, "assets", "brand")
OUT = os.path.join(BRAND, "share-card.png")

W, H = 1080, 864


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def gradient_bg(w, h, c1, c2):
    """135deg 对角渐变：左上 → 右下"""
    grid = Image.new("RGB", (135, 135))
    px = grid.load()
    for y in range(135):
        for x in range(135):
            px[x, y] = _lerp(c1, c2, (x + y) / 268.0)
    return grid.resize((w, h), Image.BICUBIC)


def soft_glow(size, center, radius, color, alpha):
    """在透明层上画一枚柔光斑"""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = center
    r = radius
    d.ellipse([x - r, y - r, x + r, y + r], fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(r * 0.55))


def circle_badge(asset_path, diameter, white_mix=0.35, rotate=0):
    """浅底品牌资产 → 软圆徽章：裁圆 + 与白色混合成粉彩盘 + 可选旋转"""
    asset = Image.open(asset_path).convert("RGB")
    inner = int(diameter * 0.86)
    asset = asset.resize((inner, inner), Image.LANCZOS)
    if rotate:
        asset = asset.rotate(rotate, expand=False, fillcolor=(255, 255, 255))
    # 与白色混合，压掉浅底与渐变的反差
    white = Image.new("RGB", asset.size, (255, 255, 255))
    asset = Image.blend(asset, white, white_mix)

    inner_mask = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(inner_mask).ellipse([0, 0, inner - 1, inner - 1], fill=255)
    badge = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    badge.paste(asset, ((diameter - inner) // 2, (diameter - inner) // 2), inner_mask)
    return badge


def text_center(draw, y, text, font, fill, spacing=0):
    """水平居中绘制文本（支持 letter-spacing），返回文本宽度"""
    widths = []
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font)
        widths.append(bbox[2] - bbox[0])
    total = sum(widths) + spacing * (len(text) - 1)
    x = (W - total) / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + spacing
    return total


def main():
    PURPLE = (0x8B, 0x5C, 0xF6)
    DEEP = (0x7C, 0x3A, 0xED)
    ORANGE = (0xF9, 0x73, 0x16)
    LIGHT_ORANGE = (0xFD, 0xBA, 0x74)
    INK = (0x1E, 0x1B, 0x2E)
    WHITE = (255, 255, 255)

    # 1. 渐变底 + 柔光
    card = gradient_bg(W, H, PURPLE, ORANGE).convert("RGBA")
    card.alpha_composite(soft_glow((W, H), (190, 120), 460, WHITE, 46))
    card.alpha_composite(soft_glow((W, H), (980, 800), 520, DEEP, 60))
    card.alpha_composite(soft_glow((W, H), (540, 900), 480, LIGHT_ORANGE, 34))

    # 2. 角落软圆徽章（先放，压在内容下）
    spark = circle_badge(os.path.join(BRAND, "spark.png"), 168, white_mix=0.42)
    card.alpha_composite(spark, (W - 196, 96))
    ribbon = circle_badge(os.path.join(BRAND, "ribbon.png"), 132, white_mix=0.42, rotate=18)
    card.alpha_composite(ribbon, (72, H - 216))

    # 3. 中央标志（透明底资产）
    mark = Image.open(os.path.join(BRAND, "logo-mark.png")).convert("RGBA")
    mark = mark.resize((620, 396), Image.LANCZOS)
    mark_y = 176
    card.alpha_composite(mark, ((W - 620) // 2, mark_y))

    d = ImageDraw.Draw(card)

    # 4. 品牌文字
    bold = ImageFont.truetype(os.path.join("C:/Windows/Fonts", "msyhbd.ttc"), 104)
    reg = ImageFont.truetype(os.path.join("C:/Windows/Fonts", "msyhl.ttc"), 52)
    text_center(d, 592, "叭啦", bold, WHITE + (255,))
    text_center(d, 730, "BABBLE", reg, WHITE + (225,), spacing=14)

    # 5. 品牌三点（呼应启动页加载点）
    for i in range(3):
        cx = W // 2 + (i - 1) * 44
        d.ellipse([cx - 7, 826, cx + 7, 840], fill=WHITE + (215,))

    # 6. 轻暗角，收拢视觉
    vignette = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vignette)
    dv.ellipse([-W * 0.25, -H * 0.3, W * 1.25, H * 1.3], fill=26)
    vignette = vignette.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGBA", (W, H), INK + (255,))
    card = Image.composite(dark, card, vignette)

    card = card.convert("RGB")
    card.save(OUT, "PNG", optimize=True)
    print("saved", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
