import hashlib
import json
from pathlib import Path
import sys
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_archive_notebook_assets import straight_cut_issues


class RoundedArchiveStickerTests(unittest.TestCase):
    def test_all_rejected_masks_have_a_rounded_candidate_revision(self):
        prepared = ROOT / ".local" / "archive-import-20261009" / "prepared-v1"
        rounded = ROOT / ".local" / "archive-import-20261009" / "rounded-v4"
        rejected = json.loads(
            (prepared / "stickers" / "rejected-straight-cuts.json").read_text(encoding="utf-8")
        )["rejected"]
        manifest = json.loads((rounded / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["failures"], [])
        self.assertEqual(
            {record["id"] for record in rejected},
            {record["id"] for record in manifest["photos"]},
        )
        self.assertEqual(len(manifest["photos"]), 90)

        for photo in manifest["photos"]:
            mask_file = rounded / "masks" / f"{photo['id']}.png"
            self.assertEqual(hashlib.sha256(mask_file.read_bytes()).hexdigest(), photo["mask_sha256"])
            with Image.open(mask_file) as mask:
                self.assertEqual(straight_cut_issues(mask.convert("L")), [])
            self.assertGreaterEqual(photo["retained_foreground_fraction"], 0.58)
            for variant in photo["variants"]:
                file = rounded / "stickers" / variant["file"]
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), variant["sha256"])
                with Image.open(file) as image:
                    self.assertEqual(image.mode, "RGBA")
                    alpha = image.getchannel("A")
                    self.assertEqual(alpha.getextrema(), (0, 255))
                    bounds = alpha.getbbox()
                    self.assertGreater(bounds[0], 0)
                    self.assertGreater(bounds[1], 0)
                    self.assertLess(bounds[2], image.width)
                    self.assertLess(bounds[3], image.height)


if __name__ == "__main__":
    unittest.main()
