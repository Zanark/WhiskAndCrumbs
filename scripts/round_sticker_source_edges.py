"""Round existing photo-frame cuts inward without reshaping interior objects."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil

import numpy as np
from PIL import Image

from prepare_cake_stickers import sticker
from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
REVISION = "rounded-source-edges-20261010"


def contiguous_runs(values):
    differences = np.diff(np.r_[False, values, False].astype(np.int8))
    return [(int(start), int(end)) for start, end in
            zip(np.flatnonzero(differences == 1), np.flatnonzero(differences == -1))]


def source_edge_runs(mask):
    solid = np.asarray(mask.convert("L")) >= 128
    height, width = solid.shape
    minimum = max(36, round(min(width, height) * .05))
    return {
        edge: [(start, end) for start, end in contiguous_runs(values) if end - start >= minimum]
        for edge, values in (("left", solid[:, 0]), ("right", solid[:, -1]),
                             ("top", solid[0]), ("bottom", solid[-1]))
    }


def edge_curvature_metrics(mask, edges):
    solid = np.asarray(mask) >= 128
    metrics = []
    for edge, detail in edges.items():
        oriented = solid if edge == "top" else solid[::-1] if edge == "bottom" else (
            solid.T if edge == "left" else solid[:, ::-1].T)
        first, present = oriented.argmax(axis=0), oriented.any(axis=0)
        for start, end in detail["source_runs"]:
            longest = current = 0
            previous = None
            for coordinate in range(start, end):
                value = int(first[coordinate]) if present[coordinate] else None
                current = 0 if value is None else current + 1 if value == previous else 1
                previous = value
                longest = max(longest, current)
            metrics.append({"edge": edge, "old_flat_run": end - start, "new_max_flat_run": longest})
    return metrics


def round_source_edges(mask):
    if mask.mode != "L":
        raise ValueError("Source-edge rounding requires an existing greyscale alpha mask.")
    original = np.asarray(mask).copy()
    if not (original >= 128).any():
        raise ValueError("Cannot round an empty sticker.")
    height, width = original.shape
    runs = source_edge_runs(mask)
    if not any(runs.values()):
        return mask.copy(), {"modified": False, "edges": {}, "retained_alpha_fraction": 1}
    inset = max(8, round(min(width, height) * .012))
    gate = np.ones(original.shape, dtype=np.float32)
    protected = np.ones(original.shape, dtype=bool)
    details = {}
    for edge, segments in runs.items():
        if not segments:
            continue
        vertical = edge in {"left", "right"}
        coordinate = np.arange(height if vertical else width, dtype=np.float32)
        profile = np.full(coordinate.shape, inset, dtype=np.float32)
        for start, end in segments:
            length = end - start
            depth = max(12, min(48, length * .10))
            shoulder = min(length / 2, depth * 2)
            middle = (start + end - 1) / 2
            half = max(1, (length - 1) / 2)
            arch = depth * np.square((coordinate - middle) / half)
            left = np.clip((coordinate - start + shoulder) / shoulder, 0, 1)
            right = np.clip((end - 1 + shoulder - coordinate) / shoulder, 0, 1)
            outside = np.where(coordinate < start, left, right)
            extra = np.where((coordinate >= start) & (coordinate < end), arch,
                             depth * outside * outside * (3 - 2 * outside))
            profile = np.maximum(profile, inset + extra)
        distance = np.arange(width if vertical else height, dtype=np.float32)
        if edge in {"right", "bottom"}:
            distance = distance[::-1]
        distance = distance[None, :] if vertical else distance[:, None]
        limit = profile[:, None] if vertical else profile[None, :]
        gate = np.minimum(gate, np.clip((distance - limit) / 1.2 + .5, 0, 1))
        protected &= distance > float(profile.max()) + 2
        details[edge] = {"source_runs": segments, "maximum_inward_pixels": float(profile.max()),
                         "minimum_inset_pixels": inset}
    rounded = np.minimum(original, np.rint(original * gate).astype(np.uint8))
    if not np.array_equal(rounded[protected], original[protected]):
        raise ValueError("Rounding changed protected interior alpha.")
    retained = float(rounded.astype(np.float64).sum() / original.astype(np.float64).sum())
    if retained < .90:
        raise ValueError(f"Source-edge rounding would remove too much foreground: {retained:.4f}")
    if np.any(rounded > original):
        raise ValueError("Rounding must never reveal new foreground or background.")
    result = Image.fromarray(rounded)
    if any(source_edge_runs(result).values()):
        raise ValueError("A long source-frame cut remains after rounding.")
    curves = edge_curvature_metrics(result, details)
    if any(item["new_max_flat_run"] > max(24, item["old_flat_run"] * .3) for item in curves):
        raise ValueError(f"Rounding left a replacement straight cut: {curves}")
    return result, {"modified": True, "edges": details, "retained_alpha_fraction": retained,
                    "newly_visible_pixels": 0, "protected_interior_alpha_unchanged": True,
                    "protected_pixel_count": int(protected.sum()), "curvature": curves}


def prepare(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        raise ValueError("Prepare rounded candidates privately before explicit installation.")
    if output.exists():
        raise FileExistsError(f"Preserve earlier rounding outputs: {output}")
    stickers = json.loads((ROOT / "assets/images/cake-stickers/manifest.json").read_text())
    photos = {record["id"]: record for record in json.loads((ROOT / "assets/images/cakes/manifest.json").read_text())["photos"]}
    records, unchanged = [], []
    for record in stickers["photos"]:
        identity = record["id"]
        mask_path = ROOT / "assets/images/cake-stickers/masks" / f"{identity}.png"
        payload = mask_path.read_bytes()
        if sha256(payload).hexdigest() != record["mask_sha256"]:
            raise ValueError(f"Existing reviewed mask changed: {identity}")
        mask = Image.open(mask_path).convert("L")
        rounded, proof = round_source_edges(mask)
        if not proof["modified"]:
            unchanged.append(identity)
            continue
        photo_record = photos[identity]
        folder = ROOT / photo_record.get("private_directory", ".local/photos/prototype-20261004") / "crops"
        crop_path = folder / f"{identity}.png"
        crop_payload = crop_path.read_bytes()
        if sha256(crop_payload).hexdigest() != record["source_crop_sha256"]:
            raise ValueError(f"Original source crop changed: {identity}")
        image = Image.open(crop_path).convert("RGB")
        prepared, bounds, padding, outline = sticker(image, rounded)
        mask_payload = encoded(rounded, "PNG", optimize=True)
        save_preserving_existing(output / "masks" / f"{identity}.png", mask_payload)
        variants = []
        for width in sorted({min(480, prepared.width), min(1000, prepared.width)}):
            resized = prepared.resize((width, round(prepared.height * width / prepared.width)), Image.Resampling.LANCZOS)
            for extension, format_name, options in (
                ("webp", "WEBP", {"quality": 94, "method": 6}), ("png", "PNG", {"optimize": True}),
            ):
                name = f"{identity}-sticker-{width}.{extension}"
                data = encoded(resized, format_name, **options)
                save_preserving_existing(output / "stickers" / name, data)
                variants.append({"file": name, "width": resized.width, "height": resized.height,
                                 "bytes": len(data), "sha256": sha256(data).hexdigest()})
        updated = {
            **record, "previous_mask_sha256": record["mask_sha256"],
            "mask_sha256": sha256(mask_payload).hexdigest(), "revision": REVISION,
            "masked_bounds": list(bounds), "padding": padding, "white_outline": outline,
            "source_edge_rounding": proof, "variants": variants,
            "source_limitation": record["source_limitation"] +
                " Original photo-frame cuts are now rounded inward; no missing detail is reconstructed.",
        }
        records.append(updated)
        print(json.dumps({"id": identity, "retained_alpha_fraction": proof["retained_alpha_fraction"],
                          "edges": list(proof["edges"])}), flush=True)
    result = {
        "status": "prepared-alpha-only-source-edge-rounding",
        "revision": REVISION, "audited_stickers": len(stickers["photos"]), "photos": records,
        "unchanged_ids": unchanged, "covers_unchanged": [cover["id"] for cover in stickers.get("covers", [])],
        "original_photos_changed": False, "source_rgb_changed": False,
        "image_tool_views": 0, "owner_visual_acceptance": "Not established for this revision.",
    }
    save_preserving_existing(output / "manifest.json", (json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({"rounded": len(records), "unchanged": len(unchanged), "output": str(output)}))


def install(prepared, backup):
    prepared, backup = prepared.resolve(), backup.resolve()
    if not all(path.is_relative_to(ROOT / ".local") for path in (prepared, backup)):
        raise ValueError("Prepared revisions and backups must remain private.")
    if backup.exists():
        raise FileExistsError("Use a fresh backup directory for an explicit sticker installation.")
    revision = json.loads((prepared / "manifest.json").read_text())
    manifest_path = ROOT / "assets/images/cake-stickers/manifest.json"
    manifest_payload = manifest_path.read_bytes()
    manifest = json.loads(manifest_payload)
    current = {record["id"]: record for record in manifest["photos"]}
    replacements = {record["id"]: record for record in revision["photos"]}
    if (revision["revision"] != REVISION or len(replacements) != len(revision["photos"])
            or set(current) != set(replacements) | set(revision["unchanged_ids"])
            or set(replacements) & set(revision["unchanged_ids"])
            or len(current) != revision["audited_stickers"]):
        raise ValueError("The active catalogue changed after the rounding preparation.")
    copies = []
    for identity, updated in replacements.items():
        previous = current[identity]
        if (updated["previous_mask_sha256"] != previous["mask_sha256"]
                or updated["source_crop_sha256"] != previous["source_crop_sha256"]
                or {v["file"] for v in updated["variants"]} != {v["file"] for v in previous["variants"]}):
            raise ValueError(f"Revision no longer matches the reviewed sticker: {identity}")
        items = [(Path("masks") / f"{identity}.png", updated["mask_sha256"], previous["mask_sha256"])]
        old_variants = {item["file"]: item for item in previous["variants"]}
        for variant in updated["variants"]:
            if not re.fullmatch(rf"{re.escape(identity)}-sticker-\d+\.(png|webp)", variant["file"]):
                raise ValueError("Unsafe rounded sticker path.")
            items.append((Path(variant["file"]), variant["sha256"], old_variants[variant["file"]]["sha256"]))
        for relative, new_hash, old_hash in items:
            source = prepared / ("masks" if relative.parent.name == "masks" else "stickers") / relative.name
            target = ROOT / "assets/images/cake-stickers" / relative
            if sha256(source.read_bytes()).hexdigest() != new_hash or sha256(target.read_bytes()).hexdigest() != old_hash:
                raise ValueError(f"Prepared or original sticker changed before installation: {relative}")
            copies.append((source, target, relative, new_hash))
    save_preserving_existing(backup / "manifest.json", manifest_payload)
    for source, target, relative, _ in copies:
        save_preserving_existing(backup / relative, target.read_bytes())
    for source, target, _, new_hash in copies:
        shutil.copyfile(source, target)
        if sha256(target.read_bytes()).hexdigest() != new_hash:
            raise ValueError(f"Installed sticker differs from its prepared bytes: {target}")
    manifest["photos"] = [replacements.get(record["id"], record) for record in manifest["photos"]]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    receipt = {
        "status": "installed-in-authoring-sources-not-published", "revision": REVISION,
        "updated_ids": sorted(replacements), "unchanged_ids": revision["unchanged_ids"],
        "cover_records_unchanged": True, "source_files_replaced": len(copies),
        "backup": str(backup.relative_to(ROOT)), "public_build_performed": False,
        "source_manifest_before": sha256(manifest_payload).hexdigest(),
        "source_manifest_after": sha256(manifest_path.read_bytes()).hexdigest(),
    }
    save_preserving_existing(prepared / "installation.json", (json.dumps(receipt, indent=2) + "\n").encode())
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--install", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.install:
        if not args.backup:
            parser.error("--install requires a fresh --backup directory")
        install(args.install, args.backup)
    else:
        prepare(args.output)
