"""Check the three private owner-selected cover candidates; never mark masks reviewed."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from prepare_cake_stickers import sticker
from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / ".local" / "photos" / "owner-covers-20261005"
CANDIDATES = ROOT / ".local" / "stickers" / "owner-covers-20261005"


def check():
    photos = json.loads((PHOTOS / "prepared" / "manifest.json").read_text(encoding="utf-8"))["photos"]
    recipes = json.loads((PHOTOS / "selection.json").read_text(encoding="utf-8"))
    if len(photos) != 3 or {photo["id"] for photo in photos} != {recipe["slug"] for recipe in recipes}:
        raise ValueError("Expected the three exact owner-selected cover sources.")
    canvas = Image.new("RGB", (1600, 980), "#f5ebdd")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(ROOT / "web" / "assets" / "fonts" / "dm-sans-regular.ttf"), 17)
    draw.text((16, 12), "OWNER COVER CANDIDATES - 15 labelled thumbnails - NOT VISUALLY REVIEWED", font=font, fill="#34483a")
    headings = ["Source", "Detailed / cream", "Detailed / dark", "Lite / cream", "Lite / dark"]
    checks = []
    for row, photo in enumerate(photos):
        recipe = next(item for item in recipes if item["slug"] == photo["id"])
        original = PHOTOS / "originals" / photo["source_file"]
        imported = ROOT / ".local" / "instagram" / "imported" / "images" / photo["source_file"]
        digest = sha256(original.read_bytes()).hexdigest()
        if digest != recipe["sha256"] or original.read_bytes() != imported.read_bytes():
            raise ValueError(f"Original source changed: {original}")
        crop_path = PHOTOS / "crops" / f"{photo['id']}.png"
        with Image.open(original) as opened, Image.open(crop_path) as cropped:
            source = ImageOps.exif_transpose(opened).convert("RGB")
            image = cropped.convert("RGB")
            if source.size != image.size or ImageChops.difference(source, image).getbbox():
                raise ValueError(f"The full-framing source RGB was changed: {photo['id']}")
        versions = []
        for model in ("detailed", "lite"):
            folder = CANDIDATES / f"{model}-prepared"
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            record = next(item for item in manifest["photos"] if item["id"] == photo["id"])
            mask_path = folder / "masks" / f"{photo['id']}.png"
            if sha256(mask_path.read_bytes()).hexdigest() != record["mask_sha256"]:
                raise ValueError(f"Mask changed: {mask_path}")
            with Image.open(mask_path) as opened:
                mask = opened.convert("L")
            result, bounds, padding, _ = sticker(image, mask)
            opaque = mask.crop(bounds).point(lambda value: 255 if value > 244 else 0)
            rgb = image.crop(bounds)
            retained = result.crop((padding, padding, padding + rgb.width, padding + rgb.height)).convert("RGB")
            difference = ImageChops.difference(rgb, retained)
            if Image.composite(difference, Image.new("RGB", difference.size), opaque).getbbox():
                raise ValueError(f"Opaque source pixels changed: {photo['id']} / {model}")
            for variant in record["variants"]:
                path = folder / variant["file"]
                if sha256(path.read_bytes()).hexdigest() != variant["sha256"]:
                    raise ValueError(f"Candidate variant changed: {path}")
                with Image.open(path) as saved:
                    if saved.size != (variant["width"], variant["height"]) or saved.mode != "RGBA":
                        raise ValueError(f"Invalid variant dimensions/mode: {path}")
                    if saved.getexif() or saved.info.get("xmp") or saved.getpixel((0, 0))[3] != 0:
                        raise ValueError(f"Metadata/padding check failed: {path}")
                    if saved.width > result.width or saved.height > result.height:
                        raise ValueError(f"Upscaled candidate: {path}")
            alpha = mask.point(lambda value: 255 if value > 244 else 0)
            checks.append({"id": photo["id"], "model": model, "source_sha256": digest,
                           "mask_sha256": record["mask_sha256"], "masked_bounds": list(bounds),
                           "opaque_fraction": sum(alpha.histogram()[245:]) / (alpha.width * alpha.height),
                           "source_rgb_preserved": True, "variants": len(record["variants"]),
                           "visual_review": "pending", "selected": False})
            versions.append(result)
        tiles = [(image, "#f5ebdd"), (versions[0], "#f5ebdd"), (versions[0], "#34483a"),
                 (versions[1], "#f5ebdd"), (versions[1], "#34483a")]
        for column, (art, background) in enumerate(tiles):
            left, top = column * 320, 64 + row * 300
            for offset, text in [(0, Path(photo["export_file"]).name), (24, headings[column])]:
                if draw.textlength(text, font=font) > 296:
                    raise ValueError(f"Review label does not fit: {text}")
                draw.text((left + 12, top + offset), text, font=font, fill="#34483a")
            tile = Image.new("RGBA", (296, 228), background)
            thumb = ImageOps.contain(art, (280, 212), Image.Resampling.LANCZOS)
            tile.alpha_composite(thumb.convert("RGBA"), ((tile.width - thumb.width) // 2, (tile.height - thumb.height) // 2))
            canvas.paste(tile.convert("RGB"), (left + 12, top + 52))
    sheet = CANDIDATES / "owner-cover-candidates-15.jpg"
    save_preserving_existing(sheet, encoded(canvas, "JPEG", quality=92, subsampling=0))
    report = {
        "status": "technical-checks-passed-visual-selection-pending",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_photos": 3, "candidate_cutouts": 6, "sticker_variants": 24,
        "contact_sheet": str(sheet), "contact_sheet_thumbnails": 15,
        "contact_sheet_sha256": sha256(sheet.read_bytes()).hexdigest(),
        "checks": checks,
        "limitations": [
            "No candidate mask has been visually selected or approved.",
            "Original RGB/hash preservation does not establish correct foreground segmentation.",
            "Both tea cakes, all visible chocolate pieces and the complete visible topper need contact-sheet inspection.",
            "Source-clipped details and existing lettering must not be reconstructed or rewritten.",
            "Nothing here has been promoted to public assets or installed on website covers.",
        ],
    }
    (CANDIDATES / "technical-checks.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "source_photos", "candidate_cutouts", "sticker_variants",
                                                 "contact_sheet", "contact_sheet_thumbnails")}, indent=2))


if __name__ == "__main__":
    check()
