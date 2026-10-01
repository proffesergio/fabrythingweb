"""Build NobleSeek web logo assets from the uploaded stacked PNG.

Usage (repo root):  python tools/make_ns_logo.py

Reads  frontend/ecommerce_inventory/public/nobleseek_logo.png  (kept as-is),
writes transparent derivatives next to it:
  nobleseek-logo-wide.png  horizontal lockup — masthead + drawer
  nobleseek-logo-white.png white silhouette — dark footer only
  nobleseek-mark.png       square globe+lens badge — favicon + shop pill

The bbox/split constants below were measured from the first uploaded logo.
If the source artwork changes, re-measure with a quick trim/gap scan.
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "frontend", "ecommerce_inventory", "public")
SRC = os.path.join(PUBLIC, "nobleseek_logo.png")

Image.MAX_IMAGE_PIXELS = None

# Measured content box + icon/wordmark split of the source file.
CONTENT_BBOX = (2668, 2775, 8850, 5730)
ICON_BOTTOM = 1847   # of trimmed height
WORD_TOP = 2229      # of trimmed height


def to_transparent(part):
    """White background -> alpha (flat vector art)."""
    rgba = part.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            px[x, y] = (r, g, b, 255 - min(r, g, b))
    bbox = rgba.split()[3].getbbox()
    return rgba.crop(bbox) if bbox else rgba


def main():
    img = Image.open(SRC).convert("RGB")
    trimmed = img.crop(CONTENT_BBOX)
    W, H = trimmed.size
    t_icon = to_transparent(trimmed.crop((0, 0, W, ICON_BOTTOM)))
    t_word = to_transparent(trimmed.crop((0, WORD_TOP, W, H)))
    print("icon:", t_icon.size, "word:", t_word.size)

    # 1. Square mark 512px
    side = max(t_icon.size)
    mark = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mark.paste(t_icon, ((side - t_icon.size[0]) // 2, (side - t_icon.size[1]) // 2), t_icon)
    mark.resize((512, 512), Image.LANCZOS).save(os.path.join(PUBLIC, "nobleseek-mark.png"))

    # 2. Horizontal lockup, height 480
    TARGET_H = 480
    sc = TARGET_H / t_icon.size[1]
    icon_r = t_icon.resize((round(t_icon.size[0] * sc), TARGET_H), Image.LANCZOS)
    word_h = round(TARGET_H * 0.52)
    sc2 = word_h / t_word.size[1]
    word_r = t_word.resize((round(t_word.size[0] * sc2), word_h), Image.LANCZOS)
    GAP, PAD = 56, 40
    canvas = Image.new("RGBA", (PAD + icon_r.size[0] + GAP + word_r.size[0] + PAD, TARGET_H + PAD * 2), (0, 0, 0, 0))
    canvas.paste(icon_r, (PAD, PAD), icon_r)
    canvas.paste(word_r, (PAD + icon_r.size[0] + GAP, PAD + (TARGET_H - word_h) // 2), word_r)
    canvas.save(os.path.join(PUBLIC, "nobleseek-logo-wide.png"))

    # 3. White silhouette of the lockup (dark footer)
    r, g, b, a = canvas.split()
    white = Image.new("RGB", canvas.size, (255, 255, 255)).split()
    Image.merge("RGBA", (white[0], white[1], white[2], a)).save(os.path.join(PUBLIC, "nobleseek-logo-white.png"))
    print("done:", canvas.size)


if __name__ == "__main__":
    main()
