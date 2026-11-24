"""Capture honest complete desktop/mobile viewports for the website launch artwork."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from urllib.request import urlopen

from PIL import Image
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://zanark.github.io/WhiskAndCrumbs/"
SCENES = [
    ("01-welcome", "home"),
    ("02-bakery-entrance", ""),
    ("03-our-story", "story"),
    ("04-cake-notebooks", "cakes"),
    ("05-open-notebook", "cakes"),
    ("06-simple-ordering", "order"),
]
FEATURES = [
    ("02-bakery-entrance", "", ".entrance-shop"),
    ("03-our-story", "story", ".recipe-note"),
    ("04-cake-notebooks", "cakes", "#category-notebooks"),
    ("05-open-notebook", "cakes", "#notebook-dialog"),
]


def digest(value):
    return sha256(value).hexdigest()


def decode(page, selector):
    for image in page.locator(selector).all():
        if image.get_attribute("loading") == "lazy":
            image.scroll_into_view_if_needed()
        image.evaluate("async n=>{await n.decode();if(!n.naturalWidth)throw new Error('Missing capture image')}")


def hold_cream_for_capture(page):
    layer = page.locator("#cream-effects")
    if not layer.count() or not layer.is_visible():
        return False
    button = page.locator("#cream-motion-toggle")
    if button.get_attribute("aria-pressed") != "true":
        if page.locator("dialog[open]").count():
            page.keyboard.press("Alt+Shift+P")
        else:
            # Use the existing control's action without scrolling the footer into this capture.
            button.evaluate("node=>node.click()")
    expect(layer).to_have_attribute("data-state", "paused")
    return True


def capture(url, output, source_dir=None):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Use the loopback preview; this tool does not upload media.")
    if parsed.query or parsed.fragment:
        raise ValueError("Use a loopback base URL without a query or fragment.")
    if output.exists():
        raise FileExistsError(f"Preserve existing captures: {output}")
    site = (source_dir or ROOT / "site").resolve()
    if not site.is_relative_to(ROOT) or not (site / "index.html").is_file():
        raise ValueError("Capture sources must be a generated site inside this repository.")
    with urlopen(url.rstrip("/") + "/", timeout=30) as response:
        if response.read() != (site / "index.html").read_bytes():
            raise ValueError("The preview is not serving the declared generated source.")
    output.mkdir(parents=True)
    source_names = [
        "index.html", "styles.css", "readability.css", "entrance-shop.css",
        "cozy-bakery.css", "main.mjs", "notebooks.mjs", "entrance.mjs",
        "bakery-interior.mjs", "bakery-view.mjs", "bakery-scene.mjs",
        "awning.mjs", "awning-cloth.mjs", "assets/bakery-awning.svg", "assets/bakery-awning-supports.svg",
        "assets/bakery-sign-wood.webp", "assets/bakery-paint-atlas.png",
        "assets/bakery-light-bake.bin", "assets/bakery-interior-wide.webp",
        "assets/bakery-interior-portrait.webp", "assets/bakery-interior-short.webp",
        "assets/bakery-facade-upper.svg", "assets/bakery-facade-upper-mobile.svg",
        "assets/bakery-facade-ground.svg", "assets/bakery-facade-plaster.webp",
    ]
    if b'data-cream-effects="enabled"' in (site / "index.html").read_bytes():
        source_names += ["cream.css", "cream.mjs", "cream-model.mjs", "cream-material.mjs",
                         "assets/bakery-glass-etching.svg"]
    sources = {name: digest((site / name).read_bytes()) for name in source_names}
    records, features = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        for name, fragment in SCENES:
            for device, width, height, touch in [("desktop", 1280, 800, False), ("mobile", 390, 844, True)]:
                context = browser.new_context(
                    viewport={"width": width, "height": height}, device_scale_factor=2,
                    is_mobile=touch, has_touch=touch, reduced_motion="no-preference",
                    color_scheme="light", forced_colors="none",
                )
                page = context.new_page()
                errors, requests = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("requestfailed", lambda request: errors.append(f"{request.url}: {request.failure}"))
                page.on("request", lambda request: requests.append(request.url))
                page.goto(url.rstrip("/") + "/" + ("#" + fragment if fragment else ""), wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                expect(page.locator('link[rel="canonical"]')).to_have_attribute("href", CANONICAL)
                if name == "01-welcome":
                    decode(page, ".site-header img,.site-awning img,#home img")
                    page.evaluate("scrollTo({top:0,behavior:'instant'})")
                elif name == "02-bakery-entrance":
                    expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
                    decode(page, "#bakery-entrance img")
                    expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=15000)
                elif name == "03-our-story":
                    if touch:
                        page.locator(".recipe-note").scroll_into_view_if_needed()
                    else:
                        page.locator("#story").evaluate("n=>scrollTo({top:n.offsetTop-24,behavior:'instant'})")
                elif name == "04-cake-notebooks":
                    expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
                    decode(page, ".notebook-cover img")
                    if touch:
                        page.locator('.notebook-cover[data-category="birthday-cakes"]').scroll_into_view_if_needed()
                    else:
                        page.locator("#cakes").evaluate("n=>scrollTo({top:n.offsetTop-24,behavior:'instant'})")
                elif name == "05-open-notebook":
                    expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
                    cover = page.locator('.notebook-cover[data-category="decorated-cakes"]')
                    cover.tap() if touch else cover.click()
                    expect(page.locator("#notebook-dialog")).to_be_visible()
                    page.wait_for_function("document.querySelector('#notebook-dialog .category-notebook').getAnimations().length===0")
                    decode(page, "#notebook-dialog article:visible img")
                    expect(page.locator("#notebook-dialog article:visible")).to_have_count(4)
                else:
                    decode(page, ".bakery-shelf img")
                    page.locator("#order").evaluate("n=>scrollTo({top:n.offsetTop-24,behavior:'instant'})")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(250)
                if name == "01-welcome":
                    page.evaluate("scrollTo({top:0,behavior:'instant'})")
                    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                page.wait_for_function("document.querySelector('.site-awning')?.dataset.fabricState!=='moving'", timeout=26000)
                cream_paused = hold_cream_for_capture(page)
                if name == "01-welcome":
                    assert page.evaluate("scrollY === 0"), "Welcome capture moved away from the complete header."
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (name, device)
                geometry = page.evaluate("""()=>{
                  const visible=n=>{const b=n.getBoundingClientRect();return b.width>0&&b.height>0&&b.bottom>0&&b.top<innerHeight&&getComputedStyle(n).visibility!=='hidden'};
                  return {scrollY,viewport:[innerWidth,innerHeight],
                    images:[...document.querySelectorAll('img[src]')].filter(visible).map(n=>({
                      src:n.currentSrc,loaded:n.complete&&n.naturalWidth>0,
                      natural:[n.naturalWidth,n.naturalHeight]})),
                    elements:[...document.querySelectorAll('.site-header,.site-awning,#home,#story,#cakes,#order,.recipe-note,.notebook-cover,#notebook-dialog,#order-contact,.mobile-enquire')].filter(visible).map(n=>{
                      const b=n.getBoundingClientRect();return {id:n.id,classes:n.className,bounds:{x:b.x,y:b.y,width:b.width,height:b.height}};
                    })};
                }""")
                assert all(image["loaded"] for image in geometry["images"]), geometry
                assert not errors, errors
                assert all(request.startswith(url) for request in requests), requests
                payload = page.screenshot(full_page=False, animations="disabled", caret="hide")
                with Image.open(BytesIO(payload)) as image:
                    assert image.size == (width * 2, height * 2)
                filename = f"{name}-{device}.png"
                (output / filename).write_bytes(payload)
                records.append({
                    "id": name, "device": device, "file": filename, "sha256": digest(payload),
                    "viewport_css": [width, height], "raster_pixels": [width * 2, height * 2],
                    "dpr": 2, "touch_emulated": touch, "source_url": page.url,
                    "capture": "Complete actual viewport; no section crop or page-style/DOM modification.",
                    "cream_motion": "Paused through the existing site's control action without changing scroll position." if cream_paused else "Not paused by this capture; unavailable or blocked at capture preparation.",
                    "browser_geometry": geometry, "browser_errors": errors,
                })
                context.close()
        feature_directory = output / "features"
        feature_directory.mkdir()
        for name, fragment, selector in FEATURES:
            context = browser.new_context(
                viewport={"width": 1280, "height": 1000}, device_scale_factor=2,
                reduced_motion="no-preference", color_scheme="light", forced_colors="none",
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: errors.append(f"{request.url}: {request.failure}"))
            page.goto(url.rstrip("/") + "/" + ("#" + fragment if fragment else ""), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            if name == "02-bakery-entrance":
                expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
                expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=15000)
                decode(page, "#bakery-entrance img")
            elif name == "04-cake-notebooks":
                expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
                decode(page, ".notebook-cover img")
            elif name == "05-open-notebook":
                page.locator('.notebook-cover[data-category="decorated-cakes"]').click()
                expect(page.locator("#notebook-dialog")).to_be_visible()
                page.wait_for_function("document.querySelector('#notebook-dialog .category-notebook').getAnimations().length===0")
                decode(page, "#notebook-dialog article:visible img")
                expect(page.locator("#notebook-dialog article:visible")).to_have_count(4)
            feature = page.locator(selector)
            feature.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            cream_paused = hold_cream_for_capture(page)
            bounds = feature.bounding_box()
            assert bounds and bounds["width"] > 0 and bounds["height"] > 0, selector
            capture_note = "Complete actual component bounds; no DOM/style changes."
            if name in {"03-our-story", "04-cake-notebooks"}:
                envelope = feature.evaluate("""node=>{
                  const boxes=[node,...node.querySelectorAll('*')].filter(n=>n.getClientRects().length)
                    .map(n=>n.getBoundingClientRect());
                  return {left:Math.min(...boxes.map(b=>b.left))+scrollX-28,
                    top:Math.min(...boxes.map(b=>b.top))+scrollY-28,
                    right:Math.max(...boxes.map(b=>b.right))+scrollX+28,
                    bottom:Math.max(...boxes.map(b=>b.bottom))+scrollY+28};
                }""")
                full_page = page.screenshot(full_page=True, animations="disabled", caret="hide")
                with Image.open(BytesIO(full_page)) as image:
                    crop = (
                        max(0, int(envelope["left"] * 2)),
                        max(0, int(envelope["top"] * 2)),
                        min(image.width, int(envelope["right"] * 2 + 1)),
                        min(image.height, int(envelope["bottom"] * 2 + 1)),
                    )
                    buffer = BytesIO()
                    image.crop(crop).save(buffer, format="PNG")
                    payload = buffer.getvalue()
                bounds = {"x": crop[0] / 2, "y": crop[1] / 2,
                          "width": (crop[2] - crop[0]) / 2, "height": (crop[3] - crop[1]) / 2}
                capture_note = "Complete actual component including decoration and shadows; bounded crop from full-page capture, no DOM/style changes."
            else:
                payload = feature.screenshot(animations="disabled", caret="hide")
            with Image.open(BytesIO(payload)) as image:
                pixels = list(image.size)
                assert abs(image.width / 2 - bounds["width"]) <= 2
                assert abs(image.height / 2 - bounds["height"]) <= 2
            assert not errors, errors
            filename = f"features/{name}.png"
            (output / filename).write_bytes(payload)
            features.append({
                "id": name, "file": filename, "selector": selector, "sha256": digest(payload),
                "raster_pixels": pixels, "dpr": 2, "viewport_css": [1280, 1000],
                "capture": capture_note,
                "cream_motion": "Paused through the existing site's control action without changing scroll position." if cream_paused else "Not paused by this capture; unavailable or blocked at capture preparation.",
                "bounds_css": bounds, "source_url": page.url, "browser_errors": errors,
            })
            context.close()
        browser_version = browser.version
        browser.close()
    assert sources == {name: digest((site / name).read_bytes()) for name in source_names}, "Site changed during capture."
    result = {
        "status": "captured-and-checked", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "campaign_revision": "editorial-20261009-final",
        "source_worktree_dirty": bool(subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", "site"], cwd=ROOT).strip()),
        "canonical_url": CANONICAL, "browser": browser_version, "source_sha256": sources,
        "source_directory": str(site.relative_to(ROOT)),
        "captures": records, "features": features,
        "image_tool_views": 0, "limitations": [
            "These are real browser viewports with mobile emulation, not photographs of physical devices.",
            "Raw captures are not a visual-approval claim and are not publication assets by themselves.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"captures": len(records), "features": len(features),
                      "manifest": str(output / "manifest.json"), "image_tool_views": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, help="Explicit reviewed generated site, instead of the main worktree.")
    args = parser.parse_args()
    capture(args.url, args.output, args.source_dir)
