"""Copy selected originals from locally supplied Instagram exports; never use the network."""

import argparse
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import zipfile
import zlib


PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".jpe", ".png", ".webp", ".heic", ".heif",
                    ".avif", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp",
                    ".3g2", ".mpeg", ".mpg"}
CATEGORIES = {"posts", "reels", "igtv", "stories", "archived_posts"}
EXCLUDED_COMPONENTS = {
    "messages", "inbox", "direct", "chats", "contacts", "profile",
    "profile_pictures", "ads", "saved", "saved_posts", "liked", "liked_posts",
    "tagged", "tagged_posts",
}
MIB = 1024 * 1024
CHUNK_SIZE = MIB
MAX_ENTRIES = 200_000
MAX_MANIFEST_BYTES = 32 * MIB
SCOPE = ("Only eligible media in the supplied export sources is covered. "
         "This is NOT proof that all profile posts were exported.")
MEDIA_VALIDATION = ("Media types are inferred from filename extensions, not decoded or "
                    "visually verified. No cake identification or video-frame extraction.")


class ImportFailure(Exception):
    """An actionable input, integrity, or safety error."""


@dataclass(frozen=True)
class Candidate:
    root: Path
    relative: str
    category: str
    extension: str
    media_type: str
    size: int
    archive: zipfile.ZipFile | None = None
    member: zipfile.ZipInfo | None = None

    def association(self):
        # Distinguish identically named archives without storing absolute source paths.
        source_id = hashlib.sha256(os.fsencode(os.path.normcase(self.root))).hexdigest()
        return {"source": self.root.name, "source_id": source_id,
                "path": self.relative, "category": self.category,
                "extension": self.extension}


def is_link(info):
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0) & 0x400))


def check_local_path(path):
    """Reject symlinks and Windows reparse points in every existing ancestor."""
    if str(path).startswith(("\\\\", "//")):
        raise ImportFailure(f"Use a local drive, not a network/device path: {path}")
    for part in reversed((path, *path.parents)):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if is_link(info):
            raise ImportFailure(f"Symlink/junction/reparse point is not allowed: {part}")


def canonical_parts(name, directory=False):
    value = name[:-1] if directory and name.endswith("/") else name
    parts = value.split("/")
    if (not value or "\\" in value or any(ord(c) < 32 for c in value)
            or len(parts) > 128
            or any(p in ("", ".", "..") or any(c in p for c in ':*?"<>|')
                   or p.endswith((" ", "."))
                   or re.fullmatch(r"(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])",
                                   p.split(".")[0]) for p in parts)):
        raise ImportFailure(f"Unsafe or non-canonical export path: {name!r}")
    return parts


def category_for(parts, include_other):
    lowered = [part.casefold() for part in parts]
    if EXCLUDED_COMPONENTS.intersection(lowered):
        return None
    try:
        index = lowered.index("media")
    except ValueError:
        return None
    allowed = CATEGORIES | ({"other"} if include_other else set())
    if index + 2 < len(lowered) and lowered[index + 1] in allowed:
        return lowered[index + 1]
    return None


def classify(name, include_other, include_videos):
    parts = canonical_parts(name)
    category = category_for(parts, include_other)
    extension = Path(parts[-1]).suffix.lower()
    if category is None:
        return None, "outside_scope"
    if extension in PHOTO_EXTENSIONS:
        return (category, extension, "photo"), None
    if extension in VIDEO_EXTENSIONS:
        if include_videos:
            return (category, extension, "video"), None
        return None, "videos_disabled"
    return None, "unsupported_extension"


def validate_roots(sources, output):
    roots = [Path(os.path.abspath(source)) for source in sources]
    output = Path(os.path.abspath(output))
    check_local_path(output)
    if output.exists() and not output.is_dir():
        raise ImportFailure(f"Output must be a directory: {output}")
    for root in roots:
        check_local_path(root)
        if not root.exists() or not (root.is_dir() or root.is_file()):
            raise ImportFailure(f"Source is missing or is not a regular file/directory: {root}")
        if (root == output or root.is_relative_to(output)
                or (root.is_dir() and output.is_relative_to(root))):
            raise ImportFailure(f"Source and output must not overlap: {root} / {output}")
    return roots, output


