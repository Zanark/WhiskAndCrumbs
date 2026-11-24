"""Checked cream-material layers for static launch artwork, never website runtime."""

from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
CREAM_DESIGN_REVISION = "cream-20261009-sculpted-editorial"
FROSTED_DESIGN_REVISION = "frosted-gaussian-cream-20261009"
PORTRAIT_GROUNDS = {
    "01-welcome": {"name": "Buttercream", "hex": "#f4e1b6"},
    "02-bakery-entrance": {"name": "Blush", "hex": "#f3cada"},
    "03-our-story": {"name": "Soft green", "hex": "#d1dfce"},
    "04-cake-notebooks": {"name": "Peach", "hex": "#efc5b2"},
    "05-open-notebook": {"name": "Oat", "hex": "#e6d6c5"},
    "06-simple-ordering": {"name": "Vanilla", "hex": "#f4eddd"},
}


def portrait_palette(stem, tint_strength=1):
    if (stem not in PORTRAIT_GROUNDS or isinstance(tint_strength, bool)
            or not isinstance(tint_strength, (int, float)) or not math.isfinite(tint_strength)
            or not 0 < tint_strength <= 1):
        raise ValueError("Portrait tint strength must be finite, above zero and at most one.")
    palette = PORTRAIT_GROUNDS[stem].copy()
    if tint_strength != 1:
        colour = ImageColor.getrgb(palette["hex"])
        lighter = [round(255 - (255 - channel) * tint_strength) for channel in colour]
        palette.update(original_hex=palette["hex"], hex="#" + "".join(f"{channel:02x}" for channel in lighter),
                       tint_strength=tint_strength, white_blend_fraction=1 - tint_strength)
    return palette


def portrait_ground(base, stem, tint_strength=1):
    """Tint only the editorial ground before unchanged material and glass are added."""
    if base.mode != "RGBA" or stem not in PORTRAIT_GROUNDS:
        raise ValueError("Portrait ground requires an RGBA base and a known campaign scene.")
    portrait_palette(stem, tint_strength)
    pixels = np.asarray(base).copy()
    offset = np.array(ImageColor.getrgb(PORTRAIT_GROUNDS[stem]["hex"]), dtype=np.int16) - (245, 235, 221)
    pixels[..., :3] = np.clip(pixels[..., :3].astype(np.int16) + offset, 0, 255).astype(np.uint8)
    if tint_strength != 1:
        pixels[..., :3] = np.rint(255 - (255 - pixels[..., :3].astype(np.float64)) * tint_strength).astype(np.uint8)
    return Image.fromarray(pixels)


def validate_portrait_grounds(entries):
    found = {}
    strengths = set()
    for entry in entries:
        palette = entry.get("background_palette")
        if entry["edition"] == "wide":
            if palette is not None:
                raise ValueError("Instagram palette variation must not recolour README landscapes.")
            continue
        stem = Path(entry["filename"]).stem
        strength = palette.get("tint_strength", 1) if isinstance(palette, dict) else 1
        if stem in found or stem not in PORTRAIT_GROUNDS or palette != portrait_palette(stem, strength):
            raise ValueError("Each Instagram portrait needs its assigned distinct background colour.")
        found[stem] = palette
        strengths.add(strength)
    if set(found) != set(PORTRAIT_GROUNDS) or len(strengths) != 1 or len({p["hex"] for p in found.values()}) != 6:
        raise ValueError("Expected six distinct Instagram background colours.")
    result = {"scope": "instagram-portraits-only", "grounds": found, "cream_material_recoloured": False}
    strength = next(iter(strengths))
    if strength != 1:
        result.update(tint_strength=strength, white_blend_fraction=1 - strength)
    return result


