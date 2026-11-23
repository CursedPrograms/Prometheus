# Prometheus' placeholder splash (release/datafiles/splash.png, 1000 x 500) until the painted one comes.
# Changeling grey, the name, an Atelier blue rule, and the credit. No logo: the logos are painted by hand.
# Needs: pillow, fonttools, brotli (Inter from release/datafiles/fonts, OFL).
import io
import os

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BG, RULE, WHITE, GREY = "#1a1a1a", "#007bb7", "#e6e6e6", "#9a9a9a"


def inter(size, weight):
    f = TTFont(os.path.join(ROOT, "release", "datafiles", "fonts", "Inter.woff2"))
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    font = ImageFont.truetype(buf, size)
    try:
        font.set_variation_by_axes([weight])
    except (OSError, AttributeError):
        pass
    return font


def main():
    w, h = 1000, 500
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    x = 64
    d.text((x, 150), "Prometheus", font=inter(96, 600), fill=WHITE)
    d.rectangle((x, 280, x + 120, 285), fill=RULE)
    d.text((x, 306), "Shape people from clay.", font=inter(26, 400), fill=WHITE)
    d.text((x, 420), "Atelier  ·  based on Blender  ·  Farica☆Kimora © Cursed Entertainment",
           font=inter(17, 400), fill=GREY)
    out = os.path.join(ROOT, "release", "datafiles", "splash.png")
    img.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
