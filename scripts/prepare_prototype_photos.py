"""Prepare reviewed photographs with crop-only edits and untouched originals."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
RECIPES = [
    {
        "source": "Screenshot 2026-10-04 020847.png",
        "size": (1295, 1297),
        "slug": "peacock-feather-cake",
        "crop": (285, 0, 995, 1150),
        "alt": "An orange cake with white floral piping, green trim and a tall peacock feather decoration.",
        "use": "Portrait gallery; keep the full visible feather in frame.",
        "limitation": "Patterned seating remains behind the feather; its upper edge was already clipped in the source.",
    },
    {
        "source": "Screenshot 2026-10-04 020937.png",
        "size": (1277, 1281),
        "slug": "ribbon-and-pearl-cake",
        "crop": (90, 195, 1145, 1150),
        "alt": "A white-frosted round cake decorated with burgundy bows, pink pearl shapes and piped loops.",
        "use": "Strongest candidate for a prototype feature image or menu card.",
        "limitation": "Original frosting texture, lighting and table setting are retained.",
    },
    {
        "source": "Screenshot 2026-10-04 020956.png",
        "size": (1550, 1287),
        "slug": "cherry-topped-cake",
        "crop": (45, 0, 1175, 955),
        "alt": "A round cake with white piped swirls, red cherries, colourful sprinkles and textured sides.",
        "use": "Close-up menu card; preserve the native crop instead of another cover crop.",
        "limitation": "Some top cherries were already clipped in the source; a small background object remains.",
    },
    {
        "source": "Screenshot 2026-10-04 021017.png",
        "size": (1292, 1284),
        "slug": "pink-doll-cake",
        "crop": (235, 160, 1120, 1284),
        "alt": "A doll cake with a pink-and-white piped dress and small gold-coloured decorations.",
        "use": "Portrait custom-design example, not a wide hero.",
        "limitation": "The dress base was already clipped in the source; some household background remains.",
    },
    {
        "source": "Screenshot 2026-10-04 021041.png",
        "size": (1283, 1273),
        "slug": "butterfly-celebration-cake",
        "crop": (115, 365, 1140, 1255),
        "alt": "A white-frosted celebration cake with butterfly decorations, red cherries and a piped message.",
        "use": "Celebration/menu card with topper and cake board visible.",
        "limitation": "Existing lettering is unchanged; no flavour is inferred from its appearance.",
    },
]


def save_preserving_existing(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing file differs: {path}. Use a new output revision.")
        return
    with path.open("xb") as output:
        output.write(data)


def encoded(image, format_name, **options):
    buffer = BytesIO()
    image.save(buffer, format=format_name, **options)
    return buffer.getvalue()


def prepare(source, output, private, recipes=RECIPES):
    source, output, private = source.resolve(), output.resolve(), private.resolve()
    for target in (output, private):
        if target == source or target.is_relative_to(source) or source.is_relative_to(target):
            raise ValueError("Source and output folders must not overlap.")
    loaded = []
    # Validate the entire reviewed batch before publishing any derived files.
    if not recipes or len({recipe["slug"] for recipe in recipes}) != len(recipes):
        raise ValueError("The reviewed recipe must contain unique photo IDs.")
    for recipe in recipes:
        path = source / recipe["source"]
        data = path.read_bytes()
        if recipe.get("sha256") and sha256(data).hexdigest() != recipe["sha256"]:
            raise ValueError(f"Source hash changed: {path.name}")
        with Image.open(BytesIO(data)) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
        if image.size != tuple(recipe["size"]):
            raise ValueError(f"Unexpected dimensions for {path.name}: {image.size}")
        left, top, right, bottom = recipe["crop"]
        if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
            raise ValueError(f"Invalid crop for {path.name}")
        image.info.clear()
        loaded.append((recipe, data, image))

    sheet = Image.new("RGB", (1320, 150 + len(recipes) * 430), "#f5ebdd")
    draw = ImageDraw.Draw(sheet)
    draw.text((30, 20), "PROTOTYPE PHOTOS - crop-only preparation", fill="#34483a", font_size=28)
    source_label = "Source screenshots" if recipes is RECIPES else "Source photographs"
    draw.text((30, 62), f"{source_label} on the left; prepared crops on the right.", fill="#76543d", font_size=20)
    draw.text((30, 94), "No background replacement, icing edits, colour filters or generated detail.", fill="#76543d", font_size=18)
    records = []
    for index, (recipe, data, original) in enumerate(loaded):
        save_preserving_existing(private / "originals" / recipe["source"], data)
        cropped = original.crop(recipe["crop"])
        save_preserving_existing(
            private / "crops" / f"{recipe['slug']}.png",
            encoded(cropped, "PNG"),
        )
        variants = []
        for width in sorted({min(480, cropped.width), min(1000, cropped.width)}):
            height = round(cropped.height * width / cropped.width)
            resized = cropped.resize((width, height), Image.Resampling.LANCZOS)
            for extension, format_name, options in (
                ("webp", "WEBP", {"quality": 90, "method": 6}),
                ("jpg", "JPEG", {"quality": 92, "subsampling": 0, "optimize": True}),
            ):
                filename = f"{recipe['slug']}-{width}.{extension}"
                payload = encoded(resized, format_name, **options)
                save_preserving_existing(output / filename, payload)
                variants.append({
                    "file": filename, "width": width, "height": height,
                    "bytes": len(payload), "sha256": sha256(payload).hexdigest(),
                })
        records.append({
            "id": recipe["slug"],
            "source_type": recipe.get("source_type", "user-supplied-screenshot"),
            "source_file": recipe["source"],
            "source_sha256": sha256(data).hexdigest(),
            "source_dimensions": recipe["size"],
            "crop_left_top_right_bottom": recipe["crop"],
            "alt": recipe["alt"],
            "suggested_use": recipe["use"],
            "limitation": recipe["limitation"],
            "variants": variants,
        })
        if recipe.get("source_type") == "instagram-export":
            records[-1]["private_directory"] = private.relative_to(ROOT).as_posix()
            records[-1]["export_file"] = recipe["export_file"]
        row_top = 145 + index * 430
        draw.text((30, row_top), recipe["slug"], fill="#34483a", font_size=22)
        draw.text((30, row_top + 30), recipe["source"], fill="#76543d", font_size=16)
        for image, left in ((original, 30), (cropped, 680)):
            thumb = ImageOps.contain(image, (580, 350), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (left + (580 - thumb.width) // 2, row_top + 64))

    manifest = {
        "schema_version": 1,
        "status": "prototype-assets-not-user-approved-final-photography",
        "policy": "Crop, downsize and compress only. Originals unchanged; no invented pixels or colour changes.",
        "layout_rule": "Preserve each image's aspect ratio; do not apply another cover crop that clips decorations.",
        "photos": records,
    }
    save_preserving_existing(
        output / "manifest.json",
        (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode("utf-8"),
    )
    save_preserving_existing(private / "review.jpg", encoded(sheet, "JPEG", quality=92))
    print(f"Prepared {len(records)} photos and {sum(len(r['variants']) for r in records)} web variants.")
    print(f"Untouched originals and before/after preview: {private}")
    print(f"Prototype assets and crop manifest: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="folder containing the reviewed source images")
    parser.add_argument("--recipe", type=Path, help="JSON list of reviewed crops; defaults to the original five screenshots")
    parser.add_argument("--output", type=Path, default=ROOT / "assets" / "images" / "cakes")
    parser.add_argument("--private", type=Path, default=ROOT / ".local" / "photos" / "prototype-20261004")
    args = parser.parse_args()
    recipes = json.loads(args.recipe.read_text(encoding="utf-8")) if args.recipe else RECIPES
    prepare(args.source, args.output, args.private, recipes)


if __name__ == "__main__":
    main()
