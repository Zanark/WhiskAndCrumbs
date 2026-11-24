import hashlib
import json
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_cake_stickers import sticker


class StickerTests(unittest.TestCase):
    def test_source_colours_and_input_remain_unchanged(self):
        source = Image.new("RGB", (100, 120), (34, 84, 41))
        mask = Image.new("L", source.size)
        ImageDraw.Draw(mask).rectangle((30, 20, 80, 100), fill=255)
        source_before, mask_before = source.tobytes(), mask.tobytes()
        result, bounds, padding, outline = sticker(source, mask)
        self.assertEqual(bounds, (30, 20, 81, 101))
        self.assertEqual(result.getpixel((padding + 20, padding + 40)), (34, 84, 41, 255))
        self.assertEqual(result.getpixel((padding - outline // 2, padding + 40)), (255, 255, 255, 255))
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(source.tobytes(), source_before)
        self.assertEqual(mask.tobytes(), mask_before)

    def test_empty_mismatched_and_nearly_transparent_masks_are_rejected(self):
        source = Image.new("RGB", (100, 120))
        for mask in [Image.new("L", (10, 10)), Image.new("L", source.size), Image.new("L", source.size, 5)]:
            with self.subTest(size=mask.size, extrema=mask.getextrema()), self.assertRaises(ValueError):
                sticker(source, mask)

    def test_real_stickers_have_alpha_padding_matching_hashes_and_no_upscaling(self):
        folder = ROOT / "assets" / "images" / "cake-stickers"
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["photos"]), 148)
        for photo in manifest["photos"]:
            bounds, padding = photo["masked_bounds"], photo["padding"]
            width = bounds[2] - bounds[0] + padding * 2
            height = bounds[3] - bounds[1] + padding * 2
            with Image.open(folder / "masks" / f"{photo['id']}.png") as mask:
                self.assertEqual(mask.size, tuple(photo["source_dimensions"]))
            for variant in photo["variants"]:
                file = folder / variant["file"]
                with self.subTest(file=file.name):
                    self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), variant["sha256"])
                    with Image.open(file) as image:
                        self.assertFalse(image.getexif())
                        self.assertFalse(image.info.get("xmp"))
                        self.assertEqual(image.mode, "RGBA")
                        self.assertEqual(image.size, (variant["width"], variant["height"]))
                        self.assertLessEqual(image.width, width)
                        self.assertLessEqual(image.height, height)
                        self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
                        alpha_bounds = image.getchannel("A").getbbox()
                        self.assertGreater(alpha_bounds[0], 0)
                        self.assertGreater(alpha_bounds[1], 0)
                        self.assertLess(alpha_bounds[2], image.width)
                        self.assertLess(alpha_bounds[3], image.height)

    def test_reviewed_masks_preserve_the_cake_and_dark_feather_eye(self):
        points = {
            "peacock-feather-cake": (365, 108),
            "ribbon-and-pearl-cake": (500, 350),
            "cherry-topped-cake": (540, 330),
            "pink-doll-cake": (420, 285),
            "butterfly-celebration-cake": (520, 65),
        }
        for slug, point in points.items():
            with self.subTest(cake=slug), Image.open(ROOT / "assets" / "images" / "cake-stickers" / "masks" / f"{slug}.png") as mask:
                self.assertGreater(mask.getpixel(point), 244)
                self.assertEqual(mask.getpixel((10, 10)), 0)

    def test_local_originals_and_all_opaque_source_pixels_are_preserved(self):
        private = ROOT / ".local" / "photos" / "prototype-20261004"
        if not private.exists():
            self.skipTest("Private source photos are not part of the public repository.")
        folder = ROOT / "assets" / "images" / "cake-stickers"
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        originals = json.loads((ROOT / "assets" / "images" / "cakes" / "manifest.json").read_text(encoding="utf-8"))
        for photo in manifest["photos"]:
            original = next(item for item in originals["photos"] if item["id"] == photo["id"])
            photo_private = ROOT / original["private_directory"] if original.get("private_directory") else private
            source_file = photo_private / "crops" / f"{photo['id']}.png"
            with self.subTest(cake=photo["id"]):
                self.assertEqual(hashlib.sha256(source_file.read_bytes()).hexdigest(), photo["source_crop_sha256"])
                original_file = photo_private / "originals" / original["source_file"]
                if original_file.exists():
                    self.assertEqual(
                        hashlib.sha256(original_file.read_bytes()).hexdigest(),
                        original["source_sha256"],
                    )
                with Image.open(source_file) as source, Image.open(folder / "masks" / f"{photo['id']}.png") as mask:
                    rendered, bounds, padding, _ = sticker(source, mask)
                    original_crop = source.crop(bounds).convert("RGB")
                    rendered_crop = rendered.crop((padding, padding, padding + original_crop.width, padding + original_crop.height)).convert("RGB")
                    difference = ImageChops.difference(original_crop, rendered_crop)
                    opaque = mask.crop(bounds).point(lambda value: 255 if value > 244 else 0)
                    retained_difference = Image.composite(difference, Image.new("RGB", difference.size), opaque)
                    self.assertIsNone(retained_difference.getbbox())

    def test_export_photos_match_reviewed_source_associations(self):
        expected = {
            "rainbow-butterfly-cake": "18044905895803258.jpg",
            "purple-birthday-cake": "18111742513623390.jpg",
            "golden-drip-cake": "17869361955513158.jpg",
            "cherry-curl-cake": "17855219376447920.jpg",
            "pink-swirl-cake": "17902994580257952.jpg",
            "rose-topped-cake": "17918554095254701.jpg",
            "lavender-swirl-cake": "17967840659940950.jpg",
            "pastel-celebration-cake": "18077297165641061.jpg",
            "round-and-heart-tea-cakes": "18069978263206386.jpg",
            "assorted-moulded-chocolates": "17952408272859389.jpg",
        }
        folder = ROOT / "assets" / "images" / "cakes"
        photos = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["photos"]
        exported = [photo for photo in photos if photo["id"] in expected]
        self.assertEqual(len(exported), 10)
        self.assertEqual(len({photo["source_sha256"] for photo in exported}), 10)
        for photo in exported:
            self.assertEqual(Path(photo["export_file"]).name, expected[photo["id"]])
            for variant in photo["variants"]:
                file = folder / variant["file"]
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), variant["sha256"])
                with Image.open(file) as image:
                    self.assertFalse(image.getexif())
                    self.assertFalse(image.info.get("xmp"))
                    self.assertEqual(image.size, (variant["width"], variant["height"]))
                    self.assertLessEqual(image.width, photo["crop_left_top_right_bottom"][2] - photo["crop_left_top_right_bottom"][0])

    def test_new_mask_correction_removes_only_the_recorded_background(self):
        folder = ROOT / "assets" / "images" / "cake-stickers"
        with Image.open(folder / "masks" / "lavender-swirl-cake.png") as mask:
            self.assertEqual(mask.getpixel((800, 440)), 0)
            self.assertGreater(mask.getpixel((600, 430)), 244)
        review = json.loads((folder / "masks" / "notebook-review.json").read_text(encoding="utf-8"))
        self.assertEqual(len(review["photos"]), 7)
        for photo in review["photos"]:
            file = folder / "masks" / f"{photo['id']}.png"
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), photo["reviewed_mask_sha256"])

    def test_owner_cover_extension_preserves_every_previous_record_and_variant(self):
        snapshot = ROOT / ".local" / "stickers" / "owner-covers-20261005" / "before-local-preview"
        if not snapshot.exists():
            self.skipTest("Private pre-extension evidence is not part of the public repository.")
        for kind in ("cakes", "cake-stickers"):
            relative = Path("assets") / "images" / kind
            old = json.loads((snapshot / relative / "manifest.json").read_text(encoding="utf-8"))["photos"]
            current = json.loads((ROOT / relative / "manifest.json").read_text(encoding="utf-8"))["photos"]
            self.assertEqual(len(old), 12)
            for previous in old:
                self.assertEqual(next(photo for photo in current if photo["id"] == previous["id"]), previous)
                for variant in previous["variants"]:
                    self.assertEqual(hashlib.sha256((ROOT / relative / variant["file"]).read_bytes()).hexdigest(),
                                     variant["sha256"])

    def test_owner_covers_keep_both_tea_cakes_topper_and_neutral_chocolates(self):
        folder = ROOT / "assets" / "images" / "cake-stickers" / "masks"
        with Image.open(folder / "assorted-moulded-chocolates.png") as mask:
            for point in ((161, 86), (150, 231), (97, 410), (62, 238), (254, 355),
                          (163, 145), (190, 175), (175, 200)):
                self.assertGreater(mask.getpixel(point), 244)
        with Image.open(folder / "round-and-heart-tea-cakes.png") as mask:
            self.assertGreater(mask.getpixel((280, 620)), 244)
            self.assertGreater(mask.getpixel((690, 600)), 244)
            self.assertEqual(mask.getpixel((100, 100)), 0)
        with Image.open(folder / "pastel-celebration-cake.png") as mask:
            self.assertGreater(mask.getpixel((580, 290)), 244)
            self.assertGreater(mask.getpixel((620, 650)), 244)


if __name__ == "__main__":
    unittest.main()
