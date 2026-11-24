"""Package six landscape and six 3:4 launch images without posting to social media."""

import argparse
from hashlib import sha256
import html
import json
import math
from pathlib import Path
import shutil
import zipfile

from compose_launch_campaign import DESIGN_REVISION, FINAL_REVISION, validate_jpeg, validate_layout_contract, validate_portrait_lighting
from campaign_cream import CREAM_DESIGN_REVISION, FROSTED_DESIGN_REVISION, validate_cream_receipt, validate_frosted_receipt
from campaign_gaussian import validate_distinct_recipes
from campaign_cream import validate_portrait_grounds
from campaign_phone import validate_raised_phones


NAMES = [
    ("01-welcome.jpg", "Our little corner is now online", "The real desktop and mobile home page, with the Whisk & Crumbs wooden sign and striped awning."),
    ("02-bakery-entrance.jpg", "Come on in", "Desktop and mobile views of the website's illustrated bakery entrance, with glowing whisk and heart neon emblems on the glass doors."),
    ("03-our-story.jpg", "A little care in every layer", "The original home-baking story and recipe note, shown at desktop and mobile sizes."),
    ("04-cake-notebooks.jpg", "Find your kind of cake", "The website's pink category notebooks, real cake stickers and pastel edge tabs on desktop and mobile."),
    ("05-open-notebook.jpg", "Take a closer look", "A real four-photo Decorated cakes catalogue open on desktop and mobile, with clickable cake images, centered names and arrow tags on the right."),
    ("06-simple-ordering.jpg", "Your next cake starts with hello", "The website's actual Instagram enquiry section on desktop and mobile."),
]
CANONICAL = "https://zanark.github.io/WhiskAndCrumbs/"
PORTRAIT_ALT = {
    "02-bakery-entrance.jpg": "The complete illustrated bakery entrance with glowing whisk and heart neon emblems on its glass doors, presented as an oversized, genuine website feature without browser or phone mockups.",
    "03-our-story.jpg": "The original recipe-note illustration presented as a large, genuine website detail, without device frames.",
    "04-cake-notebooks.jpg": "All six real category notebooks presented as an uncluttered website collection, including their real cake stickers and exterior tabs; no phone mockup.",
    "05-open-notebook.jpg": "A large genuine four-photo Decorated cakes catalogue, with centered names, clickable images and both page-arrow tags attached on the right; no phone mockup.",
}


def image_alt(filename, edition, cream_background=False, frosted_glass=False):
    if edition not in {"wide", "portrait"}:
        raise ValueError("Unknown campaign edition.")
    common = next(alt for name, _, alt in NAMES if name == filename)
    description = PORTRAIT_ALT.get(filename, common) if edition == "portrait" else common
    if frosted_glass:
        return description + " All foreground content sits on lightly frosted glass above a unique arrangement of irregular cream clusters and small droplets."
    return description + (" Original sculpted cream blobs decorate the editorial background; the website capture is unchanged."
                          if cream_background else "")


