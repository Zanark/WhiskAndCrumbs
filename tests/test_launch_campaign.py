from io import BytesIO
from contextlib import contextmanager
import copy
from hashlib import sha256
import json
import inspect
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile

from PIL import Image, ImageChops, ImageDraw


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compose_launch_campaign import (
    DESIGN_REVISION, FINAL_REVISION, SCENES, Art, check_raster_typography, checked_feature, font, layout_contract,
    load_mark, validate_jpeg, validate_layout_contract, backdrop, validate_portrait_lighting,
)
from package_launch_campaign import image_alt, package, validate_delivery_source, validate_raster_receipt
from campaign_cream import CREAM_DESIGN_REVISION, cream_background, cream_visibility, validate_cream_receipt
from campaign_cream import FROSTED_DESIGN_REVISION, frosted_cream_background, validate_frosted_receipt
from campaign_cream import PORTRAIT_GROUNDS, portrait_palette, portrait_ground, validate_portrait_grounds
from campaign_gaussian import gaussian_recipe, validate_distinct_recipes
from campaign_phone import raised_phone_shell, validate_raised_phones
from capture_launch_views import capture


ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def scratch():
    folder = ROOT / ".local" / "studio-launch-refresh-20261009" / "test-runs" / uuid4().hex
    folder.mkdir(parents=True)
    try:
        yield folder
    finally:
        shutil.rmtree(folder)


def layout_entries():
    entries = []
    for scene in SCENES:
        for edition in ("wide", "portrait"):
            contract = layout_contract(scene["stem"], edition)
            devices = [{
                "device": name, "frame_inside_canvas": True, "all_source_corners_retained": True,
                "frame_bounds_xywh": [60, 550, 450, 320],
            } for name in contract["devices"]]
            features = [{
                "inside_canvas": True, "complete_supplied_feature_retained": True,
                "bounds_xywh": [60, 550, 800, 720], "draft_only": False,
                "important_content_verified_by_capture_owner": True,
                "source": {"feature_type": "element-capture"},
            }] if contract["features"] else []
            entries.append({
                "filename": scene["stem"] + ".jpg", "edition": edition,
                "layout": contract["layout"], "devices": devices, "features": features,
                "phone_count": contract["devices"].count("mobile"),
                "validation": {"dimensions": [1600, 1000] if edition == "wide" else [1080, 1440]},
            })
    return entries


