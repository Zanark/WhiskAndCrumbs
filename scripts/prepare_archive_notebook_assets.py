"""Prepare private notebook-ready photos and candidate stickers from reviewed archive decisions."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from prepare_cake_stickers import sticker
from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_PREFIXES = {
    "Birthday Cakes": "birthday-cakes",
    "Cream cakes": "cream-cakes",
    "Decorated cakes": "decorated-cakes",
    "Tea cakes": "tea-cakes",
    "Doll cakes": "doll-cakes",
    "Chocolates": "chocolates",
}
PUBLICATION_EXCLUSIONS = {"non-product", "process", "uncertain"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    save_preserving_existing(
        path,
        (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8"),
    )


def replace_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def current_source_map():
    photo_manifest = read_json(ROOT / "assets" / "images" / "cakes" / "manifest.json")
    notebooks = read_json(ROOT / "content" / "notebooks.json")
    category_by_cake = {
        cake_id: notebook["id"]
        for notebook in notebooks
        for cake_id in notebook["cakeIds"]
    }
    result = {}
    for photo in photo_manifest["photos"]:
        digest = photo["source_sha256"]
        result[digest] = {
            "cake_id": photo["id"],
            "notebook_id": category_by_cake[photo["id"]],
        }
    return result


def reviewed_decisions(review):
    result = {}
    for path in sorted((review / "decisions").glob("batch-*.json")):
        document = read_json(path)
        if document["status"] != "reviewed":
            raise ValueError(f"Review batch is not complete: {path}")
        for item in document["items"]:
            if item["id"] in result:
                raise ValueError(f"Duplicate review decision: {item['id']}")
            result[item["id"]] = item
    return result


def category_from_reason(reason):
    for label, notebook_id in CATEGORY_PREFIXES.items():
        if reason.startswith(label + ":"):
            return notebook_id
    return "chocolates"


def category_ledger(review):
    inventory = read_json(review / "inventory.json")
    records = inventory["files"]
    by_id = {record["id"]: record for record in records}
    decisions = reviewed_decisions(review)
    owners = {
        item["id"]: item
        for item in read_json(review / "owner-classifications.json")["items"]
    }
    current = current_source_map()
    resolved = {}

    for record in records:
        if record["duplicate_of"]:
            continue
        if record["id"] in owners:
            owner = owners[record["id"]]
            notebook_id = owner.get("notebook_id") or owner.get("suggested_notebook_id")
            if not notebook_id:
                notebook_id = "chocolates"
            classification = owner["classification"]
            reason = owner["reason"]
            include = classification not in PUBLICATION_EXCLUSIONS
        elif record["id"] in decisions:
            decision = decisions[record["id"]]
            classification = decision["classification"]
            reason = decision["reason"]
            notebook_id = category_from_reason(reason)
            include = classification not in PUBLICATION_EXCLUSIONS
        elif record["sha256"] in current:
            classification = "cake-prior-selection"
            reason = "Existing prepared website source; retain its current notebook membership."
            notebook_id = current[record["sha256"]]["notebook_id"]
            include = True
        else:
            raise ValueError(f"Missing classification for unique source {record['id']}")

        resolved[record["id"]] = {
            **record,
            "classification": classification,
            "reason": reason,
            "notebook_id": notebook_id,
            "include": include,
            "existing": current.get(record["sha256"]),
        }

    ledger = []
    for record in records:
        primary = resolved[record["duplicate_of"]] if record["duplicate_of"] else resolved[record["id"]]
        ledger.append({
            "id": record["id"],
            "relative_path": record["relative_path"],
            "sha256": record["sha256"],
            "duplicate_of": record["duplicate_of"],
            "classification": "exact-byte-duplicate" if record["duplicate_of"] else primary["classification"],
            "notebook_id": primary["notebook_id"] if primary["include"] else None,
            "include": primary["include"],
            "existing_cake_id": primary["existing"]["cake_id"] if primary["existing"] else None,
            "reason": (
                f"Exact duplicate of {record['duplicate_of']}; inherit its classification."
                if record["duplicate_of"] else primary["reason"]
            ),
        })
    return inventory, resolved, ledger


def photo_variants(image, asset_id, output):
    variants = []
    for width in sorted({min(480, image.width), min(1000, image.width)}):
        height = round(image.height * width / image.width)
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        for extension, format_name, options in (
            ("webp", "WEBP", {"quality": 92, "method": 6}),
            ("jpg", "JPEG", {"quality": 92, "subsampling": 0, "optimize": True}),
        ):
            name = f"{asset_id}-{width}.{extension}"
            payload = encoded(resized, format_name, **options)
            save_preserving_existing(output / "photos" / name, payload)
            variants.append({
                "file": name,
                "width": width,
                "height": height,
                "bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
            })
    return variants


def prepare_photos(review, output):
    inventory, resolved, ledger = category_ledger(review)
    if output.exists():
        raise ValueError(f"Choose a new output directory: {output}")

    manifest = {
        "schema_version": 1,
        "status": "private-reviewed-sources-candidate-assets-not-approved-for-publication",
        "policy": "Full framing, orientation correction, metadata removal, downsize and compression only.",
        "source_root": inventory["source_root"],
        "private_directory": str(output.relative_to(ROOT)).replace("/", "\\"),
        "photos": [],
    }
    categories = defaultdict(list)
    for record_id, record in resolved.items():
        if not record["include"]:
            continue
        if record["existing"]:
            categories[record["notebook_id"]].append({
                "source_id": record_id,
                "existing_cake_id": record["existing"]["cake_id"],
                "source_sha256": record["sha256"],
            })
            continue

        source = Path(record["path"])
        payload = source.read_bytes()
        if sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError(f"Source hash changed: {source}")
        with Image.open(BytesIO(payload)) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        image.info.clear()
        asset_id = f"archive-{record_id.lower()}-{record['sha256'][:8]}"
        crop_payload = encoded(image, "PNG", optimize=True)
        save_preserving_existing(output / "crops" / f"{asset_id}.png", crop_payload)
        photo = {
            "id": asset_id,
            "source_id": record_id,
            "source_type": "instagram-export",
            "source_file": record["filename"],
            "source_sha256": record["sha256"],
            "source_dimensions": [record["display_width"], record["display_height"]],
            "crop_left_top_right_bottom": [0, 0, image.width, image.height],
            "alt": f"A reviewed food photograph assigned to {record['notebook_id'].replace('-', ' ')} from visible appearance.",
            "suggested_use": f"Candidate for the {record['notebook_id']} notebook.",
            "limitation": "Contact-sheet classification only; preserve visible lettering, props and original framing. Candidate mask requires review.",
            "private_directory": str(output.relative_to(ROOT)).replace("/", "\\"),
            "export_file": record["relative_path"].replace("\\", "/"),
            "notebook_id": record["notebook_id"],
            "review_reason": record["reason"],
            "source_crop_sha256": sha256(crop_payload).hexdigest(),
            "variants": photo_variants(image, asset_id, output),
        }
        manifest["photos"].append(photo)
        categories[record["notebook_id"]].append({
            "source_id": record_id,
            "candidate_cake_id": asset_id,
            "source_sha256": record["sha256"],
        })

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "manifest.json", manifest)
    write_json(output / "category-map.json", {
        "categories": {key: value for key, value in sorted(categories.items())},
        "counts": dict(sorted(Counter(
            item["notebook_id"] for item in ledger if item["include"] and not item["duplicate_of"]
        ).items())),
    })
    write_json(output / "source-ledger.json", {"files": ledger})
    print(f"Prepared {len(manifest['photos'])} new full-photo records in {output}")


def sticker_sheet(entries, output, page_size=18):
    font = ImageFont.truetype(
        str(ROOT / "web" / "assets" / "fonts" / "dm-sans-regular.ttf"), 18
    )
    for page, start in enumerate(range(0, len(entries), page_size), 1):
        batch = entries[start:start + page_size]
        canvas = Image.new("RGB", (1600, 90 + 350 * ((len(batch) + 3) // 4)), "#f5ebdd")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 16), f"{output.stem} candidate stickers | page {page}", font=font, fill="#34483a")
        for index, entry in enumerate(batch):
            with Image.open(entry["sticker_file"]) as opened:
                image = opened.convert("RGBA")
            tile = Image.new("RGBA", (360, 270), "#f5ebdd")
            thumb = ImageOps.contain(image, (330, 235), Image.Resampling.LANCZOS)
            tile.alpha_composite(thumb, ((360 - thumb.width) // 2, (270 - thumb.height) // 2))
            left, top = (index % 4) * 400 + 20, 80 + (index // 4) * 350
            canvas.paste(tile.convert("RGB"), (left, top))
            draw.text((left, top + 278), entry["id"], font=font, fill="#34483a")
            draw.text((left, top + 303), entry["source_id"], font=font, fill="#34483a")
        save_preserving_existing(
            output.parent / f"{output.stem}-{page:02}.jpg",
            encoded(canvas, "JPEG", quality=92, subsampling=0),
        )


def straight_cut_issues(alpha):
    solid = alpha.point(lambda value: 255 if value >= 128 else 0)
    bounds = solid.getbbox()
    if not bounds:
        return ["empty-mask"]
    width, height = solid.size
    margin = max(6, round(min(width, height) * 0.008))
    left, top, right, bottom = bounds
    issues = []
    if left < margin or top < margin or right > width - margin or bottom > height - margin:
        issues.append("foreground-reaches-source-edge")

    threshold = max(36, round(max(width, height) * 0.10))
    boundary = ImageChops.subtract(solid, solid.filter(ImageFilter.MinFilter(3)))
    needle = b"\xff" * threshold
    horizontal = boundary.tobytes()
    if any(needle in horizontal[y * width:(y + 1) * width] for y in range(height)):
        issues.append(f"long-straight-horizontal-boundary:{threshold}px+")
    vertical_image = boundary.transpose(Image.Transpose.TRANSPOSE)
    vertical = vertical_image.tobytes()
    if any(needle in vertical[x * height:(x + 1) * height] for x in range(width)):
        issues.append(f"long-straight-vertical-boundary:{threshold}px+")
    flattened = (
        boundary.get_flattened_data()
        if hasattr(boundary, "get_flattened_data")
        else boundary.getdata()
    )
    coordinates = [
        (index % width, index // width)
        for index, value in enumerate(flattened)
        if value
    ]
    if len(coordinates) > 12000:
        coordinates = coordinates[::math.ceil(len(coordinates) / 12000)]
    diagonal_threshold = max(60, round(max(width, height) * 0.18))
    for degrees in range(2, 180, 2):
        radians = math.radians(degrees)
        cosine, sine = math.cos(radians), math.sin(radians)
        buckets = defaultdict(list)
        for x, y in coordinates:
            rho = round((x * cosine + y * sine) / 2)
            tangent = -x * sine + y * cosine
            buckets[rho].append(tangent)
        found = False
        for values in buckets.values():
            if len(values) < diagonal_threshold // 2:
                continue
            values.sort()
            start = previous = values[0]
            for value in values[1:]:
                if value - previous > 3:
                    start = value
                elif value - start >= diagonal_threshold:
                    issues.append(
                        f"long-straight-diagonal-boundary:{diagonal_threshold}px+"
                    )
                    found = True
                    break
                previous = value
            if found:
                break
        if found:
            break
    return issues


def prepare_stickers(prepared, masks):
    manifest = read_json(prepared / "manifest.json")
    output = prepared / "stickers"
    records = []
    rejected = []
    sheets = defaultdict(list)
    for photo in manifest["photos"]:
        crop_file = prepared / "crops" / f"{photo['id']}.png"
        mask_file = masks / f"{photo['id']}.png"
        with Image.open(crop_file) as opened:
            image = opened.convert("RGB")
        with Image.open(mask_file) as opened:
            mask = opened.convert("L")
        issues = straight_cut_issues(mask)
        if issues:
            rejected.append({
                "id": photo["id"],
                "source_id": photo["source_id"],
                "notebook_id": photo["notebook_id"],
                "mask_sha256": sha256(mask_file.read_bytes()).hexdigest(),
                "issues": issues,
                "status": "rejected-no-sticker-created",
            })
            print(f"Rejected straight-cut candidate: {photo['id']} ({', '.join(issues)})", flush=True)
            continue
        result, bounds, padding, outline = sticker(image, mask)
        result_issues = straight_cut_issues(result.getchannel("A"))
        if result_issues:
            rejected.append({
                "id": photo["id"],
                "source_id": photo["source_id"],
                "notebook_id": photo["notebook_id"],
                "mask_sha256": sha256(mask_file.read_bytes()).hexdigest(),
                "issues": result_issues,
                "status": "rejected-no-sticker-created",
            })
            print(
                f"Rejected straight-cut sticker: {photo['id']} ({', '.join(result_issues)})",
                flush=True,
            )
            continue
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
                save_preserving_existing(output / name, payload)
                variants.append({
                    "file": name, "width": width, "height": height,
                    "bytes": len(payload), "sha256": sha256(payload).hexdigest(),
                })
        record = {
            "id": photo["id"],
            "source_id": photo["source_id"],
            "notebook_id": photo["notebook_id"],
            "source_photo_sha256": photo["source_sha256"],
            "source_crop_sha256": sha256(crop_file.read_bytes()).hexdigest(),
            "mask_sha256": sha256(mask_file.read_bytes()).hexdigest(),
            "mask_status": "model-candidate-unreviewed",
            "source_dimensions": list(image.size),
            "masked_bounds": list(bounds),
            "padding": padding,
            "white_outline": outline,
            "alt": photo["alt"],
            "source_limitation": photo["limitation"],
            "variants": variants,
        }
        records.append(record)
        preview = next(output / item["file"] for item in variants if item["file"].endswith(".png"))
        sheets[photo["notebook_id"]].append({
            "id": photo["id"], "source_id": photo["source_id"], "sticker_file": preview,
        })
        print(f"Prepared candidate sticker: {photo['id']}", flush=True)

    write_json(output / "manifest.json", {
        "schema_version": 1,
        "status": "private-candidate-stickers-require-mask-review-before-import",
        "policy": "Local model masks, transparent padding and white outline; source RGB is unchanged. Straight or source-edge-clipped contours are rejected fail-closed.",
        "photos": records,
    })
    write_json(output / "rejected-straight-cuts.json", {
        "policy": "No sticker is emitted when its candidate contour reaches the source edge or contains a long straight boundary.",
        "rejected": rejected,
    })
    for notebook_id, entries in sheets.items():
        sticker_sheet(entries, prepared / "review-sheets" / notebook_id)
    print(
        f"Prepared {len(records)} candidate stickers; rejected {len(rejected)} straight-cut candidates."
    )


def finalize_stickers(prepared, review_file):
    output = prepared / "stickers"
    manifest_path = output / "manifest.json"
    rejected_path = output / "rejected-straight-cuts.json"
    manifest = read_json(manifest_path)
    rejected = read_json(rejected_path)
    review = read_json(review_file)
    if review.get("status") != "complete":
        raise ValueError("Sticker contact-sheet review must be complete before finalization.")

    reasons = {}
    for sheet in review["sheets"]:
        if sheet["status"] != "reviewed":
            raise ValueError(f"Unreviewed sticker sheet: {sheet['sheet']}")
        for asset_id in sheet["manual_reject_ids"]:
            if asset_id in reasons:
                raise ValueError(f"Repeated manual sticker rejection: {asset_id}")
            reasons[asset_id] = sheet["reason"]

    kept, removed = [], []
    for photo in manifest["photos"]:
        if photo["id"] not in reasons:
            kept.append(photo)
            continue
        for variant in photo["variants"]:
            path = output / variant["file"]
            if path.is_file():
                path.unlink()
        removed.append({
            "id": photo["id"],
            "source_id": photo["source_id"],
            "notebook_id": photo["notebook_id"],
            "mask_sha256": photo["mask_sha256"],
            "issues": ["contact-sheet-visible-straight-edge-or-mask-remnant"],
            "reason": reasons[photo["id"]],
            "status": "rejected-after-contact-sheet-review-no-sticker-retained",
        })

    unknown = set(reasons) - {photo["id"] for photo in manifest["photos"]}
    if unknown:
        raise ValueError(f"Manual rejections were not present in the candidate manifest: {unknown}")

    for photo in kept:
        pngs = [variant for variant in photo["variants"] if variant["file"].endswith(".png")]
        if not pngs:
            raise ValueError(f"No PNG sticker variant remains for {photo['id']}")
        for variant in pngs:
            path = output / variant["file"]
            with Image.open(path) as opened:
                alpha = opened.getchannel("A")
                bounds = alpha.getbbox()
                if not bounds:
                    raise ValueError(f"Retained sticker has empty alpha: {photo['id']}")
                if (
                    bounds[0] <= 0 or bounds[1] <= 0
                    or bounds[2] >= opened.width or bounds[3] >= opened.height
                ):
                    raise ValueError(f"Retained sticker lacks transparent margin: {photo['id']}")

    manifest["status"] = "private-contact-sheet-reviewed-candidate-stickers-not-approved-for-publication"
    manifest["review_file"] = str(review_file)
    manifest["photos"] = kept
    rejected["rejected"].extend(removed)
    rejected["contact_sheet_rejected"] = len(removed)
    replace_json(manifest_path, manifest)
    replace_json(rejected_path, rejected)
    print(f"Finalized {len(kept)} retained stickers; removed {len(removed)} visual rejects.")


def validate_package(prepared, review_workspace):
    photo_manifest = read_json(prepared / "manifest.json")
    sticker_manifest = read_json(prepared / "stickers" / "manifest.json")
    rejected = read_json(prepared / "stickers" / "rejected-straight-cuts.json")
    ledger = read_json(prepared / "source-ledger.json")
    review = read_json(prepared / "sticker-review-decisions.json")
    budget = read_json(review_workspace / "session-budget.json")

    photo_ids = {photo["id"] for photo in photo_manifest["photos"]}
    sticker_ids = {photo["id"] for photo in sticker_manifest["photos"]}
    rejected_ids = {photo["id"] for photo in rejected["rejected"]}
    if len(photo_ids) != len(photo_manifest["photos"]):
        raise ValueError("Prepared photo IDs are not unique.")
    if sticker_ids & rejected_ids or sticker_ids | rejected_ids != photo_ids:
        raise ValueError("Every prepared photo must be retained or rejected exactly once.")
    if len(ledger["files"]) != 159:
        raise ValueError("Source ledger no longer accounts for all 159 archive paths.")
    if review["status"] != "complete" or budget["successful_image_views"] != 13:
        raise ValueError("Expected complete five-sheet sticker review and 13 total image views.")

    for photo in photo_manifest["photos"]:
        for variant in photo["variants"]:
            path = prepared / "photos" / variant["file"]
            payload = path.read_bytes()
            if sha256(payload).hexdigest() != variant["sha256"]:
                raise ValueError(f"Prepared photo hash mismatch: {path}")
    for photo in sticker_manifest["photos"]:
        for variant in photo["variants"]:
            path = prepared / "stickers" / variant["file"]
            payload = path.read_bytes()
            if sha256(payload).hexdigest() != variant["sha256"]:
                raise ValueError(f"Sticker hash mismatch: {path}")

    category_counts = dict(sorted(Counter(
        photo["notebook_id"] for photo in sticker_manifest["photos"]
    ).items()))
    completion = {
        "status": "complete-private-handoff-no-website-import",
        "source_paths_accounted": len(ledger["files"]),
        "prepared_new_full_photos": len(photo_manifest["photos"]),
        "retained_contact_sheet_reviewed_stickers": len(sticker_manifest["photos"]),
        "rejected_straight_or_low_quality_stickers": len(rejected["rejected"]),
        "retained_stickers_by_notebook": category_counts,
        "image_views": {
            "archive_contact_sheets": 8,
            "sticker_contact_sheets": 5,
            "total": budget["successful_image_views"],
            "stop_threshold": budget["stop_at_views"],
        },
        "website_data_modified_by_this_workflow": False,
        "next_step": "A later website-import session may consume the prepared photo manifest and only the retained sticker manifest. Rejected masks require separate refinement and review.",
    }
    replace_json(prepared / "completion.json", completion)
    print(json.dumps(completion, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    photos = commands.add_parser("photos")
    photos.add_argument("--review", type=Path, required=True)
    photos.add_argument("--output", type=Path, required=True)
    stickers = commands.add_parser("stickers")
    stickers.add_argument("--prepared", type=Path, required=True)
    stickers.add_argument("--masks", type=Path, required=True)
    final = commands.add_parser("finalize")
    final.add_argument("--prepared", type=Path, required=True)
    final.add_argument("--review", type=Path, required=True)
    validation = commands.add_parser("validate")
    validation.add_argument("--prepared", type=Path, required=True)
    validation.add_argument("--review-workspace", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "photos":
        prepare_photos(args.review.resolve(), args.output.resolve())
    elif args.command == "stickers":
        prepare_stickers(args.prepared.resolve(), args.masks.resolve())
    elif args.command == "finalize":
        finalize_stickers(args.prepared.resolve(), args.review.resolve())
    else:
        validate_package(args.prepared.resolve(), args.review_workspace.resolve())


if __name__ == "__main__":
    main()
