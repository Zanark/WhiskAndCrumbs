"""Capture the local covers and create one final, labelled 15-thumbnail review."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
STICKERS = ROOT / "assets" / "images" / "cake-stickers"
CROPS = ROOT / ".local" / "photos" / "owner-covers-20261005" / "crops"
FIT = ROOT / ".local" / "category-notebooks" / "viewport-fit-confirmed-weight"


def create(url, output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        raise ValueError("Review sheets and captures must stay private.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference")
        page.goto(url + "#cakes")
        page.evaluate("document.fonts.ready")
        for category in ("birthday-cakes", "tea-cakes", "chocolates"):
            cover = page.locator(f'.notebook-cover[data-category="{category}"]')
            cover.scroll_into_view_if_needed()
            cover.locator("img").evaluate("image => image.decode()")
            save_preserving_existing(output / f"{category}-cover.png", cover.screenshot(animations="disabled"))
        for image in page.locator(".notebook-cover picture img").all():
            image.scroll_into_view_if_needed()
            image.evaluate("image => image.decode()")
        save_preserving_existing(output / "category-overview.png", page.locator("#category-notebooks").screenshot(animations="disabled"))
        browser.close()
    manifest = json.loads((STICKERS / "manifest.json").read_text(encoding="utf-8"))["photos"]
    chocolate = next(photo for photo in manifest if photo["id"] == "assorted-moulded-chocolates")
    variant = next(item for item in chocolate["variants"] if item["file"].endswith("-1000.png"))
    with Image.open(CROPS / "assorted-moulded-chocolates.png") as opened:
        source = opened.convert("RGB")
    with Image.open(STICKERS / variant["file"]) as opened:
        final = opened.convert("RGBA")
    with Image.open(STICKERS / "masks" / "assorted-moulded-chocolates.png") as opened:
        mask = opened.convert("L")
    alpha = source.convert("RGBA")
    alpha.putalpha(mask)
    left = (65, 100, 305, 285)
    birthday = Image.open(CROPS / "pastel-celebration-cake.png").convert("RGBA")
    with Image.open(STICKERS / "masks" / "pastel-celebration-cake.png") as opened:
        birthday.putalpha(opened.convert("L"))
    tiles = [
        ("Chocolates: full source", source, "#f5ebdd"),
        ("Chocolates: final candidate / cream", final, "#f5ebdd"),
        ("Chocolates: final candidate / green", final, "#34483a"),
        ("Source: reflective face / native", source.crop(left), "#f5ebdd"),
        ("Corrected: same native region", alpha.crop(left), "#34483a"),
        ("Birthday: actual local cover", output / "birthday-cakes-cover.png", "#f5ebdd"),
        ("Tea cakes: actual local cover", output / "tea-cakes-cover.png", "#f5ebdd"),
        ("Chocolates: actual local cover", output / "chocolates-cover.png", "#f5ebdd"),
        ("Birthday: unchanged topper detail", birthday.crop((340, 160, 820, 510)), "#34483a"),
        ("Actual six-category overview", output / "category-overview.png", "#f5ebdd"),
        ("Four photos: desktop 1440x1000", FIT / "decorated-cakes-1440x1000-100-page1.png", "#f5ebdd"),
        ("Four photos: phone 390x844", FIT / "decorated-cakes-390x844-100-page1.png", "#f5ebdd"),
        ("Four photos: landscape 844x390", FIT / "decorated-cakes-844x390-100-page1.png", "#f5ebdd"),
        ("Image-free weights: phone 390x844", FIT / "birthday-cakes-390x844-100-page0.png", "#f5ebdd"),
        ("Four photos: 320x900, 200% text", FIT / "decorated-cakes-320x900-200-page1.png", "#f5ebdd"),
    ]
    canvas = Image.new("RGB", (2150, 1570), "#f5ebdd")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(ROOT / "web" / "assets" / "fonts" / "dm-sans-regular.ttf"), 18)
    draw.text((16, 16), "FINAL LOCAL COVER / NO-SCROLL REVIEW - 15 labelled thumbnails - NOT YET PUBLISHED", font=font, fill="#34483a")
    records = []
    for index, (label, item, background) in enumerate(tiles):
        if isinstance(item, Path):
            with Image.open(item) as opened:
                art = opened.convert("RGBA")
            origin = str(item)
        else:
            art = item.convert("RGBA")
            origin = "Source/candidate region specified by this script"
        x, y = (index % 5) * 430 + 12, (index // 5) * 500 + 60
        if draw.textlength(label, font=font) > 406:
            raise ValueError(f"The review label is too long: {label}")
        draw.text((x, y), label, font=font, fill="#34483a")
        tile = Image.new("RGBA", (406, 450), background)
        thumb = art.copy()
        thumb.thumbnail((390, 434), Image.Resampling.LANCZOS)
        tile.alpha_composite(thumb, ((tile.width - thumb.width) // 2, (tile.height - thumb.height) // 2))
        canvas.paste(tile.convert("RGB"), (x, y + 32))
        records.append({"tile": index + 1, "label": label, "source": origin})
    sheet = output / "covers-and-no-scroll-final-15.jpg"
    payload = encoded(canvas, "JPEG", quality=94, subsampling=0)
    save_preserving_existing(sheet, payload)
    receipt = {"sheet": str(sheet), "sha256": sha256(payload).hexdigest(), "thumbnails": len(tiles),
               "status": "not-yet-viewed", "tiles": records}
    save_preserving_existing(output / "sheet.json", (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({key: receipt[key] for key in ("sheet", "sha256", "thumbnails", "status")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create(args.url, args.output)