def scan_sources(roots, stack, include_other, include_videos, max_file, max_total):
    candidates = []
    counts = {"sources": len(roots), "scanned_files": 0, "eligible_files": 0,
              "imported": 0, "duplicates": 0, "skipped": 0,
              "skipped_by_reason": {"outside_scope": 0, "videos_disabled": 0,
                                    "unsupported_extension": 0}}
    entries = total = 0

    def consider(root, relative, size, directory=False, archive=None, member=None):
        nonlocal entries, total
        entries += 1
        if entries > MAX_ENTRIES:
            raise ImportFailure(f"More than {MAX_ENTRIES:,} entries; use smaller source batches.")
        canonical_parts(relative, directory)
        if directory:
            return
        counts["scanned_files"] += 1
        selection, reason = classify(relative, include_other, include_videos)
        if selection is None:
            counts["skipped"] += 1
            counts["skipped_by_reason"][reason] += 1
            return
        if size <= 0 or size > max_file:
            raise ImportFailure(f"Eligible file is empty or exceeds --max-file-mib: "
                                f"{root.name}/{relative} ({size} bytes)")
        total += size
        if total > max_total:
            raise ImportFailure("Eligible bytes exceed --max-total-mib; use smaller batches "
                                "or explicitly increase that limit.")
        category, extension, media_type = selection
        candidates.append(Candidate(root, relative, category, extension, media_type,
                                    size, archive, member))
        counts["eligible_files"] += 1

    for root in roots:
        if root.is_file():
            try:
                stream = stack.enter_context(open_regular(root))
                archive = stack.enter_context(zipfile.ZipFile(stream))
            except (OSError, zipfile.BadZipFile, ValueError) as error:
                raise ImportFailure(f"Cannot read ZIP {root.name}: {error}. Supply an intact "
                                    "ZIP, not a binary split segment.") from error
            for member in archive.infolist():
                mode = member.external_attr >> 16
                if (stat.S_ISLNK(mode) or
                        (member.create_system == 0 and member.external_attr & 0x400)):
                    raise ImportFailure(f"ZIP symlink/reparse point is not allowed: "
                                        f"{root.name}/{member.orig_filename}")
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ImportFailure(f"ZIP contains a non-regular entry: {member.orig_filename}")
                consider(root, member.orig_filename, member.file_size, member.is_dir(),
                         archive, member)
        else:
            pending = [root]
            while pending:
                directory = pending.pop()
                check_local_path(directory)
                with os.scandir(directory) as children:
                    for child in children:
                        info = child.stat(follow_symlinks=False)
                        relative = Path(child.path).relative_to(root).as_posix()
                        if is_link(info):
                            raise ImportFailure(f"Source symlink/junction is not allowed: {relative}")
                        is_directory = stat.S_ISDIR(info.st_mode)
                        if not is_directory and not stat.S_ISREG(info.st_mode):
                            raise ImportFailure(f"Source contains a non-regular file: {relative}")
                        consider(root, relative, info.st_size, is_directory)
                        if is_directory:
                            pending.append(Path(child.path))
    if not candidates:
        raise ImportFailure("No eligible media found. Supply the export root or intact ZIP(s) "
                            "containing media/posts, media/reels, media/igtv, media/stories or "
                            "media/archived_posts. Videos need --include-videos; ambiguous "
                            "media/other needs --include-other-media.")
    candidates.sort(key=lambda c: (str(c.root), c.relative))
    return candidates, counts