def load_cream_layers(directory, stems, gaussian=False):
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT / ".local"):
        raise ValueError("Cream layers must come from the private local export.")
    source = directory / "manifest.json"
    payload = source.read_bytes()
    manifest = json.loads(payload)
    if (manifest.get("status") != "exported-and-checked"
            or manifest.get("kind") != ("gaussian-cream-campaign-layers" if gaussian else "static-cream-campaign-layers")
            or manifest.get("static_not_animation") is not True):
        raise ValueError("Cream layer export has not passed its material checks.")
    expected = {(edition, stem) for edition in ("wide", "portrait") for stem in stems}
    records = manifest.get("layers", [])
    if len(records) != 12 or {(r["edition"], r["stem"]) for r in records} != expected:
        raise ValueError("Expected twelve unique cream layers.")
    layers = {}
    for record in records:
        path = (directory / record["file"]).resolve()
        dimensions = (3200, 2000) if record["edition"] == "wide" else (2160, 2880)
        if not path.is_relative_to(directory) or sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Cream layer path or hash does not match its receipt.")
        with Image.open(path) as image:
            if image.mode != "RGBA" or image.size != dimensions or record["dimensions"] != list(dimensions):
                raise ValueError("Cream layer dimensions or alpha mode changed.")
            if image.getchannel("A").getextrema() != (0, 255):
                raise ValueError("Cream artwork needs transparent space and solid material.")
            layers[(record["edition"], record["stem"])] = (image.copy(), record)
        if len(record["forms"]) != (17 if gaussian else 6) or len(record["coverage_components"]) != (9 if gaussian else 6):
            raise ValueError("Cream primitive/group counts do not match the reviewed layout.")
        if record["original_shader_reconstruction_maximum_error"] > 2:
            raise ValueError("Transparent export no longer reproduces the original cream material.")
    if gaussian:
        from campaign_gaussian import validate_distinct_recipes
        validate_distinct_recipes([record["gaussian_layout"] for record in records])
        if not all(record["gaussian_layout"].get("every_cluster_has_protruding_lobes") is True for record in records):
            raise ValueError("Merged cream groups must have genuinely irregular outlines.")
        if manifest.get("layout_validation", {}).get("maximum_normalized_coverage_iou", 1) >= .65:
            raise ValueError("Cream structures repeat too closely across images.")
    provenance = {
        "manifest": str(source.relative_to(ROOT)), "manifest_sha256": sha256(payload).hexdigest(),
        "source_hashes": manifest["source_hashes"], "method": manifest["method"],
        "scope": manifest["scope"], "static_not_animation": True,
    }
    if gaussian:
        provenance["layout_validation"] = manifest["layout_validation"]
        provenance["recipe_source_sha256"] = manifest["recipe_source_sha256"]
    return layers, provenance


def cream_background(base, layer, texts, scale):
    if base.mode != "RGBA" or layer.mode != "RGBA" or base.size != layer.size:
        raise ValueError("Cream artwork and editorial background must share RGBA dimensions.")
    quiet = Image.new("L", base.size, 255)
    draw = ImageDraw.Draw(quiet)
    boxes = []
    for text in texts:
        x, y, width, height = text["bounds_xywh"]
        box = (math.floor(x * scale), math.floor(y * scale),
               math.ceil((x + width) * scale), math.ceil((y + height) * scale))
        boxes.append(box)
        draw.rectangle((box[0] - 20 * scale, box[1] - 20 * scale,
                        box[2] + 20 * scale, box[3] + 20 * scale), fill=0)
    quiet = quiet.filter(ImageFilter.GaussianBlur(12 * scale))
    draw = ImageDraw.Draw(quiet)
    for left, top, right, bottom in boxes:
        draw.rectangle((left - 3 * scale, top - 3 * scale, right + 3 * scale, bottom + 3 * scale), fill=0)
    material = layer.copy()
    material.putalpha(ImageChops.multiply(material.getchannel("A"), quiet))
    result = Image.alpha_composite(base, material)
    difference = ImageChops.difference(base.convert("RGB"), result.convert("RGB"))
    if any(difference.crop(box).getbbox() for box in boxes):
        raise ValueError("Cream decoration changed the protected reading background.")
    return result


def frosted_cream_background(base, layer, scale):
    """One continuous, low-tint glass surface; deliberately independent of text boxes."""
    if base.mode != "RGBA" or layer.mode != "RGBA" or base.size != layer.size:
        raise ValueError("Frosted artwork layers must have matching RGBA dimensions.")
    width, height = base.size
    bounds = (16 * scale, 16 * scale, width - 16 * scale, height - 12 * scale)
    mask = Image.new("L", base.size)
    ImageDraw.Draw(mask).rounded_rectangle(bounds, radius=28 * scale, fill=255)
    raw = Image.alpha_composite(base, layer)
    blurred = raw.filter(ImageFilter.GaussianBlur(9 * scale))
    glass = Image.blend(blurred, Image.new("RGBA", base.size, "#fffaf1"), .08)
    pixels = np.asarray(glass).copy()
    grain = np.random.default_rng(61009).normal(0, .28, (height, width, 1))
    pixels[..., :3] = np.clip(pixels[..., :3].astype(np.float32) + grain, 0, 255).astype(np.uint8)
    glass = Image.fromarray(pixels)
    shadow_mask = Image.new("L", base.size)
    ImageDraw.Draw(shadow_mask).rounded_rectangle(
        (bounds[0], bounds[1] + 7 * scale, bounds[2], bounds[3] + 7 * scale),
        radius=28 * scale, fill=24)
    shadow = Image.new("RGBA", base.size, (52, 72, 58, 0))
    shadow.putalpha(shadow_mask.filter(ImageFilter.GaussianBlur(8 * scale)))
    result = Image.alpha_composite(raw, shadow)
    result.paste(glass, (0, 0), mask)
    rim = Image.new("RGBA", base.size)
    edge = ImageDraw.Draw(rim)
    edge.rounded_rectangle(bounds, radius=28 * scale, outline=(255, 250, 241, 180), width=scale)
    edge.rounded_rectangle(tuple(value + (scale if i < 2 else -scale) for i, value in enumerate(bounds)),
                           radius=27 * scale, outline=(52, 72, 58, 22), width=scale)
    result = Image.alpha_composite(result, rim)
    return result, {
        "panel_bounds_xywh": [16, 16, width / scale - 32, height / scale - 28],
        "panel_count": 1, "tint_opacity": .08, "background_transmission": .92,
        "blur_css_pixels": 9, "text_shaped_masks": False,
    }


