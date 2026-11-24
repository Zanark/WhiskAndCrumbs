import base64
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_instagram as importer


def png(red):
    """A real one-pixel RGB PNG, with distinct valid bytes for each red value."""
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes((0, red, 20, 30))))
            + chunk(b"IEND", b""))


# A genuine one-pixel GIF. Video fixtures below test byte copying, not decoding.
GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
VIDEO = b"synthetic opaque video bytes; no media-decoding claim"


class ImportInstagramTests(unittest.TestCase):
    def setUp(self):
        # All scratch data stays under the repository, never in the system temp directory.
        self.workspace = tempfile.TemporaryDirectory(prefix="instagram-test-", dir=ROOT)
        self.addCleanup(self.workspace.cleanup)
        self.base = Path(self.workspace.name)
        self.output = self.base / "imported"

    def archive(self, name, files):
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative, data in files.items():
                member = zipfile.ZipInfo(relative)
                # ZipInfo otherwise normalizes Windows backslashes before writing fixtures.
                member.filename = relative
                member.orig_filename = relative
                member.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(member, data)
        return path

    def directory(self, name, files):
        root = self.base / name
        root.mkdir(parents=True, exist_ok=True)
        for relative, data in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return root

    def run_import(self, *sources, **kwargs):
        return importer.import_media(sources, self.output, **kwargs)

    def assert_clean_failure(self):
        self.assertFalse((self.output / "manifest.json").exists())
        if self.output.exists():
            self.assertFalse(list(self.output.glob(".import*")))
            self.assertFalse(list(self.output.rglob("cake-*")))

    def test_every_carousel_proxy_photo_and_distinct_equal_basenames(self):
        source = self.archive("export.zip", {
            "wrapper/media/posts/carousel/slide_1.png": png(1),
            "wrapper/media/posts/carousel/slide_2.png": png(2),
            "wrapper/media/posts/another/slide_1.png": png(3),
        })
        result = self.run_import(source)
        self.assertEqual(result["last_successful_run"]["imported"], 3)
        self.assertEqual(result["last_successful_run"]["eligible_files"], 3)
        self.assertEqual(len(result["files"]), 3)
        for record in result["files"]:
            copied = (self.output / record["file"]).read_bytes()
            self.assertIn(copied, (png(1), png(2), png(3)))
            self.assertEqual(hashlib.sha256(copied).hexdigest(), record["sha256"])
            self.assertEqual(record["bytes"], len(copied))
            self.assertEqual(Path(record["file"]).name, f"cake-{record['sha256']}.png")

    def test_extracted_directory_recurses_through_enclosing_export_wrappers(self):
        source = self.directory("extracted export", {
            "download/account-export/media/posts/carousel/slide_1.png": png(1),
            "download/account-export/media/posts/carousel/slide_2.png": png(2),
            "download/account-export/media/reels/cover.png": png(3),
            "download/account-export/media/stories/photo.png": png(4),
            "download/account-export/messages/inbox/private.png": png(5),
            "screenshots/profile.png": png(6),
            "unrelated.png": png(7),
        })
        result = self.run_import(source)
        counts = result["last_successful_run"]
        self.assertEqual((counts["eligible_files"], counts["imported"], counts["skipped"]),
                         (4, 4, 3))
        self.assertEqual({(self.output / record["file"]).read_bytes()
                          for record in result["files"]},
                         {png(1), png(2), png(3), png(4)})

    def test_scope_defaults_and_opt_in_categories_and_video(self):
        source = self.archive("scope.zip", {
            **{f"media/{category}/photo.png": png(index)
               for index, category in enumerate(sorted(importer.CATEGORIES))},
            "media/reels/movie.mp4": VIDEO,
            "media/posts/animated.gif": GIF,
            "media/other/ambiguous.png": png(20),
            "messages/inbox/chat/picture.png": png(21),
            "messages/inbox/media/posts/leak.png": png(22),
            "media/profile/photo.png": png(23),
            "media/profile_pictures/photo.png": png(24),
            "media/ads/photo.png": png(25),
            "media/saved/photo.png": png(26),
            "media/tagged/photo.png": png(27),
            "media/liked/photo.png": png(28),
            "contacts/photo.png": png(29),
            "media/posts/captions.json": b'{"caption":"private metadata"}',
            "media/posts/index.html": b"<p>not media</p>",
        })
        first = self.run_import(source)
        counts = first["last_successful_run"]
        self.assertEqual((counts["imported"], counts["skipped"]), (6, 13))
        self.assertEqual(counts["skipped_by_reason"]["videos_disabled"], 1)
        self.assertEqual(counts["skipped_by_reason"]["unsupported_extension"], 2)
        self.assertFalse((self.output / "videos").exists())
        second = self.run_import(source, include_videos=True, include_other_media=True)
        counts = second["last_successful_run"]
        self.assertEqual((counts["imported"], counts["duplicates"], counts["skipped"]), (2, 6, 11))
        self.assertEqual(len(list((self.output / "videos").iterdir())), 1)
        manifest_text = (self.output / "manifest.json").read_text(encoding="utf-8")
        self.assertNotIn("private metadata", manifest_text)
        self.assertNotIn("profile_pictures", manifest_text)
        self.assertNotIn(str(self.base), manifest_text)
        self.assertEqual({s["category"] for r in second["files"] for s in r["sources"]},
                         importer.CATEGORIES | {"other"})

    def test_multiple_archives_directory_duplicates_and_reruns_preserve_associations(self):
        first = self.archive("part1.zip", {"media/posts/a.png": png(1)})
        second = self.archive("part2.zip", {"wrap/media/stories/b.png": png(1),
                                          "wrap/media/posts/new.png": png(2)})
        directory = self.directory("unpacked", {"media/archived_posts/c.png": png(1)})
        result = self.run_import(first, second, directory)
        self.assertEqual((result["last_successful_run"]["imported"],
                          result["last_successful_run"]["duplicates"]), (2, 2))
        digest = hashlib.sha256(png(1)).hexdigest()
        record = next(r for r in result["files"] if r["sha256"] == digest)
        self.assertEqual(len(record["sources"]), 3)
        original_files = result["files"]
        for sources in ((second,), (first, second, directory)):
            result = self.run_import(*sources)
            self.assertEqual(result["last_successful_run"]["imported"], 0)
            self.assertEqual(result["files"], original_files)
        self.assertEqual(result["last_successful_run"]["duplicates"], 4)

    def test_identical_archive_labels_keep_distinct_source_associations(self):
        first = self.archive("a/export.zip", {"media/posts/a.png": png(1)})
        second = self.archive("b/export.zip", {"media/posts/a.png": png(1)})
        result = self.run_import(first, second)
        associations = result["files"][0]["sources"]
        self.assertEqual(len(associations), 2)
        self.assertEqual({s["source"] for s in associations}, {"export.zip"})
        self.assertEqual(len({s["source_id"] for s in associations}), 2)
        self.assertEqual(self.run_import(second)["files"], result["files"])

    def test_extension_recognition_is_not_a_decoding_claim(self):
        source = self.archive("extensions.zip", {
            "media/posts/photo.JPEG": b"not a decoded jpeg",
            "media/posts/photo.jpg": b"not a decoded jpeg",
            "media/posts/photo.HEIC": b"not a decoded heic",
        })
        result = self.run_import(source)
        self.assertEqual((result["last_successful_run"]["imported"],
                          result["last_successful_run"]["duplicates"]), (2, 1))
        self.assertIn("not decoded", result["media_validation"])
        self.assertEqual(len(result["files"]), 2)
        self.assertTrue(any(r["file"].endswith(".jpg") for r in result["files"]))

    def test_missing_and_malformed_sources_are_validated_before_any_output(self):
        good = self.archive("good.zip", {"media/posts/a.png": png(1)})
        bad = self.base / "bad.zip"
        bad.write_bytes(b"not a zip")
        for invalid in (self.base / "missing.zip", bad):
            with self.subTest(source=invalid.name):
                with self.assertRaises(importer.ImportFailure):
                    self.run_import(good, invalid)
                self.assertFalse(self.output.exists())

    def test_zero_eligible_media_fails_without_success_manifest(self):
        for name, files in (
            ("empty.zip", {}),
            ("metadata.zip", {"messages/a.png": png(1), "media/posts/metadata.json": b"{}"}),
            ("video.zip", {"media/reels/movie.mp4": VIDEO}),
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(importer.ImportFailure, "No eligible media"):
                    self.run_import(self.archive(name, files))
                self.assert_clean_failure()
        result = self.run_import(self.base / "video.zip", include_videos=True)
        self.assertEqual(result["files"][0]["media_type"], "video")

    def test_unsafe_zip_paths_fail_without_extracting(self):
        for index, name in enumerate((
            "../media/posts/escape.png",
            "media/posts/../../../escape.png",
            "/media/posts/absolute.png",
            "C:/media/posts/drive.png",
            r"media\posts\backslash.png",
            "media/posts/stream.png:secret",
            "media/posts/./dot.png",
            "media//posts/empty.png",
            "media/posts/con.png",
            "media/posts/trailing.png ",
            "media/posts/null\0hidden.png",
            "media/posts/invalid?.png",
        )):
            with self.subTest(path=name):
                source = self.archive(f"unsafe-{index}.zip", {
                    "media/posts/good.png": png(1), name: png(2)})
                with self.assertRaisesRegex(importer.ImportFailure, "Unsafe"):
                    self.run_import(source)
                self.assertFalse(self.output.exists())
                self.assertFalse((self.base / "escape.png").exists())

    def test_zip_symlink_is_rejected(self):
        path = self.base / "link.zip"
        member = zipfile.ZipInfo("media/posts/link.png")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("media/posts/good.png", png(1))
            archive.writestr(member, "../../outside.png")
        with self.assertRaisesRegex(importer.ImportFailure, "symlink"):
            self.run_import(path)
        self.assertFalse(self.output.exists())

    def make_symlink(self, target, link, is_directory=False):
        try:
            link.symlink_to(target, target_is_directory=is_directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Platform does not permit symlink fixtures: {error}")

    def test_directory_symlink_is_not_followed(self):
        outside = self.directory("outside", {"private.png": png(2)})
        source = self.directory("source", {"media/posts/good.png": png(1)})
        self.make_symlink(outside, source / "media" / "posts" / "linked", True)
        with self.assertRaisesRegex(importer.ImportFailure, "symlink|junction"):
            self.run_import(source)
        self.assertFalse(self.output.exists())

    def test_source_root_symlink_is_rejected(self):
        source = self.directory("source", {"media/posts/good.png": png(1)})
        linked = self.base / "source-link"
        self.make_symlink(source, linked, True)
        with self.assertRaisesRegex(importer.ImportFailure, "Symlink|junction"):
            self.run_import(linked)

    def test_directory_junction_is_not_followed_on_windows(self):
        if os.name != "nt":
            self.skipTest("Windows junction fixture")
        outside = self.directory("outside", {"private.png": png(2)})
        source = self.directory("source", {"media/posts/good.png": png(1)})
        junction = source / "media" / "posts" / "linked"
        result = subprocess.run([os.environ["ComSpec"], "/c", "mklink", "/J",
                                 str(junction), str(outside)], capture_output=True)
        if result.returncode:
            self.skipTest(f"Could not create Windows junction: {result.stderr!r}")
        try:
            with self.assertRaisesRegex(importer.ImportFailure, "symlink|junction"):
                self.run_import(source)
            self.assertFalse(self.output.exists())
        finally:
            junction.rmdir()
        self.assertEqual((outside / "private.png").read_bytes(), png(2))

    def test_source_output_overlap_in_both_directions_is_rejected(self):
        source = self.directory("source", {"media/posts/a.png": png(1)})
        archive = self.archive("inside/export.zip", {"media/posts/a.png": png(1)})
        for root, output in ((source, source), (source, source / "imported"),
                             (source, self.base), (archive, archive.parent)):
            with self.subTest(source=root, output=output):
                with self.assertRaisesRegex(importer.ImportFailure, "overlap"):
                    importer.import_media([root], output)
        self.assertFalse((source / "imported").exists())

    def test_tampered_output_fails_and_preserves_prior_manifest(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        result = self.run_import(source)
        previous = (self.output / "manifest.json").read_bytes()
        target = self.output / result["files"][0]["file"]
        original = target.read_bytes()
        tampered = original[:-1] + bytes((original[-1] ^ 1,))
        target.write_bytes(tampered)
        with self.assertRaisesRegex(importer.ImportFailure, "SHA256 mismatch"):
            self.run_import(source)
        self.assertEqual(target.read_bytes(), tampered)
        self.assertEqual((self.output / "manifest.json").read_bytes(), previous)
        self.assertFalse(list(self.output.glob(".import*")))

    def test_existing_destination_without_manifest_is_hash_checked(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        digest = hashlib.sha256(png(1)).hexdigest()
        target = self.output / "images" / f"cake-{digest}.png"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"conflicting bytes")
        with self.assertRaisesRegex(importer.ImportFailure, "Output conflict"):
            self.run_import(source)
        self.assertEqual(target.read_bytes(), b"conflicting bytes")
        self.assertFalse((self.output / "manifest.json").exists())
        target.write_bytes(png(1))
        result = self.run_import(source)
        self.assertEqual((result["last_successful_run"]["imported"],
                          result["last_successful_run"]["duplicates"]), (0, 1))
        self.assertEqual(len(result["files"]), 1)

    def test_output_symlink_is_not_written(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        outside = self.directory("outside", {})
        self.output.mkdir()
        self.make_symlink(outside, self.output / "images", True)
        with self.assertRaisesRegex(importer.ImportFailure, "Symlink|junction"):
            self.run_import(source)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.output / "manifest.json").exists())

    def test_corrupt_manifest_is_never_replaced(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        self.run_import(source)
        manifest = self.output / "manifest.json"
        for invalid in (b"not json", b"[]", b'{"schema_version":999,"files":[]}'):
            with self.subTest(contents=invalid):
                manifest.write_bytes(invalid)
                with self.assertRaisesRegex(importer.ImportFailure, "Invalid existing manifest"):
                    self.run_import(source)
                self.assertEqual(manifest.read_bytes(), invalid)
                self.assertFalse(list(self.output.glob(".import*")))

    def test_per_file_and_total_limits_fail_before_writing(self):
        large = self.archive("large.zip", {"media/posts/a.png": b"x" * (importer.MIB + 1)})
        with self.assertRaisesRegex(importer.ImportFailure, "max-file-mib"):
            self.run_import(large, max_file_mib=1)
        self.assertFalse(self.output.exists())
        total = self.archive("total.zip", {"media/posts/a.png": b"a" * 600_000,
                                          "media/posts/b.png": b"b" * 600_000})
        with self.assertRaisesRegex(importer.ImportFailure, "max-total-mib"):
            self.run_import(total, max_total_mib=1)
        self.assertFalse(self.output.exists())

    def test_combined_collection_limit_preserves_previous_run(self):
        first = self.archive("first.zip", {"media/posts/a.png": b"a" * 600_000})
        second = self.archive("second.zip", {"media/posts/b.png": b"b" * 600_000})
        self.run_import(first, max_total_mib=1)
        previous = (self.output / "manifest.json").read_bytes()
        with self.assertRaisesRegex(importer.ImportFailure, "Resulting collection exceeds"):
            self.run_import(second, max_total_mib=1)
        self.assertEqual((self.output / "manifest.json").read_bytes(), previous)
        self.assertEqual(len(list((self.output / "images").iterdir())), 1)
        self.assertFalse(list(self.output.glob(".import*")))

    def test_empty_eligible_file_is_an_error_not_a_photo(self):
        source = self.archive("empty-photo.zip", {"media/posts/empty.jpg": b""})
        with self.assertRaisesRegex(importer.ImportFailure, "empty"):
            self.run_import(source)
        self.assertFalse(self.output.exists())

    def test_excluded_payloads_are_never_opened(self):
        source = self.archive("private.zip", {
            "media/posts/a.png": png(1),
            "messages/inbox/private.png": png(2),
            "media/posts/captions.json": b'{"caption":"private"}',
            "media/other/unknown.png": png(3),
        })
        opened = []
        real_open = zipfile.ZipFile.open

        def record_open(archive, member, *args, **kwargs):
            opened.append(member.filename)
            return real_open(archive, member, *args, **kwargs)

        with patch.object(zipfile.ZipFile, "open", record_open):
            self.run_import(source)
        self.assertEqual(opened, ["media/posts/a.png"])

    def test_tampered_manifest_cannot_redirect_output_outside_collection(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        result = self.run_import(source)
        result["files"][0]["file"] = "../outside.png"
        manifest = self.output / "manifest.json"
        manifest.write_text(json.dumps(result), encoding="utf-8")
        previous = manifest.read_bytes()
        with self.assertRaisesRegex(importer.ImportFailure, "Invalid existing manifest"):
            self.run_import(source)
        self.assertEqual(manifest.read_bytes(), previous)
        self.assertFalse((self.base / "outside.png").exists())

    def test_streaming_limit_rejects_more_than_declared_bytes(self):
        with self.assertRaisesRegex(importer.ImportFailure, "exceeded"):
            importer.stream_hash(io.BytesIO(b"abcdef"), 5, io.BytesIO())

    def test_crc_error_removes_staging_and_does_not_publish_manifest(self):
        source = self.base / "corrupt.zip"
        name = "media/posts/b.png"
        with zipfile.ZipFile(source, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("media/posts/a.png", png(1))
            archive.writestr(name, png(2))
            offset = archive.getinfo(name).header_offset + 30 + len(name.encode("utf-8"))
        data = bytearray(source.read_bytes())
        data[offset] ^= 1
        source.write_bytes(data)
        with self.assertRaisesRegex(importer.ImportFailure, "Bad CRC"):
            self.run_import(source)
        self.assert_clean_failure()

    def test_manifest_publish_failure_rolls_back_new_files_and_preserves_previous(self):
        first = self.archive("first.zip", {"media/posts/a.png": png(1)})
        second = self.archive("second.zip", {"media/posts/b.png": png(2)})
        result = self.run_import(first)
        previous = (self.output / "manifest.json").read_bytes()
        with patch.object(importer.os, "replace", side_effect=OSError("simulated disk failure")):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.run_import(second)
        self.assertEqual((self.output / "manifest.json").read_bytes(), previous)
        self.assertEqual([p.name for p in (self.output / "images").iterdir()],
                         [Path(result["files"][0]["file"]).name])
        self.assertFalse(list(self.output.glob(".import*")))

    def test_concurrent_output_lock_is_respected(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        self.output.mkdir()
        lock = self.output / ".import.lock"
        lock.write_text("some other importer", encoding="ascii")
        with self.assertRaisesRegex(importer.ImportFailure, "locked"):
            self.run_import(source)
        self.assertEqual(lock.read_text(), "some other importer")
        self.assertFalse((self.output / "manifest.json").exists())

    def test_cli_exit_codes_summary_and_help_contract(self):
        source = self.archive("source.zip", {"media/posts/a.png": png(1)})
        command = [sys.executable, str(ROOT / "scripts" / "import_instagram.py")]
        completed = subprocess.run(command + [str(source), "--output", str(self.output)],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Imported 1 new file(s); duplicates 0", completed.stdout)
        self.assertIn("NOT proof", completed.stdout)
        self.assertIn("not decoded", completed.stdout)
        failure = subprocess.run(command + [str(self.base / "missing.zip"), "--output",
                                            str(self.output)], capture_output=True, text=True)
        self.assertNotEqual(failure.returncode, 0)
        self.assertIn("last committed run", failure.stderr)
        help_result = subprocess.run(command + ["--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        for flag in ("--include-videos", "--include-other-media", "--max-file-mib",
                     "--max-total-mib", "media/archived_posts"):
            self.assertIn(flag, help_result.stdout)


if __name__ == "__main__":
    unittest.main()
