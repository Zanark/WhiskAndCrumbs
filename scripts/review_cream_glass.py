"""Measure full-column themed glass and actual reading contrast without viewing images."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image
from playwright.sync_api import expect, sync_playwright

SECTIONS = ("#home", "#story", "#cakes", "#order", ".site-footer")
COPY = ".hero-copy h1,.hero-copy h1 em,.hero-description,.story-copy h2,.story-copy h2 em,.story-copy p,.story-copy a,#cakes>.section-heading h2,#cakes>.section-heading h2 em,#cakes>.section-heading>p,#order h2,#order h2 em,#order p,.site-footer>span:not(.cream-glass),.site-footer>a"


def luminance(rgb):
    values = np.asarray(rgb, dtype=float) / 255
    linear = np.where(values <= .04045, values / 12.92, ((values + .055) / 1.055) ** 2.4)
    return np.sum(linear * (.2126, .7152, .0722), axis=-1)


def review(url, output, only_width=None, only_text=None, motion_samples=3, stylesheet=None, spawn_count=0):
    if output.exists() or output.with_name(output.stem + "-progress.json").exists():
        raise FileExistsError("Use a new evidence filename for each glass review.")
    records = []
    def progress(status, current=None):
        output.with_name(output.stem + "-progress.json").write_text(json.dumps({
            "status": status, "url": url, "cases": records, "current": current,
        }, indent=2) + "\n", encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for width, height, text_size in ((1920, 1080, 100), (1440, 1000, 100), (768, 1000, 100),
                                         (390, 844, 100), (320, 568, 100), (1440, 1000, 200), (390, 844, 200)):
            if (only_width is not None and width != only_width) or (only_text is not None and text_size != only_text):
                continue
            page = browser.new_page(viewport={"width": width, "height": height})
            if stylesheet:
                page.route("**/cream.css?*", lambda route: route.fulfill(path=str(stylesheet), content_type="text/css"))
            page.add_init_script("crypto.getRandomValues=array=>{array[0]=4;return array}")
            page.goto(url + "#home", wait_until="networkidle")
            page.evaluate("value=>document.documentElement.style.fontSize=value+'%'", text_size)
            page.evaluate("document.fonts.ready")
            expect(page.locator("#cream-effects")).to_have_attribute("data-state", "moving")
            if spawn_count:
                for index in range(spawn_count):
                    page.mouse.click(8 if index % 2 == 0 else width - 8,
                                     100 + (index // 2) * (height - 200) / 4)
                expect(page.locator("#cream-effects")).to_have_attribute("data-spawn-count", str(spawn_count))
            page.locator("#cream-motion-toggle").click()
            expect(page.locator("#cream-effects")).to_have_attribute("data-state", "paused")
            revision = page.locator("#cream-effects").get_attribute("data-revision")
            geometry = page.evaluate("""selectors=>{
              const rect=n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height}};
              return selectors.map(selector=>{
                const section=document.querySelector(selector),pane=section.querySelector(':scope > .cream-glass'),b=rect(pane);
                const texts=[...section.querySelectorAll('h1,h2,h3,p,a,li')].filter(n=>n.getClientRects().length&&n.textContent.trim());
                return {selector,section:rect(section),pane:b,colour:getComputedStyle(pane).backgroundColor,
                  backdrop:getComputedStyle(pane).backdropFilter,
                  textOutside:texts.map(n=>({tag:n.tagName,text:n.textContent.trim().slice(0,48),...rect(n)}))
                    .filter(r=>r.left<b.left-1||r.right>b.right+1||r.top<b.top-1||r.bottom>b.bottom+1),
                  plates:[...section.querySelectorAll('.hero-copy,.section-heading,.story-copy,.order-layout>div,.order-action')]
                    .map(n=>({class:n.className,content:getComputedStyle(n,'::before').content,background:getComputedStyle(n).backgroundColor}))};
              });
            }""", list(SECTIONS))
            centres = [(record["pane"]["left"] + record["pane"]["right"]) / 2 for record in geometry]
            assert max(centres) - min(centres) <= 1
            for record in geometry:
                assert abs(record["pane"]["width"] - min(1344, width - 32)) <= 1, record
                assert not record["textOutside"], record
                assert record["pane"]["top"] >= record["section"]["top"] - 1
                assert record["pane"]["bottom"] <= record["section"]["bottom"] + 1
                assert "blur" in record["backdrop"], record
                assert all(plate["content"] == "none" for plate in record["plates"]), record
                if record["selector"] in {"#story", "#order"}:
                    assert "52" in record["colour"] or "0.203922" in record["colour"], record
            contrasts = []
            for section in SECTIONS:
                page.locator(section).evaluate("n=>scrollTo({top:n.getBoundingClientRect().top+scrollY,behavior:'instant'})")
                page.wait_for_timeout(150)
                texts = page.locator(COPY).evaluate_all("""nodes=>nodes.filter(n=>{
                  const b=n.getBoundingClientRect();return b.width>0&&b.height>0&&b.bottom>0&&b.top<innerHeight;
                }).map(n=>{
                  const b=n.getBoundingClientRect(),s=getComputedStyle(n),range=document.createRange();range.selectNodeContents(n);
                  return {text:n.textContent.trim().slice(0,60),colour:s.color,size:parseFloat(s.fontSize),
                    heading:/^H[1-6]$/.test(n.tagName)||!!n.closest('h1,h2,h3'),
                    boxes:[...range.getClientRects()].map(r=>({left:r.left,top:r.top,right:r.right,bottom:r.bottom}))};
                })""")
                style = page.add_style_tag(content=f"{COPY}, {COPY.replace(',', ' *,')} * {{ color:transparent !important;text-shadow:none !important;text-decoration-color:transparent !important; }}")
                image = np.asarray(Image.open(BytesIO(page.screenshot())).convert("RGB"))
                style.evaluate("n=>n.remove()")
                for text in texts:
                    rgb = [float(value) for value in re.findall(r"[\d.]+", text["colour"])[:3]]
                    ink = luminance(rgb)
                    ratios = []
                    for box in text["boxes"]:
                        x0, y0 = max(0, int(box["left"])), max(0, int(box["top"]))
                        x1, y1 = min(width, int(box["right"] + 1)), min(height, int(box["bottom"] + 1))
                        if x1 <= x0 or y1 <= y0:
                            continue
                        background = luminance(image[y0:y1, x0:x1])
                        ratios.append(float(np.min((np.maximum(ink, background) + .05) / (np.minimum(ink, background) + .05))))
                    if not ratios:
                        continue
                    minimum = min(ratios)
                    threshold = 3 if text["heading"] and text["size"] >= 24 else 4.5
                    if minimum < threshold:
                        location = np.unravel_index(np.argmin((np.maximum(ink, background) + .05) / (np.minimum(ink, background) + .05)), background.shape)
                        x, y = x0 + int(location[1]), y0 + int(location[0])
                        print(json.dumps({"failure_pixel": [x, y], "rgb": image[y, x].tolist(), "size": text_size,
                            "layers": page.evaluate("""([x,y])=>({state:document.querySelector('#cream-effects').dataset.state,
                              elements:document.elementsFromPoint(x,y).map(n=>({tag:n.tagName,id:n.id,class:n.className,background:getComputedStyle(n).backgroundColor})),
                              panes:[...document.querySelectorAll('.cream-glass')].map(n=>{const b=n.getBoundingClientRect();return {parent:n.parentElement.id,top:b.top,bottom:b.bottom,colour:getComputedStyle(n).backgroundColor}})})""", [x, y])}, indent=2))
                    assert minimum >= threshold, (width, section, text, minimum, threshold)
                    contrasts.append({"section": section, "text": text["text"], "minimum": minimum, "threshold": threshold})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            visible_motion = []
            for selector in ("#home", "#story"):
                page.locator(selector).evaluate("n=>scrollTo({top:n.getBoundingClientRect().top+scrollY,behavior:'instant'})")
                page.mouse.move(0, 0)
                page.wait_for_timeout(300)
                page.keyboard.press("Alt+Shift+P")
                expect(page.locator("#cream-effects")).to_have_attribute("data-state", "moving")
                page.wait_for_timeout(100)
                for sample in range(motion_samples):
                    before = np.asarray(Image.open(BytesIO(page.screenshot())).convert("RGB"), dtype=np.int16)
                    clock = float(page.locator("#cream-effects").get_attribute("data-motion-time"))
                    page.wait_for_timeout(2000)
                    after = np.asarray(Image.open(BytesIO(page.screenshot())).convert("RGB"), dtype=np.int16)
                    assert float(page.locator("#cream-effects").get_attribute("data-motion-time")) > clock + 1
                    pane = page.locator(selector + " > .cream-glass").bounding_box()
                    left, top = max(0, int(pane["x"])), max(64, int(pane["y"]))
                    right, bottom = min(width, int(pane["x"] + pane["width"])), min(height, int(pane["y"] + pane["height"]))
                    changed = int(np.count_nonzero(np.max(np.abs(after[top:bottom, left:right] - before[top:bottom, left:right]), axis=2) >= 3))
                    visible_motion.append({"section": selector, "sample": sample, "start_time": clock,
                                           "changed_glass_pixels": changed, "channel_threshold": 3})
                    progress("in-progress" if changed > 100 else "failed", {
                        "viewport": [width, height], "text_size": text_size, "revision": revision,
                        "sections": geometry, "contrasts": contrasts, "visible_motion": visible_motion,
                    })
                    assert changed > 100, (width, text_size, selector, sample, "No perceptible motion through glass", changed)
                page.keyboard.press("Alt+Shift+P")
                expect(page.locator("#cream-effects")).to_have_attribute("data-state", "paused")
            inherited = page.locator("#story").evaluate("""section=>{
              const pane=section.querySelector(':scope>.cream-glass'),before=getComputedStyle(pane).backgroundColor;
              section.style.setProperty('--green','#244838');
              const after=getComputedStyle(pane).backgroundColor,source=getComputedStyle(section).backgroundColor;
              section.style.removeProperty('--green');
              return {before,after,source,restored:getComputedStyle(pane).backgroundColor};
            }""")
            assert inherited["after"] != inherited["before"] and inherited["restored"] == inherited["before"]
            assert inherited["source"] == "rgb(36, 72, 56)"
            records.append({"viewport": [width, height], "text_size": text_size, "revision": revision,
                            "spawn_count": spawn_count, "sections": geometry,
                            "contrasts": contrasts, "inherited_theme_change": inherited, "visible_motion": visible_motion})
            progress("in-progress")
            page.close()
        browser.close()
    result = {"status": "passed", "url": url, "authoring_overlay": bool(stylesheet), "motion_samples_per_section": motion_samples,
              "spawn_count": spawn_count, "cases": records, "image_tool_views": 0}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "passed", "viewports": len(records), "text_measurements": sum(len(r["contrasts"]) for r in records)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only-width", type=int, choices=[320, 390, 768, 1440, 1920])
    parser.add_argument("--only-text", type=int, choices=[100, 200])
    parser.add_argument("--motion-samples", type=int, choices=range(1, 13), default=3)
    parser.add_argument("--stylesheet", type=Path, help="Prototype only: override CSS; not valid release evidence.")
    parser.add_argument("--spawn-count", type=int, choices=range(9), default=0,
                        help="Exercise reading contrast at a supported spawned-blob population.")
    args = parser.parse_args()
    review(args.url, args.output, args.only_width, args.only_text, args.motion_samples, args.stylesheet, args.spawn_count)
