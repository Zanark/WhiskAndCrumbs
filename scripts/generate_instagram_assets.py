"""Create circle-safe Instagram branding from the approved local mark and fonts."""

from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from playwright.sync_api import sync_playwright

from generate_brand_assets import CREAM, GREEN, ACCENT, mark_svg, render_svg
from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "social" / "instagram"
REVIEW = ROOT / ".local" / "instagram-profile-review"
FONTS = ROOT / "web" / "assets" / "fonts"
SCALE = 3
SIZE = 1080
SOURCES = [
    {
        "url": "https://blog.hootsuite.com/social-media-image-sizes-guide/",
        "accessed": "2026-10-04",
        "guidance": "Recommends at least 320x320 for the square source; profile photos display as circles, so important elements should be centred.",
        "authority": "Third-party guidance, not an official Instagram upload limit.",
    },
    {
        "url": "https://sproutsocial.com/insights/social-media-image-sizes-guide/",
        "accessed": "2026-10-04",
        "guidance": "Recommends a 1:1 profile image and a clean logo recognisable at small sizes; lists 110x110 for profile imagery.",
        "authority": "Third-party guidance; 110px is a small-size review target, not the export resolution.",
    },
]


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), round(size * SCALE))


def centred_text(layer, text, top, size, colour=GREEN, face="courgette-regular.ttf"):
    draw = ImageDraw.Draw(layer)
    selected_font = font(face, size)
    bounds = draw.textbbox((0, 0), text, font=selected_font)
    x = (layer.width - (bounds[2] - bounds[0])) / 2 - bounds[0]
    draw.text((round(x), round(top * SCALE - bounds[1])), text, font=selected_font, fill=colour)


def emblem(page):
    image = render_svg(page, mark_svg("Whisk & Crumbs"), (SIZE * 2, SIZE * 2))
    return image.crop(image.getchannel("A").getbbox())


