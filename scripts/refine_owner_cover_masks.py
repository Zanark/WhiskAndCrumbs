"""Generate private alpha-only chocolate candidates and a bounded comparison sheet."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from scipy import ndimage

from prepare_cake_stickers import sticker
from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / ".local" / "stickers" / "owner-covers-20261005"
SOURCE = ROOT / ".local" / "photos" / "owner-covers-20261005" / "crops" / "assorted-moulded-chocolates.png"
MASK = BATCH / "detailed-masks" / "assorted-moulded-chocolates.png"


def local_puzzle_mask(candidate):
    neutral_path = BATCH / "refined-v2" / "chocolates-gentle.png"
    if sha256(neutral_path.read_bytes()).hexdigest() != "b995ba5aa4fa0956cf770feda5cd8566e64aa6b6ba3c4fa22dc076b463e36911":
        raise ValueError("The recorded neutral foreground candidate has changed.")
    with Image.open(neutral_path) as opened:
        neutral = np.asarray(opened) >= 128
    restored = np.zeros(neutral.shape, dtype=bool)
    for box, point in (
        ((80, 0, 320, 220), (161, 86)),
        ((65, 145, 325, 355), (150, 231)),
        ((0, 305, 215, 535), (97, 410)),
    ):
        left, top, right, bottom = box
        support = np.asarray(candidate)[top:bottom, left:right] >= 12
        x, y = point[0] - left, point[1] - top
        components, _ = ndimage.label(neutral[top:bottom, left:right] & support)
        component = components[y, x]
        if component == 0:
            raise ValueError(f"The protected puzzle foreground was lost: {point}")
        foreground = ndimage.binary_fill_holes(components == component) & support
        if foreground.sum() < 400:
            raise ValueError(f"The puzzle recovery is only an isolated seed: {point}")
        restored[top:bottom, left:right] |= foreground
    return restored


def refine(image, candidate, paper_threshold):
    pixels = np.asarray(image, dtype=np.int16)
    red, green, blue = (pixels[:, :, channel] for channel in range(3))
    support = np.asarray(candidate) >= 12
    warm = (red - blue > 9) & (red - green > 3) & (pixels.max(axis=2) < 220) & support
    labels, _ = ndimage.label(warm)
    sizes = np.bincount(labels.ravel())
    seeds = ndimage.binary_erosion(warm & (sizes[labels] >= 900), iterations=2)
    blue_tray = (blue - red > 45) & (blue > 110)
    paper = (pixels.max(axis=2) > paper_threshold) & (blue - red > 8) & (green - red > 5)
    labels = np.full(support.shape, cv2.GC_PR_BGD, dtype=np.uint8)
    labels[support] = cv2.GC_PR_FGD
    labels[~support | ndimage.binary_erosion(blue_tray | paper, iterations=2)] = cv2.GC_BGD
    labels[seeds] = cv2.GC_FGD
    for x, y in ((161, 86), (150, 231), (97, 410), (62, 238), (254, 355)):
        labels[y - 4:y + 5, x - 4:x + 5] = cv2.GC_FGD
    cv2.setRNGSeed(0)
    cv2.setNumThreads(1)
    cv2.grabCut(np.asarray(image), labels, None, np.zeros((1, 65)), np.zeros((1, 65)),
                8, cv2.GC_INIT_WITH_MASK)
    foreground = np.isin(labels, [cv2.GC_FGD, cv2.GC_PR_FGD]) & support
    foreground |= local_puzzle_mask(candidate)
    holes = ndimage.binary_fill_holes(foreground) & ~foreground
    labels, _ = ndimage.label(holes)
    sizes = np.bincount(labels.ravel())
    foreground |= holes & (sizes[labels] <= 200)
    labels, _ = ndimage.label(foreground)
    sizes = np.bincount(labels.ravel())
    foreground &= sizes[labels] >= 400
    mask = Image.fromarray(np.uint8(foreground) * 255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.5))
    return mask


def run(output):
    output = output.resolve()
    if not output.is_relative_to(BATCH.resolve()) or output == BATCH.resolve():
        raise ValueError("Use a new private revision inside the owner-cover candidate directory.")
    raw_mask = MASK.read_bytes()
    if sha256(raw_mask).hexdigest() != "b785574e22886ba1ed84adda3d35a500b838fffb322d2044af00c0c86511f135":
        raise ValueError("The reviewed detailed candidate has changed.")
    photos = json.loads((SOURCE.parent.parent / "prepared" / "manifest.json").read_text(encoding="utf-8"))["photos"]
    photo = next(item for item in photos if item["id"] == "assorted-moulded-chocolates")
    original = SOURCE.parent.parent / "originals" / photo["source_file"]
    if sha256(original.read_bytes()).hexdigest() != photo["source_sha256"]:
        raise ValueError("The chocolate original has changed.")
    with Image.open(SOURCE) as opened, Image.open(MASK) as opened_mask, Image.open(original) as opened_original:
        image = opened.convert("RGB")
        candidate = opened_mask.convert("L")
        if ImageOps.exif_transpose(opened_original).convert("RGB").tobytes() != image.tobytes():
            raise ValueError("The crop must retain the original full-frame RGB.")
    masks = {
        name: refine(image, candidate, threshold)
        for name, threshold in (("gentle", 215), ("strict", 190))
    }
    rendered = {name: sticker(image, mask)[0] for name, mask in masks.items()}
    raw_sticker = sticker(image, candidate)[0]
    cutouts = {}
    for name, mask in masks.items():
        cutout = image.convert("RGBA")
        cutout.putalpha(mask)
        cutouts[name] = cutout
    boxes = {
        "upper left": (0, 0, 540, 540),
        "lower left": (0, 500, 540, 1040),
        "upper right": (540, 0, 1080, 540),
        "lower right": (540, 500, 1080, 1040),
    }
    tiles = [
        ("Full source", image, "#f5ebdd"),
        ("Raw detailed - rejected tray", raw_sticker, "#f5ebdd"),
        ("Strict candidate", rendered["strict"], "#f5ebdd"),
        ("Gentle candidate", rendered["gentle"], "#f5ebdd"),
        ("Gentle candidate / green", rendered["gentle"], "#34483a"),
        ("Source / upper left", image.crop(boxes["upper left"]), "#f5ebdd"),
        ("Strict alpha / upper left", cutouts["strict"].crop(boxes["upper left"]), "#34483a"),
        ("Gentle alpha / upper left", cutouts["gentle"].crop(boxes["upper left"]), "#34483a"),
        ("Source / lower left", image.crop(boxes["lower left"]), "#f5ebdd"),
        ("Gentle alpha / lower left", cutouts["gentle"].crop(boxes["lower left"]), "#34483a"),
        ("Source / upper right", image.crop(boxes["upper right"]), "#f5ebdd"),
        ("Gentle alpha / upper right", cutouts["gentle"].crop(boxes["upper right"]), "#34483a"),
        ("Source / lower right", image.crop(boxes["lower right"]), "#f5ebdd"),
        ("Gentle alpha / lower right", cutouts["gentle"].crop(boxes["lower right"]), "#34483a"),
        ("Strict candidate / green", rendered["strict"], "#34483a"),
    ]
    canvas = Image.new("RGB", (1800, 1220), "#f5ebdd")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(ROOT / "web" / "assets" / "fonts" / "dm-sans-regular.ttf"), 17)
    draw.text((16, 14), "CHOCOLATE ALPHA REFINEMENT - 15 labelled thumbnails - UNREVIEWED CANDIDATES", font=font, fill="#34483a")
    for index, (label, art, background) in enumerate(tiles):
        left, top = (index % 5) * 360 + 12, (index // 5) * 390 + 58
        draw.text((left, top), "17952408272859389.jpg", font=font, fill="#34483a")
        draw.text((left, top + 25), label, font=font, fill="#34483a")
        tile = Image.new("RGBA", (336, 322), background)
        thumb = ImageOps.contain(art, (320, 306), Image.Resampling.LANCZOS)
        tile.alpha_composite(thumb.convert("RGBA"), ((tile.width - thumb.width) // 2, (tile.height - thumb.height) // 2))
        canvas.paste(tile.convert("RGB"), (left, top + 52))
    records = []
    for name, mask in masks.items():
        payload = encoded(mask, "PNG")
        file = output / f"chocolates-{name}.png"
        save_preserving_existing(file, payload)
        records.append({"name": name, "mask": str(file), "sha256": sha256(payload).hexdigest(),
                        "reviewed": False, "selected": False})
    sheet = output / "chocolate-refinement-15.jpg"
    payload = encoded(canvas, "JPEG", quality=94, subsampling=0)
    save_preserving_existing(sheet, payload)
    receipt = {
        "source_sha256": photo["source_sha256"], "crop_sha256": sha256(SOURCE.read_bytes()).hexdigest(),
        "candidate_mask_sha256": sha256(raw_mask).hexdigest(), "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "correction": "Eight-iteration deterministic GrabCut with warm foreground components, five protected neutral samples, original detailed-mask support and blue/paper seeds. Three source-box-local recoveries use the seed-connected neutral-v2 puzzle components and fill their internal alpha holes. Paper thresholds215/190; other holes at most200pixels, components at least400pixels, 0.5px alpha blur. No RGB changes.",
        "candidates": records, "contact_sheet": str(sheet), "thumbnails": len(tiles),
        "contact_sheet_sha256": sha256(payload).hexdigest(), "visual_review": "pending",
    }
    save_preserving_existing(output / "refinement-source.py", Path(__file__).read_bytes())
    save_preserving_existing(output / "refinement.json", (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(receipt, indent=2))


def restore_reflection(output):
    output = output.resolve()
    if not output.is_relative_to(BATCH.resolve()) or output == BATCH.resolve():
        raise ValueError("Use a new private reflection-mask revision.")
    recipe_path = BATCH / "final-mask-recipe.json"
    recipe_data = recipe_path.read_bytes()
    recipe = json.loads(recipe_data)
    if sha256(SOURCE.read_bytes()).hexdigest() != recipe["reflection_source_crop_sha256"]:
        raise ValueError("The reflection source crop changed.")
    with Image.open(SOURCE) as opened:
        pixels = np.asarray(opened.convert("RGB"), dtype=np.int16)
    rule = recipe["retain_prior_alpha_for_new_blue_pixels"]
    blue = ((pixels[:, :, 2] - pixels[:, :, 0] > rule["blue_minus_red_greater_than"]) &
            (pixels[:, :, 0] < rule["red_less_than"]) & (pixels[:, :, 2] > rule["blue_greater_than"]))
    records = []
    for photo in recipe["photos"]:
        base_path = BATCH / "preview-masks" / f"{photo['id']}.png"
        base_data = base_path.read_bytes()
        with Image.open(base_path) as opened:
            base = opened.convert("L")
        mask = base.copy()
        draw = ImageDraw.Draw(mask)
        for polygon in photo.get("keep_polygons", []):
            draw.polygon([tuple(point) for point in polygon], fill=255)
        retained_blue = 0
        if photo["id"] == "assorted-moulded-chocolates":
            if sha256(base_data).hexdigest() != recipe["reflection_base_mask_sha256"]:
                raise ValueError("The recorded reflection base mask changed.")
            before, after = np.asarray(base), np.asarray(mask).copy()
            excluded = (after > before) & blue
            retained_blue = int(excluded.sum())
            after[excluded] = before[excluded]
            if np.any(after < before):
                raise ValueError("Reflection recovery must not erase existing foreground.")
            mask = Image.fromarray(after)
        payload = encoded(mask, "PNG")
        save_preserving_existing(output / base_path.name, payload)
        records.append({"id": photo["id"], "candidate_mask_sha256": sha256(base_data).hexdigest(),
                        "output_mask_sha256": sha256(payload).hexdigest(),
                        "new_blue_pixels_kept_at_prior_alpha": retained_blue, "correction": photo["reason"]})
    receipt = {"status": "visual-review-pending", "recipe_sha256": sha256(recipe_data).hexdigest(),
               "source_rgb_changed": False, "photos": records}
    save_preserving_existing(output / "reflection-recipe.json", recipe_data)
    save_preserving_existing(output / "refinement-source.py", Path(__file__).read_bytes())
    save_preserving_existing(output / "review.json", (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reflection-only", action="store_true")
    args = parser.parse_args()
    (restore_reflection if args.reflection_only else run)(args.output)