def fixture_campaign(folder):
    entries = layout_entries()
    for index, entry in enumerate(entries):
        path = folder / entry["edition"] / entry["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", tuple(entry["validation"]["dimensions"]),
                  (90 + index * 6, 145, 120)).save(path, "JPEG", quality=95, subsampling=0)
        entry["sha256"] = sha256(path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 2, "canonical_url": "https://zanark.github.io/WhiskAndCrumbs/",
        "draft": False, "capture_manifest": {"campaign_revision": FINAL_REVISION,
                                           "note": "Unit-test fixture, not a real capture release."},
        "exports": entries, "layout_contract": validate_layout_contract(entries),
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def jpeg_bytes():
    output = BytesIO()
    Image.new("RGB", (32, 24), (245, 235, 221)).save(output, "JPEG", quality=95)
    return output.getvalue()


def with_segment(data, marker, payload):
    segment = b"\xff" + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload
    return data[:2] + segment + data[2:]


class CaptureSourceTests(unittest.TestCase):
    def test_capture_rejects_a_preview_that_does_not_match_its_declared_source(self):
        with scratch() as folder:
            source = folder / "source"
            source.mkdir()
            (source / "index.html").write_text("<main>reviewed catalogue</main>", encoding="utf-8")
            output = folder / "captures"
            with patch("capture_launch_views.urlopen", return_value=BytesIO(b"<main>stale preview</main>")):
                with self.assertRaisesRegex(ValueError, "declared generated source"):
                    capture("http://127.0.0.1:4180/", output, source)
            self.assertFalse(output.exists())

    def test_capture_requires_a_plain_loopback_base_url(self):
        with scratch() as folder:
            for url in ("https://example.com/", "http://127.0.0.1:4180/?old=1", "http://localhost:4180/#cakes"):
                with self.assertRaises(ValueError):
                    capture(url, folder / "capture")


class FrostedCreamTests(unittest.TestCase):
    def test_one_third_tint_blends_only_the_ground_two_thirds_toward_white(self):
        import numpy as np
        base = Image.new("RGBA", (80, 80), (245, 235, 221, 217))
        ImageDraw.Draw(base).rectangle((5, 5, 40, 40), fill=(230, 220, 210, 135))
        for stem in PORTRAIT_GROUNDS:
            before = np.asarray(portrait_ground(base, stem))
            after = np.asarray(portrait_ground(base, stem, 1 / 3))
            expected = np.rint(255 - (255 - before[..., :3].astype(float)) / 3).astype("uint8")
            self.assertTrue(np.array_equal(after[..., :3], expected))
            self.assertTrue(np.array_equal(after[..., 3], before[..., 3]))

    def test_lighter_palette_receipt_retains_all_six_distinct_colours(self):
        entries = layout_entries()
        for entry in entries:
            if entry["edition"] == "portrait":
                entry["background_palette"] = portrait_palette(Path(entry["filename"]).stem, 1 / 3)
        receipt = validate_portrait_grounds(entries)
        self.assertEqual(receipt["tint_strength"], 1 / 3)
        self.assertEqual(len({p["hex"] for p in receipt["grounds"].values()}), 6)
        self.assertEqual(receipt["grounds"]["01-welcome"]["hex"], "#fbf5e7")
        entries[1]["background_palette"]["tint_strength"] = .5
        with self.assertRaisesRegex(ValueError, "assigned"):
            validate_portrait_grounds(entries)

    def test_invalid_tint_strengths_fail_explicitly(self):
        for value in (0, -1, 2, float("nan"), float("inf"), True, "one third"):
            with self.assertRaises(ValueError):
                portrait_palette("01-welcome", value)

    def test_lightening_the_ground_does_not_fade_opaque_cream_or_change_glass(self):
        base = Image.new("RGBA", (200, 200), "#f5ebdd")
        layer = Image.new("RGBA", base.size, (245, 229, 211, 255))
        old, old_glass = frosted_cream_background(portrait_ground(base, "01-welcome"), layer, 1)
        new, new_glass = frosted_cream_background(portrait_ground(base, "01-welcome", 1 / 3), layer, 1)
        self.assertEqual(old.tobytes(), new.tobytes())
        self.assertEqual(old_glass, new_glass)

    def test_clean_lighting_removes_the_diagonal_rail_without_recolouring_wide_images(self):
        import numpy as np
        def rail_depth(image):
            pixels = np.asarray(image.convert("RGB"))
            height, width = pixels.shape[:2]
            values = []
            for fraction in (.4, .6, .8):
                y = round(height * fraction)
                centre = 1.02 - fraction * .2
                samples = []
                for offset in (-.025, 0, .025):
                    x = round(width * (centre + offset))
                    samples.append(float(pixels[y-3:y+4, x-3:x+4].mean()))
                values.append((samples[0] + samples[2]) / 2 - samples[1])
            return sum(values) / len(values)
        original = backdrop((540, 720), 0, False, tabletop=False)
        clean = backdrop((540, 720), 0, False, tabletop=False, light_bands=False)
        self.assertGreater(rail_depth(original), 5)
        self.assertLess(abs(rail_depth(clean)), .6)
        mark = load_mark()
        old_wide = Art(SCENES[0], "wide", 0, mark, frosted=True)
        new_wide = Art(SCENES[0], "wide", 0, mark, frosted=True, portrait_light_bands=False)
        self.assertEqual(old_wide.image.tobytes(), new_wide.image.tobytes())

    def test_clean_portrait_lighting_requires_both_bands_absent_on_all_six(self):
        entries = layout_entries()
        for entry in entries:
            if entry["edition"] == "portrait":
                entry["background_lighting"] = {"diagonal_highlight_band": False, "diagonal_shadow_band": False}
        self.assertFalse(validate_portrait_lighting(entries)["diagonal_bands"])
        entries[1]["background_lighting"]["diagonal_shadow_band"] = True
        with self.assertRaisesRegex(ValueError, "both diagonal"):
            validate_portrait_lighting(entries)

    def test_portrait_ground_tints_preserve_alpha_and_leave_inputs_unchanged(self):
        base = Image.new("RGBA", (64, 64), (245, 235, 221, 217))
        before = base.tobytes()
        colours = set()
        for stem in PORTRAIT_GROUNDS:
            result = portrait_ground(base, stem)
            colours.add(result.getpixel((30, 30))[:3])
            self.assertEqual(result.getchannel("A").tobytes(), base.getchannel("A").tobytes())
            self.assertEqual(base.tobytes(), before)
            self.assertEqual(result.tobytes(), portrait_ground(base, stem).tobytes())
        self.assertEqual(len(colours), 6)
        with self.assertRaisesRegex(ValueError, "RGBA"):
            portrait_ground(base.convert("RGB"), "01-welcome")

    def test_portrait_palette_cannot_leak_into_readme_or_repeat_a_colour(self):
        entries = layout_entries()
        for entry in entries:
            if entry["edition"] == "portrait":
                entry["background_palette"] = PORTRAIT_GROUNDS[Path(entry["filename"]).stem].copy()
        self.assertEqual(validate_portrait_grounds(entries)["scope"], "instagram-portraits-only")
        entries[0]["background_palette"] = PORTRAIT_GROUNDS["01-welcome"]
        with self.assertRaisesRegex(ValueError, "README"):
            validate_portrait_grounds(entries)
        del entries[0]["background_palette"]
        entries[3]["background_palette"] = entries[1]["background_palette"]
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_portrait_grounds(entries)

    def test_opaque_cream_is_not_recoloured_by_portrait_grounds(self):
        base = Image.new("RGBA", (200, 200), "#f5ebdd")
        material = Image.new("RGBA", base.size, (245, 229, 211, 255))
        outputs = [frosted_cream_background(portrait_ground(base, stem), material, 1)[0]
                   for stem in PORTRAIT_GROUNDS]
        self.assertTrue(all(image.tobytes() == outputs[0].tobytes() for image in outputs))

    def test_gaussian_recipes_are_deterministic_and_distinct_in_all_twelve_orientations(self):
        recipes = [gaussian_recipe(width, height, index * 2 + edition)
                   for edition, (width, height) in enumerate(((1600, 1000), (1080, 1440)))
                   for index in range(6)]
        self.assertEqual(recipes[0], gaussian_recipe(1600, 1000, 0))
        self.assertGreater(validate_distinct_recipes(recipes)["minimum_orientation_gap_radians"], .3)
        for recipe in recipes:
            self.assertEqual(len(recipe["forms"]), 17)
            self.assertEqual((recipe["cluster_count"], recipe["droplet_count"]), (4, 5))
            for group in recipe["groups"][:4]:
                main = recipe["forms"][group["members"][0]]
                protrusions = [
                    ((node["x"] - main["x"]) ** 2 + (node["y"] - main["y"]) ** 2) ** .5 + node["radius"]
                    for node in (recipe["forms"][i] for i in group["members"][1:])
                ]
                self.assertGreaterEqual(max(protrusions), main["radius"] * 1.15 - .0001)
            sizes = [node["radius"] for node in recipe["forms"]]
            self.assertGreater(max(sizes) / min(sizes), 3)

    def test_repeated_orientation_is_rejected_even_with_different_geometry_hashes(self):
        recipes = [gaussian_recipe(1080, 1440, slot) for slot in range(12)]
        recipes[1]["orientation_radians"] = recipes[0]["orientation_radians"]
        with self.assertRaisesRegex(ValueError, "orientations"):
            validate_distinct_recipes(recipes)

    def test_glass_is_continuous_and_retains_ninety_two_percent_of_the_background(self):
        self.assertEqual(set(inspect.signature(frosted_cream_background).parameters), {"base", "layer", "scale"})
        base = Image.new("RGBA", (400, 400), "#f5ebdd")
        layer = Image.new("RGBA", base.size, (205, 211, 199, 255))
        result, glass = frosted_cream_background(base, layer, 1)
        self.assertEqual(glass["panel_count"], 1)
        self.assertFalse(glass["text_shaped_masks"])
        self.assertEqual((glass["tint_opacity"], glass["background_transmission"]), (.08, .92))
        expected = [round(channel * .92 + tint * .08) for channel, tint in zip((205, 211, 199), (255, 250, 241))]
        self.assertLessEqual(max(abs(a - b) for a, b in zip(result.getpixel((200, 200))[:3], expected)), 2)

    def test_glass_really_blurs_the_underlying_material_instead_of_only_tinting_it(self):
        base = Image.new("RGBA", (400, 400), "#fffaf1")
        draw = ImageDraw.Draw(base)
        for y in range(0, 400, 8):
            for x in range(0, 400, 8):
                if (x // 8 + y // 8) % 2:
                    draw.rectangle((x, y, x + 7, y + 7), fill="#bcae96")
        result, _ = frosted_cream_background(base, Image.new("RGBA", base.size), 1)
        from PIL import ImageStat
        before = ImageStat.Stat(base.crop((100, 100, 300, 300)).convert("RGB")).stddev
        after = ImageStat.Stat(result.crop((100, 100, 300, 300)).convert("RGB")).stddev
        self.assertTrue(all(a < b * .2 for a, b in zip(after, before)))

    def test_frosted_receipt_rejects_opaque_glass_and_content_outside_the_panel(self):
        entry = {"sha256": "a" * 64, "texts": [{"bounds_xywh": [40, 40, 80, 30]}],
                 "devices": [], "features": [], "brand_ornaments": [],
                 "frosted_cream": {"jpeg_sha256": "a" * 64, "cluster_count": 4, "droplet_count": 5,
                     "source_primitive_count": 17, "foreground_on_glass": True, "visible_change_fraction": .1,
                     "left_visible_fraction": .03, "right_visible_fraction": .03, "material_contrast_retained": .9,
                     "glass": {"panel_bounds_xywh": [16, 16, 300, 400], "panel_count": 1,
                               "text_shaped_masks": False, "tint_opacity": .08, "background_transmission": .92}}}
        validate_frosted_receipt(entry)
        entry["frosted_cream"]["glass"]["tint_opacity"] = .8
        with self.assertRaisesRegex(ValueError, "frosted-glass"):
            validate_frosted_receipt(entry)
        entry["frosted_cream"]["glass"]["tint_opacity"] = .08
        entry["texts"][0]["bounds_xywh"][0] = 0
        with self.assertRaisesRegex(ValueError, "leaves"):
            validate_frosted_receipt(entry)

    def test_frosted_design_cannot_bypass_actual_jpeg_readability(self):
        with scratch() as folder:
            manifest = fixture_campaign(folder)
            manifest["design_revision"] = FROSTED_DESIGN_REVISION
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raster review"):
                validate_delivery_source(folder)

    def test_frosted_alt_text_describes_glass_and_unique_clustered_cream(self):
        alt = image_alt("02-bakery-entrance.jpg", "portrait", frosted_glass=True)
        self.assertIn("lightly frosted glass", alt)
        self.assertIn("unique arrangement", alt)
        self.assertIn("small droplets", alt)


class CreamBackgroundTests(unittest.TestCase):
    def test_cream_keeps_copy_background_exact_and_does_not_mutate_inputs(self):
        base = Image.new("RGBA", (400, 300), "#34483a")
        layer = Image.new("RGBA", base.size)
        ImageDraw.Draw(layer).ellipse((0, 0, 380, 290), fill="#fffaf1")
        before_base, before_layer = base.tobytes(), layer.tobytes()
        result = cream_background(base, layer, [{"bounds_xywh": [100, 80, 160, 70]}], 1)
        self.assertIsNone(ImageChops.difference(base, result).crop((100, 80, 260, 150)).convert("RGB").getbbox())
        self.assertNotEqual(result.getpixel((50, 230)), base.getpixel((50, 230)))
        self.assertEqual(base.tobytes(), before_base)
        self.assertEqual(layer.tobytes(), before_layer)

    def test_effect_hidden_by_foreground_or_visible_on_only_one_side_is_rejected(self):
        before = Image.new("RGB", (300, 200), "#34483a")
        with self.assertRaisesRegex(ValueError, "not sufficiently visible"):
            cream_visibility(before, before.copy(), {"sha256": "a" * 64})
        after = before.copy()
        ImageDraw.Draw(after).rectangle((0, 0, 80, 199), fill="#fffaf1")
        with self.assertRaisesRegex(ValueError, "not sufficiently visible"):
            cream_visibility(before, after, {"sha256": "a" * 64})

    def test_cream_receipt_is_bound_to_the_final_jpeg(self):
        entry = {"sha256": "b" * 64, "cream_background": {
            "kind": "original-webgl-cream", "jpeg_sha256": "b" * 64, "layer_sha256": "a" * 64,
            "separate_material_forms": 6, "text_regions_unchanged": True, "background_only": True,
            "static_not_animation": True, "visible_change_fraction": .1,
            "left_visible_fraction": .03, "right_visible_fraction": .03,
        }}
        validate_cream_receipt(entry)
        entry["cream_background"]["jpeg_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "mismatched"):
            validate_cream_receipt(entry)

    def test_cream_design_cannot_bypass_existing_jpeg_typography_proofs(self):
        with scratch() as folder:
            manifest = fixture_campaign(folder)
            manifest["design_revision"] = CREAM_DESIGN_REVISION
            manifest["cream_backgrounds"] = {"manifest_sha256": "a" * 64}
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raster review"):
                validate_delivery_source(folder)

    def test_cream_alt_text_distinguishes_artwork_from_website_changes(self):
        description = image_alt("02-bakery-entrance.jpg", "portrait", cream_background=True)
        self.assertIn("cream blobs", description)
        self.assertIn("website capture is unchanged", description)
        self.assertIn("without browser or phone", description)
        self.assertNotIn("cream blobs", image_alt("02-bakery-entrance.jpg", "portrait"))


class LaunchMetadataTests(unittest.TestCase):
    def test_plain_rgb_export_has_only_standard_jfif_metadata(self):
        result = validate_jpeg(jpeg_bytes(), (32, 24))
        self.assertEqual(result["metadata_segments"], ["APP0"])

    def test_valid_nontext_jpeg_data_is_not_scanned_as_private_text(self):
        data = bytearray(jpeg_bytes())
        table = data.index(b"\xff\xdb")
        # Positive, legal quantization coefficients can coincidentally spell a drive prefix.
        data[table + 5:table + 8] = b"C:\\"
        self.assertIn(b"C:\\", data)
        self.assertEqual(validate_jpeg(bytes(data), (32, 24))["format"], "JPEG")

    def test_comment_metadata_is_rejected(self):
        data = with_segment(jpeg_bytes(), 0xFE, b"C:\\private\\capture.png")
        with self.assertRaisesRegex(ValueError, "metadata"):
            validate_jpeg(data, (32, 24))

    def test_unknown_application_metadata_is_rejected(self):
        data = with_segment(jpeg_bytes(), 0xE3, b".local capture provenance")
        with self.assertRaisesRegex(ValueError, "metadata"):
            validate_jpeg(data, (32, 24))


class EditorialLayoutTests(unittest.TestCase):
    def test_raised_phone_receipt_rejects_altered_viewports_and_readme_changes(self):
        entries = layout_entries()
        _, proof = raised_phone_shell((100, 240), 1)
        proof["unaltered_screen_raster"] = True
        for entry in entries:
            for device in entry["devices"]:
                if entry["edition"] == "portrait" and device["device"] == "mobile":
                    device["raised_glass"] = proof.copy()
        self.assertEqual(validate_raised_phones(entries)["phones"], 2)
        entries[1]["devices"][1]["raised_glass"]["screen_overlay"] = True
        with self.assertRaisesRegex(ValueError, "unaltered"):
            validate_raised_phones(entries)
        entries[1]["devices"][1]["raised_glass"]["screen_overlay"] = False
        entries[0]["devices"][1]["raised_glass"] = proof
        with self.assertRaisesRegex(ValueError, "README"):
            validate_raised_phones(entries)

    def test_raised_glass_has_a_rounded_silhouette_directional_ridge_and_side_depth(self):
        import numpy as np
        frame, proof = raised_phone_shell((550, 1170), 2)
        self.assertEqual(frame.getpixel((0, 0))[3], 0)
        self.assertEqual(proof["glass_roll_width_px"], 7)
        self.assertEqual(proof["body_depth_offset_px"], [3, 4])
        pixels = np.asarray(frame)
        left = pixels[585, 7:28, :3].mean(axis=1)
        right = pixels[585, -28:-7, :3].mean(axis=1)
        self.assertGreater(float(left.max() - left.min()), 40)
        self.assertGreater(float(left.max() - right.max()), 15)
        self.assertEqual(frame.tobytes(), raised_phone_shell((550, 1170), 2)[0].tobytes())

    def test_raised_phone_retains_every_resized_screen_pixel_and_remains_portrait_only(self):
        image = Image.new("RGBA", (780, 1688), "#cf8297")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 779, 1687), outline="#34ae81", width=3)
        for edition in ("wide", "portrait"):
            art = Art(SCENES[0], edition, 0, load_mark(), frosted=True, raised_phone_glass=True)
            art.device(image, "mobile", {"fixture": True}, SCENES[0][edition]["mobile"])
            record = art.devices[0]
            self.assertTrue(record["all_source_corners_retained"])
            self.assertEqual("raised_glass" in record, edition == "portrait")
            if edition == "portrait":
                self.assertTrue(record["raised_glass"]["unaltered_screen_raster"])
                self.assertFalse(record["raised_glass"]["screen_overlay"])
                self.assertEqual(record["screen_dimensions"][0], 247)

    def test_only_first_and_last_portraits_have_phones(self):
        result = validate_layout_contract(layout_entries())
        self.assertEqual(result["phone_counts"], {"wide": 6, "portrait": 2})
        self.assertEqual({stem for stem, count in result["portrait_phones_by_stem"].items() if count},
                         {"01-welcome", "06-simple-ordering"})

    def test_middle_portraits_have_four_distinct_feature_directions(self):
        contracts = [layout_contract(scene["stem"], "portrait") for scene in SCENES[1:5]]
        self.assertEqual(len({item["layout"] for item in contracts}), 4)
        self.assertTrue(all(item["features"] == 1 and not item["devices"] for item in contracts))

    def test_middle_portrait_rejects_reintroduced_phone(self):
        entries = layout_entries()
        entry = entries[3]
        entry["devices"].append(copy.deepcopy(entries[1]["devices"][1]))
        with self.assertRaisesRegex(ValueError, "layout"):
            validate_layout_contract(entries)

    def test_wide_still_requires_both_genuine_devices(self):
        entries = layout_entries()
        entries[0]["devices"].pop()
        with self.assertRaisesRegex(ValueError, "layout"):
            validate_layout_contract(entries)

    def test_device_less_does_not_mean_media_or_bounds_checks_are_optional(self):
        entries = layout_entries()
        entries[5]["features"] = []
        with self.assertRaises(ValueError):
            validate_layout_contract(entries)
        entries = layout_entries()
        entries[5]["features"][0]["bounds_xywh"] = [950, 550, 800, 720]
        with self.assertRaisesRegex(ValueError, "safe area"):
            validate_layout_contract(entries)

    def test_portrait_four_by_five_is_not_accepted(self):
        entries = layout_entries()
        entries[1]["validation"]["dimensions"] = [1080, 1350]
        with self.assertRaisesRegex(ValueError, "dimensions"):
            validate_layout_contract(entries)

    def test_phone_count_receipt_cannot_disagree_with_devices(self):
        entries = layout_entries()
        entries[3]["phone_count"] = 1
        with self.assertRaisesRegex(ValueError, "phone count"):
            validate_layout_contract(entries)

    def test_middle_editorial_copy_is_readable_at_540px(self):
        for index in range(1, 5):
            art = Art(SCENES[index], "portrait", index, load_mark())
            art.identity()
            art.heading()
            art.footer()
            body = [item for item in art.texts if item["role"] == "editorial-body"]
            self.assertTrue(body)
            self.assertTrue(all(item["estimated_font_px_at_540px_width"] >= 16 for item in body))
            self.assertTrue(all(item["minimum_backdrop_contrast"] >= 4.5 for item in body))

    def test_all_twelve_editions_have_16px_supporting_copy_at_540px(self):
        for index, scene in enumerate(SCENES):
            for edition in ("wide", "portrait"):
                art = Art(scene, edition, index, load_mark())
                art.identity()
                art.heading()
                art.footer()
                body = [item for item in art.texts if item["role"] == "editorial-body"]
                self.assertTrue(body, (scene["stem"], edition))
                self.assertTrue(all(item["estimated_font_px_at_540px_width"] >= 16 for item in body))
                if edition == "portrait":
                    address = next(item for item in art.texts if item["role"] == "website-url")
                    self.assertEqual(address["estimated_font_px_at_540px_width"], 16)


class ActualRasterTypographyTests(unittest.TestCase):
    def fixture(self, missing_ink=False):
        size = (720, 400)
        background = Image.new("RGB", (1440, 800), "#f5ebdd")
        image = background.copy()
        draw = ImageDraw.Draw(image)
        selected = font(40)
        text = "A real website."
        box = draw.textbbox((0, 0), text, font=selected)
        if not missing_ink:
            draw.text((80 - box[0], 100 - box[1]), text, font=selected, fill="#34483a")
        output = BytesIO()
        image.resize(size, Image.Resampling.LANCZOS).save(output, "JPEG", quality=95, subsampling=0)
        record = {"text": text, "role": "editorial-body", "font_size_px": 40,
                  "font": "dm-sans-regular.ttf", "bounds_xywh": [40, 50, (box[2] - box[0]) / 2, (box[3] - box[1]) / 2]}
        return output.getvalue(), size, background, [record]

    def test_actual_jpeg_ink_passes_at_native_and_540px(self):
        args = self.fixture()
        result = check_raster_typography(*args)
        self.assertEqual(result["jpeg_sha256"], sha256(args[0]).hexdigest())
        self.assertEqual(result["tested_widths"], [720, 540])
        self.assertEqual(len(result["checks"]), 2)
        self.assertTrue(all(check["fifth_percentile_contrast"] >= 4.5 for check in result["checks"]))

    def test_declared_text_without_actual_jpeg_ink_fails(self):
        with self.assertRaisesRegex(ValueError, "Actual JPEG glyph contrast"):
            check_raster_typography(*self.fixture(missing_ink=True))

    def test_tiny_540px_support_cannot_pass_using_native_size_only(self):
        args = self.fixture()
        args[3][0]["font_size_px"] = 10
        with self.assertRaisesRegex(ValueError, "16px"):
            check_raster_typography(*args)

    def test_packager_rejects_mismatched_or_partial_raster_receipt(self):
        args = self.fixture()
        proof = check_raster_typography(*args)
        entry = {"sha256": sha256(args[0]).hexdigest(), "validation": {"dimensions": list(args[1])},
                 "texts": args[3], "raster_typography": proof}
        validate_raster_receipt(entry)
        entry["raster_typography"]["jpeg_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "mismatched"):
            validate_raster_receipt(entry)
        entry["raster_typography"] = copy.deepcopy(proof)
        entry["raster_typography"]["jpeg_sha256"] = entry["sha256"]
        entry["raster_typography"]["checks"].pop()
        with self.assertRaisesRegex(ValueError, "every critical"):
            validate_raster_receipt(entry)

    def test_studio_manifest_without_actual_raster_proof_cannot_be_packaged(self):
        with scratch() as folder:
            manifest = fixture_campaign(folder)
            manifest["design_revision"] = DESIGN_REVISION
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raster review"):
                validate_delivery_source(folder)


class FeatureProvenanceTests(unittest.TestCase):
    def feature_record(self, folder):
        path = folder / "feature.png"
        Image.new("RGB", (400, 300), (245, 235, 221)).save(path, "PNG")
        return {
            "id": "03-story-note", "file": path.name, "sha256": sha256(path.read_bytes()).hexdigest(),
            "raster_pixels": [400, 300], "dpr": 2, "feature_type": "element-capture",
            "source_url": "http://127.0.0.1:4173/#story", "selector": ".recipe-note",
            "crop_css_pixels": {"x": 20, "y": 300, "width": 200, "height": 150},
            "important_bounds": [{"label": "whole note", "x": 10, "y": 10, "width": 180, "height": 130}],
            "all_important_content_inside": True, "browser_errors": [],
        }

    def test_real_feature_keeps_crop_and_hash_provenance(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            image, provenance = checked_feature(record, folder)
            self.assertEqual(image.size, (400, 300))
            self.assertEqual(provenance["source_crop"], record["crop_css_pixels"])
            self.assertEqual(provenance["sha256"], record["sha256"])

    def test_feature_rejects_clipped_important_content_even_with_true_flag(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["important_bounds"][0]["width"] = 250
            with self.assertRaisesRegex(ValueError, "clips important"):
                checked_feature(record, folder)

    def test_feature_rejects_changed_bytes(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "recorded hash"):
                checked_feature(record, folder)

    def test_feature_rejects_false_dpr_or_missing_bounds(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["crop_css_pixels"]["width"] = 190
            with self.assertRaisesRegex(ValueError, "DPR2 crop"):
                checked_feature(record, folder)
            record = self.feature_record(folder)
            record["important_bounds"] = []
            with self.assertRaisesRegex(ValueError, "important-content bounds"):
                checked_feature(record, folder)

    def test_parent_component_schema_and_feature_subfolder_are_supported(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            child = folder / "features"
            child.mkdir()
            (folder / record["file"]).rename(child / "feature.png")
            record["id"] = "03-our-story"
            record["file"] = str(Path("features") / "feature.png")
            record["bounds_css"] = record.pop("crop_css_pixels")
            record.pop("feature_type")
            record["capture"] = "Complete actual component bounds; no DOM/style changes"
            image, provenance = checked_feature(record, folder)
            self.assertEqual(image.size, (400, 300))
            self.assertEqual(provenance["source_crop"], record["bounds_css"])
            self.assertEqual(provenance["feature_type"], "element-capture")

    def test_conflicting_parent_capture_bounds_are_rejected(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["bounds_css"] = {**record["crop_css_pixels"], "width": 150}
            with self.assertRaisesRegex(ValueError, "conflicting"):
                checked_feature(record, folder)

    def test_fixed_parent_contract_with_period_needs_no_invented_child_bounds(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["bounds_css"] = record.pop("crop_css_pixels")
            record["capture"] = "Complete actual component bounds; no DOM/style changes."
            for key in ("important_bounds", "all_important_content_inside", "feature_type"):
                record.pop(key)
            _, provenance = checked_feature(record, folder)
            self.assertEqual(provenance["important_bounds"], [])
            self.assertFalse(provenance["independent_descendant_bounds_checked"])
            self.assertIn("Parent's complete-component", provenance["content_completeness_evidence"])
            self.assertEqual(provenance["source_crop"], record["bounds_css"])

    def test_parent_declaration_does_not_override_explicit_clipping_failure(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["bounds_css"] = record.pop("crop_css_pixels")
            record["capture"] = "Complete actual component bounds; no DOM/style changes."
            record["all_important_content_inside"] = False
            with self.assertRaisesRegex(ValueError, "unresolved clipping"):
                checked_feature(record, folder)

    def test_full_page_component_union_crop_keeps_honest_page_crop_provenance(self):
        with scratch() as folder:
            record = self.feature_record(folder)
            record["bounds_css"] = {**record.pop("crop_css_pixels"), "y": 2200}
            record["capture"] = (
                "Complete actual component including decoration and shadows; "
                "bounded crop from full-page capture, no DOM/style changes."
            )
            for key in ("important_bounds", "all_important_content_inside", "feature_type"):
                record.pop(key)
            _, provenance = checked_feature(record, folder)
            self.assertEqual(provenance["capture_method"], "bounded-component-crop-from-full-page")
            self.assertEqual(provenance["source_crop"]["y"], 2200)
            self.assertFalse(provenance["whole_viewport_claimed"])
            self.assertEqual(provenance["capture_declaration"], record["capture"])


class EditorialPackageTests(unittest.TestCase):
    def test_middle_portrait_alt_text_does_not_claim_phone_views(self):
        self.assertIn("genuine website feature", image_alt("02-bakery-entrance.jpg", "portrait").lower())
        for name in ("03-our-story.jpg", "04-cake-notebooks.jpg", "05-open-notebook.jpg"):
            self.assertNotIn("desktop and mobile", image_alt(name, "portrait").lower())
            self.assertIn("desktop and mobile", image_alt(name, "wide").lower())

    def test_draft_and_stale_manifests_cannot_be_packaged(self):
        with scratch() as folder:
            manifest = fixture_campaign(folder)
            for draft, revision in ((True, FINAL_REVISION), (False, "old-captures")):
                manifest["draft"] = draft
                manifest["capture_manifest"]["campaign_revision"] = revision
                (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "draft or stale"):
                    validate_delivery_source(folder)

    def test_package_zip_has_only_six_portraits_and_mixed_layout_descriptions(self):
        with scratch() as folder:
            source, output = folder / "source", folder / "delivery"
            source.mkdir()
            fixture_campaign(source)
            package(source, output)
            with zipfile.ZipFile(output / "Whisk-and-Crumbs-Instagram-3x4.zip") as archive:
                self.assertEqual(set(archive.namelist()), {scene["stem"] + ".jpg" for scene in SCENES})
                self.assertEqual(len(archive.namelist()), 6)
            preview = (output / "preview.html").read_text(encoding="utf-8")
            self.assertIn("middle four", preview)
            self.assertIn("without phone mockups", preview)
            packaged = json.loads((output / "manifest.json").read_text())
            self.assertEqual(packaged["layout_contract"]["phone_counts"], {"wide": 6, "portrait": 2})

    def test_packager_reuses_strict_jpeg_segment_validation(self):
        with scratch() as folder:
            source = folder / "source"
            source.mkdir()
            manifest = fixture_campaign(source)
            entry = manifest["exports"][0]
            path = source / entry["edition"] / entry["filename"]
            path.write_bytes(with_segment(path.read_bytes(), 0xE3, b"private receipt"))
            entry["sha256"] = sha256(path.read_bytes()).hexdigest()
            (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "metadata"):
                package(source, folder / "delivery")


if __name__ == "__main__":
    unittest.main()