@contextmanager
def open_regular(path):
    check_local_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ImportFailure(f"Not a regular file: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0)
                         | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        after = os.fstat(stream.fileno())
        if is_link(after) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ImportFailure(f"File changed while opening; retry with stable sources: {path}")
        yield stream


def stream_hash(stream, max_bytes, destination=None):
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(min(CHUNK_SIZE, max_bytes - size + 1)):
        size += len(chunk)
        if size > max_bytes:
            raise ImportFailure("A file exceeded its declared size or --max-file-mib; "
                                "the source may have changed or be corrupt.")
        digest.update(chunk)
        if destination is not None:
            destination.write(chunk)
    return digest.hexdigest(), size


def verify_existing(path, digest, size, max_file):
    with open_regular(path) as stream:
        if os.fstat(stream.fileno()).st_size != size or size > max_file:
            raise ImportFailure(f"Output conflict (size/limit mismatch): {path}. "
                                "Restore the original or use a new output directory.")
        actual_hash, actual_size = stream_hash(stream, size)
    if (actual_hash, actual_size) != (digest, size):
        raise ImportFailure(f"Output conflict (SHA256 mismatch): {path}. "
                            "Restore the original or use a new output directory.")


def output_name(digest, extension, media_type):
    extension = {".jpeg": ".jpg", ".jpe": ".jpg", ".tif": ".tiff"}.get(extension, extension)
    folder = "images" if media_type == "photo" else "videos"
    return f"{folder}/cake-{digest}{extension}"


def association_key(source):
    return source["source_id"], source["path"], source["extension"]


def load_manifest(output, max_file, max_total):
    path = output / "manifest.json"
    if not path.exists():
        check_local_path(path)
        return {}
    with open_regular(path) as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ImportFailure("Existing manifest exceeds the 32 MiB safety limit.")
    try:
        manifest = json.loads(raw)
        if (type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
                or not isinstance(manifest["files"], list)):
            raise ValueError("unsupported schema")
        records = {}
        total = 0
        for record in manifest["files"]:
            digest, size = record["sha256"], record["bytes"]
            extension, kind = record["extension"], record["media_type"]
            if (set(record) != {"sha256", "bytes", "extension", "media_type", "file", "sources"}
                    or not re.fullmatch("[0-9a-f]{64}", digest) or digest in records
                    or type(size) is not int or size <= 0
                    or kind not in ("photo", "video")
                    or extension not in (PHOTO_EXTENSIONS if kind == "photo" else VIDEO_EXTENSIONS)
                    or record["file"] != output_name(digest, extension, kind)
                    or not isinstance(record["sources"], list) or not record["sources"]):
                raise ValueError("invalid media record")
            for source in record["sources"]:
                if (set(source) != {"source", "source_id", "path", "category", "extension"}
                        or not isinstance(source["source"], str)
                        or len(canonical_parts(source["source"])) != 1
                        or not re.fullmatch("[0-9a-f]{64}", source["source_id"])
                        or source["category"] != category_for(canonical_parts(source["path"]), True)
                        or source["category"] not in CATEGORIES | {"other"}
                        or source["extension"] != Path(source["path"]).suffix.lower()
                        or source["extension"] not in PHOTO_EXTENSIONS | VIDEO_EXTENSIONS):
                    raise ValueError("invalid source association")
            total += size
            if total > max_total:
                raise ImportFailure("Existing collection exceeds --max-total-mib; "
                                    "explicitly increase that limit.")
            records[digest] = record
    except (KeyError, TypeError, ValueError, ImportFailure) as error:
        raise ImportFailure(f"Invalid existing manifest: {error}. Restore it or use a "
                            "new output directory; it will not be overwritten.") from error
    for record in records.values():
        verify_existing(output / record["file"], record["sha256"], record["bytes"], max_file)
    return records


@contextmanager
def output_lock(output):
    path = output / ".import.lock"
    check_local_path(path)
    try:
        lock = path.open("x", encoding="ascii")
    except FileExistsError as error:
        raise ImportFailure("Output is locked (.import.lock). Wait for the other importer. "
                            "After a crash, remove this file only after confirming no import "
                            "is running.") from error
    try:
        with lock:
            lock.write(str(os.getpid()))
        yield
    finally:
        path.unlink()


def import_media(sources, output, *, include_videos=False, include_other_media=False,
                 max_file_mib=512, max_total_mib=20_480):
    if max_file_mib <= 0 or max_total_mib <= 0:
        raise ImportFailure("Size limits must be positive.")
    max_file, max_total = max_file_mib * MIB, max_total_mib * MIB
    roots, output = validate_roots(sources, output)
    with ExitStack() as stack:
        candidates, counts = scan_sources(roots, stack, include_other_media, include_videos,
                                         max_file, max_total)
        output.mkdir(parents=True, exist_ok=True)
        stack.enter_context(output_lock(output))
        for folder in ("images", "videos"):
            check_local_path(output / folder)
            if (output / folder).exists() and not (output / folder).is_dir():
                raise ImportFailure(f"Output {folder} must be a directory.")
        records = load_manifest(output, max_file, max_total)
        collection_bytes = sum(record["bytes"] for record in records.values())
        associations = {digest: {association_key(source) for source in record["sources"]}
                        for digest, record in records.items()}
        staging = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".import-",
                                                                        dir=output)))
        pending = []
        for index, candidate in enumerate(candidates):
            staged = staging / f"{index}.part"
            try:
                source = (candidate.archive.open(candidate.member)
                          if candidate.archive is not None
                          else open_regular(candidate.root / candidate.relative))
                with source as stream, staged.open("xb") as destination:
                    digest, size = stream_hash(stream, min(candidate.size, max_file), destination)
                if size != candidate.size:
                    raise ImportFailure("File size changed or archive is truncated.")
            except (OSError, zipfile.BadZipFile, RuntimeError, EOFError, zlib.error,
                    ImportFailure) as error:
                raise ImportFailure(f"Cannot import {candidate.root.name}/{candidate.relative}: "
                                    f"{error}") from error
            association = candidate.association()
            key = association_key(association)
            if digest in records:
                counts["duplicates"] += 1
                if key not in associations[digest]:
                    records[digest]["sources"].append(association)
                    associations[digest].add(key)
                staged.unlink()
                continue
            collection_bytes += size
            if collection_bytes > max_total:
                raise ImportFailure("Resulting collection exceeds --max-total-mib; use a "
                                    "separate output batch or explicitly increase that limit.")
            relative = output_name(digest, candidate.extension, candidate.media_type)
            target = output / relative
            check_local_path(target)
            if target.exists():
                verify_existing(target, digest, size, max_file)
                counts["duplicates"] += 1
                staged.unlink()
            else:
                pending.append((staged, target))
                counts["imported"] += 1
            records[digest] = {"sha256": digest, "bytes": size, "file": relative,
                               "extension": candidate.extension,
                               "media_type": candidate.media_type, "sources": [association]}
            associations[digest] = {key}
        for record in records.values():
            record["sources"].sort(key=association_key)
        counts["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest = {"schema_version": 1, "scope": SCOPE, "media_validation": MEDIA_VALIDATION,
                    "last_successful_run": counts,
                    "files": sorted(records.values(), key=lambda r: r["sha256"])}
        serialized = (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
        if len(serialized) > MAX_MANIFEST_BYTES:
            raise ImportFailure("Resulting manifest exceeds 32 MiB; use separate output batches.")
        manifest_stage = staging / "manifest.json"
        with manifest_stage.open("xb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        created = []
        committed = False
        try:
            for staged, target in pending:
                target.parent.mkdir(exist_ok=True)
                check_local_path(target)
                # Exclusive creation never overwrites a pre-existing original.
                with target.open("xb") as destination:
                    created.append(target)
                    with staged.open("rb") as source:
                        shutil.copyfileobj(source, destination, CHUNK_SIZE)
                    destination.flush()
                    os.fsync(destination.fileno())
            check_local_path(output / "manifest.json")
            os.replace(manifest_stage, output / "manifest.json")
            committed = True
        finally:
            if not committed:
                for path in reversed(created):
                    path.unlink()
    return manifest


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline-only, byte-preserving Instagram export media importer.",
        epilog=("Supported own-upload folders: media/posts, media/reels, media/igtv, "
                "media/stories, media/archived_posts, with optional wrapper directories. "
                "media/other is excluded unless explicitly enabled. Messages, contacts, "
                "profile pictures, ads and saved/liked/tagged folders are excluded. "
                "ZIPs must be independent complete archives, not binary split segments. "
                f"At most {MAX_ENTRIES:,} entries per run; manifest limit 32 MiB. "
                "Unsafe paths, symlinks and junctions are rejected. "
                "Inputs must remain unchanged during import. " + MEDIA_VALIDATION + " " + SCOPE))
    parser.add_argument("sources", metavar="SOURCE", nargs="+",
                        help="local ZIP archive(s) or extracted export root directory/directories")
    parser.add_argument("--output", required=True, type=Path,
                        help=r"local collection directory, e.g. .local\instagram\imported")
    parser.add_argument("--include-videos", action="store_true",
                        help="also preserve video files in videos/; never extract still frames")
    parser.add_argument("--include-other-media", action="store_true",
                        help="opt in to ambiguous media/other; review its contents yourself")
    parser.add_argument("--max-file-mib", type=positive_int, default=512,
                        help="maximum uncompressed bytes per file, in MiB (default: 512)")
    parser.add_argument("--max-total-mib", type=positive_int, default=20_480,
                        help="maximum eligible input bytes and cumulative collection bytes, "
                             "each in MiB (default: 20480); duplicates count toward input limit")
    args = parser.parse_args(argv)
    try:
        manifest = import_media(args.sources, args.output, include_videos=args.include_videos,
                                include_other_media=args.include_other_media,
                                max_file_mib=args.max_file_mib, max_total_mib=args.max_total_mib)
    except (ImportFailure, OSError, zipfile.BadZipFile, RuntimeError, EOFError,
            ValueError, zlib.error) as error:
        print(f"ERROR: {error}\nImport did not complete normally. The manifest, if present, "
              "describes the last committed run, not necessarily this attempt.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("ERROR: Import interrupted. The manifest, if present, describes the last "
              "committed run, not necessarily this attempt.", file=sys.stderr)
        return 130
    counts = manifest["last_successful_run"]
    print(f"Imported {counts['imported']} new file(s); duplicates {counts['duplicates']}; "
          f"skipped {counts['skipped']}; eligible {counts['eligible_files']}.")
    print(f"Collection: {len(manifest['files'])} unique file(s). "
          f"Manifest: {args.output / 'manifest.json'}")
    print(MEDIA_VALIDATION)
    print(SCOPE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