def artwork(mark, height=SIZE):
    layer = Image.new("RGBA", (SIZE * SCALE, height * SCALE))
    offset = 0 if height == SIZE else 135
    fitted = ImageOps.contain(mark, (380 * SCALE, 390 * SCALE), Image.Resampling.LANCZOS)
    layer.alpha_composite(fitted, ((layer.width - fitted.width) // 2, (155 + offset) * SCALE))
    centred_text(layer, "Whisk", 575 + offset, 166)
    centred_text(layer, "& Crumbs", 748 + offset, 146)
    draw = ImageDraw.Draw(layer)
    draw.arc(tuple(value * SCALE for value in (445, 846 + offset, 635, 880 + offset)),
             10, 170, fill=ACCENT, width=3 * SCALE)
    for x, y, radius in [(517, 904 + offset, 5), (542, 910 + offset, 7), (568, 904 + offset, 4)]:
        draw.ellipse(tuple(value * SCALE for value in (x - radius, y - radius, x + radius, y + radius)), fill=ACCENT)
    if height != SIZE:
        centred_text(layer, "Home-baked vegetarian cakes", 1180, 37, face="dm-sans-regular.ttf")
        centred_text(layer, "@homemadevegcakes", 1243, 31, colour=ACCENT, face="dm-sans-semibold.ttf")
    return layer


def circle_mask(size):
    mask = Image.new("L", size)
    diameter = min(size)
    left, top = (size[0] - diameter) / 2, (size[1] - diameter) / 2
    ImageDraw.Draw(mask).ellipse((left, top, left + diameter, top + diameter), fill=255)
    return mask


def circle_frame(image):
    result = image.copy()
    draw = ImageDraw.Draw(result)
    draw.ellipse((0, 0, result.width, result.height), outline=GREEN, width=12 * SCALE)
    inset = 28 * SCALE
    draw.ellipse((inset, inset, result.width - inset, result.height - inset), outline=ACCENT, width=2 * SCALE)
    return result


def finish(layer):
    paper = Image.new("RGBA", layer.size, CREAM)
    paper.alpha_composite(layer)
    return paper.convert("RGB")


def radial_bounds(alpha):
    width, height = alpha.size
    cx, cy = width / 2, height / 2
    maximum = 0.0
    for y in range(height):
        row = alpha.crop((0, y, width, y + 1)).point(lambda value: 255 if value >= 32 else 0).getbbox()
        if row:
            maximum = max(maximum, math.hypot(row[0] - cx, y - cy),
                          math.hypot(row[2] - 1 - cx, y - cy))
    return round(maximum / SCALE, 2)


def create_review(images):
    REVIEW.mkdir(parents=True, exist_ok=True)
    overview = Image.new("RGB", (1392, 640), "#e7ddd0")
    draw = ImageDraw.Draw(overview)
    label = ImageFont.truetype(str(FONTS / "dm-sans-semibold.ttf"), 20)
    for index, (name, image) in enumerate(images.items()):
        thumb = ImageOps.contain(image, (432, 570), Image.Resampling.LANCZOS)
        x = index * 464 + (464 - thumb.width) // 2
        overview.paste(thumb, (x, 48))
        draw.text((index * 464 + 18, 16), name, font=label, fill=GREEN)
    save_preserving_existing(REVIEW / "three-variants.jpg", encoded(overview, "JPEG", quality=94))

    sheet = Image.new("RGB", (1050, 640), "#ffffff")
    draw = ImageDraw.Draw(sheet)
    for row, (name, image) in enumerate(list(images.items())[:2]):
        draw.text((20, row * 320 + 14), name + " / simulated circular crop", font=label, fill=GREEN)
        for x, width in [(25, 240), (335, 180), (580, 110), (790, 64)]:
            thumb = image.resize((width * 3, width * 3), Image.Resampling.LANCZOS).convert("RGBA")
            thumb.putalpha(circle_mask(thumb.size))
            thumb = thumb.resize((width, width), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (x, row * 320 + 56), thumb.getchannel("A"))
            draw.text((x, row * 320 + 297), f"{width}px", font=label, fill=GREEN)
    save_preserving_existing(REVIEW / "circle-crop-small-sizes.png", encoded(sheet, "PNG", optimize=True))


def generate():
    config = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    if config["name"] != "Whisk & Crumbs" or config["instagramHandle"] != "homemadevegcakes":
        raise ValueError("The reviewed composition requires the current name and Instagram handle.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            mark = emblem(browser.new_page())
        finally:
            browser.close()

    square_layer = artwork(mark)
    radius = radial_bounds(square_layer.getchannel("A"))
    if radius > 440:
        raise ValueError(f"Essential artwork exceeds its circle-safe radius: {radius}px.")
    portrait_layer = artwork(mark, 1440)
    square = finish(square_layer)
    framed = circle_frame(square)
    portrait = finish(portrait_layer)
    large = {"Square": square, "Circle frame": framed, "Portrait 3x4": portrait}
    filenames = {
        "Square": "whisk-and-crumbs-profile-square-1080.png",
        "Circle frame": "whisk-and-crumbs-profile-circle-1080.png",
        "Portrait 3x4": "whisk-and-crumbs-portrait-1080x1440.png",
    }
    records, exports = [], {}
    for name, image in large.items():
        output_size = (SIZE, 1440 if name == "Portrait 3x4" else SIZE)
        final = image.resize(output_size, Image.Resampling.LANCZOS)
        final.info.clear()
        payload = encoded(final, "PNG", optimize=True)
        save_preserving_existing(OUTPUT / filenames[name], payload)
        records.append({"file": filenames[name], "width": final.width, "height": final.height,
                        "bytes": len(payload), "sha256": sha256(payload).hexdigest(), "mode": final.mode})
        exports[name] = final
    if ImageChops.difference(exports["Square"], exports["Circle frame"]).getbbox() is None:
        raise ValueError("The framed copy must include its visible circular border.")
    crop = exports["Circle frame"].convert("RGBA")
    crop.putalpha(circle_mask(crop.size))
    save_preserving_existing(REVIEW / "circle-crop-preview.png", encoded(crop, "PNG", optimize=True))
    create_review(exports)
    manifest = {
        "name": config["name"], "handle": config["instagramHandle"],
        "generated_with": "Local Pillow and Edge, existing original mark and locally licensed fonts.",
        "palette": {"paper": CREAM, "ink": GREEN, "accent": ACCENT},
        "square_circle_geometry": {"centre": [540, 540], "radius": 540, "outer_border_px": 12,
                                   "touches": ["top", "right", "bottom", "left"]},
        "essential_artwork_radius_px": radius, "minimum_clearance_to_crop_px": round(540 - radius, 2),
        "portrait_has_circular_frame": False,
        "sources": SOURCES, "files": records,
        "limitations": [
            "These are local exports, not an uploaded Instagram profile photo.",
            "Sizing references are third-party recommendations, not official maximum or minimum limits.",
            "Crop previews assume centred positioning without zoom; confirm the actual app crop when uploading.",
            "The portrait is an alternate 3:4 asset, not the recommended profile-photo upload.",
            "Small comment-thread avatars cannot be expected to show every letter; the large whisk remains the main identifier.",
        ],
    }
    save_preserving_existing(OUTPUT / "manifest.json",
                             (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"output": str(OUTPUT), "review": str(REVIEW),
                      "artwork_radius_px": radius, "files": records}, indent=2))


if __name__ == "__main__":
    generate()
