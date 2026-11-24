import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "social" / "instagram"


class InstagramAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))

    def test_exact_dimensions_formats_and_hashes(self):
        expected = {
            "whisk-and-crumbs-profile-square-1080.png": (1080, 1080),
            "whisk-and-crumbs-profile-circle-1080.png": (1080, 1080),
            "whisk-and-crumbs-portrait-1080x1440.png": (1080, 1440),
        }
        self.assertEqual(self.manifest["name"], "Whisk & Crumbs")
        self.assertEqual({record["file"] for record in self.manifest["files"]}, set(expected))
        for record in self.manifest["files"]:
            path = ASSETS / record["file"]
            with self.subTest(file=path.name), Image.open(path) as image:
                self.assertEqual(image.size, expected[path.name])
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.format, "PNG")
                self.assertFalse(image.getexif())
                self.assertFalse(image.info.get("xmp"))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])
                self.assertEqual(path.stat().st_size, record["bytes"])

    def test_all_square_artwork_is_well_inside_the_circular_crop(self):
        with Image.open(ASSETS / "whisk-and-crumbs-profile-square-1080.png") as square:
            ink = ImageChops.difference(square, Image.new("RGB", square.size, "#f5ebdd")).convert("L")
            ink = ink.point(lambda value: 255 if value > 2 else 0)
            safe = Image.new("L", square.size)
            ImageDraw.Draw(safe).ellipse((100, 100, 980, 980), fill=255)
            self.assertIsNone(ImageChops.multiply(ink, ImageOps.invert(safe)).getbbox())
        self.assertLessEqual(self.manifest["essential_artwork_radius_px"], 440)
        self.assertGreaterEqual(self.manifest["minimum_clearance_to_crop_px"], 100)

    def test_circle_touches_all_four_edges_without_changing_inner_artwork(self):
        circle = self.manifest["square_circle_geometry"]
        self.assertEqual(circle["centre"], [540, 540])
        self.assertEqual(circle["radius"], 540)
        self.assertEqual(set(circle["touches"]), {"top", "right", "bottom", "left"})
        with Image.open(ASSETS / "whisk-and-crumbs-profile-square-1080.png") as square, \
                Image.open(ASSETS / "whisk-and-crumbs-profile-circle-1080.png") as framed:
            for point in [(540, 0), (1079, 540), (540, 1079), (0, 540)]:
                with self.subTest(edge=point):
                    self.assertLessEqual(max(abs(a - b) for a, b in
                                             zip(framed.getpixel(point), ImageColor.getrgb("#34483a"))), 3)
            inner = Image.new("L", framed.size)
            ImageDraw.Draw(inner).ellipse((40, 40, 1040, 1040), fill=255)
            difference = ImageChops.difference(square, framed).convert("L")
            self.assertIsNone(ImageChops.multiply(difference, inner).getbbox())
            self.assertIsNotNone(difference.getbbox())

    def test_portrait_extends_the_composition_without_stretching_or_circle(self):
        self.assertFalse(self.manifest["portrait_has_circular_frame"])
        with Image.open(ASSETS / "whisk-and-crumbs-profile-square-1080.png") as square, \
                Image.open(ASSETS / "whisk-and-crumbs-portrait-1080x1440.png") as portrait:
            self.assertEqual(portrait.width * 4, portrait.height * 3)
            self.assertIsNone(ImageChops.difference(square.crop((0, 0, 1080, 1020)),
                                                   portrait.crop((0, 135, 1080, 1155))).getbbox())
            for box in [(0, 0, 1080, 20), (0, 1420, 1080, 1440),
                        (0, 0, 20, 1440), (1060, 0, 1080, 1440)]:
                edge = portrait.crop(box)
                self.assertIsNone(ImageChops.difference(edge, Image.new("RGB", edge.size, "#f5ebdd")).getbbox())


if __name__ == "__main__":
    unittest.main()
