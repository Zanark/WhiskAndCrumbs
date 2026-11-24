"""Check actual notebook content bounds, not merely hidden scrollbars."""

import argparse
import json
from io import BytesIO
from math import ceil, floor
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
READABLE_FALLBACK_CASES = {
    "decorated-cakes": {
        (320, 480, "100%"), (360, 540, "100%"), (320, 568, "100%"),
        (320, 900, "200%"), (390, 844, "200%"), (390, 844, "150%"), (600, 800, "200%"),
    },
    "birthday-cakes": {(320, 900, "200%"), (390, 844, "200%")},
    "tea-cakes": {(320, 900, "200%")},
    "cream-cakes": {(320, 900, "200%")},
    "chocolates": {(320, 900, "200%")},
}

def settle_layout(page):
    page.evaluate("""() => new Promise((resolve, reject) => {
      let previous='',stable=0,frame;
      const timeout=setTimeout(()=>{cancelAnimationFrame(frame);reject(new Error('Notebook review layout did not settle.'));},5000);
      const sample=()=>{
        const r=document.querySelector('#notebook-dialog')?.getBoundingClientRect();
        const state=JSON.stringify([scrollX,scrollY,r?.x,r?.y,r?.width,r?.height,document.fonts.status]);
        stable=state===previous&&document.fonts.status==='loaded'?stable+1:0;
        previous=state;
        if(stable>=8){clearTimeout(timeout);resolve();return;}
        frame=requestAnimationFrame(sample);
      };
      frame=requestAnimationFrame(sample);
    })""")


def check_caption_alignment(scope, label):
    captions = scope.locator(".cake-card-info h4:visible").evaluate_all("""nodes=>nodes.map(n=>{
      const box=n.getBoundingClientRect(),image=n.closest('.cake-card').querySelector('img').getBoundingClientRect(),
        style=getComputedStyle(n),range=document.createRange();
      range.selectNodeContents(n);
      const lines=[...range.getClientRects()],center=(image.left+image.right)/2;
      return {name:n.textContent,alignment:style.textAlign,
        frameCenterDelta:Math.abs((box.left+box.right)/2-center),
        singleLineCenterDelta:lines.length===1?Math.abs((lines[0].left+lines[0].right)/2-center):null};
    })""")
    assert captions, f"No visible cake captions: {label}"
    for caption in captions:
        assert caption["alignment"] == "center" and caption["frameCenterDelta"] <= 1, (label, caption)
        if caption["singleLineCenterDelta"] is not None:
            assert caption["singleLineCenterDelta"] <= 1, (label, caption)
    return captions


