"""Compose a private, twelve-image website launch campaign from supplied captures.

No browser is opened, no website is captured, and no network request is made.
Website imagery must be capture-owner full viewports or provenance-bound UI features.
Checked original cream layers are an optional, artwork-only background input.
Portrait editions are independently laid out at 1080x1440, never landscape crops.
Use a new --output revision when existing evidence differs.
"""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from prepare_prototype_photos import encoded, save_preserving_existing
from campaign_phone import raised_phone_shell, validate_raised_phones
from campaign_cream import (
    CREAM_DESIGN_REVISION, FROSTED_DESIGN_REVISION, cream_background, cream_visibility,
    frosted_cream_background, load_cream_layers, material_visibility, validate_foreground_on_glass,
    portrait_palette, portrait_ground, validate_portrait_grounds,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".local" / "launch-campaign-20261008"
OUTPUT = BASE / "composed"
FONTS = ROOT / "web" / "assets" / "fonts"
LOGO = ROOT / "web" / "assets" / "whisk-and-crumbs-logo.png"
MARK = ROOT / "web" / "assets" / "whisk-and-crumbs-mark.svg"
URL = "zanark.github.io/WhiskAndCrumbs/"
CANONICAL = f"https://{URL}"
CREAM, FOREST, TERRA = "#f5ebdd", "#34483a", "#a45137"
PAPER, BLUSH = "#fffaf1", "#f7dbe4"
SCALE = 2
DESIGN_REVISION = "studio-20261009-readable-editorial"
FINAL_REVISION = "editorial-20261009-final"
COMPONENT_CAPTURE_METHODS = {
    "Complete actual component bounds; no DOM/style changes": "complete-component-bounds",
    "Complete actual component including decoration and shadows; bounded crop from full-page capture, no DOM/style changes":
        "bounded-component-crop-from-full-page",
}
PHONE_PORTRAITS = {"01-welcome", "06-simple-ordering"}
FEATURES = {
    "02-bakery-entrance": ("02-bakery-entrance", "frameless-entrance-editorial", (55, 553, 970, 743)),
    "03-our-story": ("03-our-story", "recipe-note-editorial", (182, 559, 716, 715)),
    "04-cake-notebooks": ("04-cake-notebooks", "frameless-category-collection", (42, 493, 996, 823)),
    "05-open-notebook": ("05-open-notebook", "four-photo-gallery-spread", (43, 518, 994, 810)),
}
FEATURE_ALIASES = {
    "03-our-story": "03-story-note", "04-cake-notebooks": "04-category-overview",
    "05-open-notebook": "05-decorated-notebook",
}

SCENES = [
    {
        "stem": "01-welcome", "dark": False, "kicker": "THE WEBSITE IS LIVE",
        "plain": "Our little corner", "script": "is now online.",
        "micro": "Explore the website.", "portrait_sizes": [88, 94], "wide_sizes": [78, 88],
        "wide": {"desktop": [152, 332, 900, 0], "mobile": [1090, 331, 250, -4]},
        "portrait": {"desktop": [151, 538, 858, 0], "mobile": [41, 754, 247, 3]},
        "direction": "Warm opening edition: sunlit cream, an expansive announcement, "
                     "desktop-led welcome and a left-hand portrait phone protecting the hero cake.",
    },
    {
        "stem": "02-bakery-entrance", "dark": True, "kicker": "STEP INSIDE",
        "plain": "", "script": "Come on in.",
        "micro": "Explore our illustrated bakery.",
        "portrait_sizes": [86, 126], "wide_sizes": [78, 104],
        "wide": {"desktop": [514, 332, 900, 0], "mobile": [121, 336, 250, 4]},
        "portrait": {"desktop": [57, 495, 869, 0], "mobile": [749, 729, 237, -4]},
        "direction": "Forest evening edition: a luminous entrance in a large browser, "
                     "a gently leaning phone and a generous one-line invitation.",
    },
    {
        "stem": "03-our-story", "dark": False, "kicker": "FROM OUR KITCHEN",
        "plain": "A little care", "script": "in every layer.",
        "micro": "The story behind our home-baked cakes.",
        "portrait_sizes": [91, 95], "wide_sizes": [84, 90],
        "wide": {"desktop": [152, 332, 900, 0], "mobile": [1090, 347, 243, -3]},
        "portrait": {"desktop": [152, 540, 855, 0], "mobile": [50, 767, 241, 3]},
        "direction": "Quiet paper edition: warm reflected light, the unchanged story "
                     "on desktop and the authentic mobile recipe-note view.",
    },
    {
        "stem": "04-cake-notebooks", "dark": True, "kicker": "THE CAKE COLLECTION",
        "plain": "Find your", "script": "kind of cake.",
        "micro": "Six little notebooks to explore.",
        "portrait_sizes": [93, 100], "wide_sizes": [87, 96],
        "wide": {"desktop": [514, 332, 900, 0], "mobile": [126, 340, 250, 3]},
        "portrait": {"desktop": [55, 539, 868, 0], "mobile": [757, 770, 234, -3]},
        "direction": "Collection edition: forest, restrained blush reflected light, "
                     "and real pink notebooks framed by opposing device poses.",
    },
    {
        "stem": "05-open-notebook", "dark": False, "kicker": "OPEN A NOTEBOOK",
        "plain": "Take a", "script": "closer look.",
        "micro": "Real cake photos, one page at a time.",
        "portrait_sizes": [95, 110], "wide_sizes": [92, 100],
        "wide": {"desktop": [152, 332, 900, 0], "mobile": [1092, 346, 242, -2]},
        "portrait": {"desktop": [140, 512, 873, 0], "mobile": [48, 814, 220, 2]},
        "direction": "Gallery edition: cream above a deep-green tabletop wash, "
                     "the genuine four-photo desktop dialog and its complete mobile counterpart.",
    },
    {
        "stem": "06-simple-ordering", "dark": True, "kicker": "LET'S MAKE SOMETHING LOVELY",
        "plain": "Your next cake", "script": "starts with hello.",
        "micro": "Explore the website. Message us when you're ready.",
        "portrait_sizes": [81, 85], "wide_sizes": [72, 81],
        "wide": {"desktop": [514, 332, 900, 0], "mobile": [126, 344, 245, 3]},
        "portrait": {"desktop": [55, 548, 858, 0], "mobile": [746, 728, 236, -3]},
        "direction": "Closing invitation: warm forest light and a mobile-forward "
                     "Instagram handoff, with no invented handle or order confirmation.",
    },
]


def layout_contract(stem, edition):
    if edition not in {"wide", "portrait"} or stem not in {scene["stem"] for scene in SCENES}:
        raise ValueError("Unknown campaign scene or edition.")
    if edition == "wide" or stem in PHONE_PORTRAITS:
        return {"layout": "desktop-and-phone", "devices": ["desktop", "mobile"], "features": 0}
    return {"layout": FEATURES[stem][1], "devices": [], "features": 1}


def validate_layout_contract(exports):
    expected = {(scene["stem"] + ".jpg", edition) for scene in SCENES for edition in ("wide", "portrait")}
    actual = {(entry["filename"], entry["edition"]) for entry in exports}
    if len(exports) != 12 or actual != expected:
        raise ValueError("Layout validation requires each of the twelve named editions exactly once.")
    phones = {"wide": 0, "portrait": 0}
    portrait_counts = {}
    for entry in exports:
        stem = Path(entry["filename"]).stem
        contract = layout_contract(stem, entry["edition"])
        devices = [device["device"] for device in entry["devices"]]
        if sorted(devices) != sorted(contract["devices"]) or len(entry.get("features", [])) != contract["features"]:
            raise ValueError(f"Incorrect device/feature layout for {entry['edition']}/{stem}")
        if entry.get("layout") != contract["layout"]:
            raise ValueError(f"Incorrect editorial art direction for {stem}")
        phone_count = devices.count("mobile")
        if entry.get("phone_count") != phone_count:
            raise ValueError("Declared phone count does not match rendered devices.")
        phones[entry["edition"]] += phone_count
        if entry["edition"] == "portrait":
            portrait_counts[stem] = phone_count
        for device in entry["devices"]:
            if not device["frame_inside_canvas"] or not device["all_source_corners_retained"]:
                raise ValueError("Device layout loses a frame or viewport.")
        for feature in entry.get("features", []):
            if not feature["inside_canvas"] or not feature["complete_supplied_feature_retained"]:
                raise ValueError("Feature layout loses important source content.")
        canvas = (1600, 1000) if entry["edition"] == "wide" else (1080, 1440)
        if entry.get("validation", {}).get("dimensions") != list(canvas):
            raise ValueError("Editorial edition has incorrect dimensions.")
        boxes = [device["frame_bounds_xywh"] for device in entry["devices"]]
        boxes += [feature["bounds_xywh"] for feature in entry.get("features", [])]
        for x, y, width, height in boxes:
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y, width, height)):
                raise ValueError("Non-finite editorial media geometry.")
            if min(x, y) < 25 or width <= 0 or height <= 0 or x + width > canvas[0] - 25 or y + height > canvas[1] - 25:
                raise ValueError("Editorial media exceeds its required safe area.")
        if not entry["devices"] and not entry.get("features"):
            raise ValueError("A device-less layout still requires a validated genuine feature.")
    if phones != {"wide": 6, "portrait": 2}:
        raise ValueError("Expected six wide phones and only two portrait phones.")
    return {"phone_counts": phones, "portrait_phones_by_stem": portrait_counts,
            "middle_portrait_phone_count": 0, "contract_passed": True}


