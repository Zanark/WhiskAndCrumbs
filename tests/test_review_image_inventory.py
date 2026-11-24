import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("image_review", ROOT / "scripts" / "review_image_inventory.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ImageReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project"
        self.source = self.base / "source"
        self.output = self.project / ".local" / "review"
        self.events = self.base / "session-a" / "events.jsonl"
        self.events.parent.mkdir(parents=True)
        self.events.write_text("", encoding="utf-8")
        self.source.mkdir()
        font = self.project / "web" / "assets" / "fonts" / "dm-sans-regular.ttf"
        font.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "web" / "assets" / "fonts" / font.name, font)
        for number in range(16):
            Image.new("RGB", (96 + number, 80), (number * 10, 60, 90)).save(self.source / f"{number:02}.png")
        shutil.copyfile(self.source / "00.png", self.source / "99.png")
        self.usage = self.project / "usage.json"
        self.usage.write_text(json.dumps({"photos": [{
            "id": "existing-cake", "source_sha256": review.sha256((self.source / "00.png").read_bytes()).hexdigest()
        }]}), encoding="utf-8")
        patcher = patch.object(review, "ROOT", self.project)
        patcher.start()
        self.addCleanup(patcher.stop)

    def prepare(self):
        review.prepare(self.source, self.output, self.usage)
        return review.read_json(self.output / "inventory.json")

    def write_view(self, path, successful=True):
        timestamp = review.datetime.now(review.timezone.utc).isoformat()
        call = str(len(self.events.read_text(encoding="utf-8")))
        events = [
            {"type": "tool.execution_start", "timestamp": timestamp,
             "data": {"toolName": "view", "toolCallId": call, "arguments": {"path": str(path)}}},
            {"type": "tool.execution_complete", "timestamp": timestamp,
             "data": {"toolCallId": call, "success": successful}},
        ]
        with self.events.open("a", encoding="utf-8") as output:
            for event in events:
                output.write(json.dumps(event) + "\n")

    def test_balanced_groups_cover_inventory_without_small_tail(self):
        for count in (15, 20, 30, 37, 145, 152, 159, 160):
            batches = review.groups(list(range(count)))
            self.assertEqual([item for batch in batches for item in batch], list(range(count)))
            self.assertTrue(all(15 <= len(batch) <= 20 for batch in batches))
        for count in (1, 14, 21, 29):
            with self.assertRaises(ValueError):
                review.groups(list(range(count)))

    def test_inventory_preserves_all_sources_and_excludes_redundant_views(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.source.iterdir()}
        inventory = self.prepare()
        self.assertEqual(len(inventory["files"]), 17)
        self.assertEqual(sum(bool(r["duplicate_of"]) for r in inventory["files"]), 1)
        self.assertEqual(sum(bool(r["existing_website_cake_ids"]) for r in inventory["files"]), 2)
        sheets = review.all_sheets(self.output)
        self.assertEqual([len(s["ids"]) for s in sheets], [15])
        self.assertNotIn("P001", sheets[0]["ids"])
        self.assertEqual(review.verify_sources(self.output), 17)
        for path in self.source.iterdir():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before[path.name])
        for tile in sheets[0]["tiles"]:
            self.assertLessEqual(tile["thumbnail_size"][0], review.THUMB[0])
            self.assertLessEqual(tile["thumbnail_size"][1], review.THUMB[1])
        with Image.open(self.output / sheets[0]["file"]) as sheet:
            self.assertEqual(sheet.size, (1600, 1494))
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare()
        (self.source / "01.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash changed"):
            review.verify_sources(self.output)

    def test_decode_failure_is_recorded_not_silently_classified(self):
        (self.source / "broken.jpg").write_bytes(b"not an image")
        inventory = self.prepare()
        broken = next(r for r in inventory["files"] if r["filename"] == "broken.jpg")
        self.assertEqual(broken["decode_status"], "decode-failed")
        self.assertTrue(broken["error"])
        self.assertFalse(any(broken["id"] in s["ids"] for s in review.all_sheets(self.output)))

    def test_owner_source_decisions_are_hash_bound_and_not_repeated_or_claimed_as_cutout_review(self):
        Image.new("RGB", (125, 95), "gold").save(self.source / "50.png")
        owners = self.base / "owners.json"
        owner = {"evidence": "owner-provided-source-classification", "recorded_at": "2026-10-04T23:12:02+05:30",
                 "items": [{"id": "P002", "sha256": review.sha256((self.source / "01.png").read_bytes()).hexdigest(),
                            "classification": "cake", "label": "Tea cakes", "reason": "Owner identified this source."}]}
        owners.write_text(json.dumps(owner), encoding="utf-8")
        review.prepare(self.source, self.output, self.usage, owners)
        self.assertTrue(all("P002" not in sheet["ids"] for sheet in review.all_sheets(self.output)))
        self.assertEqual([len(sheet["ids"]) for sheet in review.all_sheets(self.output)], [15])
        result = review.report(self.output, self.project / "docs" / "review.md", self.events)
        self.assertEqual(result["classifications"]["owner-confirmed-cake"], 1)
        self.assertEqual(result["classifications"]["unreviewed"], 15)
        self.assertFalse((self.output / "decisions").exists())
        self.assertIn("not new contact-sheet or cutout review",
                      (self.project / "docs" / "review.md").read_text(encoding="utf-8"))
        owner["items"][0]["sha256"] = "0" * 64
        owners.write_text(json.dumps(owner), encoding="utf-8")
        records = review.read_json(self.output / "inventory.json")["files"]
        with self.assertRaisesRegex(ValueError, "hash-mismatched"):
            review.owner_classifications(owners, records)

    def test_exif_orientation_and_source_metadata_are_not_modified(self):
        path = self.source / "oriented.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (70, 120), "green").save(path, exif=exif)
        before = path.read_bytes()
        record = review.inspect_file(path, self.source, 1, {})
        self.assertEqual((record["width"], record["height"]), (70, 120))
        self.assertEqual((record["display_width"], record["display_height"]), (120, 70))
        self.assertTrue(record["has_exif"])
        self.assertEqual(path.read_bytes(), before)

    def test_budget_counts_failed_attempts_and_blocks_before_twenty(self):
        self.prepare()
        for index in range(review.STOP_AT_VIEWS):
            self.write_view(self.base / f"earlier-{index}.png", successful=index != 0)
        audit = review.audit_session(self.events)
        self.assertEqual(audit["image_view_attempts"], 16)
        self.assertEqual(audit["successful_image_views"], 15)
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            review.reserve(self.output, "batch-01", self.events)
        self.assertFalse((self.output / "views").exists())

    def test_budget_audit_streams_the_real_log_without_loading_all_payloads(self):
        self.write_view(self.base / "one.png")
        self.write_view(self.base / "failed.webp", successful=False)
        with self.events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"type": "tool.execution_complete",
                                     "data": {"toolCallId": "unrelated", "success": True}}) + "\n")
        with patch.object(Path, "read_text", side_effect=AssertionError("Do not load the complete session log.")):
            audit = review.audit_session(self.events)
        self.assertEqual(audit["image_view_attempts"], 2)
        self.assertEqual(audit["successful_image_views"], 1)
        self.assertEqual([call["success"] for call in audit["calls"]], [True, False])

    def test_reservation_precedes_view_and_prevents_repeats(self):
        self.prepare()
        path = review.reserve(self.output, "batch-01", self.events)
        self.assertTrue((self.output / "views" / "batch-01.json").exists())
        with self.assertRaisesRegex(ValueError, "already viewed or reserved"):
            review.reserve(self.output, "batch-01", self.events)
        ids = review.all_sheets(self.output)[0]["ids"]
        review.focus(self.output, "focus-01", ids, "Focused comparison needed for uncertain details.")
        with self.assertRaisesRegex(ValueError, "preceding batch"):
            review.reserve(self.output, "focus-01", self.events)
        self.assertEqual(path, self.output / "sheets" / "batch-01.jpg")

    def test_record_requires_successful_view_and_complete_reasoned_decisions(self):
        self.prepare()
        path = review.reserve(self.output, "batch-01", self.events)
        draft = review.read_json(self.output / "drafts" / "batch-01.json")
        draft.update(status="reviewed", summary="Synthetic test evidence, not actual cake review.")
        for item in draft["items"]:
            item.update(classification="uncertain", selection="hold",
                        reason="Synthetic fixture has no cake content evidence.", needs_focus=True)
        decision_file = self.base / "decision.json"
        decision_file.write_text(json.dumps(draft), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "No successful"):
            review.record_batch(self.output, "batch-01", decision_file, self.events)
        self.write_view(path, successful=False)
        with self.assertRaisesRegex(ValueError, "No successful"):
            review.record_batch(self.output, "batch-01", decision_file, self.events)
        self.write_view(path)
        review.record_batch(self.output, "batch-01", decision_file, self.events)
        destination = self.project / "docs" / "review.md"
        result = review.report(self.output, destination, self.events)
        self.assertEqual(result["classifications"]["uncertain"], 15)
        self.assertIn("contact sheet only", destination.read_text(encoding="utf-8"))
        self.assertEqual(review.read_json(self.output / "decisions" / "batch-01.json")["review_level"],
                         "contact-sheet-only")

    def test_cross_session_interruption_recovery_does_not_invent_review(self):
        self.prepare()
        review.reserve(self.output, "batch-01", self.events)
        self.events = self.base / "session-b" / "events.jsonl"
        self.events.parent.mkdir()
        self.events.write_text("", encoding="utf-8")
        failure = self.base / "interrupted.json"
        failure.write_text(json.dumps({"status": "interrupted-unclassified", "items": [],
                                      "summary": "No reliable notes survived; keep all tiles unreviewed."}),
                           encoding="utf-8")
        review.record_batch(self.output, "batch-01", failure, self.events)
        destination = self.project / "docs" / "review.md"
        result = review.report(self.output, destination, self.events)
        self.assertEqual(result["classifications"]["unreviewed"], 15)
        self.assertEqual(result["successful_image_views"], 0)

    def test_public_output_manual_docs_and_small_focus_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "below this project's .local"):
            review.private_output(self.project / "site" / "review")
        self.prepare()
        with self.assertRaisesRegex(ValueError, "15-20"):
            review.focus(self.output, "focus-01", ["P002"], "Uncertain image.")
        destination = self.project / "docs" / "existing.md"
        destination.parent.mkdir()
        destination.write_text("Existing user documentation.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manually authored"):
            review.report(self.output, destination, self.events)
        self.assertEqual(destination.read_text(encoding="utf-8"), "Existing user documentation.")
        with self.assertRaisesRegex(ValueError, "project's docs directory"):
            review.report(self.output, self.project / "docs" / ".." / "site" / "review.md", self.events)


if __name__ == "__main__":
    unittest.main()
