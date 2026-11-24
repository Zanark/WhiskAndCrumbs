"""Promote reviewed archive photos and stickers into the website source catalogues."""

from hashlib import sha256
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / ".local" / "archive-import-20261009" / "prepared-v1"
PHOTO_SOURCE = PREPARED / "photos"
MASK_SOURCE = PREPARED / "candidate-masks"
STICKER_SOURCE = PREPARED / "stickers"
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


def main():
    prepared_photos = read_json(PREPARED / "manifest.json")
    prepared_stickers = read_json(STICKER_SOURCE / "manifest.json")
    rejected = read_json(STICKER_SOURCE / "rejected-straight-cuts.json")
    decisions = read_json(PREPARED / "sticker-review-decisions.json")

    if decisions["status"] != "complete" or any(
        sheet["status"] != "reviewed" for sheet in decisions["sheets"]
    ):
        raise ValueError("Every retained sticker sheet must be reviewed before import.")

    stickers = prepared_stickers["photos"]
    retained_ids = {photo["id"] for photo in stickers}
    rejected_ids = {
        item["id"] if isinstance(item, dict) else item
        for item in rejected.get("photos", rejected.get("rejected", []))
    }
    if retained_ids & rejected_ids:
        raise ValueError("A rejected sticker cannot be imported.")
    if len(stickers) != 45:
        raise ValueError(f"Expected 45 retained stickers, found {len(stickers)}.")

    prepared_by_id = {photo["id"]: photo for photo in prepared_photos["photos"]}
    if retained_ids - prepared_by_id.keys():
        raise ValueError("Every retained sticker must have a prepared full photograph.")

    cakes_path = ROOT / "content" / "cakes.json"
    notebooks_path = ROOT / "content" / "notebooks.json"
    photo_manifest_path = PHOTO_DESTINATION / "manifest.json"
    sticker_manifest_path = STICKER_DESTINATION / "manifest.json"
    cakes = read_json(cakes_path)
    notebooks = read_json(notebooks_path)
    photo_manifest = read_json(photo_manifest_path)
    sticker_manifest = read_json(sticker_manifest_path)

    existing_ids = {cake["id"] for cake in cakes}
    existing_photo_ids = {photo["id"] for photo in photo_manifest["photos"]}
    existing_sticker_ids = {photo["id"] for photo in sticker_manifest["photos"]}
    notebook_by_id = {book["id"]: book for book in notebooks}

    imported_by_category = {category: [] for category in CATEGORY_LABELS}
    ordered_stickers = sorted(stickers, key=lambda item: int(item["source_id"][1:]))
    for sticker_record in ordered_stickers:
        cake_id = sticker_record["id"]
        photo_record = prepared_by_id[cake_id]
        category_id = photo_record["notebook_id"]
        if category_id not in CATEGORY_LABELS:
            raise ValueError(f"Unknown notebook category: {category_id}")
        if sticker_record["notebook_id"] != category_id:
            raise ValueError(f"Photo/sticker category mismatch: {cake_id}")

        imported_by_category[category_id].append(cake_id)
        position = len(imported_by_category[category_id])
        singular, category_label = CATEGORY_LABELS[category_id]
        cake_record = {
            "id": cake_id,
            "name": f"{singular} {position}",
            "category": category_label,
        }
        reviewed_sticker = {
            **sticker_record,
            "mask_status": "contact-sheet-reviewed",
        }

        if cake_id in existing_ids:
            if next(cake for cake in cakes if cake["id"] == cake_id) != cake_record:
                raise ValueError(f"Existing cake record differs: {cake_id}")
        else:
            cakes.append(cake_record)
            existing_ids.add(cake_id)

        if cake_id in existing_photo_ids:
            if next(photo for photo in photo_manifest["photos"] if photo["id"] == cake_id) != photo_record:
                raise ValueError(f"Existing photo record differs: {cake_id}")
        else:
            photo_manifest["photos"].append(photo_record)
            existing_photo_ids.add(cake_id)

        if cake_id in existing_sticker_ids:
            existing = next(photo for photo in sticker_manifest["photos"] if photo["id"] == cake_id)
            if existing != reviewed_sticker:
                raise ValueError(f"Existing sticker record differs: {cake_id}")
        else:
            sticker_manifest["photos"].append(reviewed_sticker)
            existing_sticker_ids.add(cake_id)

        for variant in photo_record["variants"]:
            copy_verified(
                PHOTO_SOURCE / variant["file"],
                PHOTO_DESTINATION / variant["file"],
                variant["sha256"],
            )
        for variant in sticker_record["variants"]:
            copy_verified(
                STICKER_SOURCE / variant["file"],
                STICKER_DESTINATION / variant["file"],
                variant["sha256"],
            )
        copy_verified(
            MASK_SOURCE / f"{cake_id}.png",
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
    print(f"Imported {len(retained_ids)} reviewed archive photos and stickers.")


if __name__ == "__main__":
    main()
