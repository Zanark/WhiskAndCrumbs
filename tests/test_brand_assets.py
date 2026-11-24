import hashlib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "web" / "assets"
SVG = "{http://www.w3.org/2000/svg}"


class BrandAssetsTests(unittest.TestCase):
    def test_original_shop_art_is_layered_and_has_no_embedded_external_content(self):
        viewboxes = {
            "bakery-awning.svg": "0 0 1200 300",
            "bakery-awning-supports.svg": "0 0 1200 300",
            "bakery-shelf.svg": "0 0 960 120",
        }
        hashes = set()
        for name, viewbox in viewboxes.items():
            path = ASSETS / name
            with self.subTest(file=name):
                tree = ET.parse(path).getroot()
                self.assertEqual(tree.tag, SVG + "svg")
                self.assertEqual(tree.attrib["viewBox"], viewbox)
                self.assertFalse(any(node.tag in {
                    SVG + "script", SVG + "foreignObject", SVG + "image", SVG + "text",
                    SVG + "animate", SVG + "animateTransform", SVG + "set",
                } for node in tree.iter()))
                ids = [node.attrib["id"] for node in tree.iter() if "id" in node.attrib]
                self.assertEqual(len(ids), len(set(ids)), "SVG IDs must be unique within each layer.")
                for node in tree.iter():
                    for attribute, value in node.attrib.items():
                        self.assertFalse(attribute.lower().startswith("on"))
                        if attribute.endswith("href"):
                            self.assertTrue(value.startswith("#"), value)
                            self.assertIn(value[1:], ids)
                        for reference in re.findall(r"url\(#([^)]+)\)", value):
                            self.assertIn(reference, ids)
                self.assertLess(path.stat().st_size, 90_000)
                hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(len(hashes), 3)

    def test_awning_has_full_width_fabric_and_separate_hanging_valance(self):
        tree = ET.parse(ASSETS / "bakery-awning.svg").getroot()
        self.assertEqual(tree.attrib["preserveAspectRatio"], "none")
        for feature in ("awning-sloped-fabric", "awning-hanging-valance", "awning-front-bar", "awning-wall-rail"):
            self.assertIsNotNone(tree.find(f".//{SVG}g[@id='{feature}']"))
        front = tree.find(f".//{SVG}g[@id='awning-front-bar']/{SVG}rect")
        self.assertEqual(front.get("x", "0"), "0")
        self.assertEqual(front.attrib["width"], "1200")
        valance = tree.find(f".//{SVG}mask[@id='awning-valance-mask']")
        self.assertEqual(valance.attrib["height"], "108")
        self.assertEqual(front.attrib["y"], "182")
        slope = tree.find(f".//{SVG}g[@id='awning-sloped-fabric']")
        self.assertEqual(slope.attrib["data-stripe-count"], "40")
        self.assertIsNotNone(slope.find(f"{SVG}g[@fill='#ce7183']"))
        slope_clip = tree.find(f".//{SVG}clipPath[@id='awning-slope-clip']/{SVG}rect")
        self.assertIsNotNone(slope_clip)
        self.assertEqual(slope_clip.get("x", "0"), "0")
        self.assertEqual(slope_clip.attrib, {"y": "13", "width": "1200", "height": "171"})
        last_rose = slope.findall(f"{SVG}g[@fill='#ce7183']/{SVG}path")[-1]
        self.assertIn("H1200L1200 112.84Q1200 160 1200 184", last_rose.attrib["d"])
        stripes = tree.find(f".//{SVG}pattern[@id='awning-stripes']")
        stripe_widths = [float(node.attrib["width"]) for node in stripes.findall(SVG+"rect")]
        panels = tree.find(f".//{SVG}pattern[@id='awning-hanging-panels']")
        stitches = tree.find(f".//{SVG}pattern[@id='awning-hem-stitch']")
        self.assertEqual(stripe_widths, [30, 30])
        self.assertEqual(float(stripes.attrib["width"]), sum(stripe_widths))
        self.assertEqual(float(panels.attrib["width"]), stripe_widths[0])
        self.assertEqual(float(stitches.attrib["width"]), stripe_widths[0])
        hanging = tree.find(f".//{SVG}g[@id='awning-hanging-valance']")
        self.assertEqual(int(hanging.attrib["data-scallop-count"]), 1200 / stripe_widths[0])
        self.assertEqual(float(hanging.attrib["data-curve-depth"]), stripe_widths[0] / 2)
        self.assertEqual(float(hanging.attrib["data-straight-depth"]), 91)
        self.assertEqual(panels.find(SVG+"path").attrib["d"], "M0 188H30V279A15 15 0 0 1 0 279Z")
        self.assertIn("M4 279A11 11 0 0 0 26 279", stitches.findall(SVG+"path")[1].attrib["d"])

    def test_awning_uses_two_plane_lighting_and_consistently_directed_support_shadows(self):
        cloth = ET.parse(ASSETS / "bakery-awning.svg").getroot()
        for name in ("awning-rear-contact", "awning-fold-light", "awning-lip-shadow", "awning-front-roll"):
            gradient = cloth.find(f".//{SVG}linearGradient[@id='{name}']")
            self.assertIsNotNone(gradient)
            self.assertEqual(gradient.attrib["gradientUnits"], "userSpaceOnUse")
        self.assertIsNotNone(cloth.find(f".//{SVG}rect[@id='awning-front-lip-shadow']"))
        front = cloth.find(f"{SVG}g[@id='awning-front-bar']")
        self.assertEqual(front.find(SVG+"rect").attrib["fill"], "url(#awning-front-roll)")
        hardware = ET.parse(ASSETS / "bakery-awning-supports.svg").getroot()
        shadows = hardware.find(f"{SVG}g[@id='awning-support-cast-shadows']")
        self.assertIsNotNone(shadows)
        self.assertNotIn("transform", shadows.attrib)
        self.assertEqual([node.attrib["d"] for node in shadows.findall(SVG+"path")],
                         ["M162 18Q149 109 92 188", "M1042 18Q1099 109 1112 188"])
        lights = hardware.find(f"{SVG}g[@id='awning-support-light-edges']")
        self.assertEqual([node.attrib["d"] for node in lights.findall(SVG+"path")],
                         ["M158.5 16 88.5 186", "M1038.5 16 1108.5 186"])
        self.assertIsNotNone(hardware.find(f".//{SVG}filter[@id='awning-support-shadow-softness']/{SVG}feGaussianBlur"))

    def test_painted_room_fallbacks_and_atlas_are_bounded_metadata_free_images(self):
        sizes = {"bakery-paint-atlas.png": (1024, 1024), "bakery-interior-wide.webp": (1600, 1000),
                 "bakery-interior-portrait.webp": (640, 960), "bakery-interior-short.webp": (1280, 480)}
        for name, size in sizes.items():
            with self.subTest(file=name), Image.open(ASSETS / name) as image:
                self.assertEqual(image.size, size)
                self.assertEqual(image.mode, "RGB")
                self.assertFalse(image.getexif())
                self.assertFalse(image.info.get("xmp"))
                self.assertLess((ASSETS / name).stat().st_size, 1_000_000)

    def test_sign_wood_is_opaque_and_retains_grain_through_its_center(self):
        file = ASSETS / "bakery-sign-wood.webp"
        with Image.open(file) as image:
            self.assertEqual(image.size, (1600, 600))
            self.assertEqual(image.mode, "RGB")
            self.assertFalse(image.getexif())
            self.assertFalse(image.info.get("xmp"))
            center = ImageStat.Stat(image.crop((500, 120, 1100, 480)))
            self.assertGreater(center.stddev[0], 3)
            self.assertGreater(center.stddev[1], 2)
            self.assertLess(max(high for _, high in image.getextrema()), 130)
        self.assertLess(file.stat().st_size, 600_000)

    def test_six_landscape_showcase_images_are_distinct_and_metadata_free(self):
        names = [
            "01-welcome.jpg", "02-bakery-entrance.jpg", "03-our-story.jpg",
            "04-cake-notebooks.jpg", "05-open-notebook.jpg", "06-simple-ordering.jpg",
        ]
        hashes = set()
        for name in names:
            file = ASSETS / "showcase" / name
            with self.subTest(file=name), Image.open(file) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (1600, 1000))
                self.assertFalse(image.getexif())
                self.assertFalse(image.info.get("xmp"))
                self.assertLess(file.stat().st_size, 2_000_000)
            hashes.add(hashlib.sha256(file.read_bytes()).hexdigest())
        self.assertEqual(len(hashes), 6)

    def test_vector_mark_and_favicon_identify_the_brand_without_external_content(self):
        for file in ["whisk-and-crumbs-mark.svg", "favicon.svg"]:
            with self.subTest(file=file):
                root = ET.parse(ASSETS / file).getroot()
                self.assertEqual(root.attrib["viewBox"], "0 0 64 64")
                self.assertIn("Whisk & Crumbs", root.find(SVG + "title").text)
                self.assertIsNone(root.find(".//" + SVG + "image"))
                self.assertIsNone(root.find(".//" + SVG + "script"))
                self.assertGreater(len(root.findall(".//" + SVG + "path")), 2)

    def test_png_and_ico_sizes_and_transparency(self):
        for file, size in [("favicon-16.png", 16), ("favicon-32.png", 32), ("apple-touch-icon.png", 180)]:
            with self.subTest(file=file), Image.open(ASSETS / file) as image:
                self.assertEqual(image.size, (size, size))
                self.assertEqual(image.mode, "RGBA")
                if size == 180:
                    self.assertEqual(image.getchannel("A").getextrema(), (255, 255))
                else:
                    self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
        with Image.open(ASSETS / "favicon.ico") as image:
            self.assertEqual(image.ico.sizes(), {(16, 16), (32, 32), (48, 48)})
        with Image.open(ASSETS / "whisk-and-crumbs-logo.png") as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertGreater(image.width, 900)
            left, top, right, bottom = image.getchannel("A").getbbox()
            self.assertTrue(left > 8 and top > 8 and right < image.width - 8 and bottom < image.height - 8)

    def test_backgrounds_are_sparse_outline_only_and_low_opacity(self):
        for theme, stroke, opacity in [("cream", "#34483a", 0.075), ("green", "#f5ebdd", 0.065)]:
            with self.subTest(theme=theme):
                root = ET.parse(ASSETS / f"bakery-pattern-{theme}.svg").getroot()
                self.assertEqual(root.attrib["viewBox"], "0 0 640 480")
                self.assertEqual(root.attrib["fill"], "none")
                group = root.find(SVG + "g")
                self.assertEqual(group.attrib["stroke"], stroke)
                self.assertEqual(float(group.attrib["opacity"]), opacity)
                self.assertLessEqual(float(group.attrib["stroke-width"]), 1.8)
                self.assertFalse(any(node.attrib.get("fill", "none") != "none" for node in root.iter()))
                self.assertFalse(any(node.tag in {SVG + "image", SVG + "text", SVG + "animate", SVG + "script"} for node in root.iter()))

    def test_generated_brand_receipt_matches_files_when_present(self):
        receipt = ROOT / ".local" / "singular-brand" / "asset-manifest.json"
        if not receipt.exists():
            self.skipTest("Private generation receipt is not part of the public snapshot.")
        manifest = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "Whisk & Crumbs")
        self.assertEqual(len(manifest["files"]), 9)
        for file, record in manifest["files"].items():
            with self.subTest(file=file):
                self.assertEqual(hashlib.sha256((ASSETS / file).read_bytes()).hexdigest(), record["sha256"])
        with Image.open(ASSETS / "whisk-and-crumbs-social-card.jpg") as card:
            self.assertEqual(card.size, (1200, 630))


if __name__ == "__main__":
    unittest.main()