def check_static_fallback(page, label, notebooks):
    expect(page.locator("#notebook-dialog")).to_be_hidden()
    notice = page.locator("#notebook-fit-note")
    expect(notice).to_be_visible()
    reasons = json.loads(notice.get_attribute("data-fit-reasons"))
    assert reasons, f"Fallback has no measured reason: {label}"
    expect(page.locator("#cake-gallery")).to_be_visible()
    expect(page.locator("#cake-gallery .category-notebook:visible")).to_have_count(6)
    expect(page.locator(".cake-card:visible")).to_have_count(sum(len(book["cakeIds"]) for book in notebooks))
    expect(page.locator(".notebook-sheet[inert], .notebook-sheet[hidden]")).to_have_count(0)
    expected_sheets = sum(max(1, (len(book["cakeIds"]) + 3) // 4) for book in notebooks)
    expect(page.locator("#cake-gallery .notebook-sheet:visible")).to_have_count(expected_sheets)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1 && scrollX === 0"), label
    assert notice.evaluate("n=>parseFloat(getComputedStyle(n).fontSize)>=18"), label
    assert page.locator("#cake-gallery .cake-card img").evaluate_all("""nodes => nodes.every(n => {
      const b=n.getBoundingClientRect();return b.width>=24 && b.height>=24 && getComputedStyle(n).objectFit==='contain';
    })"""), label
    assert page.locator("#cake-gallery .cake-card-info h4").evaluate_all(
        "nodes => nodes.every(n => parseFloat(getComputedStyle(n).fontSize)>=28)"), label
    expect(page.locator(".cake-card-actions,.cake-enquire,[data-enlarge-photo]")).to_have_count(0)
    assert page.locator("#cake-gallery .photo-link").evaluate_all(
        "nodes=>nodes.every(n=>getComputedStyle(n,'::after').content==='none')"), label
    return {"state": label, "all_photos_and_6_books": True, "reasons": reasons,
            "centered_captions": check_caption_alignment(page.locator("#cake-gallery"), label)}


def check_photo_fit(page, label, image_loaded=True):
    dialog = page.locator("#photo-dialog")
    expect(dialog).to_be_visible()
    assert page.locator("#photo-title").evaluate(
        "n=>parseFloat(getComputedStyle(n).fontSize)>=1.75*parseFloat(getComputedStyle(document.documentElement).fontSize)"), label
    image = page.locator("#photo-image")
    if image_loaded:
        image.evaluate("node => node.decode()")
        expect(image).to_be_visible()
    metrics = dialog.evaluate("""node => {
      const bounds = node.getBoundingClientRect();
      const elements = [node, ...node.querySelectorAll('div, p, span, button, img')].filter(n => n.getClientRects().length);
      const items = elements.map(n => {
        const box = n.getBoundingClientRect();
        return {id: n.id || n.className, width: n.clientWidth, scrollWidth: n.scrollWidth,
          height: n.clientHeight, scrollHeight: n.scrollHeight,
          left: box.left, right: box.right, top: box.top, bottom: box.bottom,
          control: n.tagName === 'BUTTON', image: n.tagName === 'IMG', fit: getComputedStyle(n).objectFit};
      });
      const before = [node.scrollLeft, node.scrollTop];
      node.scrollTo({left: 10000, top: 10000, behavior: 'instant'});
      const scrolled = [node.scrollLeft, node.scrollTop];
      node.scrollTo({left: before[0], top: before[1], behavior: 'instant'});
      return {items, scrolled, bounds: {left: bounds.left, right: bounds.right, top: bounds.top, bottom: bounds.bottom},
        rootWidth: document.documentElement.clientWidth, rootScrollWidth: document.documentElement.scrollWidth};
    }""")
    assert metrics["scrolled"] == [0, 0], f"Scrollable enlarged photo: {label}: {metrics}"
    assert metrics["rootScrollWidth"] <= metrics["rootWidth"] + 1, f"Page scrolls sideways: {label}"
    bounds = metrics["bounds"]
    for item in metrics["items"]:
        assert item["scrollWidth"] <= item["width"] + 1, f"Photo-view horizontal overflow: {label}: {item}"
        assert item["scrollHeight"] <= item["height"] + 1, f"Photo-view vertical overflow: {label}: {item}"
        assert (item["left"] >= bounds["left"] - 1 and item["right"] <= bounds["right"] + 1 and
                item["top"] >= bounds["top"] - 1 and item["bottom"] <= bounds["bottom"] + 1), (label, item)
        if item["control"]:
            assert item["bottom"] - item["top"] >= 48, f"Small photo control: {label}: {item}"
        if item["image"]:
            assert item["height"] >= 24 and item["fit"] == "contain", (label, item)
    return {"photo": label, "no_scroll_or_clipping": True}


def check_opaque_surfaces(page, label, paper):
    tabs = page.locator("#notebook-dialog button").evaluate_all("""nodes=>nodes
      .filter(n=>n.getClientRects().length).map(n=>{
        const b=n.getBoundingClientRect(),s=getComputedStyle(n),paint=getComputedStyle(n,'::before');
        return {label:n.textContent.trim(),left:b.left,top:b.top,right:b.right,bottom:b.bottom,
          pigment:s.getPropertyValue('--tab-color').trim().split(/\\s+/).map(Number),
          background:s.backgroundColor,face:paint.backgroundColor,gradient:paint.backgroundImage};
      })""")
    for tab in tabs:
        expected = "rgb(" + ", ".join(str(value) for value in tab["pigment"]) + ")"
        assert tab["background"] == expected and tab["face"] == expected, (label, tab)
        assert tab["gradient"] == "none", (label, tab)
    page.evaluate("""() => {
      const underlay=document.createElement('div');
      underlay.id='notebook-opacity-probe';
      underlay.style.cssText='position:fixed;inset:0;z-index:2147483647;pointer-events:none;background:rgb(255,0,255)';
      document.body.append(underlay);
    }""")
    settle_layout(page)
    pink = Image.open(BytesIO(page.screenshot())).convert("RGB")
    page.locator("#notebook-opacity-probe").evaluate("n=>n.style.background='rgb(0,255,0)'")
    settle_layout(page)
    green = Image.open(BytesIO(page.screenshot())).convert("RGB")
    page.locator("#notebook-opacity-probe").evaluate("n=>n.remove()")
    difference = ImageChops.difference(pink, green)
    regions = [paper, *tabs]
    for region in regions:
        bounds = (ceil(region["left"] + 3), ceil(region["top"] + 3),
                  floor(region["right"] - 3), floor(region["bottom"] - 3))
        assert not difference.crop(bounds).getbbox(), f"Background shows through paper/tab: {label}: {region}"
    pigment_samples = []
    for tab in tabs:
        points = [(round(tab["left"] + 5), round(tab["top"] + 5)),
                  (round(tab["right"] - 5), round(tab["top"] + 5))]
        colors = [pink.getpixel(point) for point in points]
        for color in colors:
            assert max(abs(a-b) for a,b in zip(color, tab["pigment"])) <= 2, (label, tab, colors)
        pigment_samples.append({"label": tab["label"], "attachment_and_face_rgb": colors})
    return {"state": label, "paper_and_tabs_opaque": True, "changed_pixels_through_surfaces": 0,
            "tab_pigments": pigment_samples}


def check(url, output):
    notebooks = json.loads((ROOT / "content" / "notebooks.json").read_text(encoding="utf-8"))
    cases = [
        (320, 480, "100%"), (360, 540, "100%"),
        (320, 900, "200%"), (390, 844, "200%"), (1440, 1000, "200%"),
        (1440, 1000, "100%"), (1366, 768, "100%"), (1280, 720, "100%"),
        (1024, 768, "100%"), (768, 1024, "100%"), (600, 800, "100%"),
        (390, 844, "100%"), (360, 640, "100%"), (320, 568, "100%"),
        (844, 390, "100%"), (667, 375, "100%"),
        (599, 800, "100%"), (601, 800, "100%"), (390, 844, "150%"),
        (600, 800, "200%"),
    ]
    output.mkdir(parents=True, exist_ok=True)
    findings = []
    photo_findings = []
    cover_findings = []
    fallbacks = []
    silhouette_pixels = []
    opaque_surfaces = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        context = browser.new_context(reduced_motion="no-preference")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("Element.prototype.animate = undefined")
        for case_index, (width, height, text_size) in enumerate(cases):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(url + f"?notebook-fit={case_index}#cakes")
            page.evaluate("size => document.documentElement.style.fontSize = size", text_size)
            page.evaluate("document.fonts.ready")
            assert page.locator("#cakes .section-heading > p").evaluate(
                "n=>parseFloat(getComputedStyle(n).fontSize)>=1.5*parseFloat(getComputedStyle(document.documentElement).fontSize)")
            assert page.locator(".notebook-cover h3").evaluate_all(
                "nodes=>nodes.every(n=>parseFloat(getComputedStyle(n).fontSize)>=2.25*parseFloat(getComputedStyle(document.documentElement).fontSize))")
            info = page.locator("#cake-weight-info")
            expect(info).to_have_text("Cake weights 1/2 KG 1 KG 1.5 KG 2 KG 2.5 KG 3 KG")
            assert info.evaluate("""node => {
              const box = node.getBoundingClientRect(), covers = document.getElementById('category-notebooks');
              return node.tabIndex === -1 && parseFloat(getComputedStyle(node).fontSize) >= 16 &&
                node.scrollWidth <= node.clientWidth + 1 && box.bottom <= covers.getBoundingClientRect().top &&
                !!(node.compareDocumentPosition(covers) & Node.DOCUMENT_POSITION_FOLLOWING);
            }"""), f"Shared cake weights do not fit before the covers: {width}x{height} {text_size}"
            expect(info.get_by_role("listitem")).to_have_count(6)
            assert info.locator(".cake-weight-heading, .cake-weight-values li").evaluate_all("""nodes => nodes.every(node => {
              const b=node.getBoundingClientRect(), parent=node.closest('.cake-weight-info').getBoundingClientRect();
              return parseFloat(getComputedStyle(node).fontSize)>=18 && node.tabIndex===-1 &&
                node.scrollWidth<=node.clientWidth+1 && b.left>=parent.left && b.right<=parent.right &&
                b.top>=parent.top && b.bottom<=parent.bottom;
            })"""), f"Clipped, small or interactive weight-note text: {width}x{height} {text_size}"
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1 && scrollX === 0"), (
                f"Category overview scrolls horizontally: {width}x{height} {text_size}"
            )
            cover_flags = page.locator(".notebook-cover").evaluate_all("""nodes => nodes.map(node => {
              const flags = node.querySelector('.notebook-cover-tabs');
              return {category:node.dataset.category, decorative:flags.getAttribute('aria-hidden') === 'true',
                text:flags.textContent, interactive:!!flags.querySelector('a, button, [tabindex]'),
                flags:[...flags.children].map(flag => {
                  const s=getComputedStyle(flag), b=flag.getBoundingClientRect();
                  return {color:flag.dataset.tabColor, pigment:s.getPropertyValue('--tab-color').trim(),
                    out:flag.offsetLeft + flag.offsetWidth - flags.clientWidth, height:flag.offsetHeight,
                    innerOverlap:Math.max(0, flags.clientWidth-flag.offsetLeft),
                    pointerEvents:s.pointerEvents, background:s.backgroundColor,
                    fits:b.left >= 0 && b.right <= innerWidth};
                })};
            })""")
            for cover in cover_flags:
                assert cover["decorative"] and not cover["text"] and not cover["interactive"], cover
                assert 3 <= len(cover["flags"]) <= 5, cover
                assert len({flag["color"] for flag in cover["flags"]}) == len(cover["flags"]), cover
                for flag in cover["flags"]:
                    assert 18 <= flag["out"] <= 26 and 36 <= flag["height"] <= 50, (width, text_size, cover)
                    assert flag["innerOverlap"] == 0, f"Cover attachment is painted inside pink paper: {cover}"
                    assert flag["fits"] and flag["pointerEvents"] == "none" and flag["pigment"], cover
                    assert flag["background"] == "rgb(" + ", ".join(flag["pigment"].split()) + ")", flag
            cover_findings.append({"viewport": [width, height], "text_size": text_size, "covers": cover_flags})
            for category in notebooks:
                page.locator(f'[data-open-notebook="notebook-{category["id"]}"]').click()
                dialog = page.locator("#notebook-dialog")
                book = dialog.locator(".category-notebook")
                total = max(1, (len(category["cakeIds"]) + 3) // 4)
                tested_photos = set()
                fell_back = False
                for index in range(total):
                    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                    page.evaluate("document.fonts.ready")
                    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                    label = f"{category['id']} page{index} {width}x{height} {text_size}"
                    if not dialog.is_visible():
                        expected_fallback = (
                            (width, height, text_size) in READABLE_FALLBACK_CASES.get(category["id"], set())
                            or (width <= 360 and height <= 568)
                            or text_size != "100%"
                        )
                        assert expected_fallback, (
                            f"An unexpected viewport lost its complete four-photo enhancement: {label}")
                        fallbacks.append({**check_static_fallback(page, label, notebooks),
                                          "category": category["id"], "viewport": [width, height], "text_size": text_size})
                        fell_back = True
                        static_book = page.locator(f'#notebook-{category["id"]}')
                        for link in static_book.locator("a[data-photo]").all():
                            photo_name = link.get_attribute("data-photo-title")
                            if photo_name in tested_photos:
                                continue
                            link.click()
                            photo_findings.append(check_photo_fit(page, f"{photo_name} {width}x{height} {text_size} static"))
                            page.locator("#photo-close").click()
                            expect(link).to_be_focused()
                        break
                    expect(book.locator('.weight-page, .weight-list, [data-page-kind="weights"]')).to_have_count(0)
                    if total == 1:
                        expect(book.locator(".notebook-controls")).to_be_hidden()
                    expect(book).to_have_attribute("data-page-index", str(index))
                    page.evaluate("""async () => {
                      await Promise.all([...document.querySelectorAll('#notebook-dialog img')]
                        .filter(image => image.getClientRects().length).map(image => image.decode()));
                    }""")
                    settle_layout(page)
                    centered_captions = check_caption_alignment(book, label)
                    metrics = dialog.evaluate("""node => {
                      const box = node.getBoundingClientRect();
                      const visible = element => element.getClientRects().length > 0;
                      const targets = [...node.querySelectorAll('button, a, .cake-card img, .cake-card-info h4, [data-page-counter]')]
                        .filter(visible).map(element => {
                          const b = element.getBoundingClientRect(), s = getComputedStyle(element);
                          return {tag: element.tagName, text: (element.textContent || element.getAttribute('alt') || '').trim().slice(0,80),
                            top: b.top, bottom: b.bottom, left: b.left, right: b.right, width: b.width, height: b.height,
                            contentWidth: element.clientWidth, scrollWidth: element.scrollWidth,
                            font: parseFloat(s.fontSize), isImage: element.tagName === 'IMG',
                            isControl: element.matches('button, a'), fit: s.objectFit,
                            pageArrow:element.matches('[data-page-previous],[data-page-next]'),
                            textControl:element.matches('button'),
                            fullAreaHit: !element.matches('button, a[data-photo]') ||
                              [[2,2],[b.width-2,2],[2,b.height-2],[b.width-2,b.height-2],[b.width/2,b.height/2]].every(([x,y]) => {
                                const hit=document.elementFromPoint(b.left+x,b.top+y);
                                return hit === element || element.contains(hit);
                              })};
                        });
                      const containers = [node, ...node.querySelectorAll('#notebook-mount, .category-notebook, .notebook-stage, .notebook-sheet, .cake-grid, .notebook-controls')]
                        .filter(visible).map(element => ({name: element.className || element.id,
                          height: element.clientHeight, scrollHeight: element.scrollHeight,
                          width: element.clientWidth, scrollWidth: element.scrollWidth,
                          scrollTop: element.scrollTop, scrollLeft: element.scrollLeft}));
                      const overlaps = [...node.querySelectorAll('.cake-card')].filter(visible).some(card => {
                        return card.querySelector('.photo-link').getBoundingClientRect().bottom >
                          card.querySelector('.cake-card-info').getBoundingClientRect().top + 1;
                      });
                      const stage=node.querySelector('.notebook-stage'), sb=stage.getBoundingClientRect();
                      const paperStyle=getComputedStyle(stage,'::before'), ds=getComputedStyle(node);
                      const paper={left:sb.left+parseFloat(paperStyle.left),right:sb.right-parseFloat(paperStyle.right),
                        top:sb.top,bottom:sb.bottom-parseFloat(paperStyle.bottom)};
                      const close=node.querySelector('#notebook-close').getBoundingClientRect();
                      const pageFlags=[...node.querySelectorAll('.notebook-controls button')].filter(visible).map(button => {
                        const b=button.getBoundingClientRect();
                        return {label:button.getAttribute('aria-label'),
                            attached:paper.right-b.left,exposed:b.right-paper.right,
                            beyondBacking:b.right-paper.right-2,
                            labelCenterBeyondBacking:(b.left+b.right)/2-paper.right-2,
                            direction:'right',glyph:button.textContent.trim()};
                      });
                      return {box: {top: box.top, bottom: box.bottom, left: box.left, right: box.right}, overlaps,
                        paper,retiredPhotoControls:node.querySelectorAll('.cake-card-actions,.cake-enquire,[data-enlarge-photo]').length,
                        leftGutter:parseFloat(ds.getPropertyValue('--book-left-gutter')),
                        fontScale:parseFloat(getComputedStyle(document.documentElement).fontSize)/16,
                        titleFont:parseFloat(getComputedStyle(node.querySelector('#notebook-dialog-title')).fontSize),
                        dialogPaint:{background:ds.backgroundColor,border:ds.borderWidth,shadow:ds.boxShadow},
                        pageFlags, closeFlag: {exposed:close.right-paper.right, attached:paper.right-close.left},
                        rootFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1 && scrollX === 0,
                        targets, containers, visibleCards: node.querySelectorAll('.notebook-sheet:not([hidden]) .cake-card').length};
                    }""")
                    assert not metrics["overlaps"], f"Overlapping photo action and caption: {label}"
                    assert metrics["rootFits"], f"Page scrolls sideways with notebook open: {label}"
                    assert metrics["retiredPhotoControls"] == 0 and metrics["leftGutter"] == 0, label
                    assert metrics["titleFont"] >= 34 * metrics["fontScale"], (label, metrics["titleFont"])
                    assert metrics["dialogPaint"] == {"background": "rgba(0, 0, 0, 0)", "border": "0px", "shadow": "none"}, (
                        f"An opaque native surround still encloses the tabs: {label}", metrics["dialogPaint"])
                    assert metrics["closeFlag"]["exposed"] >= 87 and 15 <= metrics["closeFlag"]["attached"] <= 17, (
                        f"Back to categories is not attached across the right edge: {label}", metrics["closeFlag"])
                    for flag in metrics["pageFlags"]:
                        assert flag["direction"] == "right"
                        assert flag["glyph"] == ("\u2190" if flag["label"] == "Previous page" else "\u2192")
                        assert abs(flag["attached"] - 16) <= 1 and flag["beyondBacking"] >= 87, (
                           f"Page flag does not cross the complete visible book edge: {label}", flag)
                        assert flag["labelCenterBeyondBacking"] > 0, (label, flag)
                    for item in metrics["containers"]:
                        if (item["scrollHeight"] > item["height"] + 1 or item["scrollWidth"] > item["width"] + 1 or
                                item["scrollTop"] or item["scrollLeft"]):
                            raise AssertionError(f"Notebook overflow: {label}: {item}")
                    bounds = metrics["box"]
                    for item in metrics["targets"]:
                        if item["isControl"] and item["scrollWidth"] > item["contentWidth"] + 1:
                            raise AssertionError(f"Overflowing notebook control text: {label}: {item}")
                        if not (item["top"] >= bounds["top"] - 1 and item["bottom"] <= bounds["bottom"] + 1 and
                                item["left"] >= bounds["left"] - 1 and item["right"] <= bounds["right"] + 1):
                            raise AssertionError(f"Clipped notebook content: {label}: {item}")
                        if item["isImage"] and (item["height"] < 24 or item["width"] < 24 or item["fit"] != "contain"):
                            raise AssertionError(f"Collapsed or cropped photograph: {label}: {item}")
                        if item["isControl"] and item["height"] < 48:
                            raise AssertionError(f"Small control: {label}: {item}")
                        expected_font = 28 if item["pageArrow"] else 20
                        if item["textControl"] and abs(item["font"] - expected_font * metrics["fontScale"]) > .1:
                            raise AssertionError(f"Approved control text size changed: {label}: {item}")
                        if item["tag"] == "H4" and item["font"] < 28 * metrics["fontScale"]:
                            raise AssertionError(f"Small cake caption: {label}: {item}")
                        if not item["fullAreaHit"]:
                            raise AssertionError(f"Obscured tab hit area: {label}: {item}")
                    expected = min(4, max(0, len(category["cakeIds"]) - index * 4))
                    assert metrics["visibleCards"] == expected, (label, metrics)
                    findings.append({"category": category["id"], "page": index, "viewport": [width, height],
                                     "text_size": text_size, "photos": expected, "no_scroll_or_clipping": True,
                                     "page_flags": metrics["pageFlags"], "close_flag": metrics["closeFlag"],
                                     "direct_photo_links": True, "paper": metrics["paper"],
                                     "smallest_photo_box": {
                                         "width": min(item["width"] for item in metrics["targets"] if item["isImage"]),
                                         "height": min(item["height"] for item in metrics["targets"] if item["isImage"])},
                                     "smallest_text_control_font": min(item["font"] for item in metrics["targets"] if item["textControl"]),
                                     "smallest_caption_font": min(item["font"] for item in metrics["targets"] if item["tag"] == "H4"),
                                     "centered_captions": centered_captions,
                                     "complete_tab_hit_areas": True})
                    if (width, height, text_size) in [(1440, 1000, "100%"), (390, 844, "100%"), (844, 390, "100%"), (320, 900, "200%")]:
                        if category["id"] in ["birthday-cakes", "tea-cakes", "chocolates", "decorated-cakes"] and index <= 1:
                            name = f"{category['id']}-{width}x{height}-{text_size.rstrip('%')}-page{index}.png"
                            page.screenshot(path=str(output / name))
                    if index == 0 and (width, height, text_size) in [(1440, 1000, "100%"), (390, 844, "100%"), (844, 390, "100%")]:
                        paper = metrics["paper"]
                        opaque_surfaces.append(check_opaque_surfaces(page, label, paper))
                        screenshot = Image.open(BytesIO(page.screenshot())).convert("RGB")
                        obstacles = page.locator(
                            "#notebook-dialog button:visible, #notebook-dialog [data-page-counter]:visible, #notebook-dialog-title"
                        ).evaluate_all("""nodes=>nodes.map(node=>{
                          const b=node.getBoundingClientRect();
                          return {left:b.left-8,right:b.right+8,top:b.top-8,bottom:b.bottom+8};
                        })""")
                        # Sample opaque paper, not a legitimate tab shadow or title focus ring.
                        candidates = [round(paper["top"] + offset) for offset in range(2, 41)
                                      if not any(box["left"] <= paper["right"] + 8
                                                 and box["right"] >= paper["right"] - 5
                                                 and box["top"] <= round(paper["top"] + offset) <= box["bottom"]
                                                 for box in obstacles)]
                        assert candidates, ("No unobscured upper paper-edge sample", label, obstacles)
                        sample_y = min(candidates,
                                       key=lambda y: max(abs(a-b) for a,b in zip(
                                           screenshot.getpixel((round(paper["right"] - 5), y)), (245,235,221))))
                        inside = screenshot.getpixel((round(paper["right"] - 5), sample_y))
                        outside = screenshot.getpixel((round(paper["right"] + 8), sample_y))
                        assert max(abs(a-b) for a,b in zip(inside, (245,235,221))) <= 3, (
                            label, inside, paper, page.locator(".is-open-notebook .notebook-stage").bounding_box(),
                            page.evaluate("({fontStatus:document.fonts.status,dpr:devicePixelRatio,scrollY})"))
                        assert max(abs(a-b) for a,b in zip(inside, outside)) >= 20, (label, inside, outside)
                        silhouette_pixels.append({"state":label,"inside_paper_rgb":inside,"outside_paper_rgb":outside})
                    for card in book.locator(".cake-card:visible").all():
                        link = card.locator("a[data-photo]")
                        photo_name = link.get_attribute("data-photo-title")
                        link.click()
                        expect(page.locator("#photo-title")).to_have_text(photo_name)
                        assert page.locator("#photo-image").get_attribute("src") == link.evaluate("n=>n.href")
                        photo_findings.append(check_photo_fit(page, f"{photo_name} {width}x{height} {text_size}"))
                        page.locator("#photo-close").click()
                        expect(link).to_be_focused()
                        tested_photos.add(photo_name)
                    if index + 1 < total:
                        book.locator("[data-page-next]").click()
                if fell_back:
                    page.goto(url + f"?fit-resume={case_index}-{category['id']}#cakes")
                    page.evaluate("size => document.documentElement.style.fontSize = size", text_size)
                    page.evaluate("document.fonts.ready")
                else:
                    page.locator("#notebook-close").click()
            assert not errors, errors
        expected_fallbacks = {
            (category, width, height, text_size)
            for category, category_cases in READABLE_FALLBACK_CASES.items()
            for width, height, text_size in category_cases & set(cases)
        }
        actual_fallbacks = {
            (item["category"], *item["viewport"], item["text_size"])
            for item in fallbacks
        }
        assert expected_fallbacks <= actual_fallbacks, (
            "A required readable fallback disappeared without an explicit measured update."
        )
        for resize_open_book in (False, True):
            page.set_viewport_size({"width": 1440 if resize_open_book else 320, "height": 1000 if resize_open_book else 360})
            page.goto(url + f"?notebook-fit-extreme={int(resize_open_book)}#cakes")
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
            if resize_open_book:
                page.locator("#notebook-dialog [data-page-next]").click()
                page.set_viewport_size({"width": 320, "height": 360})
            expect(page.locator("#notebook-dialog")).to_be_hidden()
            expect(page.locator("#cake-gallery")).to_be_visible()
            expect(page.locator("#notebook-fit-note")).to_be_visible()
            expect(page.locator(".cake-card:visible")).to_have_count(sum(len(book["cakeIds"]) for book in notebooks))
            expect(page.locator(".notebook-sheet[inert], .notebook-sheet[hidden]")).to_have_count(0)
        late_font_cases = []
        for outcome in ("loaded", "failed"):
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.goto(url + f"?late-font-fit={outcome}#cakes")
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            page.evaluate("document.fonts.ready")
            page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
            page.locator("#notebook-dialog [data-page-next]").click()
            requests = []
            font_url = f"assets/fonts/dm-sans-regular.ttf?fit-late={outcome}"
            page.route(f"**/{font_url}", lambda route: requests.append(route))
            page.evaluate("""url => {
              const font = new FontFace('LateFitReview', `url("${url}")`);
              document.fonts.add(font);
              window.__lateFitFont = font.load().then(() => 'loaded', error => error.name);
            }""", font_url)
            page.wait_for_function("document.fonts.status === 'loading'")
            page.set_viewport_size({"width": 320, "height": 360})
            page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
            expect(page.locator("#notebook-dialog")).to_be_visible()
            assert requests, "Expected a held late font request."
            for request in requests:
                if outcome == "loaded":
                    request.fulfill(status=200, content_type="font/ttf",
                                    body=(ROOT / "web" / "assets" / "fonts" / "dm-sans-regular.ttf").read_bytes())
                else:
                    request.fulfill(status=404, body="Expected late font failure.")
            result = page.evaluate("window.__lateFitFont")
            assert result == ("loaded" if outcome == "loaded" else "NetworkError"), result
            expect(page.locator("#notebook-dialog")).to_be_hidden()
            expect(page.locator("#notebook-fit-note")).to_be_visible()
            late_font_cases.append({"font": outcome, "fit_rechecked": True, "no_clipped_notebook": True})
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(url + "?photo-load-state=1#cakes")
        page.evaluate("document.documentElement.style.fontSize = '200%'")
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        page.locator("#notebook-dialog [data-page-next]").click()
        pending_requests = []
        page.route("**/assets/images/*.jpg", lambda route: pending_requests.append(route))
        loading_opener = page.locator("#notebook-dialog .cake-card:visible a[data-photo]").first
        loading_opener_id = loading_opener.evaluate("n=>n.closest('.cake-card').dataset.cakeId")
        loading_opener.click()
        page.set_viewport_size({"width": 320, "height": 900})
        expect(page.locator("#photo-image")).to_be_hidden()
        expect(page.locator("#photo-error")).to_be_hidden()
        loading = check_photo_fit(page, "320x900 200% while loading", image_loaded=False)
        assert pending_requests, "Expected to hold the full-photo request."
        for request in pending_requests:
            request.fulfill(status=404, body="Photo loading failure fixture.")
        expect(page.locator("#photo-error")).to_be_visible()
        failed = check_photo_fit(page, "320x900 200% after loading failure", image_loaded=False)
        page.locator("#photo-close").click()
        expect(page.locator(f'[data-cake-id="{loading_opener_id}"] a[data-photo]')).to_be_focused()
        context.close()
        browser.close()
    report = {"status": "passed", "url": url, "cases": cases, "pages_checked": len(findings),
              "photo_views_checked": len(photo_findings), "photo_findings": photo_findings,
              "cover_flags": cover_findings,
              "readable_static_fallbacks": fallbacks, "painted_silhouette_pixels": silhouette_pixels,
              "opaque_surfaces": opaque_surfaces,
              "photo_load_states": [loading, failed],
              "late_font_cases": late_font_cases,
              "extreme_text_viewport_fallback": "320x360 at200% exposes all content instead of clipping",
              "findings": findings}
    (output / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "pages_checked": len(findings),
                      "photo_views_checked": len(photo_findings), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.url, args.output)
