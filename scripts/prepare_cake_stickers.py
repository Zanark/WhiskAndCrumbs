"""Make faithful, white-outlined cake stickers from separately reviewed alpha masks."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
PHOTO_MANIFEST = ROOT / "assets" / "images" / "cakes" / "manifest.json"
SOURCE = ROOT / ".local" / "photos" / "prototype-20261004" / "crops"
OUTPUT = ROOT / "assets" / "images" / "cake-stickers"


def sources(folder, manifest_path=PHOTO_MANIFEST):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for photo in manifest["photos"]:
        crop_folder = ROOT / photo["private_directory"] / "crops" if photo.get("private_directory") else folder
        file = crop_folder / f"{photo['id']}.png"
        payload = file.read_bytes()
        with Image.open(file) as original:
            image = original.convert("RGB")
        left, top, right, bottom = photo["crop_left_top_right_bottom"]
        if image.size != (right - left, bottom - top):
            raise ValueError(f"Unexpected crop dimensions: {file}")
        image.info.clear()
        yield photo, payload, image


def infer(args):
    # Only this opt-in command downloads a model. Source photographs never leave this process.
    os.environ.setdefault("U2NET_HOME", str(ROOT / ".local" / "models" / "rembg"))
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    from rembg import new_session, remove

    batch = list(sources(args.source, args.manifest))
    known = {photo["id"] for photo, _, _ in batch}
    if args.ids and set(args.ids) - known:
        raise ValueError(f"Unknown cake IDs: {set(args.ids) - known}")
    session = new_session(args.model, providers=["CPUExecutionProvider"])
    for photo, _, image in batch:
        if args.ids and photo["id"] not in args.ids:
            continue
        mask = remove(image, session=session, only_mask=True).convert("L")
        save_preserving_existing(args.output / f"{photo['id']}.png", encoded(mask, "PNG"))
        print(f"Candidate mask: {photo['id']}", flush=True)
    save_preserving_existing(args.output / "inference.json", (
        json.dumps({"model": args.model, "rembg": "2.0.85", "reviewed": False}, indent=2) + "\n"
    ).encode("utf-8"))


def refine(args):
    recipe_data = args.recipe.read_bytes()
    recipe = json.loads(recipe_data)
    records = []
    for item in recipe["photos"]:
        folder = args.detailed if item["model"] == "birefnet-general" else args.masks
        file = folder / f"{item['id']}.png"
        data = file.read_bytes()
        with Image.open(file) as opened:
            mask = opened.convert("L")
        draw = ImageDraw.Draw(mask)
        for polygon in item.get("keep_polygons", []):
            draw.polygon([tuple(point) for point in polygon], fill=255)
        for polygon in item.get("clear_polygons", []):
            draw.polygon([tuple(point) for point in polygon], fill=0)
        for box in item.get("clear_boxes", []):
            draw.rectangle(box, fill=0)
        for region in item.get("threshold_boxes", []):
            box = tuple(region["box"])
            minimum = region["minimum"]
            patch = mask.crop(box).point(lambda value: 0 if value < minimum else value)
            mask.paste(patch, box)
        payload = encoded(mask, "PNG")
        save_preserving_existing(args.output / file.name, payload)
        records.append({
            "id": item["id"], "model": item["model"],
            "candidate_mask_sha256": sha256(data).hexdigest(),
            "reviewed_mask_sha256": sha256(payload).hexdigest(),
            "correction": item["reason"],
        })
    save_preserving_existing(args.output / "review.json", (
        json.dumps({"recipe_sha256": sha256(recipe_data).hexdigest(), "photos": records}, indent=2) + "\n"
    ).encode("utf-8"))


def sticker(image, mask):
    if mask.size != image.size:
        raise ValueError("Mask dimensions must equal the source crop.")
    alpha = mask.point(lambda value: 0 if value < 12 else 255 if value > 244 else value)
    bounds = alpha.getbbox()
    if not bounds:
        raise ValueError("An empty mask cannot produce a cake sticker.")
    # Solid cake interiors retain the exact source RGB; only transparency is changed.
    foreground = image.convert("RGBA")
    foreground.putalpha(alpha)
    if ImageChops.difference(foreground.convert("RGB"), image).getbbox():
        raise ValueError("Mask application changed cake colours.")
    cutout = foreground.crop(bounds)
    padding, outline = 28, 13
    canvas = Image.new("RGBA", (cutout.width + padding * 2, cutout.height + padding * 2))
    canvas.paste(cutout, (padding, padding))
    white_alpha = canvas.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    white_alpha = white_alpha.filter(ImageFilter.MaxFilter(outline * 2 + 1))
    white_alpha = white_alpha.filter(ImageFilter.GaussianBlur(0.65))
    backing = Image.new("RGBA", canvas.size, "white")
    backing.putalpha(white_alpha)
    result = Image.alpha_composite(backing, canvas)
    if result.getpixel((0, 0))[3] != 0 or result.getchannel("A").getextrema() != (0, 255):
        raise ValueError("Sticker must have a transparent margin and opaque cake pixels.")
    return result, bounds, padding, outline


def prepare(args):
    if args.output.resolve() == args.source.resolve() or args.output.resolve().is_relative_to(args.source.resolve()):
        raise ValueError("Sticker output must be separate from source crops.")
    batch = list(sources(args.source, args.manifest))
    sheet = Image.new("RGB", (1500, len(batch) * 490 + 80), "#f5ebdd")
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 20), "SOURCE / STICKER ON CREAM / STICKER ON DARK", fill="#34483a", font_size=26)
    records = []
    for index, (photo, source_data, image) in enumerate(batch):
        mask_file = args.masks / f"{photo['id']}.png"
        mask_data = mask_file.read_bytes()
        with Image.open(mask_file) as opened:
            mask = opened.convert("L")
        result, bounds, padding, outline = sticker(image, mask)
        variants = []
        for width in sorted({min(480, result.width), min(1000, result.width)}):
            height = round(result.height * width / result.width)
            resized = result.resize((width, height), Image.Resampling.LANCZOS)
            for extension, format_name, options in (
                ("webp", "WEBP", {"quality": 94, "method": 6}),
                ("png", "PNG", {"optimize": True}),
            ):
                name = f"{photo['id']}-sticker-{width}.{extension}"
                payload = encoded(resized, format_name, **options)
                save_preserving_existing(args.output / name, payload)
                variants.append({
                    "file": name, "width": width, "height": height,
                    "bytes": len(payload), "sha256": sha256(payload).hexdigest(),
                })
        save_preserving_existing(args.output / "masks" / mask_file.name, mask_data)
        records.append({
            "id": photo["id"],
            "source_crop_sha256": sha256(source_data).hexdigest(),
            ("source_photo_sha256" if photo.get("source_type") == "instagram-export" else "source_screenshot_sha256"): photo["source_sha256"],
            "mask_sha256": sha256(mask_data).hexdigest(),
            "source_dimensions": list(image.size),
            "masked_bounds": list(bounds),
            "padding": padding,
            "white_outline": outline,
            "alt": photo["alt"],
            "source_limitation": photo["limitation"],
            "variants": variants,
        })
        y = 90 + index * 490
        draw.text((24, y), photo["id"], fill="#34483a", font_size=22)
        for column, background in enumerate(("#f5ebdd", "#f5ebdd", "#34483a")):
            tile = Image.new("RGBA", (460, 425), background)
            thumb = ImageOps.contain(image if column == 0 else result, (430, 400), Image.Resampling.LANCZOS)
            tile.alpha_composite(thumb.convert("RGBA"), ((460 - thumb.width) // 2, (425 - thumb.height) // 2))
            sheet.paste(tile.convert("RGB"), (15 + column * 495, y + 35))
        print(f"Prepared sticker: {photo['id']}", flush=True)
    manifest = {
        "schema_version": 1,
        "policy": "Background removal through reviewed masks, white outline, downsize and compression only. No cake recolouring, retouching or synthesized detail.",
        "review": "Masks require visual review; source-clipped details remain clipped. Full prepared photos remain available in the viewer.",
        "photos": records,
    }
    save_preserving_existing(args.output / "manifest.json", (
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n"
    ).encode("utf-8"))
    if (args.masks / "review.json").exists():
        save_preserving_existing(args.output / "masks" / "review.json", (args.masks / "review.json").read_bytes())
    save_preserving_existing(args.review, encoded(sheet, "JPEG", quality=94))
    print(f"Prepared {len(records)} stickers. Review: {args.review}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    candidates = commands.add_parser("infer", help="Generate local model candidates, not approved production masks.")
    candidates.add_argument("--source", type=Path, default=SOURCE)
    candidates.add_argument("--manifest", type=Path, default=PHOTO_MANIFEST)
    candidates.add_argument("--model", choices=["birefnet-general-lite", "birefnet-general", "u2net"], default="birefnet-general-lite")
    candidates.add_argument("--output", type=Path, required=True)
    candidates.add_argument("--ids", nargs="+", help="Generate only these known cake IDs.")
    candidates.set_defaults(run=infer)
    corrections = commands.add_parser("refine", help="Apply recorded alpha-only review corrections to model candidates.")
    corrections.add_argument("--masks", type=Path, required=True)
    corrections.add_argument("--detailed", type=Path, required=True)
    corrections.add_argument("--recipe", type=Path, default=OUTPUT / "mask-recipe.json")
    corrections.add_argument("--output", type=Path, required=True)
    corrections.set_defaults(run=refine)
    ready = commands.add_parser("prepare", help="Render transparent variants from reviewed masks; no model or network.")
    ready.add_argument("--source", type=Path, default=SOURCE)
    ready.add_argument("--manifest", type=Path, default=PHOTO_MANIFEST)
    ready.add_argument("--masks", type=Path, required=True)
    ready.add_argument("--output", type=Path, default=OUTPUT)
    ready.add_argument("--review", type=Path, default=ROOT / ".local" / "stickers" / "review.jpg")
    ready.set_defaults(run=prepare)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
