"""Create six landscape README compositions from the real, locally served website.

Example:
    python .\\scripts\\generate_readme_showcase.py --url http://127.0.0.1:4173/ \
        --output .\\web\\assets\\showcase --evidence .\\.local\\readme-showcase-20261007

Outputs and evidence are immutable: use separate --output and --evidence revision
directories if bytes differ. This program captures and decodes images; it does
not open a viewer, claim visual approval, or process the private photo archive.
"""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from playwright.sync_api import sync_playwright

from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "web" / "assets" / "fonts"
PRIVATE = ROOT / ".local" / "readme-showcase-20261007"
PUBLIC = ROOT / "web" / "assets" / "showcase"
CANONICAL = "https://zanark.github.io/WhiskAndCrumbs/"
CREAM = "#f5ebdd"
GREEN = "#34483a"
ACCENT = "#a45137"
PINK = "rgb(251, 237, 242)"
SIZE = (1600, 1000)
SCALE = 2
FILENAMES = (
    "01-welcome.jpg",
    "02-bakery-entrance.jpg",
    "03-our-story.jpg",
    "04-cake-notebooks.jpg",
    "05-open-notebook.jpg",
    "06-simple-ordering.jpg",
)


def digest(data):
    return sha256(data).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def write_json(path, value):
    save_preserving_existing(
        path, (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    )


def image_file(path):
    with Image.open(path) as image:
        return image.convert("RGBA")


def rectangle(box):
    return [round(value, 3) for value in box]


def make_font(size, display=False, bold=False):
    name = (
        "courgette-regular.ttf" if display else
        "dm-sans-semibold.ttf" if bold else "dm-sans-regular.ttf"
    )
    return ImageFont.truetype(str(FONTS / name), round(size * SCALE))


class Composition:
    def __init__(self, name, background, description):
        self.name = name
        self.description = description
        self.image = Image.new("RGBA", (SIZE[0] * SCALE, SIZE[1] * SCALE), background)
        self.elements = []

    def record(self, kind, name, box, **extra):
        x, y, w, h = box
        safe = x >= 0 and y >= 0 and x + w <= SIZE[0] and y + h <= SIZE[1]
        if not safe:
            raise ValueError(f"{self.name}: {name} exceeds the artwork bounds: {box}")
        self.elements.append({
            "kind": kind, "name": name, "bounds_xywh": rectangle(box),
            "inside_canvas": safe, **extra,
        })

    def text(self, text, x, y, size, colour=GREEN, display=False, bold=False):
        font = make_font(size, display=display, bold=bold)
        draw = ImageDraw.Draw(self.image)
        spacing = round(size * 0.20 * SCALE)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.multiline_text(
            (round(x * SCALE - bbox[0]), round(y * SCALE - bbox[1])),
            text, font=font, fill=colour, spacing=spacing,
        )
        self.record("text", text, (x, y, width / SCALE, height / SCALE),
                    font=font.path.split("\\")[-1], size_px=size)

    def rect(self, box, fill=None, outline=None, width=1, radius=0):
        x, y, w, h = box
        draw = ImageDraw.Draw(self.image)
        bounds = [round(v * SCALE) for v in (x, y, x + w, y + h)]
        if radius:
            draw.rounded_rectangle(bounds, radius * SCALE, fill=fill,
                                   outline=outline, width=round(width * SCALE))
        else:
            draw.rectangle(bounds, fill=fill, outline=outline, width=round(width * SCALE))

    def line(self, points, colour=GREEN, width=1):
        ImageDraw.Draw(self.image).line(
            [(round(x * SCALE), round(y * SCALE)) for x, y in points],
            fill=colour, width=round(width * SCALE), joint="curve",
        )

    def crumbs(self, x, y, colour=ACCENT, scale=1):
        draw = ImageDraw.Draw(self.image)
        for dx, dy, radius in ((0, 5, 4), (24, 0, 6), (47, 9, 3)):
            cx, cy, r = (x + dx * scale) * SCALE, (y + dy * scale) * SCALE, radius * scale * SCALE
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour)

    def sparkle(self, x, y, r=17, colour=ACCENT):
        self.line([(x - r, y), (x, y - 4), (x + r, y), (x, y + 4), (x - r, y)],
                  colour, 1.5)
        self.line([(x, y - r), (x - 4, y), (x, y + r), (x + 4, y), (x, y - r)],
                  colour, 1.5)

    def shadow(self, box, radius=12, strength=32):
        x, y, w, h = box
        layer = Image.new("RGBA", self.image.size)
        ImageDraw.Draw(layer).rounded_rectangle(
            tuple(round(v * SCALE) for v in (x, y + 13, x + w, y + h + 13)),
            radius * SCALE, fill=(24, 37, 28, strength),
        )
        self.image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(17 * SCALE)))

    def paste(self, path, box, name, mat=0, shadow=False, background=CREAM):
        """Contain the entire source; never cover-crop a UI or cake image."""
        image = image_file(path)
        x, y, w, h = box
        art = ImageOps.contain(image, (round(w * SCALE), round(h * SCALE)),
                               Image.Resampling.LANCZOS)
        actual_w, actual_h = art.width / SCALE, art.height / SCALE
        left, top = x + (w - actual_w) / 2, y + (h - actual_h) / 2
        frame = (left - mat, top - mat, actual_w + mat * 2, actual_h + mat * 2)
        if shadow:
            self.shadow(frame)
        if mat:
            self.rect(frame, fill=background, radius=8)
        self.image.alpha_composite(art, (round(left * SCALE), round(top * SCALE)))
        self.record(
            "image", name, (left, top, actual_w, actual_h),
            source=relative(path), source_sha256=digest(Path(path).read_bytes()),
            source_dimensions=list(image.size), crop=None,
            transform="Aspect-preserving contain; Lanczos resampling; no recolouring",
            all_source_pixels_retained=True,
        )
        return (left, top, actual_w, actual_h)

    def finish(self):
        image = self.image.convert("RGB").resize(SIZE, Image.Resampling.LANCZOS)
        image.info.clear()
        return image


