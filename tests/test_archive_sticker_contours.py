import sys
from pathlib import Path
import unittest

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_archive_notebook_assets import straight_cut_issues
from refine_archive_sticker_contours import organic_contour


class ArchiveStickerContourTests(unittest.TestCase):
    def test_rejects_flat_bottom_and_right_cuts(self):
        mask = Image.new("L", (400, 400))
        draw = ImageDraw.Draw(mask)
        draw.ellipse((40, 35, 375, 370), fill=255)
        draw.rectangle((330, 120, 375, 330), fill=255)
        draw.rectangle((100, 325, 330, 370), fill=255)

        issues = straight_cut_issues(mask)

        self.assertTrue(any("vertical" in issue for issue in issues), issues)
        self.assertTrue(any("horizontal" in issue for issue in issues), issues)

    def test_accepts_curved_contour_with_margin(self):
        mask = Image.new("L", (400, 400))
        ImageDraw.Draw(mask).ellipse((45, 35, 355, 365), fill=255)

        self.assertEqual(straight_cut_issues(mask), [])

    def test_rejects_source_edge_contact(self):
        mask = Image.new("L", (400, 400))
        ImageDraw.Draw(mask).ellipse((-20, 40, 360, 370), fill=255)

        self.assertIn("foreground-reaches-source-edge", straight_cut_issues(mask))

    def test_rejects_diagonal_board_edge(self):
        mask = Image.new("L", (400, 400))
        draw = ImageDraw.Draw(mask)
        draw.ellipse((80, 35, 330, 290), fill=255)
        draw.polygon([(55, 280), (330, 330), (310, 370), (35, 320)], fill=255)

        issues = straight_cut_issues(mask)

        self.assertTrue(any("diagonal" in issue for issue in issues), issues)

    def test_rounds_source_edge_and_flat_boundaries_without_emptying_the_mask(self):
        mask = Image.new("L", (400, 400))
        draw = ImageDraw.Draw(mask)
        draw.ellipse((-30, 35, 365, 360), fill=255)
        draw.rectangle((70, 300, 365, 390), fill=255)

        rounded, retained = organic_contour(mask, 12345)

        self.assertEqual(straight_cut_issues(rounded), [])
        self.assertGreater(retained, 0.58)
        self.assertIsNotNone(rounded.getbbox())


if __name__ == "__main__":
    unittest.main()
