"""Generate the original whisk/crumb identity, favicons and quiet outline patterns."""

from hashlib import sha256
from html import escape
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "web" / "assets"
REVIEW = ROOT / ".local" / "singular-brand"
CREAM, GREEN, ACCENT = "#f5ebdd", "#34483a", "#a45137"
PATTERN_SIZE = (640, 480)
WHISK = """<g transform="rotate(-28 30 32)" stroke-linejoin="round">
  <path d="M30 8C20 7 15 16 17 25C19 34 25 37 30 41C35 37 41 34 43 25C45 16 40 7 30 8Z"/>
  <path d="M30 8C22 13 23 31 30 41C37 31 38 13 30 8M30 8V41"/>
  <path d="M27.5 41H32.5V55A2.5 2.5 0 0 1 27.5 55Z"/>
</g>"""


def image_bytes(image, format_name="PNG", **kwargs):
    buffer = BytesIO()
    image.save(buffer, format=format_name, **kwargs)
    return buffer.getvalue()


def mark_svg(name, badge=False):
    stroke = CREAM if badge else GREEN
    crumbs = CREAM if badge else ACCENT
    background = f'  <rect width="64" height="64" rx="14" fill="{GREEN}"/>\n' if badge else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" fill="none" role="img">
  <title>{escape(name)} - whisk and crumbs</title>
{background}  <g stroke="{stroke}" stroke-width="2.8" stroke-linecap="round">{WHISK}</g>
  <g fill="{crumbs}"><circle cx="46" cy="10" r="2.2"/><circle cx="51" cy="18" r="1.65"/><circle cx="45" cy="25" r="1.2"/></g>
</svg>
"""


def pattern_svg(stroke, opacity):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480" fill="none">
  <g stroke="{stroke}" opacity="{opacity}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">
    <g transform="translate(52 28) rotate(12 30 32)">{WHISK}</g>
    <g transform="translate(280 66) rotate(8 30 30)">
      <path d="M5 18Q30 10 55 18M7 19C10 42 17 48 30 48C43 48 50 42 53 19ZM18 49H42M15 27Q18 36 23 38"/>
    </g>
    <g transform="translate(490 35) rotate(-12 30 28)">
      <path d="M1 27L34 8L59 25V47L1 49ZM1 27L59 25M1 36L59 34M34 8V2"/>
      <circle cx="33" cy="8" r="4"/>
    </g>
    <g transform="translate(125 223) rotate(-20 30 25)">
      <rect x="11" y="13" width="39" height="25" rx="5"/>
      <path d="M11 20H3V31H11M50 20H59V31H50M19 18V33"/>
    </g>
    <g transform="translate(354 208) rotate(12 30 33)">
      <path d="M5 29Q30 17 55 29V51Q30 63 5 51ZM5 29C10 40 17 24 23 32S33 40 39 31S49 37 55 29M7 42Q30 53 53 42M30 21V8M27 8Q24 2 30 0Q36 2 33 8Z"/>
    </g>
    <g transform="translate(530 310) rotate(18 28 27)">
      <path d="M9 8Q26 0 43 8L31 42H19ZM19 42H31L26 55ZM9 8L25 17L43 8M25 17L25 33"/>
    </g>
    <g transform="translate(57 386) rotate(-10 30 28)">
      <path d="M11 28L17 52H43L49 28ZM10 28C0 21 11 9 20 14C19 2 39-2 42 14C57 9 65 25 50 28M22 34L24 47M37 34L35 47"/>
    </g>
    <g transform="translate(278 390) rotate(30 30 32)">{WHISK}</g>
    <path d="M192 98l7 4M414 92l-4 7M66 191l6-5M463 374l7 4M377 440l-4 7"/>
    <circle cx="200" cy="120" r="2.5"/><circle cx="442" cy="188" r="2"/>
    <circle cx="230" cy="330" r="2.5"/><circle cx="591" cy="220" r="2"/>
  </g>
</svg>
"""


def render_svg(page, svg, size):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    page.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
    page.locator("svg").evaluate(
        "(node, size) => { node.style.display = 'block'; node.setAttribute('width', size[0]); node.setAttribute('height', size[1]); }",
        list(size),
    )
    data = page.locator("svg").screenshot(omit_background=True)
    with Image.open(BytesIO(data)) as image:
        return image.convert("RGBA")