class Captures:
    def __init__(self, browser, url, evidence):
        self.browser = browser
        self.url = url
        self.evidence = evidence
        self.records = []
        self.errors = []
        self.resource_paths = set()
        self.paths = {}
        self.site_version = None
        self.site_hashes = {}

    def page(self, width, height, fragment):
        page = self.browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=2,
            reduced_motion="no-preference",
        )
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        page.on("console", lambda message: self.errors.append(message.text)
                if message.type == "error" else None)
        page.on("requestfailed", lambda request: self.errors.append(
            f"Failed resource: {request.url}: {request.failure}"
        ))
        page.on("response", lambda response: self.errors.append(
            f"HTTP {response.status}: {response.url}"
        ) if response.status >= 400 else None)
        page.goto(self.url + (f"#{fragment}" if fragment else ""), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(250)
        actual = page.locator('link[rel="canonical"]').get_attribute("href")
        if actual != CANONICAL:
            raise ValueError(f"Unexpected site identity: {actual!r}")
        version = page.locator('link[href^="styles.css"]').get_attribute("href")
        if self.site_version and version != self.site_version:
            raise ValueError("The site changed during capture; use a stable built preview.")
        self.site_version = version
        for name in (
            "index.html", "styles.css", "entrance-shop.css", "cozy-bakery.css", "readability.css", "notebooks.mjs",
            "assets/bakery-awning.svg", "assets/bakery-paint-atlas.png",
            "assets/bakery-interior-wide.webp", "assets/bakery-interior-portrait.webp", "assets/bakery-interior-short.webp",
            "bakery-interior.mjs", "bakery-view.mjs", "bakery-scene.mjs",
            "assets/bakery-shelf.svg",
        ):
            value = digest((ROOT / "site" / name).read_bytes())
            if name in self.site_hashes and self.site_hashes[name] != value:
                raise ValueError(f"Built {name} changed during capture.")
            self.site_hashes[name] = value
        return page

    @staticmethod
    def ready_images(page, selector):
        for image in page.locator(selector).all():
            image.evaluate("""async image => {
                if (image.loading === 'lazy') image.scrollIntoView({block:'center'});
                await image.decode();
                if (!image.complete || !image.naturalWidth) throw new Error('Missing image');
            }""")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(120)

    @staticmethod
    def document_box(page, selector, padding=0):
        box = page.locator(selector).evaluate("""(e) => {
            const r=e.getBoundingClientRect();
            return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height};
        }""")
        x = max(0, math.floor(box["x"] - padding))
        y = max(0, math.floor(box["y"] - padding))
        right = min(page.viewport_size["width"], math.ceil(box["x"] + box["width"] + padding))
        bottom = math.ceil(box["y"] + box["height"] + padding)
        return {"x": x, "y": y, "width": right - x, "height": bottom - y}

    def save(self, page, name, clip, selectors, note, assertions=None):
        if clip["height"] > page.viewport_size["height"]:
            raise ValueError(f"{name}: the capture viewport must accommodate the complete section.")
        scroll = page.evaluate("({x:scrollX,y:scrollY})")
        if clip["y"] < scroll["y"] or clip["y"] + clip["height"] > scroll["y"] + page.viewport_size["height"]:
            page.evaluate("(y)=>scrollTo({top:y,behavior:'instant'})", clip["y"])
            page.wait_for_timeout(120)
        scroll = page.evaluate("({x:scrollX,y:scrollY})")
        viewport_clip = {**clip, "x": clip["x"] - scroll["x"], "y": clip["y"] - scroll["y"]}
        if viewport_clip["y"] < 0 or viewport_clip["y"] + clip["height"] > page.viewport_size["height"] + 1:
            raise ValueError(f"{name}: incomplete capture viewport: {viewport_clip}")
        selected = page.locator(", ".join(selectors))
        geometry = selected.evaluate_all("""els => els.filter(e => {
            let r=e.getBoundingClientRect();
            return r.width && r.height && getComputedStyle(e).visibility !== 'hidden';
        }).map(e=>{
            let r=e.getBoundingClientRect(),s=getComputedStyle(e);
            return {tag:e.tagName,id:e.id,classes:e.className,
              text:e.matches('img,svg')?null:e.innerText?.slice(0,220),
              bounds:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height},
              fontSize:s.fontSize,objectFit:s.objectFit,
              naturalWidth:e.naturalWidth||null,naturalHeight:e.naturalHeight||null,
              scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,
              scrollHeight:e.scrollHeight,clientHeight:e.clientHeight};
        })""")
        clipped = []
        for element in geometry:
            r = element["bounds"]
            contained = (
                r["x"] >= clip["x"] - 1 and r["y"] >= clip["y"] - 1 and
                r["x"] + r["width"] <= clip["x"] + clip["width"] + 1 and
                r["y"] + r["height"] <= clip["y"] + clip["height"] + 1
            )
            element["inside_capture"] = contained
            if not contained:
                clipped.append(element["id"] or str(element["classes"]))
        if clipped:
            raise ValueError(f"{name}: capture clips important elements: {clipped}")
        images = selected.locator("img").evaluate_all("""els=>els.filter(e=>
            e.getBoundingClientRect().width && e.getBoundingClientRect().height
        ).map(e=>({
            url:e.currentSrc,loaded:e.complete&&e.naturalWidth>0,
            naturalDimensions:[e.naturalWidth,e.naturalHeight]}))""")
        # Some selectors name images directly, rather than their parents.
        images += selected.evaluate_all("""els=>els.filter(e=>e.tagName==='IMG').map(e=>({
            url:e.currentSrc,loaded:e.complete&&e.naturalWidth>0,
            naturalDimensions:[e.naturalWidth,e.naturalHeight]}))""")
        images = list({item["url"]: item for item in images}.values())
        for item in images:
            if not item["loaded"]:
                raise ValueError(f"{name}: undecoded image: {item['url']}")
            self.resource_paths.add(urlsplit(item["url"]).path)
        fonts = page.evaluate("""[...document.fonts].map(f=>({
            family:f.family,status:f.status,weight:f.weight
        }))""")
        if any(font["status"] != "loaded" for font in fonts):
            raise ValueError(f"{name}: fonts not loaded: {fonts}")
        path = self.evidence / "captures" / f"{name}.png"
        page.wait_for_function("document.querySelector('.site-awning')?.dataset.fabricState !== 'moving'", timeout=26000)
        payload = page.screenshot(clip=viewport_clip, animations="disabled", caret="hide")
        save_preserving_existing(path, payload)
        with Image.open(BytesIO(payload)) as image:
            dimensions = list(image.size)
        if dimensions != [clip["width"] * 2, clip["height"] * 2]:
            raise ValueError(f"{name}: capture dimensions do not match the full selected area.")
        record = {
            "name": name, "path": relative(path), "sha256": digest(payload),
            "url": page.url, "viewport": page.viewport_size,
            "device_scale_factor": 2, "clip_document_css_pixels": clip,
            "clip_viewport_css_pixels": viewport_clip,
            "dimensions": dimensions, "capture_note": note,
            "browser_only_styles": [],
            "fonts": fonts, "images": images, "geometry": geometry,
            "all_selected_elements_inside_capture": not clipped,
            "assertions": assertions or {},
        }
        self.records.append(record)
        self.paths[name] = path
        return path

    def capture_all(self):
        page = self.page(1280, 1200, "home")
        self.ready_images(page, ".site-header img, .site-awning img, #home img")
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        page.wait_for_timeout(150)
        hero = self.document_box(page, "#home")
        self.save(
            page, "welcome-desktop",
            {"x": 0, "y": 0, "width": 1280, "height": hero["y"] + hero["height"]},
            [".site-header", ".site-awning", "#home", "#hero-title", ".hero-actions", "#home img"],
            "Unmodified header and complete hero; genuine #home bypass of entrance.",
        )
        page.close()

        page = self.page(1080, 1080, "")
        self.ready_images(page, "#bakery-entrance img")
        page.wait_for_function("['ready','unsupported','fallback'].includes(document.querySelector('.entrance-room').dataset.sceneState)", timeout=15000)
        state = page.locator("#bakery-entrance").get_attribute("data-state")
        if state != "waiting":
            raise ValueError(f"Entrance is not naturally waiting: {state}")
        self.save(
            page, "entrance-closed", {"x": 0, "y": 0, "width": 1080, "height": 1080},
            [".entrance-shop", "#entrance-enter span", "#entrance-skip"],
            "Natural closed entrance. No click, audio activation or forced state.",
            {"entrance_state": state, "audio_triggered": False},
        )
        page.close()

        page = self.page(1280, 1000, "story")
        page.locator("#story").scroll_into_view_if_needed()
        self.save(
            page, "story-desktop", self.document_box(page, "#story", 20),
            ["#story", ".story-copy", ".recipe-note"],
            "Original story, original recipe-note artwork, and complete scalloped edges.",
        )
        page.close()

        page = self.page(1280, 1440, "cakes")
        self.ready_images(page, ".notebook-cover img")
        page.locator("#category-notebooks").scroll_into_view_if_needed()
        colours = page.locator(".notebook-cover").evaluate_all(
            "els=>els.map(e=>getComputedStyle(e).backgroundColor)"
        )
        if len(colours) != 6 or set(colours) != {PINK}:
            raise ValueError(f"Expected exactly six current pink covers: {colours}")
        self.save(
            page, "six-notebooks", self.document_box(page, "#category-notebooks", 26),
            [".notebook-cover", ".notebook-cover img"],
            "Whole 3-by-2 live cover grid; no rearrangement, recolouring or product substitution.",
            {"cover_count": 6, "cover_colours": colours,
             "chocolate_artwork": "Existing complete assortment, unchanged"},
        )
        page.close()

        page = self.page(1440, 850, "cakes")
        cover = page.locator('.notebook-cover[data-category="decorated-cakes"]')
        cover.click()
        page.wait_for_timeout(600)
        dialog = page.locator("#notebook-dialog")
        self.ready_images(page, "#notebook-dialog article:visible img")
        count = page.locator("#notebook-dialog article:visible").count()
        scroll = dialog.evaluate("""e=>{
            e.scrollTop=999;e.scrollLeft=999;
            const result={x:e.scrollLeft,y:e.scrollTop,
                width:e.scrollWidth,clientWidth:e.clientWidth,
                height:e.scrollHeight,clientHeight:e.clientHeight};
            e.scrollTop=0;e.scrollLeft=0;return result;
        }""")
        if count != 4 or scroll["x"] or scroll["y"]:
            raise ValueError(f"Expected a real fitted four-photo page: {count}, {scroll}")
        self.save(
            page, "open-decorated-notebook", self.document_box(page, "#notebook-dialog"),
            ["#notebook-dialog", "#notebook-dialog article:visible",
             "#notebook-dialog article:visible img", "#notebook-close",
             "#notebook-dialog .notebook-controls"],
            "Opened through the real Decorated cakes cover; first real 2-by-2 photo page.",
            {"photo_count": count, "scroll_test": scroll},
        )
        page.locator("#notebook-close").click()
        page.wait_for_timeout(250)
        focus_returned = cover.evaluate("e=>document.activeElement===e")
        if not focus_returned or dialog.is_visible():
            raise ValueError("Notebook close/focus return failed.")
        self.records[-1]["assertions"]["close_and_focus_return"] = True
        page.close()

        page = self.page(1000, 900, "order")
        page.locator("#order").scroll_into_view_if_needed()
        href = page.locator("#order-contact").get_attribute("href")
        if "homemadevegcakes" not in href:
            raise ValueError("Unexpected contact account.")
        self.save(
            page, "order-desktop", self.document_box(page, "#order", 12),
            ["#order", "#order-title", "#order-contact", "#order-contact-help"],
            "Real desktop direct-message section; no external link is followed.",
            {"contact_url": href},
        )
        page.close()

        page = self.page(430, 930, "order")
        self.ready_images(page, ".bakery-shelf img")
        page.locator("#order").scroll_into_view_if_needed()
        start = self.document_box(page, "#order")
        end = self.document_box(page, ".site-footer")
        self.save(
            page, "order-mobile",
            {"x": 0, "y": start["y"], "width": 430,
             "height": end["y"] + end["height"] - start["y"]},
            ["#order", "#order-contact", "#order-contact-help", ".bakery-shelf", ".site-footer"],
            "Contiguous mobile order section and footer, clipped from the live document. "
                    "The editorial surround is not browser or social-network functionality.",
            {"contact_url": href, "external_navigation": False},
        )
        page.close()
        if self.errors:
            raise ValueError(f"Browser/resource errors: {self.errors}")

    def provenance(self):
        sticker_manifest = json.loads(
            (ROOT / "assets" / "images" / "cake-stickers" / "manifest.json").read_text("utf-8")
        )
        photo_manifest = json.loads(
            (ROOT / "assets" / "images" / "cakes" / "manifest.json").read_text("utf-8")
        )
        photos = {item["id"]: item for item in photo_manifest["photos"]}
        records = []
        for url_path in sorted(self.resource_paths):
            path = ROOT / "site" / unquote(url_path).lstrip("/")
            if not path.is_file():
                raise ValueError(f"Captured asset not present in generated site: {url_path}")
            content_hash = digest(path.read_bytes())
            record = {
                "capture_resource": urljoin(self.url, url_path),
                "local_asset": relative(path), "sha256": content_hash,
            }
            if "stickers" in url_path:
                match = next(
                    (photo, variant)
                    for photo in sticker_manifest["photos"]
                    for variant in photo["variants"] if variant["file"] == path.name
                )
                sticker, variant = match
                if content_hash != variant["sha256"]:
                    raise ValueError(f"Sticker differs from its reviewed manifest: {path}")
                original = photos[sticker["id"]]
                source_hash = sticker.get("source_photo_sha256") or sticker.get("source_screenshot_sha256")
                if source_hash != original["source_sha256"]:
                    raise ValueError(f"Original asset association mismatch: {sticker['id']}")
                record.update({
                    "asset_id": sticker["id"],
                    "original_asset_sha256": source_hash,
                    "original_source_type": original["source_type"],
                    "source_crop_sha256": sticker["source_crop_sha256"],
                    "mask_sha256": sticker["mask_sha256"],
                    "original_source_dimensions": original["source_dimensions"],
                    "inherited_limitation": original.get("limitation") or sticker.get("source_limitation"),
                    "processing": "Existing reviewed site sticker; browser object-fit:contain. "
                                  "No original editing, mask changes or missing-detail reconstruction.",
                })
            records.append(record)
        for name in ("courgette-regular.ttf", "dm-sans-regular.ttf", "dm-sans-semibold.ttf"):
            path = FONTS / name
            records.append({"local_asset": relative(path), "sha256": digest(path.read_bytes()),
                            "role": "Existing font; direct Pillow/FreeType rendering and live browser text"})
        return records


def compose(paths):
    scenes = []
    scene = Composition(
        FILENAMES[0], CREAM,
        "Cream editorial masthead above a large, lightly framed real desktop welcome view.",
    )
    scene.text("Whisk & Crumbs", 78, 42, 69, display=True)
    scene.text("HOME-BAKED VEGETARIAN CAKES", 1000, 64, 22, bold=True)
    scene.crumbs(1460, 100)
    source = image_file(paths["welcome-desktop"])
    scale = min(1360 / source.width, 760 / source.height)
    width, height = source.width * scale, source.height * scale
    x, y, chrome = (1600 - width) / 2, 156, 39
    scene.shadow((x, y, width, height + chrome), strength=38)
    scene.rect((x, y, width, height + chrome), fill="#fffaf1", outline="#dacebb", radius=10)
    for dot in range(3):
        scene.rect((x + 18 + dot * 16, y + 15, 7, 7), fill="#b9b8a5", radius=3)
    scene.text("zanark.github.io/WhiskAndCrumbs/", x + 102, y + 11, 15)
    scene.paste(paths["welcome-desktop"], (x, y + chrome, width, height), "Complete header and hero")
    scene.sparkle(1460, 118, 12)
    scenes.append(scene)

    scene = Composition(
        FILENAMES[1], CREAM,
        "Doorway portrait on the left; a contrasting deep-green invitation panel on the right.",
    )
    scene.rect((982, 0, 618, 1000), fill=GREEN)
    scene.paste(paths["entrance-closed"], (44, 48, 894, 894), "Natural closed entrance",
                mat=8, shadow=True, background="#fffaf1")
    scene.text("THE BAKERY ENTRANCE", 1042, 196, 21, CREAM, bold=True)
    scene.text("Come\non in.", 1040, 296, 105, CREAM, display=True)
    scene.line([(1045, 635), (1475, 635)], "#81907b", 1)
    scene.crumbs(1061, 687, CREAM, 1.4)
    scene.sparkle(1470, 125, 22, CREAM)
    scene.text("Whisk & Crumbs", 1044, 874, 36, CREAM, display=True)
    scenes.append(scene)

    scene = Composition(
        FILENAMES[2], CREAM,
        "A wide, unaltered story spread, including the original recipe note and scalloped edges.",
    )
    scene.text("Our little story", 80, 55, 78, display=True)
    scene.crumbs(1430, 104)
    scene.line([(82, 176), (1518, 176)], "#cec3af", 1)
    scene.paste(paths["story-desktop"], (62, 217, 1476, 732), "Original story and recipe note",
                mat=10, shadow=True, background="#fffaf1")
    scene.sparkle(1500, 162, 10)
    scenes.append(scene)

    scene = Composition(
        FILENAMES[3], CREAM,
        "Asymmetric category editorial: quiet typography beside the full, authentic six-cover grid.",
    )
    scene.text("SIX LITTLE NOTEBOOKS", 64, 161, 21, bold=True)
    scene.text("Cakes\nwe've\nmade.", 66, 257, 88, display=True)
    scene.line([(70, 646), (388, 646)], "#bdc0ac", 1)
    scene.crumbs(79, 690, ACCENT, 1.3)
    scene.sparkle(390, 737, 17)
    scene.paste(paths["six-notebooks"], (496, 51, 1060, 900),
                "All six pink notebooks, complete stickers and binding")
    scene.text("Whisk & Crumbs", 65, 890, 30, display=True)
    scenes.append(scene)

    scene = Composition(
        FILENAMES[4], GREEN,
        "A deep-green gallery spread dominated by the real, open four-photo Decorated notebook.",
    )
    scene.text("Turn the page.", 80, 44, 63, CREAM, display=True)
    scene.text("DECORATED CAKES", 1190, 74, 20, CREAM, bold=True)
    scene.paste(paths["open-decorated-notebook"], (236, 141, 1128, 817),
                "Real open notebook, page 1 of 3", mat=8, shadow=True, background="#dacfba")
    scene.sparkle(94, 383, 25, "#a4ac95")
    scene.sparkle(1496, 658, 17, "#a4ac95")
    scene.crumbs(92, 793, CREAM, 1.3)
    scene.crumbs(1440, 279, CREAM, 1.0)
    scenes.append(scene)

    scene = Composition(
        FILENAMES[5], CREAM,
        "Desktop ordering beside a tall mobile document crop; only the genuine Instagram handoff.",
    )
    scene.text("How to order.", 70, 70, 75, display=True)
    scene.paste(paths["order-desktop"], (70, 265, 950, 448), "Real desktop ordering",
                mat=8, shadow=True, background="#fffaf1")
    scene.rect((1070, 113, 472, 796), fill=GREEN, radius=36)
    scene.rect((1094, 144, 424, 734), fill=CREAM, radius=20)
    scene.paste(paths["order-mobile"], (1104, 186, 404, 648),
                "Unmodified contiguous mobile ordering and footer")
    scene.rect((1227, 856, 157, 4), fill="#8b927c", radius=2)
    scene.text("@homemadevegcakes", 74, 778, 35, display=True)
    scene.line([(78, 850), (925, 850)], "#bdc0ac", 1)
    scene.crumbs(85, 889)
    scene.sparkle(978, 175, 16)
    scenes.append(scene)
    return scenes


def check_export(payload):
    with Image.open(BytesIO(payload)) as image:
        image.load()
        if image.size != SIZE or image.mode != "RGB" or image.format != "JPEG":
            raise ValueError("Output must be a 1600x1000 RGB JPEG.")
        if image.getexif() or any(key in image.info for key in ("exif", "xmp", "comment", "icc_profile")):
            raise ValueError("Unexpected exported metadata.")
        info = {"format": image.format, "mode": image.mode, "dimensions": list(image.size),
                "metadata_keys": sorted(image.info), "exif_entries": len(image.getexif())}
    for marker in (b"C:\\", b"127.0.0.1", b".local", b"mishrad", b"WhiskAndCrubms"):
        if marker in payload:
            raise ValueError(f"Unexpected private/incorrect marker in JPEG: {marker!r}")
    info["private_metadata_markers_found"] = []
    return info


def review_sheet(images, evidence):
    """One sequential-review artifact: six full scenes plus nine labelled crops."""
    crops = [
        (0, "07 | 01 / masthead + browser URL", (50, 25, 1545, 222)),
        (0, "08 | 01 / hero + intact cake", (715, 290, 1518, 902)),
        (1, "09 | 02 / doorway + entry caption", (140, 156, 905, 910)),
        (2, "10 | 03 / original story copy", (78, 330, 1000, 832)),
        (2, "11 | 03 / recipe note + scallops", (995, 282, 1535, 908)),
        (3, "12 | 04 / top row + binding", (498, 80, 1550, 488)),
        (3, "13 | 04 / bottom row + Chocolate", (498, 492, 1550, 949)),
        (4, "14 | 05 / four photos + controls", (258, 213, 1342, 952)),
        (5, "15 | 06 / mobile contact + footer", (1088, 163, 1526, 847)),
    ]
    tiles = [
        (f"{index + 1:02} | {FILENAMES[index]}", image, None, index)
        for index, image in enumerate(images)
    ]
    tiles.extend((label, images[index].crop(box), box, index) for index, label, box in crops)
    sheet = Image.new("RGB", (2000, 1940), CREAM)
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype(str(FONTS / "dm-sans-semibold.ttf"), 20)
    title_font = ImageFont.truetype(str(FONTS / "dm-sans-semibold.ttf"), 28)
    draw.text((24, 18), "README SHOWCASE / REVIEW 01 / 6 COMPLETE SCENES + 9 DETAILS",
              font=title_font, fill=GREEN)
    records = []
    for index, (label, image, crop, source) in enumerate(tiles):
        x, y = 20 + (index % 3) * 660, 78 + (index // 3) * 370
        if draw.textlength(label, font=label_font) > 632:
            raise ValueError(f"Review label too long: {label}")
        draw.text((x + 4, y), label, font=label_font, fill=GREEN)
        thumb = ImageOps.contain(image, (630, 323), Image.Resampling.LANCZOS)
        draw.rectangle((x, y + 32, x + 638, y + 359), fill="#e8dece", outline="#c9beab")
        sheet.paste(thumb, (x + (638 - thumb.width) // 2, y + 34 + (323 - thumb.height) // 2))
        records.append({
            "tile": index + 1, "label": label, "composition": FILENAMES[source],
            "crop_ltrb": list(crop) if crop else None,
            "source_pixels": list(image.size), "thumbnail_pixels": list(thumb.size),
        })
    payload = encoded(sheet, "JPEG", quality=93, subsampling=0, optimize=True)
    path = evidence / "review-01.jpg"
    save_preserving_existing(path, payload)
    return {"path": relative(path), "sha256": digest(payload), "dimensions": list(sheet.size),
            "tile_count": len(tiles), "status": "generated-not-viewed", "tiles": records}


def generate(url, output, evidence):
    output, evidence = output.resolve(), evidence.resolve()
    if not (output == PUBLIC or output.is_relative_to(PRIVATE)):
        raise ValueError("Outputs belong in web\\assets\\showcase or its private revision evidence.")
    if not (evidence == PRIVATE or evidence.is_relative_to(PRIVATE)):
        raise ValueError("Evidence belongs only in .local\\readme-showcase-20261007.")
    if output == evidence or evidence.is_relative_to(output):
        raise ValueError("Keep image exports and private evidence separate.")
    parsed = urlsplit(url)
    if parsed.hostname not in ("127.0.0.1", "localhost", "::1") or parsed.scheme != "http":
        raise ValueError("Use a loopback HTTP preview; this generator never uploads media.")
    if parsed.query or parsed.fragment:
        raise ValueError("--url must be the preview root, without a query or fragment.")
    url = url.rstrip("/") + "/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        try:
            captures = Captures(browser, url, evidence)
            captures.capture_all()
            provenance = captures.provenance()
            browser_version = browser.version
        finally:
            browser.close()
    scenes = compose(captures.paths)
    images, exports, payloads = [], [], []
    for scene in scenes:
        image = scene.finish()
        payload = encoded(image, "JPEG", quality=95, subsampling=0, optimize=True)
        validation = check_export(payload)
        images.append(image)
        payloads.append(payload)
        exports.append({
            "filename": scene.name, "path": relative(output / scene.name),
            "sha256": digest(payload), "bytes": len(payload),
            "scene_description": scene.description, "validation": validation,
            "elements": scene.elements,
        })
    if len(set(item["sha256"] for item in exports)) != 6:
        raise ValueError("The six scenes must have six distinct hashes.")
    # Validate every output before publishing any of them.
    for item, payload in zip(exports, payloads):
        target = output / item["filename"]
        if target.exists() and target.read_bytes() != payload:
            raise ValueError(f"Existing output differs: {target}. Choose a private revision.")
    sheet = review_sheet(images, evidence)
    for item, payload in zip(exports, payloads):
        save_preserving_existing(output / item["filename"], payload)
        save_preserving_existing(evidence / "exports" / item["filename"], payload)
    receipt = {
        "schema_version": 1, "status": "generated-and-numerically-checked; awaiting visual review",
        "generator": relative(Path(__file__)), "generator_sha256": digest(Path(__file__).read_bytes()),
        "canonical_public_url": CANONICAL, "capture_base_url": url,
        "browser": {"engine": "Chromium / installed Microsoft Edge", "version": browser_version},
        "site_asset_version": captures.site_version, "built_site_sha256": captures.site_hashes,
        "encoding": {"dimensions": list(SIZE), "mode": "RGB", "format": "JPEG",
                     "quality": 95, "chroma_subsampling": "4:4:4", "composition_supersampling": SCALE},
        "browser_errors": captures.errors, "six_unique_hashes": True,
        "image_tool_views_performed": 0, "contact_sheet": sheet, "exports": exports,
        "captures": captures.records, "asset_provenance": provenance,
        "boundaries": {
            "original_media_modified": False, "archive_accessed": False,
            "live_site_code_or_styles_modified": False, "photo_colour_adjustments": False,
            "fictional_ui_or_products": False, "external_contact_link_followed": False,
            "chocolate_cover": "Complete existing assortment; five-piece work remains paused",
        },
        "limitations": [
            "No visual-tool inspection or owner approval is claimed.",
            "These are static editorial compositions, not photographs of physical devices.",
            "Presentation-only browser/device surrounds do not add website functionality.",
            "Live UI text is retained. At narrow README widths the full-resolution files are clearer.",
            "Existing source crop limitations remain unchanged; missing photo detail is not reconstructed.",
            "Original asset hashes are checked through existing reviewed manifests, not by opening the archive.",
            "No audio or external Instagram interaction was tested by this generator.",
        ],
        "rerun": "Use --url, --output and --evidence. Changed results need new private revision directories; "
                 "existing differing evidence and public image outputs are never overwritten.",
    }
    save_preserving_existing(evidence / "generator-source.py", Path(__file__).read_bytes())
    write_json(evidence / "manifest.json", receipt)
    print(json.dumps({
        "outputs": [{key: entry[key] for key in ("path", "sha256", "bytes")} for entry in exports],
        "contact_sheet": sheet["path"], "manifest": relative(evidence / "manifest.json"),
        "image_views": 0, "browser_errors": captures.errors,
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, default=PUBLIC)
    parser.add_argument("--evidence", type=Path, default=PRIVATE)
    arguments = parser.parse_args()
    generate(arguments.url, arguments.output, arguments.evidence)
