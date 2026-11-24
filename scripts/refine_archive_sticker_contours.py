"""Create curved, irregular sticker contours for previously rejected archive masks."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from prepare_archive_notebook_assets import (
    encoded,
    read_json,
    save_preserving_existing,
    sticker,
    sticker_sheet,
    straight_cut_issues,
    write_json,
)


ROOT = Path(__file__).resolve().parents[1]


def organic_contour(mask, seed):
    original = np.asarray(mask.convert("L"), dtype=np.uint8) >= 128
    if not original.any():
        raise ValueError("Cannot refine an empty mask.")
    height, width = original.shape
    minimum = min(width, height)
    margin = max(10, round(minimum * 0.014))
    y, x = np.indices((height, width), dtype=np.float32)
    phase = (seed % 997) / 997 * math.tau

    edge_wave_y = (
        np.sin(y * math.tau / max(37, minimum * 0.071) + phase)
        + 0.55 * np.sin(y * math.tau / max(19, minimum * 0.039) + phase * 1.7)
    )
    edge_wave_x = (
        np.sin(x * math.tau / max(41, minimum * 0.079) + phase * 0.8)
        + 0.5 * np.sin(x * math.tau / max(23, minimum * 0.043) + phase * 1.3)
    )
    edge_amplitude = max(5, round(minimum * 0.009))
    frame = (
        (x >= margin + edge_amplitude * edge_wave_y)
        & (x < width - margin - edge_amplitude * edge_wave_y)
        & (y >= margin + edge_amplitude * edge_wave_x)
        & (y < height - margin - edge_amplitude * edge_wave_x)
    )
    clipped = original & frame
    retained = clipped.sum() / original.sum()
    if retained < 0.62:
        raise ValueError(f"Organic edge clip retained too little foreground: {retained:.3f}")

    base = Image.fromarray((clipped * 255).astype(np.uint8), "L")
    for attempt, radius in enumerate((3.0, 4.5, 6.0, 8.0, 10.0), 1):
        blurred = np.asarray(base.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32)
        period_x = max(29, minimum * (0.057 + attempt * 0.006))
        period_y = max(31, minimum * (0.061 + attempt * 0.007))
        field = (
            np.sin(x * math.tau / period_x + phase)
            + np.sin(y * math.tau / period_y + phase * 1.4)
            + 0.65 * np.sin((x + y) * math.tau / max(47, minimum * 0.093) + phase * 0.6)
            + 0.45 * np.sin((x - y) * math.tau / max(33, minimum * 0.067) + phase * 1.9)
        ) / 3.1
        threshold = 128 + field * (34 + attempt * 8)
        rounded = (blurred >= threshold).astype(np.uint8) * 255
        candidate = Image.fromarray(rounded, "L").filter(ImageFilter.GaussianBlur(0.7))
        if not straight_cut_issues(candidate):
            final_retained = (rounded >= 128).sum() / original.sum()
            if final_retained < 0.58:
                raise ValueError(
                    f"Rounded contour retained too little foreground: {final_retained:.3f}"
                )
            return candidate, final_retained

    for attempt, displacement in enumerate(
        (max(5, round(minimum * 0.008)), max(8, round(minimum * 0.012)),
         max(11, round(minimum * 0.017))),
        1,
    ):
        eroded = np.asarray(
            base.filter(ImageFilter.MinFilter(displacement * 2 + 1)),
            dtype=np.uint8,
        ) >= 128
        dx = displacement * (
            0.72 * np.sin(y * math.tau / max(43, minimum * 0.067) + phase)
            + 0.28 * np.sin(y * math.tau / max(23, minimum * 0.037) + phase * 1.8)
        )
        dy = displacement * (
            0.7 * np.sin(x * math.tau / max(47, minimum * 0.073) + phase * 1.2)
            + 0.3 * np.sin(x * math.tau / max(29, minimum * 0.041) + phase * 0.7)
        )
        source_x = np.clip(np.rint(x + dx).astype(np.int32), 0, width - 1)
        source_y = np.clip(np.rint(y + dy).astype(np.int32), 0, height - 1)
        warped = eroded[source_y, source_x] & frame
        rounded = warped.astype(np.uint8) * 255
        candidate = Image.fromarray(rounded, "L").filter(ImageFilter.GaussianBlur(0.7))
        if not straight_cut_issues(candidate):
            final_retained = warped.sum() / original.sum()
            if final_retained < 0.58:
                continue
            return candidate, final_retained
    raise ValueError("Unable to remove every long straight contour deterministically.")


def prepare(prepared, output, reuse=None):
    if output.exists():
        raise ValueError(f"Choose a new output directory: {output}")
    photos = {photo["id"]: photo for photo in read_json(prepared / "manifest.json")["photos"]}
    rejected = read_json(prepared / "stickers" / "rejected-straight-cuts.json")["rejected"]
    entries = []
    records = []
    failures = []
    reused_by_id = {}
    if reuse:
        reused_by_id = {
            photo["id"]: photo
            for photo in read_json(reuse / "manifest.json")["photos"]
        }

    for rejected_record in rejected:
        asset_id = rejected_record["id"]
        photo = photos[asset_id]
        crop_file = prepared / "crops" / f"{asset_id}.png"
        source_mask = prepared / "candidate-masks" / f"{asset_id}.png"
        if asset_id in reused_by_id:
            record = reused_by_id[asset_id]
            mask_payload = (reuse / "masks" / f"{asset_id}.png").read_bytes()
            if sha256(mask_payload).hexdigest() != record["mask_sha256"]:
                raise ValueError(f"Reusable mask hash changed: {asset_id}")
            save_preserving_existing(output / "masks" / f"{asset_id}.png", mask_payload)
            for variant in record["variants"]:
                payload = (reuse / "stickers" / variant["file"]).read_bytes()
                if sha256(payload).hexdigest() != variant["sha256"]:
                    raise ValueError(f"Reusable sticker hash changed: {variant['file']}")
                save_preserving_existing(output / "stickers" / variant["file"], payload)
            records.append(record)
            preview = next(
                output / "stickers" / variant["file"]
                for variant in record["variants"]
                if variant["file"].endswith(".png")
            )
            entries.append({
                "id": asset_id,
                "source_id": photo["source_id"],
                "sticker_file": preview,
            })
            print(f"Reused rounded contour: {asset_id}", flush=True)
            continue
        with Image.open(crop_file) as opened:
            image = opened.convert("RGB")
        with Image.open(source_mask) as opened:
            mask = opened.convert("L")
        try:
            base_seed = int(sha256(asset_id.encode("ascii")).hexdigest()[:8], 16)
            result = None
            fallback = None
            rendered_warnings = []
            for contour_attempt in range(8):
                refined, retained_fraction = organic_contour(
                    mask, base_seed + contour_attempt * 7919
                )
                if straight_cut_issues(refined):
                    continue
                candidate_result, bounds, padding, outline = sticker(image, refined)
                result_issues = straight_cut_issues(candidate_result.getchannel("A"))
                fallback = (
                    candidate_result, refined, retained_fraction,
                    bounds, padding, outline, result_issues,
                )
                if result_issues:
                    continue
                result = candidate_result
                break
            if result is None:
                if fallback is None:
                    raise ValueError("No rounded source mask could be produced.")
                (
                    result, refined, retained_fraction,
                    bounds, padding, outline, rendered_warnings,
                ) = fallback
            mask_payload = encoded(refined, "PNG", optimize=True)
            mask_file = output / "masks" / f"{asset_id}.png"
            save_preserving_existing(mask_file, mask_payload)

            variants = []
            for width_value in sorted({min(480, result.width), min(1000, result.width)}):
                height_value = round(result.height * width_value / result.width)
                resized = result.resize((width_value, height_value), Image.Resampling.LANCZOS)
                for extension, format_name, options in (
                    ("webp", "WEBP", {"quality": 94, "method": 6}),
                    ("png", "PNG", {"optimize": True}),
                ):
                    name = f"{asset_id}-sticker-{width_value}.{extension}"
                    payload = encoded(resized, format_name, **options)
                    save_preserving_existing(output / "stickers" / name, payload)
                    variants.append({
                        "file": name,
                        "width": width_value,
                        "height": height_value,
                        "bytes": len(payload),
                        "sha256": sha256(payload).hexdigest(),
                    })
            record = {
                "id": asset_id,
                "source_id": photo["source_id"],
                "notebook_id": photo["notebook_id"],
                "source_photo_sha256": photo["source_sha256"],
                "source_crop_sha256": sha256(crop_file.read_bytes()).hexdigest(),
                "original_mask_sha256": sha256(source_mask.read_bytes()).hexdigest(),
                "mask_sha256": sha256(mask_payload).hexdigest(),
                "mask_status": "organic-contour-candidate-requires-contact-sheet-review",
                "original_issues": rejected_record["issues"],
                "rendered_contour_warnings": rendered_warnings,
                "retained_foreground_fraction": round(retained_fraction, 6),
                "source_dimensions": list(image.size),
                "masked_bounds": list(bounds),
                "padding": padding,
                "white_outline": outline,
                "alt": photo["alt"],
                "source_limitation": (
                    photo["limitation"]
                    + " A curved alpha edge replaces source-edge or straight-board truncation."
                ),
                "variants": variants,
            }
            records.append(record)
            preview = next(
                output / "stickers" / variant["file"]
                for variant in variants
                if variant["file"].endswith(".png")
            )
            entries.append({
                "id": asset_id,
                "source_id": photo["source_id"],
                "sticker_file": preview,
            })
            print(f"Rounded rejected contour: {asset_id}", flush=True)
        except ValueError as error:
            failures.append({"id": asset_id, "error": str(error)})

    write_json(output / "manifest.json", {
        "schema_version": 1,
        "status": "private-rounded-candidates-require-contact-sheet-review",
        "policy": (
            "Candidate alpha is inset and deterministically curved without changing source RGB. "
            "No candidate may reach a source edge or retain a long straight exterior boundary."
        ),
        "photos": records,
        "failures": failures,
    })
    sticker_sheet(entries, output / "review-sheets" / "rounded-rejected", page_size=18)
    print(f"Prepared {len(records)} rounded candidates; {len(failures)} failures.")
    if failures:
        raise ValueError(f"Some rejected masks could not be rounded: {failures}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse", type=Path)
    args = parser.parse_args()
    prepare(
        args.prepared.resolve(),
        args.output.resolve(),
        args.reuse.resolve() if args.reuse else None,
    )


if __name__ == "__main__":
    main()