def sha(data):
    return sha256(data).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def rgb(colour):
    return tuple(int(colour[index:index + 2], 16) for index in (1, 3, 5))


def font(size, face="regular", scale=SCALE):
    filenames = {
        "regular": "dm-sans-regular.ttf", "semibold": "dm-sans-semibold.ttf",
        "display": "courgette-regular.ttf",
    }
    return ImageFont.truetype(str(FONTS / filenames[face]), round(size * scale))


def luma(values):
    c = np.asarray(values, dtype=np.float32) / 255
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def overlap(a, b):
    return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(
        0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    )


def rounded(values):
    return [round(value, 3) for value in values]


def backdrop(size, index, dark, tabletop=True, light_bands=True):
    """Original deterministic light, paper grain and soft window-cast shading."""
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    x, y = xx / width, yy / height
    base = np.array(rgb(FOREST if dark else CREAM), dtype=np.float32)
    result = np.broadcast_to(base, (height, width, 3)).copy()

    def wash(cx, cy, sx, sy, colour, strength):
        field = np.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2) / 2) * strength
        result[:] = result * (1 - field[..., None]) + np.array(rgb(colour)) * field[..., None]

    if dark:
        wash(.8, .68, .52, .41, "#63725a", .29)
        wash(.15, .1, .52, .55, "#24382d", .28)
        wash(.97, .93, .35, .36, "#9e8060", .12)
        if index == 3:
            wash(.18, .75, .25, .34, BLUSH, .075)
    else:
        wash(.14, .1, .55, .7, PAPER, .82)
        wash(.92, .82, .52, .56, "#cbb79d", .37)
        wash(.79, .25, .33, .49, BLUSH, .25 if index != 2 else .12)
        if index == 4 and tabletop:
            horizon = np.clip((y - .68) / .19, 0, 1) * .87
            result[:] = result * (1 - horizon[..., None]) + np.array(rgb(FOREST)) * horizon[..., None]

    # Light bands belong to the editorial backdrop, not the website screenshot.
    if light_bands:
        slant = x + y * .20
        beam = np.exp(-((slant - .86) / .15) ** 2) * (.028 if dark else .075)
        result += beam[..., None] * (255 - result)
        rail = np.exp(-((slant - 1.02) / .012) ** 2) * (.03 if dark else .042)
        result *= (1 - rail[..., None])
    vignette = np.clip(((x - .5) / .85) ** 2 + ((y - .48) / 1.0) ** 2, 0, 1) * .026
    result *= 1 - vignette[..., None]
    grain = np.random.default_rng(1008 + index).normal(0, .46, (height, width, 1))
    result = np.clip(result + grain, 0, 255).astype(np.uint8)
    return Image.fromarray(result).resize((width * SCALE, height * SCALE), Image.Resampling.BICUBIC).convert("RGBA")


def load_mark():
    # This exact region is the original mark placed by generate_brand_assets.py,
    # not a new tracing or a redraw. Preserve its existing RGBA pixels.
    with Image.open(LOGO) as logo:
        if logo.size != (905, 240):
            raise ValueError("The approved logo construction changed; verify its mark region.")
        mark = logo.convert("RGBA").crop((18, 20, 218, 220))
    if not mark.getchannel("A").getbbox():
        raise ValueError("Original logo mark region is empty.")
    return mark


def checked_feature(record, directory):
    record = dict(record)
    capture_method = COMPONENT_CAPTURE_METHODS.get(record.get("capture", "").rstrip("."))
    declared_complete_component = (
        capture_method is not None and "bounds_css" in record
    )
    if "bounds_css" in record:
        if "crop_css_pixels" in record and record["crop_css_pixels"] != record["bounds_css"]:
            raise ValueError("Feature has conflicting capture bounds.")
        record["crop_css_pixels"] = record["bounds_css"]
    if "feature_type" not in record and declared_complete_component:
        record["feature_type"] = "element-capture"
    if "all_important_content_inside" not in record and declared_complete_component:
        record["all_important_content_inside"] = True
    if record.get("feature_type") != "element-capture" or record.get("dpr") != 2:
        raise ValueError("Feature requires a genuine DPR2 element capture.")
    if record.get("all_important_content_inside") is not True or record.get("browser_errors") != []:
        raise ValueError("Feature capture has unresolved clipping or browser errors.")
    path = (directory / record["file"]).resolve()
    if not path.is_relative_to(directory) or path.suffix.lower() != ".png":
        raise ValueError("Feature source must be a PNG inside the checked capture directory.")
    data = path.read_bytes()
    if sha(data) != record["sha256"]:
        raise ValueError("Feature capture differs from its recorded hash.")
    crop = record["crop_css_pixels"]
    if any(not isinstance(crop.get(key), (int, float)) or not math.isfinite(crop[key])
           for key in ("x", "y", "width", "height")):
        raise ValueError("Invalid feature crop geometry.")
    if crop["x"] < 0 or crop["y"] < 0 or crop["width"] <= 0 or crop["height"] <= 0:
        raise ValueError("Invalid feature crop extent.")
    bounds = record.get("important_bounds", [])
    if not bounds and not declared_complete_component:
        raise ValueError("Feature must document complete important-content bounds.")
    for bound in bounds:
        values = [bound.get(key) for key in ("x", "y", "width", "height")]
        if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
            raise ValueError("Invalid important-content geometry.")
        x, y, width, height = values
        if x < -.5 or y < -.5 or width <= 0 or height <= 0 or x + width > crop["width"] + .5 or y + height > crop["height"] + .5:
            raise ValueError("Feature capture clips important content.")
    with Image.open(BytesIO(data)) as source:
        source.load()
        if source.format != "PNG" or list(source.size) != record["raster_pixels"]:
            raise ValueError("Feature raster dimensions mismatch.")
        if any(abs(actual - css * 2) > 2 for actual, css in zip(source.size, (crop["width"], crop["height"]))):
            raise ValueError("Feature does not match its recorded DPR2 crop.")
        image = source.convert("RGBA")
    if not record.get("source_url") or not record.get("selector"):
        raise ValueError("Feature needs its real source URL and selector.")
    return image, {
        "id": record["id"], "file": record["file"], "path": rel(path), "sha256": sha(data),
        "dimensions": list(image.size), "device_scale_factor": 2,
        "capture_url": record["source_url"], "selector": record["selector"],
        "capture_viewport_css": record.get("viewport_css"),
        "source_crop": crop, "important_bounds": bounds,
        "parent_sha256_verified": True, "all_important_content_inside": True,
        "capture_declaration": record.get("capture"),
        "capture_method": capture_method or "provenance-bound-element-capture",
        "whole_viewport_claimed": False,
        "content_completeness_evidence": (
            "Parent's complete-component capture declaration; crop extent and DPR2 raster verified. "
            "No descendant bounds supplied; descendant clipping is not independently remeasured."
            if not bounds else "Parent complete-content assertion plus numerically checked crop-local important bounds."
        ),
        "independent_descendant_bounds_checked": bool(bounds),
        "feature_type": "element-capture", "draft_only": False,
    }