def generate():
    config = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    name, descriptor = config["name"], config["descriptor"]
    if name != "Whisk & Crumbs":
        raise ValueError("This reviewed visual identity is for Whisk & Crumbs.")
    REVIEW.mkdir(parents=True, exist_ok=True)
    svgs = {
        "whisk-and-crumbs-mark.svg": mark_svg(name),
        "favicon.svg": mark_svg(name, badge=True),
        "bakery-pattern-cream.svg": pattern_svg(GREEN, 0.075),
        "bakery-pattern-green.svg": pattern_svg(CREAM, 0.065),
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        mark = render_svg(page, svgs["whisk-and-crumbs-mark.svg"], (512, 512))
        badge = render_svg(page, svgs["favicon.svg"], (512, 512))
        for theme, background in [("cream", CREAM), ("green", GREEN)]:
            pattern = render_svg(page, svgs[f"bakery-pattern-{theme}.svg"], PATTERN_SIZE)
            preview = Image.alpha_composite(Image.new("RGBA", PATTERN_SIZE, background), pattern)
            preview.save(REVIEW / f"pattern-{theme}-preview.png")
        browser.close()

    title_font = ImageFont.truetype(str(ASSETS / "fonts" / "courgette-regular.ttf"), 88)
    body_font = ImageFont.truetype(str(ASSETS / "fonts" / "dm-sans-regular.ttf"), 30)
    title_width = round(title_font.getlength(name))
    descriptor_width = round(body_font.getlength(descriptor))
    logo = Image.new("RGBA", (244 + max(title_width, descriptor_width) + 32, 240))
    logo.alpha_composite(mark.resize((200, 200), Image.Resampling.LANCZOS), (18, 20))
    draw = ImageDraw.Draw(logo)
    draw.text((244, 54), name, font=title_font, fill=GREEN, anchor="lt")
    draw.text((248, 165), descriptor, font=body_font, fill="#76543d", anchor="lt")

    apple = Image.alpha_composite(Image.new("RGBA", badge.size, CREAM), badge)
    output = {file: svg.encode("utf-8") for file, svg in svgs.items()}
    output.update({
        "whisk-and-crumbs-logo.png": image_bytes(logo, optimize=True),
        "favicon-16.png": image_bytes(badge.resize((16, 16), Image.Resampling.LANCZOS)),
        "favicon-32.png": image_bytes(badge.resize((32, 32), Image.Resampling.LANCZOS)),
        "favicon.ico": image_bytes(badge, "ICO", sizes=[(16, 16), (32, 32), (48, 48)]),
        "apple-touch-icon.png": image_bytes(apple.resize((180, 180), Image.Resampling.LANCZOS), optimize=True),
    })
    for file, data in output.items():
        (ASSETS / file).write_bytes(data)

    sheet = Image.new("RGBA", (1100, 550), CREAM)
    large_logo = logo.copy()
    large_logo.thumbnail((1040, 230), Image.Resampling.LANCZOS)
    sheet.alpha_composite(large_logo, (30, 20))
    sheet.alpha_composite(mark.resize((180, 180), Image.Resampling.LANCZOS), (70, 290))
    sheet.alpha_composite(badge.resize((180, 180), Image.Resampling.LANCZOS), (350, 290))
    for index, size in enumerate([16, 32, 48]):
        image = badge.resize((size, size), Image.Resampling.LANCZOS)
        sheet.alpha_composite(image, (640 + index * 120, 335))
        ImageDraw.Draw(sheet).text(
            (620 + index * 120, 410), f"{size}px",
            font=body_font, fill=GREEN,
        )
    sheet.convert("RGB").save(REVIEW / "identity-review.png")
    (REVIEW / "asset-manifest.json").write_text(json.dumps({
        "name": name, "descriptor": descriptor,
        "pattern": {"size": list(PATTERN_SIZE), "cream_opacity": 0.075, "green_opacity": 0.065},
        "files": {file: {"bytes": len(data), "sha256": sha256(data).hexdigest()} for file, data in output.items()},
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(output)} brand assets. Private review: {REVIEW}")


if __name__ == "__main__":
    generate()
