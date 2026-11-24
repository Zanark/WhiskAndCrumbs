import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / ".local" / "archive-import-20261009" / "prepared-v1"
ROUNDED = ROOT / ".local" / "archive-import-20261009" / "rounded-v4"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ArchiveSiteImportTests(unittest.TestCase):
    def test_only_reviewed_stickers_are_imported(self):
        retained = read_json(PREPARED / "stickers" / "manifest.json")["photos"]
        retained_ids = {photo["id"] for photo in retained}
        rounded = read_json(ROUNDED / "manifest.json")["photos"]
        decisions = read_json(ROUNDED / "rounded-review-decisions.json")
        rejected_ids = {
            cake_id
            for sheet in decisions["sheets"]
            for cake_id in sheet.get("manual_reject_ids", [])
        }
        rounded_ids = {photo["id"] for photo in rounded} - rejected_ids
        approved_ids = retained_ids | rounded_ids
        cakes = read_json(ROOT / "content" / "cakes.json")
        imported_ids = {cake["id"] for cake in cakes if cake["id"].startswith("archive-")}
        self.assertEqual(len(retained_ids), 45)
        self.assertEqual(len(rounded_ids), 88)
        self.assertEqual(len(cakes), 148)
        self.assertEqual(imported_ids, approved_ids)
        self.assertFalse(imported_ids & rejected_ids)

    def test_imported_media_matches_reviewed_hashes_and_membership(self):
        photos = read_json(ROOT / "assets" / "images" / "cakes" / "manifest.json")
        stickers = read_json(ROOT / "assets" / "images" / "cake-stickers" / "manifest.json")
        notebooks = read_json(ROOT / "content" / "notebooks.json")
        membership = {
            cake_id: book["id"]
            for book in notebooks
            for cake_id in book["cakeIds"]
        }
        imported_photos = [photo for photo in photos["photos"] if photo["id"].startswith("archive-")]
        imported_stickers = [photo for photo in stickers["photos"] if photo["id"].startswith("archive-")]
        self.assertEqual(len(imported_photos), 133)
        self.assertEqual(len(imported_stickers), 133)
        self.assertEqual(
            {photo["id"] for photo in imported_photos},
            {photo["id"] for photo in imported_stickers},
        )
        for photo in imported_photos:
            self.assertEqual(membership[photo["id"]], photo["notebook_id"])
            for variant in photo["variants"]:
                payload = (ROOT / "assets" / "images" / "cakes" / variant["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), variant["sha256"])
        for sticker in imported_stickers:
            self.assertIn(
                sticker["mask_status"],
                {"contact-sheet-reviewed", "rounded-contact-sheet-reviewed"},
            )
            mask = ROOT / "assets" / "images" / "cake-stickers" / "masks" / f"{sticker['id']}.png"
            self.assertEqual(hashlib.sha256(mask.read_bytes()).hexdigest(), sticker["mask_sha256"])
            for variant in sticker["variants"]:
                payload = (ROOT / "assets" / "images" / "cake-stickers" / variant["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), variant["sha256"])


if __name__ == "__main__":
    unittest.main()