def capture_inputs(directory, draft=False):
    directory = directory.resolve()
    if not directory.is_relative_to(BASE / "captures"):
        raise ValueError("Only the parent's campaign capture directory may be used.")
    manifest_path = directory / "manifest.json"
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data)
    if manifest.get("status") != "captured-and-checked" or manifest.get("canonical_url") != CANONICAL:
        raise ValueError("Capture manifest is not complete or has an unexpected website identity.")
    if not draft and manifest.get("campaign_revision") != FINAL_REVISION:
        raise ValueError("Final editorial art needs fresh editorial-20261009-final captures; use --draft for old geometry studies.")
    supplied = {entry["file"]: entry for entry in manifest.get("captures", [])}
    if len(supplied) != 12:
        raise ValueError("The parent must supply exactly twelve checked capture records.")
    captures, evidence = {}, []
    for scene in SCENES:
        for kind, expected in (("desktop", (2560, 1600)), ("mobile", (780, 1688))):
            name = f"{scene['stem']}-{kind}.png"
            path = directory / name
            data = path.read_bytes()
            source_record = supplied.get(name)
            if not source_record or sha(data) != source_record["sha256"]:
                raise ValueError(f"{name}: capture does not match its parent's recorded hash.")
            if source_record.get("browser_errors"):
                raise ValueError(f"{name}: capture has unresolved browser errors.")
            with Image.open(BytesIO(data)) as source:
                source.load()
                if source.format != "PNG" or source.size != expected:
                    raise ValueError(f"{name}: expected a complete {expected} PNG viewport.")
                captures[(scene["stem"], kind)] = source.convert("RGBA")
            record = {
                "file": name, "path": rel(path), "sha256": sha(data),
                "dimensions": list(expected), "css_viewport": [value // 2 for value in expected],
                "device_scale_factor": 2, "source_crop": None,
                "capture_url": source_record["source_url"],
                "parent_sha256_verified": True,
            }
            evidence.append(record)
    feature_records = []
    supplied_features = {entry["id"]: entry for entry in manifest.get("features", [])}
    for stem, (feature_id, _, _) in FEATURES.items():
        source_feature = supplied_features.get(feature_id) or supplied_features.get(FEATURE_ALIASES.get(feature_id))
        if source_feature:
            image, record = checked_feature(source_feature, directory)
            record["id"] = feature_id
        elif draft:
            kind = "mobile" if stem == "03-our-story" else "desktop"
            image = captures[(stem, kind)]
            record = {**next(item for item in evidence if item["file"] == f"{stem}-{kind}.png"),
                      "id": feature_id, "feature_type": "draft-whole-viewport",
                      "draft_only": True, "all_important_content_inside": False,
                      "note": "Whole old viewport is a geometry study only; final feature capture is pending."}
        else:
            raise ValueError(f"Missing required final feature capture: {feature_id}")
        captures[(feature_id, "feature")] = image
        feature_records.append(record)
    return captures, evidence, {
        "path": rel(manifest_path), "sha256": sha(manifest_data),
        "top_level_keys": list(manifest) if isinstance(manifest, dict) else None,
        "source_commit": manifest.get("source_commit"),
        "campaign_revision": manifest.get("campaign_revision"),
        "draft": draft, "feature_records": feature_records,
        "note": "Capture identity and browser validation are owned by the parent; "
                "this compositor independently checks dimensions and records exact source hashes.",
    }


class Art:
    def __init__(self, scene, edition, index, mark, frosted=False, raised_phone_glass=False,
                 portrait_light_bands=True):
        self.frosted = frosted
        self.raised_phone_glass = raised_phone_glass
        if frosted:
            scene = {**scene, "dark": False,
                     "direction": f"Light frosted-glass {scene['stem']} edition with uniquely oriented Gaussian cream."}
        if edition == "portrait" and scene["stem"] == "04-cake-notebooks":
            scene = {**scene, "dark": False}
        self.scene, self.edition, self.index = scene, edition, index
        self.size = (1600, 1000) if edition == "wide" else (1080, 1440)
        self.image = backdrop(self.size, index, scene["dark"], tabletop=not frosted,
                              light_bands=edition == "wide" or portrait_light_bands)
        self.background = self.image.copy()
        self.texts, self.devices, self.ornaments, self.features = [], [], [], []
        self.ink = CREAM if scene["dark"] else FOREST
        self.secondary = FOREST if frosted else "#e3d9c6" if scene["dark"] else "#68523f"
        self.accent = BLUSH if scene["dark"] else TERRA
        self.mark = mark
        self.chrome_texts = []

    def safe(self, box, margin=0):
        x, y, w, h = box
        return x >= margin and y >= margin and x + w <= self.size[0] - margin and y + h <= self.size[1] - margin

    def text(self, text, x, y, size, face="regular", colour=None, role="copy", tracking=0):
        if not text:
            return 0, 0
        colour = colour or self.ink
        selected = font(size, face)
        draw = ImageDraw.Draw(self.image)
        if tracking:
            widths = [draw.textlength(letter, font=selected) for letter in text]
            total = sum(widths) + tracking * SCALE * (len(text) - 1)
            glyph_bounds = [draw.textbbox((0, 0), letter, font=selected) for letter in text]
            top = min(box[1] for box in glyph_bounds)
            bottom = max(box[3] for box in glyph_bounds)
            cursor = x * SCALE
            for letter, width in zip(text, widths):
                draw.text((round(cursor), round(y * SCALE - top)), letter, font=selected, fill=colour)
                cursor += width + tracking * SCALE
            box = [x, y, total / SCALE, (bottom - top) / SCALE]
        else:
            bounds = draw.textbbox((0, 0), text, font=selected)
            draw.text((round(x * SCALE - bounds[0]), round(y * SCALE - bounds[1])),
                      text, font=selected, fill=colour)
            box = [x, y, (bounds[2] - bounds[0]) / SCALE, (bounds[3] - bounds[1]) / SCALE]
        if not self.safe(box, 22):
            raise ValueError(f"{self.edition}/{self.scene['stem']} clipped {role}: {text}: {box}")
        for existing in self.texts:
            if overlap(box, existing["bounds_xywh"]) > 0:
                raise ValueError(f"Campaign copy overlaps: {text!r} / {existing['text']!r}")
        if any(token in text.lower() for token in ("@handle", "link in bio", "whiskandcrubms", "127.0.0.1", ".local")):
            raise ValueError(f"Unexpected campaign copy: {text}")
        x0, y0 = math.floor(box[0] * SCALE), math.floor(box[1] * SCALE)
        x1, y1 = math.ceil((box[0] + box[2]) * SCALE), math.ceil((box[1] + box[3]) * SCALE)
        samples = np.asarray(self.background.crop((x0, y0, x1, y1)).convert("RGB"))
        background_luma = luma(samples.reshape(-1, 3))
        text_luma = float(luma(rgb(colour)))
        ratios = (np.maximum(text_luma, background_luma) + .05) / (np.minimum(text_luma, background_luma) + .05)
        minimum = float(ratios.min())
        threshold = 3.0 if role == "headline" else 4.5
        if minimum < threshold:
            raise ValueError(f"{role} contrast is {minimum:.2f}, below {threshold}: {text}")
        self.texts.append({
            "text": text, "role": role, "font": Path(selected.path).name,
            "font_size_px": size, "colour": colour, "tracking_px": tracking,
            "bounds_xywh": rounded(box), "inside_canvas": True,
            "minimum_backdrop_contrast": round(minimum, 3),
            "contrast_threshold": threshold,
            "estimated_font_px_at_540px_width": round(size * 540 / self.size[0], 2),
        })
        return box[2], box[3]

    def line(self, a, b, colour, width=1):
        ImageDraw.Draw(self.image).line(
            [tuple(round(v * SCALE) for v in point) for point in (a, b)],
            fill=colour, width=round(width * SCALE),
        )

    def circle(self, box, fill=None, outline=None, width=1):
        x, y, w, h = box
        ImageDraw.Draw(self.image).ellipse(
            tuple(round(value * SCALE) for value in (x, y, x + w, y + h)),
            fill=fill, outline=outline, width=round(width * SCALE),
        )

    def identity(self):
        portrait = self.edition == "portrait"
        left, top = (58, 48) if portrait else (74, 43)
        diameter = 46 if portrait else 42
        self.circle((left, top, diameter, diameter), fill=CREAM if self.scene["dark"] else PAPER)
        target = round((diameter - 8) * SCALE)
        mark = self.mark.resize((target, target), Image.Resampling.LANCZOS)
        self.image.alpha_composite(mark, (round((left + 4) * SCALE), round((top + 4) * SCALE)))
        self.ornaments.append({
            "type": "original-brand-mark", "bounds_xywh": [left, top, diameter, diameter],
            "source": rel(LOGO), "source_crop_ltrb": [18, 20, 218, 220],
            "medallion_colour": CREAM if self.scene["dark"] else PAPER,
            "identity_redrawn": False,
        })
        self.text("Whisk & Crumbs", left + diameter + 15, top + 9, 32 if portrait else 30, "display", role="brand")
        self.text(f"{self.index + 1:02} / 06", self.size[0] - (144 if portrait else 153),
                  top + 13, 20, "semibold", role="counter", tracking=1)

    def heading(self):
        portrait = self.edition == "portrait"
        left = 61 if portrait else 78
        kicker_y = 139 if portrait else 110
        self.text(self.scene["kicker"], left, kicker_y, 18,
                  "semibold", self.ink if self.frosted else self.accent, "kicker", tracking=2.2)
        plain, italic = self.scene["plain"], self.scene["script"]
        plain_size, italic_size = self.scene[f"{self.edition}_sizes"]
        if portrait:
            if plain:
                self.text(plain, left - 3, 201, plain_size, role="headline")
                self.text(italic, left - 3, 307, italic_size, "display", self.accent, "headline")
                micro_y = 433
            else:
                self.text(italic, left - 3, 236, italic_size, "display", role="headline")
                micro_y = 408
            if self.scene["micro"]:
                if self.scene["stem"] not in PHONE_PORTRAITS:
                    lines = {
                        1: ["Explore our illustrated bakery."],
                        2: ["The story behind", "our home-baked cakes."],
                        3: ["Six little notebooks to explore."],
                        4: ["Real cake photos, one page at a time."],
                    }[self.index]
                    for line_index, line in enumerate(lines):
                        self.text(line, left, micro_y + line_index * 43, 32,
                                  colour=self.secondary, role="editorial-body")
                elif self.index == 5:
                    self.text("Explore the website.", left, micro_y, 32, colour=self.secondary, role="editorial-body")
                    self.text("Message us when you're ready.", left, micro_y + 43, 32,
                              colour=self.secondary, role="editorial-body")
                else:
                    self.text(self.scene["micro"], left, micro_y, 32,
                              colour=self.secondary, role="editorial-body")
        else:
            start = left
            if plain:
                width, _ = self.text(plain, start, 154, plain_size, role="headline")
                start += width + 23
            self.text(italic, start, 145 if plain else 151, italic_size,
                      "display", self.accent if plain else self.ink, "headline")
            if self.scene["micro"]:
                self.text(self.scene["micro"], left + 2, 264, 48,
                          colour=self.secondary, role="editorial-body")

    def footer(self):
        portrait = self.edition == "portrait"
        # The classic gallery wash needs light footer ink; clear glass keeps dark ink.
        footer_ink = CREAM if self.scene["dark"] or (self.index == 4 and not self.frosted) else FOREST
        left = 61 if portrait else 78
        y = 1350 if portrait else 944
        rule = "#778370" if self.scene["dark"] or (self.index == 4 and not self.frosted) else "#c9bba4"
        self.line((left, y), (self.size[0] - left, y), rule, .65)
        if portrait:
            self.text(URL, left, 1360, 32, colour=footer_ink, role="website-url")
            self.text("Home-baked vegetarian cakes", left, 1400, 18,
                      colour=footer_ink, role="descriptor")
            dots_x, dots_y = 835, 1381
        else:
            self.text("Home-baked vegetarian cakes", left, 955, 20,
                      colour=footer_ink, role="descriptor")
            url_bounds = font(22).getbbox(URL)
            url_width = (url_bounds[2] - url_bounds[0]) / SCALE
            self.text(URL, self.size[0] - left - url_width, 954, 22, colour=footer_ink, role="website-url")
            dots_x, dots_y = 770, 965
        for i in range(6):
            self.circle((dots_x + i * 23, dots_y, 6, 6),
                        fill=footer_ink if i == self.index else None, outline=footer_ink, width=.75)

    def device(self, image, kind, source, spec):
        x, y, screen_width, angle = spec
        screen_height = screen_width * image.height / image.width
        mobile = kind == "mobile"
        raised = mobile and self.edition == "portrait" and self.raised_phone_glass
        rim, top, bottom = (7, 19, 18) if mobile else (4, 34, 4)
        if raised:
            rim, top, bottom = 14, 26, 25
            x, y = x - 7, y - 10
        w, h = screen_width + rim * 2, screen_height + top + bottom
        pixel_w, pixel_h = round(w * SCALE), round(h * SCALE)
        if raised:
            frame, glass_proof = raised_phone_shell((pixel_w, pixel_h), SCALE)
        else:
            frame = Image.new("RGBA", (pixel_w, pixel_h))
        draw = ImageDraw.Draw(frame)
        outer = (1, 1, pixel_w - 2, pixel_h - 2)
        if not raised:
            draw.rounded_rectangle(
                outer, radius=(26 if mobile else 10) * SCALE,
                fill="#25342c" if mobile else "#e6dfd0",
                outline="#879184" if mobile else "#a7ab9b", width=SCALE,
            )
        if mobile:
            draw.rounded_rectangle((pixel_w / 2 - 17 * SCALE, 8 * SCALE,
                                    pixel_w / 2 + 17 * SCALE, 10 * SCALE),
                                   1 * SCALE, fill="#657062")
            draw.rounded_rectangle((pixel_w / 2 - 26 * SCALE, pixel_h - 9 * SCALE,
                                    pixel_w / 2 + 26 * SCALE, pixel_h - 7 * SCALE),
                                   1 * SCALE, fill="#8e9687")
        else:
            for dot in range(3):
                cx = (16 + dot * 13) * SCALE
                draw.ellipse((cx - 2.4 * SCALE, 14.6 * SCALE,
                              cx + 2.4 * SCALE, 19.4 * SCALE), fill="#889180")
            address_font = font(12)
            address_box = draw.textbbox((0, 0), URL, font=address_font)
            tx, ty = 81 * SCALE, 12 * SCALE - address_box[1]
            draw.text((tx, ty), URL, font=address_font, fill=FOREST)
            self.chrome_texts.append({
                "text": URL, "role": "editorial-browser-address",
                "font_size_px": 12, "device": kind,
                "local_bounds_xywh": [81, 12, (address_box[2] - address_box[0]) / SCALE,
                                      (address_box[3] - address_box[1]) / SCALE],
                "canvas_bounds_xywh": [x + 81, y + 12, (address_box[2] - address_box[0]) / SCALE,
                                       (address_box[3] - address_box[1]) / SCALE],
                "contrast": round(float((max(float(luma(rgb(FOREST))), float(luma(rgb("#e6dfd0")))) + .05) /
                                       (min(float(luma(rgb(FOREST))), float(luma(rgb("#e6dfd0")))) + .05)), 3),
                "presentation_only": True,
            })
        # The viewport is an intact rectangle. Corner masks never erase screenshot pixels.
        screen_pixels = (round(screen_width * SCALE), round(screen_height * SCALE))
        raster_ratio_error = abs((screen_pixels[0] / screen_pixels[1]) / (image.width / image.height) - 1)
        if raster_ratio_error > .001:
            raise ValueError("Screenshot raster aspect ratio differs by more than one tenth percent.")
        screenshot = image.resize(screen_pixels, Image.Resampling.LANCZOS)
        frame.alpha_composite(screenshot, (round(rim * SCALE), round(top * SCALE)))
        if raised:
            screen_box = (round(rim * SCALE), round(top * SCALE),
                          round(rim * SCALE) + screen_pixels[0], round(top * SCALE) + screen_pixels[1])
            if frame.crop(screen_box).tobytes() != screenshot.tobytes():
                raise ValueError("Phone glass must not paint over or clip the real viewport.")
            glass_proof["unaltered_screen_raster"] = True
        rotated = frame.rotate(angle, Image.Resampling.BICUBIC, expand=True)
        bounds = [x, y, rotated.width / SCALE, rotated.height / SCALE]
        if not self.safe(bounds, 25):
            raise ValueError(f"{self.edition}/{self.scene['stem']}: {kind} frame outside canvas: {bounds}")
        for text in self.texts:
            if overlap(bounds, text["bounds_xywh"]) > 0:
                raise ValueError(f"{self.edition}/{self.scene['stem']}: {kind} overlaps {text['text']}")
        alpha = rotated.getchannel("A")
        for blur, dy, opacity in ((25, 21, .20), (6, 6, .16)):
            mask = Image.new("L", self.image.size)
            mask.paste(alpha.point(lambda p: round(p * opacity)),
                       (round(x * SCALE), round((y + dy) * SCALE)))
            shadow = Image.new("RGBA", self.image.size, (13, 25, 17, 0))
            shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(blur * SCALE)))
            self.image.alpha_composite(shadow)
        self.image.alpha_composite(rotated, (round(x * SCALE), round(y * SCALE)))
        radians = math.radians(angle)
        polygon = []
        for px, py in ((rim, top), (rim + screen_width, top),
                       (rim + screen_width, top + screen_height), (rim, top + screen_height)):
            dx, dy = px - w / 2, py - h / 2
            polygon.append([
                x + rotated.width / SCALE / 2 + dx * math.cos(radians) + dy * math.sin(radians),
                y + rotated.height / SCALE / 2 - dx * math.sin(radians) + dy * math.cos(radians),
            ])
        record = {
            "device": kind, "source": source,
            "frame_bounds_xywh": rounded(bounds),
            "unrotated_frame_dimensions": [round(w, 3), round(h, 3)],
            "screen_dimensions": [screen_width, round(screen_height, 4)],
            "screen_polygon": [rounded(point) for point in polygon],
            "rotation_degrees_counterclockwise": angle,
            "source_dimensions": list(image.size), "crop": None,
            "all_source_corners_retained": True, "frame_inside_canvas": True,
            "source_aspect_ratio": image.width / image.height,
            "rendered_aspect_ratio": screen_width / screen_height,
            "rendered_screen_pixels_before_downsample": list(screen_pixels),
            "raster_ratio_rounding_error_fraction": round(raster_ratio_error, 7),
            "resampling": "Lanczos; optional whole-device bicubic rotation",
            "screenshot_corner_mask": False, "screen_colour_adjustment": False,
            "estimated_18px_website_text_at_native_art": round(18 * screen_width / (390 if mobile else 1280), 2),
            "estimated_18px_website_text_at_540px_art_width": round(
                18 * screen_width / (390 if mobile else 1280) * 540 / self.size[0], 2),
        }
        if raised:
            record["raised_glass"] = glass_proof
        self.devices.append(record)

    def feature(self, image, source, spec, treatment):
        x, y, width, height = spec
        fitted = ImageOps.contain(image, (round(width * SCALE), round(height * SCALE)),
                                  Image.Resampling.LANCZOS)
        w, h = fitted.width / SCALE, fitted.height / SCALE
        left, top = x + (width - w) / 2, y + (height - h) / 2
        bounds = [left, top, w, h]
        if not self.safe(bounds, 25):
            raise ValueError("Editorial feature exceeds its canvas.")
        for text in self.texts:
            if overlap(bounds, text["bounds_xywh"]) > 0:
                raise ValueError(f"Editorial feature overlaps copy: {text['text']}")
        # Shadows are presentation only. The supplied UI rectangle is never
        # masked, colour-adjusted, cover-cropped or stretched into a device.
        if treatment != "frameless-category-collection":
            mask = Image.new("L", self.image.size)
            ImageDraw.Draw(mask).rectangle(
                tuple(round(v * SCALE) for v in (left, top + 16, left + w, top + h + 16)),
                fill=38,
            )
            shadow = Image.new("RGBA", self.image.size, (22, 35, 27, 0))
            shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(22 * SCALE)))
            self.image.alpha_composite(shadow)
        self.image.alpha_composite(fitted, (round(left * SCALE), round(top * SCALE)))
        error = abs((w / h) / (image.width / image.height) - 1)
        if error > .001:
            raise ValueError("Editorial feature aspect ratio mismatch.")
        self.features.append({
            "type": treatment, "source": source, "bounds_xywh": rounded(bounds),
            "inside_canvas": True, "complete_supplied_feature_retained": True,
            "presentation": "Genuine frameless website UI detail; not a complete browser or phone.",
            "source_dimensions": list(image.size), "source_capture_crop": source.get("source_crop"),
            "composition_crop": None, "phone_frame": False, "browser_frame": False,
            "pixel_colour_adjustments": False, "source_corner_mask": False,
            "raster_ratio_rounding_error_fraction": round(error, 7),
            "target_box_xywh": list(spec),
            "target_box_fill_fraction": round(w * h / (width * height), 4),
            "canvas_area_fraction": round(w * h / (self.size[0] * self.size[1]), 4),
            "important_content_verified_by_capture_owner": source["all_important_content_inside"],
            "draft_only": source["draft_only"],
        })

    def finish(self):
        contract = layout_contract(self.scene["stem"], self.edition)
        if sorted(device["device"] for device in self.devices) != sorted(contract["devices"]) or len(self.features) != contract["features"]:
            raise ValueError("Scene does not meet its declared device/feature layout.")
        for text in self.texts:
            for device in self.devices:
                if overlap(text["bounds_xywh"], device["frame_bounds_xywh"]) > 0:
                    raise ValueError(f"Text overlaps a device: {text['text']}")
            for feature in self.features:
                if overlap(text["bounds_xywh"], feature["bounds_xywh"]) > 0:
                    raise ValueError(f"Text overlaps a feature: {text['text']}")
        frame_overlap = overlap(*(device["frame_bounds_xywh"] for device in self.devices)) if len(self.devices) == 2 else 0
        desktop = next((d for d in self.devices if d["device"] == "desktop"), None)
        # Bounding boxes intentionally overestimate a rotated phone's true occlusion.
        fraction = frame_overlap / (desktop["screen_dimensions"][0] * desktop["screen_dimensions"][1]) if desktop else 0
        if fraction > .20:
            raise ValueError(f"Device overlap exceeds the deliberate 20% ceiling: {fraction}")
        image = self.image.convert("RGB").resize(self.size, Image.Resampling.LANCZOS)
        image.info.clear()
        return image, {
            "copy": {"kicker": self.scene["kicker"], "plain_headline": self.scene["plain"],
                     "display_headline": self.scene["script"], "microcopy": self.scene["micro"]},
            "layout": contract["layout"],
            "direction": self.scene["direction"] if self.edition == "wide" or self.scene["stem"] in PHONE_PORTRAITS else {
                "02-bakery-entrance": "The complete real entrance as an oversized cinematic website detail; no browser or phone frame.",
                "03-our-story": "The original recipe note as a large, intact editorial paper feature; no device frame.",
                "04-cake-notebooks": "A cream, frameless six-notebook collection; all real covers and exterior details.",
                "05-open-notebook": "A broad four-photo gallery spread with the complete real notebook controls and tabs.",
            }[self.scene["stem"]], "texts": self.texts,
            "browser_chrome_texts": self.chrome_texts, "devices": self.devices,
            "features": self.features, "phone_count": sum(d["device"] == "mobile" for d in self.devices),
            "brand_ornaments": self.ornaments,
            "device_overlap": {
                "bounding_box_area_px2": round(frame_overlap, 3),
                "conservative_fraction_of_desktop_screen": round(fraction, 4),
                "maximum": .20,
                "note": "A limited editorial phone overlap may obscure part of the desktop view; "
                        "neither source is cropped or altered. No exhaustive semantic-occlusion claim.",
            },
            "checks": {
                "text_inside_canvas": True, "frames_inside_canvas": True,
                "headlines_and_copy_clear_of_devices": True,
                "feature_bounds_inside_canvas": all(feature["inside_canvas"] for feature in self.features),
                "headlines_and_copy_clear_of_features": True,
                "genuine_media_present": bool(self.devices or self.features),
                "source_aspect_ratios_preserved": True,
                "text_backdrop_contrast_passed": True,
                "copy_boxes_do_not_overlap": True,
                "portrait_recomposed_not_cropped": self.edition == "portrait",
            },
        }


