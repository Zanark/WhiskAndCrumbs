"""Promote approved rounded archive stickers into the website catalogues."""

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / ".local" / "archive-import-20261009" / "prepared-v1"
ROUNDED = ROOT / ".local" / "archive-import-20261009" / "rounded-v4"
PHOTO_DESTINATION = ROOT / "assets" / "images" / "cakes"
STICKER_DESTINATION = ROOT / "assets" / "images" / "cake-stickers"
MASK_DESTINATION = STICKER_DESTINATION / "masks"

CATEGORY_LABELS = {
    "birthday-cakes": ("Birthday cake", "Birthday Cakes"),
    "tea-cakes": ("Tea cake", "Tea cakes"),
    "cream-cakes": ("Cream cake", "Cream cakes"),
    "decorated-cakes": ("Decorated cake", "Decorated cakes"),
    "doll-cakes": ("Doll cake", "Doll cakes"),
    "chocolates": ("Chocolate selection", "Chocolates"),
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def copy_verified(source, destination, expected_sha256):
    payload = source.read_bytes()
    if sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f"Prepared asset hash changed: {source}")
    if destination.exists():
        if destination.read_bytes() != payload:
            raise ValueError(f"Refusing to overwrite a different asset: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def manual_rejections(decisions):
    return {
        cake_id
        for sheet in decisions["sheets"]
        for cake_id in sheet.get("manual_reject_ids", [])
    }


def main():
    decisions = read_json(ROUNDED / "rounded-review-decisions.json")
    rounded_manifest = read_json(ROUNDED / "manifest.json")
    prepared_manifest = read_json(PREPARED / "manifest.json")
    originally_rejected = read_json(
        PREPARED / "stickers" / "rejected-straight-cuts.json"
    )["rejected"]

    if decisions["pending_sheets"] or any(
        sheet["status"] != "reviewed" for sheet in decisions["sheets"]
    ):
        raise ValueError("Every rounded sticker sheet must be reviewed before import.")

    rounded_by_id = {photo["id"]: photo for photo in rounded_manifest["photos"]}
    prepared_by_id = {photo["id"]: photo for photo in prepared_manifest["photos"]}
    rounded_ids = set(rounded_by_id)
    original_rejected_ids = {photo["id"] for photo in originally_rejected}
    if rounded_ids != original_rejected_ids or len(rounded_ids) != 90:
        raise ValueError("Rounded candidates do not match the 90 original rejections.")

    rejected_ids = manual_rejections(decisions)
    approved_ids = rounded_ids - rejected_ids
    if len(approved_ids) != 88 or len(rejected_ids) != 2:
        raise ValueError("Expected 88 approved and 2 rejected rounded candidates.")
    if rejected_ids - rounded_ids:
        raise ValueError("A review rejection does not match a rounded candidate.")
    if approved_ids - prepared_by_id.keys():
        raise ValueError("Every approved sticker must have a prepared full photograph.")

    cakes_path = ROOT / "content" / "cakes.json"
    notebooks_path = ROOT / "content" / "notebooks.json"
    photo_manifest_path = PHOTO_DESTINATION / "manifest.json"
    sticker_manifest_path = STICKER_DESTINATION / "manifest.json"
    cakes = read_json(cakes_path)
    notebooks = read_json(notebooks_path)
    photo_manifest = read_json(photo_manifest_path)
    sticker_manifest = read_json(sticker_manifest_path)

    existing_cakes = {cake["id"]: cake for cake in cakes}
    existing_photos = {photo["id"]: photo for photo in photo_manifest["photos"]}
    existing_stickers = {photo["id"]: photo for photo in sticker_manifest["photos"]}
    notebook_by_id = {book["id"]: book for book in notebooks}
    base_counts = {category: 0 for category in CATEGORY_LABELS}
    for cake in cakes:
        if cake["id"] in approved_ids or not cake["id"].startswith("archive-"):
            continue
        for category_id, (singular, _) in CATEGORY_LABELS.items():
            if re.fullmatch(rf"{re.escape(singular)} \d+", cake["name"]):
                base_counts[category_id] += 1
                break

    imported_by_category = {category: [] for category in CATEGORY_LABELS}
    approved = sorted(
        (rounded_by_id[cake_id] for cake_id in approved_ids),
        key=lambda item: int(item["source_id"][1:]),
    )
    for sticker_record in approved:
        cake_id = sticker_record["id"]
        photo_record = prepared_by_id[cake_id]
        category_id = photo_record["notebook_id"]
        if category_id not in CATEGORY_LABELS:
            raise ValueError(f"Unknown notebook category: {category_id}")
        if sticker_record["notebook_id"] != category_id:
            raise ValueError(f"Photo/sticker category mismatch: {cake_id}")

        imported_by_category[category_id].append(cake_id)
        position = base_counts[category_id] + len(imported_by_category[category_id])
        singular, category_label = CATEGORY_LABELS[category_id]
        cake_record = {
            "id": cake_id,
            "name": f"{singular} {position}",
            "category": category_label,
        }
        reviewed_sticker = {
            **sticker_record,
            "mask_status": "rounded-contact-sheet-reviewed",
        }

        if cake_id in existing_cakes:
            if existing_cakes[cake_id] != cake_record:
                raise ValueError(f"Existing cake record differs: {cake_id}")
        else:
            cakes.append(cake_record)
            existing_cakes[cake_id] = cake_record

        if cake_id in existing_photos:
            if existing_photos[cake_id] != photo_record:
                raise ValueError(f"Existing photo record differs: {cake_id}")
        else:
            photo_manifest["photos"].append(photo_record)
            existing_photos[cake_id] = photo_record

        if cake_id in existing_stickers:
            if existing_stickers[cake_id] != reviewed_sticker:
                raise ValueError(f"Existing sticker record differs: {cake_id}")
        else:
            sticker_manifest["photos"].append(reviewed_sticker)
            existing_stickers[cake_id] = reviewed_sticker

        for variant in photo_record["variants"]:
            copy_verified(
                PREPARED / "photos" / variant["file"],
                PHOTO_DESTINATION / variant["file"],
                variant["sha256"],
            )
        for variant in sticker_record["variants"]:
            copy_verified(
                ROUNDED / "stickers" / variant["file"],
                STICKER_DESTINATION / variant["file"],
                variant["sha256"],
            )
        copy_verified(
            ROUNDED / "masks" / f"{cake_id}.png",
            MASK_DESTINATION / f"{cake_id}.png",
            sticker_record["mask_sha256"],
        )

    for category_id, imported_ids in imported_by_category.items():
        book = notebook_by_id[category_id]
        for cake_id in imported_ids:
            if cake_id not in book["cakeIds"]:
                book["cakeIds"].append(cake_id)

    write_json(cakes_path, cakes)
    write_json(notebooks_path, notebooks)
    write_json(photo_manifest_path, photo_manifest)
    write_json(sticker_manifest_path, sticker_manifest)
    write_json(
        ROUNDED / "website-import.json",
        {
            "status": "website-source-import-complete-validation-pending",
            "imported_approved_rounded_stickers": len(approved_ids),
            "excluded_manual_rejections": sorted(rejected_ids),
            "total_website_cake_records": len(cakes),
            "publication_deferred": True,
        },
    )
    print(
        f"Imported {len(approved_ids)} approved rounded stickers; "
        f"catalogue now contains {len(cakes)} records."
    )


if __name__ == "__main__":
    main()