def validate_delivery_source(source):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("canonical_url") != CANONICAL or manifest.get("schema_version") != 2:
        raise ValueError("Expected the current editorial campaign manifest and verified URL.")
    if manifest.get("draft") is not False or manifest.get("capture_manifest", {}).get("campaign_revision") != FINAL_REVISION:
        raise ValueError("Refusing to package draft or stale campaign captures.")
    layout = validate_layout_contract(manifest["exports"])
    if manifest.get("layout_contract") != layout:
        raise ValueError("Campaign layout receipt does not match its actual devices/features.")
    for entry in manifest["exports"]:
        if manifest.get("design_revision") in {DESIGN_REVISION, CREAM_DESIGN_REVISION, FROSTED_DESIGN_REVISION}:
            validate_raster_receipt(entry)
        if manifest.get("design_revision") == CREAM_DESIGN_REVISION:
            if not manifest.get("cream_backgrounds", {}).get("manifest_sha256"):
                raise ValueError("Cream campaign lacks material-layer provenance.")
            validate_cream_receipt(entry)
        if manifest.get("design_revision") == FROSTED_DESIGN_REVISION:
            validate_frosted_receipt(entry)
        for feature in entry.get("features", []):
            if feature.get("draft_only") is not False or feature["source"].get("feature_type") != "element-capture":
                raise ValueError("A final editorial feature must be a checked genuine element capture.")
            if not feature.get("important_content_verified_by_capture_owner"):
                raise ValueError("Editorial feature lacks complete-content verification.")
    if manifest.get("design_revision") == FROSTED_DESIGN_REVISION:
        source = manifest.get("cream_backgrounds", {})
        if not source.get("manifest_sha256") or source.get("layout_validation", {}).get("maximum_normalized_coverage_iou", 1) >= .65:
            raise ValueError("Frosted campaign lacks distinct material-layout evidence.")
        validate_distinct_recipes([entry["frosted_cream"] for entry in manifest["exports"]])
    variation = manifest.get("portrait_background_variation")
    if variation is not None or any("background_palette" in entry for entry in manifest["exports"]):
        if manifest.get("design_revision") != FROSTED_DESIGN_REVISION:
            raise ValueError("Portrait colour variance requires the frosted edition.")
        if variation != validate_portrait_grounds(manifest["exports"]):
            raise ValueError("Portrait colour receipt does not match the actual exports.")
    raised = manifest.get("raised_phone_glass")
    if raised is not None or any("raised_glass" in device for entry in manifest["exports"] for device in entry["devices"]):
        actual = validate_raised_phones(manifest["exports"])
        if (not isinstance(raised, dict) or any(raised.get(key) != value for key, value in actual.items())
                or len(raised.get("renderer_sha256", "")) != 64):
            raise ValueError("Raised phone receipt does not match the actual exports.")
    lighting = manifest.get("portrait_background_lighting")
    if lighting is not None or any("background_lighting" in entry for entry in manifest["exports"]):
        if lighting != validate_portrait_lighting(manifest["exports"]):
            raise ValueError("Portrait lighting receipt does not match the actual exports.")
    return manifest