def validate_jpeg(data, size):
    with Image.open(BytesIO(data)) as image:
        image.load()
        if image.size != size or image.mode != "RGB" or image.format != "JPEG":
            raise ValueError("Incorrect campaign export dimensions, colour mode or format.")
        if image.getexif() or any(name in image.info for name in ("exif", "xmp", "comment", "icc_profile")):
            raise ValueError("Private or unexpected JPEG metadata.")
        segments = image.applist
        if any(marker != "APP0" or not payload.startswith(b"JFIF\x00") for marker, payload in segments):
            raise ValueError("Unexpected JPEG application or comment metadata.")
        metadata = b"\x00".join(payload for _, payload in segments)
        result = {"format": image.format, "mode": image.mode, "dimensions": list(image.size),
                  "exif_entries": 0, "metadata_keys": sorted(image.info),
                  "metadata_segments": [marker for marker, _ in segments]}
    for token in (b"C:\\", b".local", b"127.0.0.1", b"mishrad", b"WhiskAndCrubms", b"homemadevegcakes"):
        if token in metadata:
            raise ValueError(f"Unexpected metadata string: {token!r}")
    result["private_metadata_scan"] = "passed; JPEG metadata segments only, not compressed pixels or quantization tables"
    return result


def check_raster_typography(data, size, background, texts):
    critical = [text for text in texts if text["role"] in {"headline", "editorial-body"}]
    if not critical or not any(text["role"] == "editorial-body" for text in critical):
        raise ValueError("A studio edition needs measured headline and supporting copy.")
    with Image.open(BytesIO(data)) as source:
        source.load()
        if source.size != tuple(size):
            raise ValueError("Raster review dimensions differ from the actual JPEG.")
        jpeg = source.convert("RGB")
    checks = []
    for target_width in (size[0], 540):
        ratio = target_width / size[0]
        target = (target_width, round(size[1] * ratio))
        pixels = np.asarray(jpeg.resize(target, Image.Resampling.LANCZOS))
        backdrop_pixels = np.asarray(background.convert("RGB").resize(target, Image.Resampling.LANCZOS))
        for text in critical:
            if text.get("tracking_px", 0):
                raise ValueError("Tracked critical copy needs an explicit glyph-mask renderer.")
            effective_size = text["font_size_px"] * ratio
            if text["role"] == "editorial-body" and effective_size < 16:
                raise ValueError("Supporting copy is smaller than 16px in the actual 540px preview.")
            x, y, w, h = text["bounds_xywh"]
            bounds = [value * ratio for value in (x, y, w, h)]
            if not all(math.isfinite(value) for value in bounds) or min(x, y) < 0 or x + w > size[0] or y + h > size[1]:
                raise ValueError("Critical raster typography has invalid or clipped bounds.")
            mask = Image.new("L", (size[0] * SCALE, size[1] * SCALE))
            draw = ImageDraw.Draw(mask)
            selected = ImageFont.truetype(str(FONTS / text["font"]), round(text["font_size_px"] * SCALE))
            ink = draw.textbbox((0, 0), text["text"], font=selected)
            draw.text((round(x * SCALE - ink[0]), round(y * SCALE - ink[1])),
                      text["text"], fill=255, font=selected)
            # Only opaque glyph interiors count; antialiased edges are not WCAG colour samples.
            core = np.asarray(mask.resize(target, Image.Resampling.LANCZOS)) >= 248
            count = int(core.sum())
            if count < 20:
                raise ValueError("Too few actual core glyph pixels for a reliable readability check.")
            foreground_luma = luma(pixels[core])
            background_luma = luma(backdrop_pixels[core])
            contrasts = (np.maximum(foreground_luma, background_luma) + .05) / (
                np.minimum(foreground_luma, background_luma) + .05)
            fifth = float(np.percentile(contrasts, 5))
            threshold = 3 if text["role"] == "headline" else 4.5
            if fifth < threshold:
                raise ValueError(f"Actual JPEG glyph contrast {fifth:.3f} < {threshold}: {text['text']}")
            checks.append({
                "text": text["text"], "role": text["role"], "target_dimensions": list(target),
                "effective_font_px": round(effective_size, 3), "bounds_xywh": rounded(bounds),
                "opaque_core_pixels": count, "fifth_percentile_contrast": round(fifth, 4),
                "threshold": threshold, "passed": True,
            })
    return {
        "jpeg_sha256": sha(data), "tested_widths": [size[0], 540], "passed": True,
        "method": "Actual final JPEG at native and Lanczos 540px width; fifth-percentile contrast "
                  "of >=248/255 opaque glyph cores against the original local backdrop.",
        "checks": checks, "visual_inspection": False,
    }


