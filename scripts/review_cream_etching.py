"""Measure visible etched ink against hidden and former-faint same-pose references."""
import argparse
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import expect, sync_playwright

SECTIONS = ("#home", "#story", "#cakes", "#order", ".site-footer")


def pixels(page):
    return np.asarray(Image.open(BytesIO(page.screenshot())).convert("RGB"), dtype=np.int16)


def review(url, output):
    if output.exists():
        raise FileExistsError("Use a new etching evidence file.")
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            for width, height in ((1440, 1000), (768, 1000), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.add_init_script("crypto.getRandomValues=a=>{a[0]=4;return a}")
                page.goto(url + "#home", wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                expect(page.locator("#cream-effects")).to_have_attribute("data-state", "moving")
                page.locator("#cream-motion-toggle").evaluate("n=>n.click()")
                expect(page.locator("#cream-effects")).to_have_attribute("data-state", "paused")
                sections = []
                for selector in SECTIONS:
                    section = page.locator(selector)
                    section.evaluate("n=>scrollTo({top:n.getBoundingClientRect().top+scrollY,behavior:'instant'})")
                    page.wait_for_timeout(100)
                    etching = section.locator(":scope > .cream-glass > .cream-etching")
                    geometry = etching.evaluate("""n=>{
                      const b=n.getBoundingClientRect(),s=getComputedStyle(n);
                      return {left:b.left,top:b.top,right:b.right,bottom:b.bottom,opacity:s.opacity,
                        image:s.backgroundImage,filter:s.filter,style:n.style.cssText};
                    }""")
                    assert geometry["opacity"] == "1" and "bakery-glass-etching.svg" in geometry["image"]
                    current = pixels(page)
                    etching.evaluate("n=>n.style.visibility='hidden'")
                    hidden = pixels(page)
                    etching.evaluate("n=>{n.style.visibility='';n.style.opacity='.08';n.style.filter='none'}")
                    faint = pixels(page)
                    etching.evaluate("(n,style)=>n.style.cssText=style", geometry["style"])
                    x0, x1 = max(0, int(geometry["left"])), min(width, int(geometry["right"]))
                    y0, y1 = max(24, int(geometry["top"])), min(height, int(geometry["bottom"]))
                    assert x1 > x0 and y1 > y0, geometry
                    difference = np.max(np.abs(current[y0:y1, x0:x1] - hidden[y0:y1, x0:x1]), axis=2)
                    old_difference = np.max(np.abs(faint[y0:y1, x0:x1] - hidden[y0:y1, x0:x1]), axis=2)
                    visible = difference >= 6
                    count = int(np.count_nonzero(visible))
                    sections.append({
                        "section": selector, "visible_ink_pixels": count,
                        "mean_current_change": float(difference[visible].mean()) if count else 0,
                        "mean_former_change_at_same_pixels": float(old_difference[visible].mean()) if count else 0,
                        "maximum_change": int(difference.max()), "geometry": geometry,
                    })
                hero = sections[0]
                assert hero["visible_ink_pixels"] > 100, (width, hero)
                assert hero["mean_current_change"] >= 8, (width, hero)
                assert hero["mean_current_change"] > hero["mean_former_change_at_same_pixels"] * 3, (width, hero)
                green = [row for row in sections if row["section"] in ("#story", "#order")]
                assert sum(row["visible_ink_pixels"] for row in green) > 100, (width, green)
                records.append({"viewport": [width, height],
                    "revision": page.locator("#cream-effects").get_attribute("data-revision"), "sections": sections})
                page.close()
        finally:
            browser.close()
    result = {"passed": True, "url": url, "cases": records, "image_tool_views": 0,
              "method": "Paused live material; actual etching compared to hidden and former8%-opacity references in the same pose."}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": True, "viewports": len(records), "sections": len(records) * len(SECTIONS)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    review(args.url, args.output)