def validate_foreground_on_glass(geometry, glass):
    x, y, width, height = glass["panel_bounds_xywh"]
    boxes = [entry["bounds_xywh"] for entry in geometry["texts"] + geometry["brand_ornaments"]]
    boxes += [entry["frame_bounds_xywh"] for entry in geometry["devices"]]
    boxes += [entry["bounds_xywh"] for entry in geometry["features"]]
    for left, top, item_width, item_height in boxes:
        if left < x or top < y or left + item_width > x + width or top + item_height > y + height:
            raise ValueError("Foreground content leaves its shared glass surface.")


def material_visibility(before, after):
    if before.size != after.size:
        raise ValueError("Background-only revision changed the output dimensions.")
    difference = np.max(np.abs(np.asarray(before.convert("RGB"), dtype=np.int16)
                               - np.asarray(after.convert("RGB"), dtype=np.int16)), axis=2) > 5
    width, height = before.size
    fractions = {
        "visible_change_fraction": float(difference.mean()),
        "left_visible_fraction": float(difference[:, :width // 3].sum() / (width * height)),
        "right_visible_fraction": float(difference[:, width * 2 // 3:].sum() / (width * height)),
    }
    if fractions["visible_change_fraction"] < .02 or min(
            fractions["left_visible_fraction"], fractions["right_visible_fraction"]) < .004:
        raise ValueError(f"Cream background is not sufficiently visible around the foreground: {fractions}")
    return fractions


def cream_visibility(before, after, record):
    return {
        "kind": "original-webgl-cream", "layer_sha256": record["sha256"],
        "separate_material_forms": 6, "text_regions_unchanged": True,
        "background_only": True, "static_not_animation": True, **material_visibility(before, after),
    }


def validate_cream_receipt(entry):
    proof = entry.get("cream_background", {})
    if (proof.get("kind") != "original-webgl-cream"
            or proof.get("jpeg_sha256") != entry.get("sha256")
            or proof.get("separate_material_forms") != 6
            or proof.get("text_regions_unchanged") is not True
            or proof.get("background_only") is not True
            or proof.get("static_not_animation") is not True
            or len(proof.get("layer_sha256", "")) != 64):
        raise ValueError("Missing or mismatched cream-background proof.")
    for key, threshold in (("visible_change_fraction", .02), ("left_visible_fraction", .004),
                           ("right_visible_fraction", .004)):
        value = proof.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not threshold <= value <= 1:
            raise ValueError("Cream decoration must be visible on both sides of the final artwork.")


def validate_frosted_receipt(entry):
    proof = entry.get("frosted_cream", {})
    glass = proof.get("glass", {})
    if (proof.get("jpeg_sha256") != entry.get("sha256") or proof.get("cluster_count") != 4
            or proof.get("droplet_count") != 5 or proof.get("source_primitive_count") != 17
            or glass.get("panel_count") != 1 or glass.get("text_shaped_masks") is not False
            or glass.get("tint_opacity") != .08 or glass.get("background_transmission") != .92
            or proof.get("foreground_on_glass") is not True):
        raise ValueError("Missing or incorrect low-tint frosted-glass proof.")
    for key, threshold in (("visible_change_fraction", .02), ("left_visible_fraction", .004),
                           ("right_visible_fraction", .004), ("material_contrast_retained", .65)):
        value = proof.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < threshold:
            raise ValueError("Cream must remain visible through the lightly frosted glass.")
    validate_foreground_on_glass(entry, glass)