def contact_sheet(exports, output):
    # Twelve complete editions plus four enlarged device/copy detail crops.
    width, height = 2160, 2080
    sheet = Image.new("RGB", (width, height), CREAM)
    draw = ImageDraw.Draw(sheet)
    label = font(18, "semibold", scale=1)
    title = font(26, "semibold", scale=1)
    draw.text((22, 16), "WHISK & CRUMBS / LAUNCH CAMPAIGN / 12 EDITIONS + 4 DETAIL PROOFS",
              font=title, fill=FOREST)
    tiles = []
    for item in exports:
        tiles.append((f"{len(tiles) + 1:02}  {item['edition']} / {item['filename']}",
                      output / item["edition"] / item["filename"], None))
    tiles.extend([
        ("13  wide 01 / browser + full viewport", output / "wide" / "01-welcome.jpg", (145, 325, 1070, 940)),
        ("14  portrait 01 / headline hierarchy", output / "portrait" / "01-welcome.jpg", (44, 126, 1025, 480)),
        ("15  portrait 05 / genuine book feature", output / "portrait" / "05-open-notebook.jpg", (36, 510, 1044, 1335)),
        ("16  portrait 02 / real entrance detail", output / "portrait" / "02-bakery-entrance.jpg", (45, 540, 1035, 1310)),
    ])
    records = []
    for index, (caption, path, crop) in enumerate(tiles):
        with Image.open(path) as source:
            image = source.convert("RGB")
            if crop:
                image = image.crop(crop)
        x, y = 20 + index % 4 * 537, 71 + index // 4 * 496
        if draw.textlength(caption, font=label) > 508:
            raise ValueError(f"Contact-sheet label exceeds its tile: {caption}")
        draw.text((x + 3, y), caption, fill=FOREST, font=label)
        draw.rectangle((x, y + 31, x + 516, y + 473), fill="#e7ddcc", outline="#c9bba4")
        thumb = ImageOps.contain(image, (504, 429), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x + (516 - thumb.width) // 2, y + 37 + (429 - thumb.height) // 2))
        records.append({"tile": index + 1, "label": caption, "source": rel(path),
                        "crop_ltrb": list(crop) if crop else None,
                        "thumbnail_dimensions": list(thumb.size)})
    data = encoded(sheet, "JPEG", quality=94, subsampling=0, optimize=True)
    path = output / "launch-review-16.jpg"
    save_preserving_existing(path, data)
    return {"path": rel(path), "sha256": sha(data), "dimensions": [width, height],
            "tiles": records, "viewed": False}


def validate_portrait_lighting(entries):
    portraits = []
    for entry in entries:
        proof = entry.get("background_lighting")
        if entry["edition"] == "portrait":
            if proof != {"diagonal_highlight_band": False, "diagonal_shadow_band": False}:
                raise ValueError("Instagram portraits must omit both diagonal light bands.")
            portraits.append(entry["filename"])
        elif proof is not None:
            raise ValueError("The Instagram lighting revision must not change README landscapes.")
    if sorted(portraits) != sorted(scene["stem"] + ".jpg" for scene in SCENES):
        raise ValueError("Clean portrait lighting requires all six Instagram images.")
    return {"scope": "instagram-portraits-only", "diagonal_bands": False}


def create(capture_directory, output, draft=False, cream_directory=None, frosted_directory=None,
           portrait_colour_variance=False, raised_phone_glass=False, portrait_light_bands=True,
           portrait_tint_strength=1):
    if cream_directory is not None and frosted_directory is not None:
        raise ValueError("Choose either the historical cream style or the new frosted-glass edition.")
    if portrait_colour_variance and frosted_directory is None:
        raise ValueError("Portrait colour variance requires the low-tint frosted-cream edition.")
    portrait_palette(SCENES[0]["stem"], portrait_tint_strength)
    if portrait_tint_strength != 1 and not portrait_colour_variance:
        raise ValueError("Reduced portrait tint requires the portrait colour-variance option.")
    output = output.resolve()
    if output != OUTPUT and not output.is_relative_to(OUTPUT):
        raise ValueError("Campaign outputs must remain under the private composed directory.")
    captures, capture_records, capture_manifest = capture_inputs(capture_directory, draft=draft)
    lookup = {(entry["file"]): entry for entry in capture_records}
    feature_lookup = {entry["id"]: entry for entry in capture_manifest["feature_records"]}
    mark = load_mark()
    layer_directory = frosted_directory or cream_directory
    frosted = frosted_directory is not None
    cream_layers, cream_source = ({}, None) if layer_directory is None else load_cream_layers(
        layer_directory, [scene["stem"] for scene in SCENES], gaussian=frosted)
    rendered, exports = [], []
    for index, scene in enumerate(SCENES):
        for edition in ("wide", "portrait"):
            art = Art(scene, edition, index, mark, frosted=frosted, raised_phone_glass=raised_phone_glass,
                      portrait_light_bands=portrait_light_bands)
            reference = None
            if frosted:
                layer, layer_record = cream_layers[(edition, scene["stem"])]
                base = art.background.copy()
                if portrait_colour_variance and edition == "portrait":
                    base = portrait_ground(base, scene["stem"], portrait_tint_strength)
                reference = Art(scene, edition, index, mark, frosted=True, raised_phone_glass=raised_phone_glass,
                                portrait_light_bands=portrait_light_bands)
                reference.background, glass = frosted_cream_background(
                    base, Image.new("RGBA", base.size), SCALE)
                reference.image = reference.background.copy()
                art.background, glass = frosted_cream_background(base, layer, SCALE)
                art.image = art.background.copy()
                raw = np.asarray(Image.alpha_composite(base, layer).convert("RGB"), dtype=np.int16)
                interior = (slice(48 * SCALE, -48 * SCALE), slice(48 * SCALE, -48 * SCALE))
                raw_delta = np.abs(raw - np.asarray(base.convert("RGB"), dtype=np.int16))[interior].sum()
                frosted_delta = np.abs(np.asarray(art.background.convert("RGB"), dtype=np.int16)
                                       - np.asarray(reference.background.convert("RGB"), dtype=np.int16))[interior].sum()
                if raw_delta == 0:
                    raise ValueError("No cream material is visible behind the interior glass.")
                retention = float(frosted_delta / raw_delta)
                if retention < .65:
                    raise ValueError("The glass obscures too much of the cream structure.")
                reference.identity()
                reference.heading()
                reference.footer()
            art.identity()
            art.heading()
            art.footer()
            if cream_layers and not frosted:
                reference = art
                art = Art(scene, edition, index, mark, raised_phone_glass=raised_phone_glass,
                          portrait_light_bands=portrait_light_bands)
                layer, layer_record = cream_layers[(edition, scene["stem"])]
                art.background = cream_background(art.background, layer, reference.texts, SCALE)
                art.image = art.background.copy()
                art.identity()
                art.heading()
                art.footer()
            contract = layout_contract(scene["stem"], edition)
            for surface in ([reference, art] if reference else [art]):
                for kind in contract["devices"]:
                    key = f"{scene['stem']}-{kind}.png"
                    spec = scene[edition][kind]
                    surface.device(captures[(scene["stem"], kind)], kind, lookup[key], spec)
                if contract["features"]:
                    feature_id, treatment, spec = FEATURES[scene["stem"]]
                    surface.feature(captures[(feature_id, "feature")], feature_lookup[feature_id], spec, treatment)
            image, geometry = art.finish()
            if portrait_colour_variance and edition == "portrait":
                geometry["background_palette"] = portrait_palette(scene["stem"], portrait_tint_strength)
            if not portrait_light_bands and edition == "portrait":
                geometry["background_lighting"] = {
                    "diagonal_highlight_band": False, "diagonal_shadow_band": False,
                }
            data = encoded(image, "JPEG", quality=95, subsampling=0, optimize=True)
            if reference:
                previous, reference_geometry = reference.finish()
                for key in ("devices", "features", "brand_ornaments"):
                    if geometry.get(key) != reference_geometry.get(key):
                        raise ValueError(f"Cream background changed foreground {key}.")
                if frosted:
                    text_spec = lambda records: [{k: v for k, v in text.items() if k != "minimum_backdrop_contrast"}
                                                 for text in records]
                    if text_spec(geometry["texts"]) != text_spec(reference_geometry["texts"]):
                        raise ValueError("The cream layer changed foreground text specifications.")
                    validate_foreground_on_glass(geometry, glass)
                    layout = layer_record["gaussian_layout"]
                    geometry["frosted_cream"] = {
                        "jpeg_sha256": sha(data), "layer_sha256": layer_record["sha256"],
                        "normalized_geometry_sha256": layout["normalized_geometry_sha256"],
                        "orientation_radians": layout["orientation_radians"], "seed": layout["seed"],
                        "cluster_count": 4, "droplet_count": 5, "source_primitive_count": 17,
                        "glass": glass, "material_contrast_retained": retention, "foreground_on_glass": True,
                        **material_visibility(previous, image),
                    }
                else:
                    if geometry["texts"] != reference_geometry["texts"]:
                        raise ValueError("Historical cream background changed foreground text.")
                    geometry["cream_background"] = {
                        **cream_visibility(previous, image, layer_record), "jpeg_sha256": sha(data),
                    }
            validation = validate_jpeg(data, art.size)
            raster_typography = check_raster_typography(data, art.size, art.background, art.texts)
            filename = scene["stem"] + ".jpg"
            target = output / edition / filename
            if target.exists() and target.read_bytes() != data:
                raise ValueError(f"Existing output differs: {target}. Use a new output revision.")
            exports.append({
                "filename": filename, "edition": edition, "path": rel(target),
                "sha256": sha(data), "bytes": len(data), "validation": validation,
                "raster_typography": raster_typography, **geometry,
            })
            rendered.append((target, data))
    if len(set(item["sha256"] for item in exports)) != 12:
        raise ValueError("The twelve campaign images must be distinct.")
    layout_check = validate_layout_contract(exports)
    for target, data in rendered:
        save_preserving_existing(target, data)
        with Image.open(BytesIO(data)) as full:
            thumb = full.resize((540, round(full.height * 540 / full.width)), Image.Resampling.LANCZOS)
            save_preserving_existing(output / "quality" / "540" / target.parent.name / (target.stem + ".png"),
                                     encoded(thumb, "PNG", optimize=True))
    sheet = contact_sheet(exports, output)
    assets = [LOGO, MARK, FONTS / "courgette-regular.ttf",
              FONTS / "dm-sans-regular.ttf", FONTS / "dm-sans-semibold.ttf"]
    manifest = {
        "schema_version": 2, "campaign": "Whisk & Crumbs / the website is live",
        "canonical_url": CANONICAL,
        "design_revision": FROSTED_DESIGN_REVISION if frosted else CREAM_DESIGN_REVISION if cream_layers else DESIGN_REVISION,
        "generator": rel(Path(__file__)), "generator_sha256": sha(Path(__file__).read_bytes()),
        "status": "draft-geometry-study-not-for-release" if draft else "composed-and-numerically-validated; not-visually-inspected",
        "draft": draft, "layout_contract": layout_check,
        "capture_manifest": capture_manifest, "captures": capture_records,
        "assets": [{"path": rel(path), "sha256": sha(path.read_bytes())} for path in assets],
        "mark_provenance": {
            "canonical_svg": rel(MARK), "pixel_source": rel(LOGO), "crop_ltrb": [18, 20, 218, 220],
            "construction_evidence": "scripts\\generate_brand_assets.py:115-119",
            "action": "Reuse existing original-mark pixels on a cream medallion; no redraw.",
        },
        "encoding": {"format": "JPEG", "mode": "RGB", "quality": 95, "subsampling": 0,
                     "wide_dimensions": [1600, 1000], "portrait_dimensions": [1080, 1440],
                     "supersampling": SCALE, "metadata": "JFIF only; no EXIF/XMP/ICC/comment"},
        "exports": exports, "contact_sheet": sheet,
        "readability": {
            "headlines": "At least 3:1 local-background contrast; native size and estimated "
                         "540px-wide display size recorded for every text box.",
            "reading_copy": "At least 4.5:1 local-background contrast.",
            "editorial_body": "All portrait supporting copy is 32px native / 16px at 540px. "
                              "Wide supporting copy is 48px native / 16.2px at 540px.",
            "raster_validation": "Every final JPEG is checked at native and actual 540px resolution; "
                                 "per-glyph contrast results are bound to its SHA256.",
            "authentic_ui": "Website text remains unedited. Device labels are contextual at feed/README scale. "
                            "Middle portraits use large, provenance-bound genuine UI features, not phone screens.",
            "rotation": "Only the complete generic mobile frame rotates, by at most four degrees.",
        },
        "boundaries": {
            "image_tool_views": 0, "network_requests": 0, "browser_launches": 0,
            "website_capture_or_dom_edits": False, "site_or_public_files_changed": False,
            "original_photos_edited": False, "instagram_upload_or_posting": False,
            "invented_handle_or_link_in_bio": False,
            "external_reference_pixels_used": False,
        },
        "limitations": [
            "No visual inspection, aesthetic acceptance or native-device review is claimed.",
            "Generic device frames and procedural light are original editorial illustrations, "
            "not photographs of physical hardware or premises.",
            "Whole viewports are preserved where device frames are promised. Frameless features explicitly "
            "record the actual source element crop. Limited paired-device overlap estimates are conservative.",
            "Pixel capture authenticity, website resource checks and release installation are "
            "the parent capture/integration owner's responsibilities.",
            "No external site, Instagram app, account rename or link-in-bio state was verified.",
        ],
        "studio_refinements": [
            "Promote wide supporting copy from 22px to 48px, with a consistent open band above intact screens.",
            "Add a short home-page invitation; promote first/last portrait support to the same 32px as the four features.",
            "Describe the entrance explicitly as illustrated; do not imply a physical shop.",
            "Strengthen the original wordmark and portrait website address; right-align the landscape address.",
            "Rebalance wide desktop frames to 900px without changing whole-source containment or phone poses.",
            "Use 25px more height for the genuine open-notebook feature, retaining all four photos and outward tabs.",
            "Retain original light/forest rhythm, fonts, palette, restrained folios and four distinct feature treatments.",
        ],
    }
    if cream_source:
        manifest["cream_backgrounds"] = cream_source
        helper = ROOT / "scripts" / "campaign_cream.py"
        manifest["cream_backgrounds"]["compositor_helper_sha256"] = sha(helper.read_bytes())
        if frosted:
            manifest["cream_backgrounds"]["foreground_treatment"] = "One continuous 8%-tint frosted pane; no text-shaped masking."
    if portrait_colour_variance:
        manifest["portrait_background_variation"] = validate_portrait_grounds(exports)
    if not portrait_light_bands:
        manifest["portrait_background_lighting"] = validate_portrait_lighting(exports)
    if raised_phone_glass:
        manifest["raised_phone_glass"] = validate_raised_phones(exports)
        phone_helper = ROOT / "scripts" / "campaign_phone.py"
        manifest["raised_phone_glass"]["renderer_sha256"] = sha(phone_helper.read_bytes())
    handoff = {
        "status": manifest["status"], "output_root": rel(output),
        "manifest": rel(output / "manifest.json"), "proof_sheet": sheet["path"],
        "wide": [item["path"] for item in exports if item["edition"] == "wide"],
        "portrait": [item["path"] for item in exports if item["edition"] == "portrait"],
        "design": [entry["direction"] for entry in exports if entry["edition"] == "wide"],
        "layout_contract": layout_check, "draft": draft,
        "implementation": "Pure local Pillow/NumPy composition; deterministic paper/light textures, "
                          "complete intact viewport images, thin generic frames, measured copy and shadows.",
        "parent_next": "Validate supplied capture identity and outputs; install wide images, "
                       "deliver the six exact-3:4 portraits, and perform any public release separately.",
        "image_views": 0,
    }
    save_preserving_existing(output / "manifest.json", json_bytes(manifest))
    save_preserving_existing(output / "quality-review.json", json_bytes({
        "status": "actual-jpeg-raster-checks-passed; generated-not-visually-inspected",
        "checks": sum(len(entry["raster_typography"]["checks"]) for entry in exports),
        "outputs": [{key: entry[key] for key in ("filename", "edition", "sha256", "raster_typography")}
                    for entry in exports],
        "image_tool_views": 0,
    }))
    save_preserving_existing(output / "artist-handoff.json", json_bytes(handoff))
    save_preserving_existing(output / "compositor-source.py", Path(__file__).read_bytes())
    if cream_source:
        save_preserving_existing(output / "cream-compositor-source.py", helper.read_bytes())
    if raised_phone_glass:
        save_preserving_existing(output / "phone-compositor-source.py", phone_helper.read_bytes())
    print(json.dumps({
        "status": handoff["status"], "manifest": handoff["manifest"],
        "contact_sheet": sheet["path"],
        "outputs": [{"path": item["path"], "sha256": item["sha256"]} for item in exports],
        "image_views": 0,
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, default=BASE / "captures")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--draft", action="store_true",
                        help="Use old captures for clearly non-publishable geometry studies while final features are pending.")
    parser.add_argument("--portrait-colour-variance", action="store_true",
                        help="Vary only Instagram ground colours; retain cream material and README landscapes.")
    parser.add_argument("--portrait-tint-strength", type=float, default=1,
                        help="Fraction of the Instagram background tint retained; one third blends two thirds toward white.")
    parser.add_argument("--raised-phone-glass", action="store_true",
                        help="Give only the first/last Instagram phones convex glass edges and side depth.")
    parser.add_argument("--no-portrait-light-bands", action="store_true",
                        help="Remove diagonal highlight/shadow bands from Instagram backgrounds only.")
    backgrounds = parser.add_mutually_exclusive_group()
    backgrounds.add_argument("--cream-backgrounds", type=Path,
                        help="Use checked static cream layers for launch-art backgrounds only.")
    backgrounds.add_argument("--frosted-cream", type=Path,
                             help="Use Gaussian cream behind one lightly tinted frosted foreground panel.")
    args = parser.parse_args()
    create(args.captures, args.output, draft=args.draft, cream_directory=args.cream_backgrounds,
           frosted_directory=args.frosted_cream, portrait_colour_variance=args.portrait_colour_variance,
           raised_phone_glass=args.raised_phone_glass, portrait_light_bands=not args.no_portrait_light_bands,
           portrait_tint_strength=args.portrait_tint_strength)
