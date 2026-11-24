import sys
from pathlib import Path
import unittest

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from round_sticker_source_edges import round_source_edges, source_edge_runs


class SourceEdgeRoundingTests(unittest.TestCase):
    def test_rounds_bottom_and_right_clips_without_expanding_or_touching_the_sign(self):
        mask = Image.new("L", (600, 600))
        draw = ImageDraw.Draw(mask)
        draw.ellipse((70, 180, 660, 680), fill=255)
        draw.rectangle((210, 70, 410, 240), fill=255)
        before = np.asarray(mask)
        result, proof = round_source_edges(mask)
        after = np.asarray(result)
        self.assertEqual(set(proof["edges"]), {"right", "bottom"})
        self.assertTrue(np.all(after <= before))
        self.assertTrue(np.array_equal(after[:260, :450], before[:260, :450]))
        self.assertFalse(any(source_edge_runs(result).values()))
        self.assertGreater(proof["retained_alpha_fraction"], .90)
        self.assertEqual(result.tobytes(), round_source_edges(mask)[0].tobytes())

    def test_leaves_real_straight_geometry_away_from_photo_edges_exactly_unchanged(self):
        mask = Image.new("L", (400, 400))
        ImageDraw.Draw(mask).rectangle((65, 45, 335, 355), fill=255)
        result, proof = round_source_edges(mask)
        self.assertFalse(proof["modified"])
        self.assertEqual(result.tobytes(), mask.tobytes())

    def test_bottom_cap_is_an_arc_not_another_straight_cut(self):
        mask = Image.new("L", (600, 600))
        ImageDraw.Draw(mask).ellipse((40, 80, 560, 780), fill=255)
        result, proof = round_source_edges(mask)
        solid = np.asarray(result) >= 128
        edge = 599 - solid[::-1].argmax(axis=0)
        start, end = proof["edges"]["bottom"]["source_runs"][0]
        middle = (start + end) // 2
        self.assertGreater(edge[middle], edge[start] + 15)
        self.assertGreater(edge[middle], edge[end - 1] + 15)
        self.assertLess(len(set(edge[start:end])), end - start)
        self.assertGreater(len(set(edge[start:end])), 20)

    def test_multiple_top_cuts_preserve_separate_curved_peaks(self):
        mask = Image.new("L", (600, 600))
        draw = ImageDraw.Draw(mask)
        draw.ellipse((70, -25, 180, 100), fill=255)
        draw.ellipse((350, -20, 485, 135), fill=255)
        draw.ellipse((80, 50, 520, 540), fill=255)
        result, proof = round_source_edges(mask)
        self.assertEqual(len(proof["edges"]["top"]["source_runs"]), 2)
        self.assertEqual(proof["newly_visible_pixels"], 0)
        self.assertFalse(any(source_edge_runs(result).values()))

    def test_invalid_or_empty_alpha_is_rejected(self):
        with self.assertRaises(ValueError):
            round_source_edges(Image.new("RGB", (100, 100)))
        with self.assertRaises(ValueError):
            round_source_edges(Image.new("L", (100, 100)))


if __name__ == "__main__":
    unittest.main()
