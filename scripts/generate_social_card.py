"""Create the Whisk & Crumbs sharing image from the brand logo and real cake."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "web" / "assets" / "fonts"
canvas = Image.new("RGB", (1200, 630), "#f5ebdd")
draw = ImageDraw.Draw(canvas)
config = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
script = ImageFont.truetype(str(FONTS / "courgette-regular.ttf"), 58)
body = ImageFont.truetype(str(FONTS / "dm-sans-regular.ttf"), 22)
label = ImageFont.truetype(str(FONTS / "dm-sans-semibold.ttf"), 16)
draw.rectangle((0, 0, 1199, 17), fill="#34483a")
with Image.open(ROOT / "web" / "assets" / "whisk-and-crumbs-logo.png") as image:
    logo = ImageOps.contain(image.convert("RGBA"), (560, 135), Image.Resampling.LANCZOS)
canvas.paste(logo, (38, 38), logo.getchannel("A"))
draw.multiline_text((62, 205), "A little cake.\nA lot of heart.", font=script, fill="#34483a", spacing=9)
draw.text((66, 384), config["descriptor"], font=body, fill="#686357")
draw.line((66, 464, 510, 464), fill="#d8ccbb", width=2)
draw.text((66, 486), "Baked at home. Made with heart.", font=label, fill="#76543d")
stickers = ROOT / "assets" / "images" / "cake-stickers"
manifest = json.loads((stickers / "manifest.json").read_text(encoding="utf-8"))
hero = next(photo for photo in manifest["photos"] if photo["id"] == "ribbon-and-pearl-cake")
full = max((variant for variant in hero["variants"] if variant["file"].endswith(".png")), key=lambda variant: variant["width"])
with Image.open(stickers / full["file"]) as image:
    photo = ImageOps.contain(image.convert("RGBA"), (506, 470), Image.Resampling.LANCZOS)
draw.ellipse((638, 88, 1118, 551), fill="#e8decd")
canvas.paste(photo, (622, 84), photo.getchannel("A"))
for x, y in [(628, 88), (1123, 456)]:
    for dx, dy in [(-11, 0), (11, 0), (0, -11), (0, 11)]:
        draw.ellipse((x + dx - 9, y + dy - 9, x + dx + 9, y + dy + 9), fill="#e8baa2")
    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#76543d")
draw.text((675, 559), "A little ribbon. A lovely celebration.", font=label, fill="#686357")
canvas.save(ROOT / "web" / "assets" / "whisk-and-crumbs-social-card.jpg", quality=92, optimize=True)
print("Saved web\\assets\\whisk-and-crumbs-social-card.jpg (1200 x 630).")