def validate_raster_receipt(entry):
    proof = entry.get("raster_typography", {})
    width, height = entry["validation"]["dimensions"]
    if proof.get("passed") is not True or proof.get("jpeg_sha256") != entry.get("sha256"):
        raise ValueError("Missing or mismatched actual-JPEG raster review.")
    if proof.get("tested_widths") != [width, 540]:
        raise ValueError("Raster review must cover native and 540px output.")
    critical = [text for text in entry["texts"] if text["role"] in {"headline", "editorial-body"}]
    expected = [(text["text"], text["role"], target)
                for target in (width, 540) for text in critical]
    actual = [(check["text"], check["role"], check["target_dimensions"][0])
              for check in proof.get("checks", [])]
    if not critical or actual != expected:
        raise ValueError("Raster review does not cover every critical copy line at both sizes.")
    for check in proof["checks"]:
        target_width = check["target_dimensions"][0]
        threshold = 3 if check["role"] == "headline" else 4.5
        if (check.get("passed") is not True or check["threshold"] != threshold
                or check["target_dimensions"] != [target_width, round(height * target_width / width)]
                or not math.isfinite(check["fifth_percentile_contrast"])
                or check["fifth_percentile_contrast"] < threshold
                or check["opaque_core_pixels"] < 20
                or (check["role"] == "editorial-body" and check["effective_font_px"] < 16)):
            raise ValueError("Actual-JPEG raster review contains a failed readability check.")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def package(source, output):
    if output.exists():
        raise FileExistsError(f"Preserve an existing delivery: {output}")
    source_manifest = validate_delivery_source(source)
    cream_background = source_manifest.get("design_revision") == CREAM_DESIGN_REVISION
    frosted_glass = source_manifest.get("design_revision") == FROSTED_DESIGN_REVISION
    expected = {(entry["edition"], entry["filename"]): entry for entry in source_manifest["exports"]}
    records = []
    for folder, dimensions, destination in [
        ("wide", (1600, 1000), "readme-landscape"),
        ("portrait", (1080, 1440), "instagram-3x4"),
    ]:
        paths = sorted((source / folder).glob("*.jpg"))
        if {path.name for path in paths} != {name for name, _, _ in NAMES}:
            raise ValueError(f"Expected exactly six named JPEGs in {source / folder}")
        for path in paths:
            validate_jpeg(path.read_bytes(), dimensions)
            if digest(path) != expected[(folder, path.name)]["sha256"]:
                raise ValueError(f"Export differs from its checked composition manifest: {path}")
            if path.stat().st_size > 4_000_000:
                raise ValueError(f"Unexpectedly large image: {path}")
            records.append({"source": str(path), "file": f"{destination}/{path.name}",
                            "dimensions": dimensions, "sha256": digest(path), "bytes": path.stat().st_size})
    if len({record["sha256"] for record in records}) != 12:
        raise ValueError("The twelve designed variants must be distinct exports.")
    output.mkdir(parents=True)
    for record in records:
        destination = output / record["file"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(record["source"], destination)
        if digest(destination) != record["sha256"]:
            raise ValueError(f"Delivery copy changed: {destination}")
    caption = (
        "Our little corner of the baking world is now online.\n\n"
        "Explore the illustrated bakery entrance, discover our original recipe note, and browse the real cake collection.\n\n"
        "Explore Whisk & Crumbs, read our little story, and open six notebooks of cakes and chocolates "
        "we've made. Take a closer look at the real photos, then use the website's Instagram link "
        "when you're ready to start an enquiry.\n\n"
        f"Visit: {CANONICAL}\n\n"
        "Home-baked vegetarian cakes. We confirm price and availability personally; an enquiry is not a confirmed order.\n\n"
        "#WhiskAndCrumbs #HomeBakedCakes #VegetarianCakes #NewWebsite\n"
    )
    (output / "CAPTION.txt").write_text(caption, encoding="utf-8")
    palettes = source_manifest.get("portrait_background_variation", {}).get("grounds", {})
    tint_strength = source_manifest.get("portrait_background_variation", {}).get("tint_strength", 1)
    def description(name, edition):
        text = image_alt(name, edition, cream_background, frosted_glass)
        if edition == "portrait" and palettes:
            text += f" The editorial background is {palettes[Path(name).stem]['name'].lower()}; the cream remains ivory."
            if tint_strength != 1:
                text += f" Its background tint is reduced to {tint_strength:.1%} strength with white; foreground content is not faded."
        if source_manifest.get("raised_phone_glass") and edition == "portrait" and name in {"01-welcome.jpg", "06-simple-ordering.jpg"}:
            text += " The phone has a rounded raised-glass rim, edge reflections and a visible sidewall; its website view is unaltered."
        return text
    (output / "ALT-TEXT.txt").write_text(
        "\n\n".join(f"{edition.upper()} / {name}\n{description(name, edition)}"
                   for edition in ("portrait", "wide") for name, _, _ in NAMES) + "\n", encoding="utf-8"
    )
    cards = lambda directory, edition: "\n".join(
        f'<figure><a href="{directory}/{name}"><img src="{directory}/{name}" alt="{html.escape(description(name, edition))}" loading="lazy"></a>'
        f'<figcaption>{html.escape(title)}'
        f'{html.escape(" - " + palettes[Path(name).stem]["name"]) if edition == "portrait" and palettes else ""}'
        f'</figcaption></figure>' for name, title, _ in NAMES
    )
    preview = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Whisk &amp; Crumbs - Website launch kit</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f5ebdd;color:#34483a;font:18px/1.6 system-ui,sans-serif}
main{width:min(1440px,calc(100% - 40px));margin:40px auto}h1{font-size:clamp(28px,4vw,48px);line-height:1.15}
a{color:inherit}nav{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}nav a{display:inline-flex;align-items:center;min-height:48px;padding:10px 18px;border:1px solid #34483a;border-radius:12px;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:24px}
figure{margin:0}img{display:block;width:100%;height:auto;border-radius:8px;box-shadow:0 10px 25px #34483a20}
figcaption{padding:12px 0;font-weight:600}summary{cursor:pointer;min-height:48px;font-size:24px;font-weight:700;padding:12px 0}
details{margin:30px 0}p{max-width:85ch}:focus-visible{outline:3px solid #a45137;outline-offset:4px}
</style></head><body><main>
<h1>Whisk &amp; Crumbs<br>Website launch kit</h1>
<p>Six 3:4 Instagram images and six landscape README images. The first and last Instagram images pair desktop and phone views;
the middle four feature the entrance, original recipe note, six notebooks and open photo book without phone mockups.
All six landscape images retain genuine desktop and mobile views. Device frames are editorial illustrations, not photographs of physical devices.</p>
<nav><a href="Whisk-and-Crumbs-Instagram-3x4.zip">Download six Instagram images</a>
<a href="CAPTION.txt">Launch caption</a><a href="ALT-TEXT.txt">Image descriptions</a></nav>
<details open><summary>Instagram - 1080 x 1440 (3:4)</summary><div class="grid">PORTRAITS</div></details>
<details><summary>README - 1600 x 1000</summary><div class="grid">LANDSCAPES</div></details>
<p>Nothing has been posted or scheduled on Instagram. The upload folder contains only the six numbered JPEGs.
The images use the existing Whisk &amp; Crumbs identity and verified website address, without assuming a new account handle.</p>
</main></body></html>"""
    if cream_background:
        preview = preview.replace("<nav>", "<p>This edition adds static sculpted cream backgrounds to the launch images only. "
                                  "It uses the latest website views; the live website background is unchanged.</p>\n<nav>", 1)
    if frosted_glass:
        preview = preview.replace("<nav>", "<p>The foreground sits on one lightly frosted panel, with only 8% tint. "
                                  "Each image has its own irregular cream clusters and smaller droplets behind the glass. "
                                  "No text-shaped cutouts are used. This is static launch artwork; the live website background is unchanged.</p>\n<nav>", 1)
    if palettes:
        preview = preview.replace("<nav>", "<p>Instagram-only colour edition: buttercream, blush, soft green, "
                                  "peach, oat and vanilla backgrounds. Cream sculptures and lightly frosted glass remain; "
                                  "the README landscapes and website are unchanged.</p>\n<nav>", 1)
    if tint_strength != 1:
        preview = preview.replace("<nav>", f"<p>The Instagram backgrounds retain only {tint_strength:.1%} "
                                  "of their previous tint, blended toward white. Text, photographs, cream sculptures "
                                  "and phone details are not faded; glass remains lightly tinted.</p>\n<nav>", 1)
    if source_manifest.get("portrait_background_lighting"):
        preview = preview.replace("<nav>", "<p>The repeated diagonal background light and shadow bands have "
                                  "been removed from all six Instagram images. Colours, cream and rounded "
                                  "phone-glass styling are retained.</p>\n<nav>", 1)
    (output / "preview.html").write_text(
        preview.replace("PORTRAITS", cards("instagram-3x4", "portrait")).replace("LANDSCAPES", cards("readme-landscape", "wide")),
        encoding="utf-8",
    )
    archive = output / "Whisk-and-Crumbs-Instagram-3x4.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for name, _, _ in NAMES:
            zipped.write(output / "instagram-3x4" / name, name)
    with zipfile.ZipFile(archive) as zipped:
        if len(zipped.namelist()) != 6 or set(zipped.namelist()) != {name for name, _, _ in NAMES}:
            raise ValueError("The Instagram archive must contain exactly six upload images.")
        for name in zipped.namelist():
            if zipped.read(name) != (output / "instagram-3x4" / name).read_bytes():
                raise ValueError(f"Archive copy differs: {name}")
    manifest = {
        "status": "packaged-not-posted", "canonical_url": CANONICAL,
        "outputs": [{key: value for key, value in record.items() if key != "source"} for record in records],
        "instagram_archive": {"file": archive.name, "sha256": digest(archive), "images": 6},
        "posting_performed": False, "image_tool_views": 0,
        "composition_manifest_sha256": digest(source / "manifest.json"),
        "capture_manifest": source_manifest["capture_manifest"],
        "layout_contract": source_manifest["layout_contract"],
        "design_revision": source_manifest.get("design_revision"),
        "actual_jpeg_raster_checks": sum(len(entry.get("raster_typography", {}).get("checks", []))
                                        for entry in source_manifest["exports"]),
        "owner_visual_acceptance": "Not established.",
    }
    if cream_background or frosted_glass:
        manifest["cream_backgrounds"] = source_manifest["cream_backgrounds"]
    if palettes:
        manifest["portrait_background_variation"] = source_manifest["portrait_background_variation"]
    if source_manifest.get("raised_phone_glass"):
        manifest["raised_phone_glass"] = source_manifest["raised_phone_glass"]
    if source_manifest.get("portrait_background_lighting"):
        manifest["portrait_background_lighting"] = source_manifest["portrait_background_lighting"]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"delivery": str(output.resolve()), "preview": str((output / "preview.html").resolve()),
                      "instagram_images": 6, "readme_images": 6, "archive": str(archive.resolve())}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.source, args.output)
