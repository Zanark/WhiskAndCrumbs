"""Review the bakery, accessible top-bound notebook and faithful cake stickers."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import re
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright, expect
from review_notebook_fit import check_static_fallback


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "website-review"
NOTEBOOKS = json.loads((ROOT / "content" / "notebooks.json").read_text(encoding="utf-8"))
PHOTO_COUNT = sum(len(book["cakeIds"]) for book in NOTEBOOKS)
DECORATED_COUNT = len(next(book for book in NOTEBOOKS if book["id"] == "decorated-cakes")["cakeIds"])
DECORATED_PAGES = (DECORATED_COUNT + 3) // 4
WEIGHT_TEXT = "Cake weights 1/2 KG 1 KG 1.5 KG 2 KG 2.5 KG 3 KG"


def color_contrast(first, second):
    def luminance(color):
        channels = [float(value) / 255 for value in re.findall(r"[\d.]+", color)[:3]]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    low, high = sorted((luminance(first), luminance(second)))
    return (high + .05) / (low + .05)


def fully_load(page):
    page.evaluate("document.fonts.ready")
    for image in page.locator("img[src]:visible").all():
        image.scroll_into_view_if_needed()
        image.evaluate("node => node.decode()")
        expect(image).to_have_js_property("complete", True, timeout=30000)
        assert image.evaluate("node => node.naturalWidth > 0"), image.get_attribute("src")
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_timeout(150)


def review_shop_sign(browser, url):
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.goto(url + "#home")
    page.evaluate("document.fonts.ready")
    page.locator(".brand img").evaluate("node=>node.decode()")
    texture=page.locator(".shop-sign").evaluate("""async n=>{
      const style=getComputedStyle(n,'::before');
      const url=style.backgroundImage.match(/url\\(["']?(.*?)["']?\\)/)?.[1];
      if(!url)throw new Error('Missing continuous wood texture.');
      const image=new Image();image.src=url;await image.decode();
      const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
      const context=canvas.getContext('2d');context.drawImage(image,0,0);
      const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
      let maxLuminance=0,minAlpha=255;
      for(let i=0;i<pixels.length;i+=4){
        let luminance=0;
        for(let c=0;c<3;c++){const value=pixels[i+c]/255;
          luminance+=(value<=.04045?value/12.92:((value+.055)/1.055)**2.4)*[.2126,.7152,.0722][c];}
        maxLuminance=Math.max(maxLuminance,luminance);minAlpha=Math.min(minAlpha,pixels[i+3]);
      }
      return {url,width:canvas.width,height:canvas.height,maxLuminance,minAlpha,
        mask:style.maskImage,opacity:style.opacity};
    }""")
    assert texture["width"]==1600 and texture["height"]==600 and texture["minAlpha"]==255,texture
    assert texture["mask"]=="none" and texture["opacity"]=="1",texture
    sign=page.locator(".shop-sign")
    lit=Image.open(BytesIO(sign.screenshot())).convert("RGB")
    page.locator(".wordmark").evaluate("n=>n.style.textShadow='none'")
    unlit=Image.open(BytesIO(sign.screenshot())).convert("RGB")
    page.locator(".wordmark").evaluate("n=>n.style.removeProperty('text-shadow')")
    difference=ImageChops.difference(lit,unlit).convert("L")
    shadow_fraction=sum(difference.histogram()[8:])/(difference.width*difference.height)
    assert shadow_fraction>.015,f"Raised lighting must alter actual pixels: {shadow_fraction}"
    page.locator(".brand").evaluate("n=>n.style.visibility='hidden'")
    bare=Image.open(BytesIO(sign.screenshot())).convert("RGB")
    page.locator(".brand").evaluate("n=>n.style.removeProperty('visibility')")
    center=ImageStat.Stat(bare.crop((int(bare.width*.35),int(bare.height*.2),int(bare.width*.65),int(bare.height*.8))))
    assert center.stddev[0]>2 and center.stddev[1]>1.5,center.stddev
    texture["rendered_center_stddev"]=center.stddev
    texture["letter_light_shadow_pixel_fraction"]=shadow_fraction
    nav_bounds=page.locator("#site-nav").bounding_box()
    sign_bounds=sign.bounding_box()
    page.locator("#site-nav").evaluate("n=>n.style.visibility='hidden'")
    try:
        continuous=Image.open(BytesIO(sign.screenshot())).convert("RGB")
    finally:
        page.locator("#site-nav").evaluate("n=>n.style.removeProperty('visibility')")
    strip=continuous.crop((32,round(nav_bounds["y"]-sign_bounds["y"]+2),
                           continuous.width-32,round(nav_bounds["y"]-sign_bounds["y"]+nav_bounds["height"]-2)))
    cream_fraction=sum(max(abs(a-b) for a,b in zip(pixel,(245,235,221)))<=3
                       for pixel in strip.getdata())/(strip.width*strip.height)
    assert cream_fraction<.001 and ImageStat.Stat(strip).stddev[0]>1, cream_fraction
    texture["navigation_cream_band_fraction"]=cream_fraction
    texture["navigation_wood_stddev"]=ImageStat.Stat(strip).stddev
    records = []
    for width in (320, 390, 600, 768, 1024, 1440, 1920, 2560):
        page.set_viewport_size({"width": width, "height": 1000})
        for size in ("100%", "200%"):
            page.evaluate("size=>document.documentElement.style.fontSize=size", size)
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            page.wait_for_timeout(80)
            metrics = page.evaluate("""()=>{
              const box=n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}};
              const sign=document.querySelector('.shop-sign'),brand=sign.querySelector('.brand'),
                word=brand.querySelector('.wordmark'),desc=brand.querySelector('.brand-descriptor'),
                logo=brand.querySelector('img'),nav=document.getElementById('site-nav'),
                signStyle=getComputedStyle(sign),wordStyle=getComputedStyle(word),logoStyle=getComputedStyle(logo);
              return {sign:box(sign),brand:box(brand),word:box(word),descriptor:box(desc),logo:box(logo),
                nav:box(nav),navInsideSign:nav.closest('.shop-sign')===sign,
                awning:box(document.querySelector('.site-awning')),
                documentWidth:document.documentElement.scrollWidth,
                font:wordStyle.fontFamily,size:parseFloat(wordStyle.fontSize),shadow:wordStyle.textShadow,
                logoShadow:logoStyle.boxShadow,textureMask:getComputedStyle(sign,'::before').maskImage,
                textColor:wordStyle.color,descriptorColor:getComputedStyle(desc).color,
                woodColor:signStyle.backgroundColor,markBackground:logoStyle.backgroundColor,
                markContentWidth:logo.clientWidth-parseFloat(logoStyle.paddingLeft)-parseFloat(logoStyle.paddingRight),
                controls:[...nav.querySelectorAll('a')].map(n=>({text:n.textContent.trim(),...box(n),
                  font:parseFloat(getComputedStyle(n).fontSize),fits:n.scrollWidth<=n.clientWidth+1,
                  color:getComputedStyle(n).color,textShadow:getComputedStyle(n).textShadow,
                  background:getComputedStyle(n).backgroundImage,shadow:getComputedStyle(n).boxShadow})),
                descendantsFit:[...sign.querySelectorAll('a,span,img')].every(n=>{
                  const b=n.getBoundingClientRect();return b.left>=0 && b.right<=innerWidth && n.scrollWidth<=n.clientWidth+1}),
                animated:sign.getAnimations({subtree:true}).length};
            }""")
            assert metrics["documentWidth"] <= width and metrics["descendantsFit"], metrics
            assert abs(metrics["sign"]["left"]) < 1 and abs(metrics["sign"]["right"] - width) < 1, metrics
            assert abs((metrics["brand"]["left"] + metrics["brand"]["right"]) / 2 - width / 2) < 1, metrics
            assert metrics["navInsideSign"] and metrics["nav"]["top"] >= metrics["brand"]["bottom"], metrics
            assert metrics["nav"]["bottom"] <= metrics["sign"]["bottom"] and metrics["awning"]["top"] >= metrics["sign"]["bottom"], metrics
            assert metrics["brand"]["top"] >= metrics["sign"]["top"] and metrics["brand"]["bottom"] <= metrics["sign"]["bottom"], metrics
            assert "Courgette" in metrics["font"] and metrics["shadow"] != "none" and metrics["animated"] == 0, metrics
            assert "7px 10px 5px" in metrics["shadow"] and "10px 15px 10px" in metrics["logoShadow"],metrics
            assert metrics["textureMask"]=="none",metrics
            expected_font = (44.8 if width <= 600 else 60.8 if width <= 900 else 88) * (2 if size == "200%" else 1)
            assert abs(metrics["size"] - expected_font) < .1, metrics
            assert metrics["logo"]["width"] >= (96 if width <= 600 else 128), metrics
            assert metrics["markContentWidth"] >= (72 if width <= 600 else 100), metrics
            assert metrics["markBackground"] == "rgb(255, 250, 241)", metrics
            for color in (metrics["textColor"], metrics["descriptorColor"]):
                assert color_contrast(color, metrics["woodColor"]) >= 4.5, metrics
            # Use a conservative bright bound above every decoded wood texel; glow is not contrast.
            bright_wood = "rgb(128, 94, 72)"
            assert color_contrast(metrics["textColor"], bright_wood) >= 4.5, metrics
            assert color_contrast(metrics["descriptorColor"], bright_wood) >= 4.5, metrics
            assert [c["text"] for c in metrics["controls"]] == ["Home", "View cakes", "How to order"], metrics
            assert all(c["height"] >= 48 and c["font"] >= (36 if size == "200%" else 18) and c["fits"] for c in metrics["controls"]), metrics
            assert all(c["color"] == metrics["descriptorColor"] and c["textShadow"] != "none" for c in metrics["controls"]), metrics
            assert "bakery-sign-wood.webp" in metrics["controls"][2]["background"] and metrics["controls"][2]["shadow"] != "none", metrics
            assert all(color_contrast(c["color"], bright_wood) >= 4.5 for c in metrics["controls"]), metrics
            records.append({"viewport_width": width, "text_size": size, **metrics})
    page.evaluate("document.documentElement.style.fontSize='100%'")
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator(".brand").focus()
    focus = page.locator(".brand").evaluate("n=>({style:getComputedStyle(n).outlineStyle,width:parseFloat(getComputedStyle(n).outlineWidth)})")
    assert focus["style"] == "solid" and focus["width"] >= 3, focus
    for label in ("Home", "View cakes", "How to order"):
        page.keyboard.press("Tab")
        expect(page.locator("#site-nav a:focus")).to_be_visible()
        expect(page.locator("#site-nav a:focus")).to_have_text(label)
        assert page.locator("#site-nav a:focus").evaluate(
            "n=>getComputedStyle(n).outlineColor==='rgb(255, 250, 241)'&&parseFloat(getComputedStyle(n).outlineWidth)>=3")
    page.emulate_media(forced_colors="active")
    assert page.locator(".wordmark").evaluate("n=>getComputedStyle(n).textShadow") == "none"
    page.emulate_media(forced_colors="none", media="print")
    assert page.locator(".wordmark").evaluate("n=>getComputedStyle(n).textShadow") == "none"
    context.close()
    return {"cases": records, "continuous_wood":texture,"keyboard_order": True, "forced_colors_and_print_no_glow": True, "image_tool_views": 0}


def review_cozy_decoration(browser, url):
    records = []
    for width, height in [(320, 900), (390, 844), (768, 900), (1280, 900), (1440, 1000)]:
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        page.goto(url + "#home")
        page.evaluate("document.fonts.ready")
        page.locator(".bakery-shelf img").scroll_into_view_if_needed()
        page.locator(".hero-photo img, .bakery-shelf img").evaluate_all(
            "nodes=>Promise.all(nodes.map(node=>node.decode()))"
        )
        geometry = page.evaluate("""() => {
          const box=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
          return {
            art:box(document.querySelector('.hero-art')),
            copy:box(document.querySelector('.hero-copy')),
            cake:box(document.querySelector('.hero-photo img')),
            cakePadding:getComputedStyle(document.querySelector('.hero-photo')).paddingTop,
            heroBackgrounds:['::before','::after'].map(p=>getComputedStyle(document.querySelector('.hero-art'),p).content),
            shelf:box(document.querySelector('.bakery-shelf')),
            order:box(document.querySelector('#order')),
            footer:box(document.querySelector('.site-footer')),
            documentWidth:document.documentElement.scrollWidth,
            decor:[...document.querySelectorAll('.bakery-shelf')].map(n=>({
              hidden:n.getAttribute('aria-hidden'),events:getComputedStyle(n).pointerEvents,
              animation:getComputedStyle(n).animationName
            }))
          };
        }""")
        assert geometry["documentWidth"] <= width, geometry
        art, copy = geometry["art"], geometry["copy"]
        overlap = max(0, min(art["right"], copy["right"]) - max(art["x"], copy["x"])) * max(
            0, min(art["bottom"], copy["bottom"]) - max(art["y"], copy["y"])
        )
        assert overlap == 0, "The cake must not overlap reading copy."
        expect(page.locator(".hero-window, img[src*='bakery-window']")).to_have_count(0)
        assert geometry["cakePadding"] == "0px", geometry
        assert geometry["heroBackgrounds"] == ["none", "none"], geometry
        assert geometry["shelf"]["y"] >= geometry["order"]["bottom"], geometry
        assert geometry["shelf"]["bottom"] <= geometry["footer"]["y"] + 1, geometry
        assert all(d == {"hidden": "true", "events": "none", "animation": "none"} for d in geometry["decor"])
        for feature in ("art", "cake", "shelf"):
            bounds = geometry[feature]
            assert bounds["x"] >= 0 and bounds["right"] <= width and bounds["height"] > 0, bounds
        assert context.request.get(url + "assets/bakery-window.svg").status == 404
        records.append({"viewport": [width, height], "rejected_hero_window_absent": True, "geometry": geometry})
        context.close()
    for mode in ("missing-stylesheet", "missing-art", "forced-colors"):
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        if mode == "missing-stylesheet":
            page.route(re.compile(r"/cozy-bakery\.css(?:\?|$)"), lambda route: route.abort())
        elif mode == "missing-art":
            page.route(re.compile(r"/bakery-shelf\.svg(?:\?|$)"), lambda route: route.abort())
        else:
            page.emulate_media(forced_colors="active")
        page.goto(url + "#home")
        expect(page.locator("#site-nav")).to_be_visible()
        expect(page.locator(".hero-photo img")).to_be_visible()
        expect(page.locator("#order-contact")).to_have_attribute("href", "https://www.instagram.com/homemadevegcakes/")
        assert page.locator(".cake-card").count() == PHOTO_COUNT
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if mode != "missing-art":
            expect(page.locator(".bakery-shelf")).to_be_hidden()
        context.close()
    return {"responsive_cases": records, "fallback_cases": ["missing-stylesheet", "missing-art", "forced-colors"], "new_image_views": 0}


def review_no_separate_turn_control(page):
    books = page.locator(".category-notebook").evaluate_all(r"""nodes => nodes.map(book => {
      const buttons=[...book.querySelectorAll('button:not(#notebook-close)')],drags=[...book.querySelectorAll('[data-page-drag]')],
        retired=book.querySelectorAll('.notebook-drag-edge,.notebook-turn-label,.page-corner,[data-page-drag]:not([data-page-next])'),
        labels=[book.textContent,...[...book.querySelectorAll('[aria-label],[title]')].flatMap(n=>[
          n.getAttribute('aria-label')||'',n.getAttribute('title')||''])],
        pseudoLabels=[...book.querySelectorAll('*')].flatMap(n=>[
          getComputedStyle(n,'::before').content,getComputedStyle(n,'::after').content]);
      return {id:book.id,buttons:buttons.map(n=>({name:n.getAttribute('aria-label'),
        text:n.textContent.trim(),next:n.hasAttribute('data-page-next'),previous:n.hasAttribute('data-page-previous')})),
        dragCount:drags.length,dragIsNext:drags.length===1&&drags[0]===book.querySelector('[data-page-next]'),
        retiredCount:retired.length,turnLabels:[...labels,...pseudoLabels].filter(s=>/\bturn\b|page[- ]turn/i.test(s))};
    })""")
    assert len(books) == len(NOTEBOOKS), books
    for book in books:
        assert book["buttons"] == [
            {"name": "Previous page", "text": "\u2190", "next": False, "previous": True},
            {"name": "Next page", "text": "\u2192", "next": True, "previous": False},
        ], book
        assert book["dragCount"] == 1 and book["dragIsNext"], book
        assert book["retiredCount"] == 0 and not book["turnLabels"], book
    return books


def review_page_tabs(page):
    review_no_separate_turn_control(page)
    if page.locator("#notebook-dialog[open]").count():
        clearance = page.locator("#notebook-dialog").evaluate("""dialog=>{
          const title=dialog.querySelector('#notebook-dialog-title'),
            wire=dialog.querySelector('.is-open-notebook > .spiral-binding'),
            toolbar=dialog.querySelector('.notebook-dialog-toolbar'),
            b=wire.getBoundingClientRect(),t=title.getBoundingClientRect(),d=dialog.getBoundingClientRect();
          return {insideHeading:!!title.closest('.notebook-heading'),gap:t.top-b.bottom,height:b.height,
            wireTop:b.top,dialogTop:d.top,backing:getComputedStyle(toolbar,'::before').content,
            backFollowsTitle:title.nextElementSibling?.id==='notebook-close'};
        }""")
        assert clearance["insideHeading"] and clearance["backFollowsTitle"], clearance
        assert clearance["gap"] >= 3.99 and clearance["height"] == 40, clearance
        assert clearance["wireTop"] >= clearance["dialogTop"] and clearance["backing"] == "none", clearance
    tabs = page.locator(
        ".category-notebook .notebook-static-back, .category-notebook .notebook-controls button, "
        ".notebook-dialog-toolbar button"
    ).evaluate_all("""nodes => nodes.filter(node => node.getClientRects().length).map(node => {
      const s = getComputedStyle(node);
      const flag = getComputedStyle(node, '::before'), b = node.getBoundingClientRect();
      const enhanced=!!node.closest('#notebook-dialog[open]'),
        navigation=enhanced && node.matches('.notebook-controls button'),
        close=enhanced && node.id==='notebook-close';
      let attachment=null;
      if(navigation || close) {
        const stage=document.querySelector('#notebook-dialog .notebook-stage'),
          r=stage.getBoundingClientRect(),paper=getComputedStyle(stage,'::before'),
          right=r.right-parseFloat(paper.right);
        attachment={side:'right',attached:right-b.left,exposed:b.right-right,
          labelBeyondBacking:(b.left+b.right)/2-right-2};
      }
      return {label: node.getAttribute('aria-label') || node.textContent.trim(),
        enhanced,navigation,close,attachment,glyph:node.textContent.trim(),
        flagHeight:parseFloat(flag.height)+(flag.boxSizing==='border-box'?0:
          parseFloat(flag.paddingTop)+parseFloat(flag.paddingBottom)+parseFloat(flag.borderTopWidth)+parseFloat(flag.borderBottomWidth)),
        color: s.color, flagColor: flag.getPropertyValue('--tab-color').trim(),
        background: flag.backgroundColor, gradient: flag.backgroundImage,
        radius: flag.borderTopLeftRadius, opacity: s.opacity, font: parseFloat(s.fontSize),
        height: b.height, width: b.width, flagWidth: parseFloat(flag.width),
        pointerEvents: flag.pointerEvents, disabled: !!node.disabled,
        transform: flag.transform, textDecoration: s.textDecorationLine};
    })""")
    assert tabs, "Expected actual inner-book actions."
    for tab in tabs:
        assert tab["radius"] == "2px" and tab["transform"] == "none", tab
        assert tab["height"] >= 48 and tab["font"] >= (20 if tab["enhanced"] else 16) and tab["opacity"] == "1", tab
        assert tab["flagWidth"] <= tab["width"] + 1, tab
        pigment = list(map(int, tab["flagColor"].split()))
        assert tab["background"] == "rgb(" + ", ".join(map(str, pigment)) + ")", tab
        assert tab["gradient"] == "none", tab
        assert tab["pointerEvents"] == "none", tab
        assert tab["flagHeight"] >= tab["height"] - 3, tab
        if tab["navigation"]:
            assert tab["label"] in ["Previous page", "Next page"], tab
            assert tab["glyph"] == ("\u2190" if tab["label"] == "Previous page" else "\u2192"), tab
            assert tab["font"] >= 28 and tab["textDecoration"] == "none", tab
            assert tab["attachment"]["side"] == "right", tab
            assert abs(tab["attachment"]["attached"] - 16) <= 1 and tab["attachment"]["exposed"] >= 87, tab
        if tab["close"]:
            assert 15 <= tab["attachment"]["attached"] <= 17 and tab["attachment"]["exposed"] >= 87, tab
        if tab["attachment"]:
            assert tab["attachment"]["labelBeyondBacking"] > 0, tab
        if not tab["disabled"]:
            assert tab["color"] == "rgb(52, 72, 58)", tab
            tab["minimum_text_contrast"] = color_contrast(tab["color"], tab["background"])
            assert tab["minimum_text_contrast"] >= 4.5, tab
    return tabs


def review_paper_turn_motion(page, reverse=False):
    sheet = page.locator("#notebook-dialog .is-turning-sheet")
    motion = sheet.evaluate("""async sheet => {
      const stage=sheet.closest('.notebook-stage'),book=sheet.closest('.category-notebook'),
        animations=stage.getAnimations({subtree:true}),main=sheet.getAnimations()[0],
        duration=main.effect.getTiming().duration,frames=main.effect.getKeyframes(),
        startTimes=animations.map(a=>a.startTime),samples=[];
      animations.forEach(a=>a.pause());
      const frame=()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      for(const fraction of [0,.12,.3,.5,.68,.76,.84,.94]){
        animations.forEach(a=>a.currentTime=duration*fraction);await frame();
        const style=getComputedStyle(sheet),matrix=new DOMMatrix(style.transform),
          box=sheet.getBoundingClientRect(),origin=style.transformOrigin.split(' ').map(parseFloat),
          cast=getComputedStyle(stage.querySelector('.notebook-turn-cast')),
          contact=getComputedStyle(stage.querySelector('.notebook-turn-contact')),
          sheen=getComputedStyle(sheet.querySelector('.notebook-turn-sheen'));
        samples.push({fraction,angle:Math.atan2(matrix.m23,matrix.m22)*180/Math.PI,
          bottomLift:matrix.m23*(sheet.offsetHeight-origin[1]),sinY:matrix.m13,
          opacity:style.opacity,backface:style.backfaceVisibility,
          bounds:{left:box.left,right:box.right,top:box.top,bottom:box.bottom},
          cast:{transform:cast.transform,opacity:+cast.opacity,blur:cast.filter},
          contactOpacity:+contact.opacity,sheen:{opacity:+sheen.opacity,position:sheen.backgroundPosition}});
      }
      animations.forEach(a=>a.currentTime=duration*.5);await frame();
      return {duration,animationCount:animations.length,startTimes,
        timings:animations.map(a=>({duration:a.effect.getTiming().duration,easing:a.effect.getTiming().easing})),
        frames:frames.map(f=>({transform:f.transform,offset:f.offset,opacity:f.opacity??null})),samples,
        viewport:[innerWidth,innerHeight],perspective:getComputedStyle(stage).perspective,
        hinge:stage.getBoundingClientRect().top+parseFloat(getComputedStyle(sheet).transformOrigin.split(' ')[1]),
        spiral:book.querySelector('.spiral-binding').getBoundingClientRect().bottom-8,
        noSeparateHandle:book.querySelector('[data-page-drag]')===book.querySelector('[data-page-next]'),
        decorationInert:[...stage.querySelectorAll('.notebook-turn-shadow,.notebook-turn-cast,.notebook-turn-contact,.notebook-turn-sheen')]
          .every(n=>n.inert&&n.getAttribute('aria-hidden')==='true'&&getComputedStyle(n).pointerEvents==='none')};
    }""")
    assert motion["duration"] == 1800 and motion["animationCount"] == 4, motion
    assert len(set(motion["startTimes"])) == 1 and motion["startTimes"][0] is not None, motion
    assert all(timing == {"duration": 1800, "easing": "cubic-bezier(0.4, 0, 0.6, 1)"} for timing in motion["timings"]), motion
    endpoints = ["rotateX(180deg)", "rotateX(0deg)"] if reverse else ["rotateX(0deg)", "rotateX(180deg)"]
    assert [motion["frames"][0]["transform"], motion["frames"][-1]["transform"]] == endpoints, motion
    assert len(motion["frames"]) >= 9 and all(frame["opacity"] is None for frame in motion["frames"]), motion
    assert abs(motion["hinge"] - motion["spiral"]) < 1, motion
    assert motion["noSeparateHandle"] and motion["decorationInert"], motion
    assert max(sample["bottomLift"] for sample in motion["samples"]) >= 60, motion
    assert max(sample["cast"]["opacity"] for sample in motion["samples"]) > .2, motion
    assert max(sample["contactOpacity"] for sample in motion["samples"]) > .2, motion
    assert len({sample["cast"]["transform"] for sample in motion["samples"]}) > 4, motion
    assert len({sample["cast"]["blur"] for sample in motion["samples"]}) > 4, motion
    angles = [sample["angle"] for sample in motion["samples"]]
    assert all(first > second if reverse else first < second for first, second in zip(angles, angles[1:])), motion
    for sample in motion["samples"]:
        assert abs(sample["sinY"]) < .001 and sample["opacity"] == "1" and sample["backface"] == "hidden", sample
        if sample["angle"] < 90:
            box = sample["bounds"]
            assert box["left"] >= 0 and box["right"] <= motion["viewport"][0], sample
            assert box["top"] >= 0 and box["bottom"] <= motion["viewport"][1], sample
    before = Image.open(BytesIO(page.screenshot())).convert("RGB")
    shadow = page.locator(".notebook-turn-shadow")
    shadow.evaluate("node=>node.style.visibility='hidden'")
    without = Image.open(BytesIO(page.screenshot())).convert("RGB")
    shadow.evaluate("node=>node.style.removeProperty('visibility')")
    difference = ImageChops.difference(before, without)
    motion["painted_shadow_pixels"] = sum(max(pixel) >= 3 for pixel in difference.getdata())
    assert motion["painted_shadow_pixels"] > 50, motion
    motion["direction"] = "lowering-previous" if reverse else "lifting-next"
    return motion


def review_static_background(browser, url):
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference", forced_colors="none")
    page = context.new_page()
    page.emulate_media(media="screen")
    requests, errors = [], []
    page.on("request", lambda request: requests.append(request.url))
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url + "#home", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    expect(page.locator("#cream-effects")).to_have_attribute("data-state", "moving")
    expect(page.locator("#cream-effects")).to_be_visible()
    expect(page.locator("#cream-material")).to_have_count(1)
    expect(page.locator("#cream-cursor")).to_have_count(1)
    expect(page.locator("#cream-surface")).to_have_count(0)
    panes = page.locator(".cream-glass").evaluate_all("""nodes=>nodes.map(pane=>{
      const p=pane.getBoundingClientRect(),section=pane.parentElement,s=getComputedStyle(pane);
      return {section:section.id||section.className,width:p.width,left:p.left,right:p.right,
        backdrop:s.backdropFilter,colour:s.backgroundColor,
        oldPlates:[...section.querySelectorAll('.hero-copy,.section-heading,.story-copy,.order-layout>div,.order-action')]
          .map(n=>getComputedStyle(n,'::before').content)};
    })""")
    assert len(panes) == 5, panes
    assert all(abs(pane["width"] - 1344) <= 1 and "blur(" in pane["backdrop"] for pane in panes), panes
    assert all(all(plate == "none" for plate in pane["oldPlates"]) for pane in panes), panes
    before_clock = float(page.locator("#cream-effects").get_attribute("data-motion-time"))
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    page.wait_for_timeout(650)
    expect(page.locator("#cream-effects")).to_be_visible()
    assert float(page.locator("#cream-effects").get_attribute("data-motion-time")) > before_clock
    assert "cream-cursor-active" not in (page.locator("body").get_attribute("class") or "")
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
    page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
    expect(page.locator("#notebook-dialog")).to_be_visible()
    expect(page.locator("#cream-effects")).to_be_visible()
    expect(page.locator("#cream-cursor")).to_be_hidden()
    viewer_clock = float(page.locator("#cream-effects").get_attribute("data-motion-time"))
    page.wait_for_timeout(300)
    assert float(page.locator("#cream-effects").get_attribute("data-motion-time")) > viewer_clock
    page.locator("#notebook-close").click()
    expect(page.locator("#cream-effects")).to_be_visible()
    assert page.locator("canvas.awning-fabric").count() <= 1
    assert page.locator("canvas.awning-fabric").evaluate_all(
        "nodes=>nodes.every(n=>n.parentElement.matches('.site-awning') && n.getAttribute('aria-hidden')==='true')"
    )
    version = page.locator("#cream-effects").get_attribute("data-revision")
    for module in ("cream.mjs", "cream-model.mjs", "cream-material.mjs"):
        assert any(request.endswith(f"/{module}?v={version}") for request in requests), (module, version, requests)
    page.locator("#cream-motion-toggle").click()
    expect(page.locator("#cream-effects")).to_have_attribute("data-state", "paused")
    paused = page.locator("#cream-material").get_attribute("data-paint-count")
    page.wait_for_timeout(250)
    assert page.locator("#cream-material").get_attribute("data-paint-count") == paused
    assert "cream-cursor-active" not in page.locator("body").get_attribute("class")
    page.emulate_media(reduced_motion="reduce")
    expect(page.locator("#cream-effects")).to_be_hidden()
    expect(page.locator("#cream-motion-control")).to_be_hidden()
    assert not errors, errors
    context.close()
    return {"background_canvas_count": 1, "pointer_canvas_count": 1, "versioned_cream_modules_requested": True,
            "full_width_themed_panes": panes, "individual_reading_backplates_removed": True,
            "visible_blur_keeps_moving": True, "pause_stops_uploads": True,
            "reduced_motion_static": True, "notebooks_keep_motion_with_native_pointer": True}


def review_cover_tab_paint(page):
    results = []
    for cover in page.locator(".notebook-cover").all():
        cover.scroll_into_view_if_needed()
        cover.locator("img").evaluate_all("nodes=>Promise.all(nodes.map(n=>n.decode()))")
        sample = cover.evaluate("""cover=>{
          const bounds=cover.getBoundingClientRect(),matrix=new DOMMatrix(getComputedStyle(cover).transform),
            flags=cover.querySelector('.notebook-cover-tabs');
          const points=[...flags.children].map(flag=>{
            const x=cover.clientWidth-9-cover.offsetWidth/2,
              y=flag.offsetTop+flag.offsetHeight/2-cover.offsetHeight/2;
            return {x:bounds.width/2+matrix.a*x+matrix.c*y,
              y:bounds.height/2+matrix.b*x+matrix.d*y};
          });
          return {category:cover.dataset.category,width:bounds.width,height:bounds.height,points};
        }""")
        visible=Image.open(BytesIO(cover.screenshot())).convert("RGB")
        flags=cover.locator(".notebook-cover-tabs")
        flags.evaluate("n=>n.style.visibility='hidden'")
        try:
            hidden=Image.open(BytesIO(cover.screenshot())).convert("RGB")
        finally:
            flags.evaluate("n=>n.style.removeProperty('visibility')")
        scale_x,scale_y=visible.width/sample["width"],visible.height/sample["height"]
        changes=[]
        for point in sample["points"]:
            x,y=round(point["x"]*scale_x),round(point["y"]*scale_y)
            patch=(max(0,x-2),max(0,y-5),min(visible.width,x+3),min(visible.height,y+6))
            difference=ImageChops.difference(visible.crop(patch),hidden.crop(patch))
            change=max(high for _,high in difference.getextrema())
            assert change<=2,f"A tab still paints over the pink cover: {sample['category']}: {change}"
            changes.append(change)
        results.append({"category":sample["category"],"inside_attachment_pixel_change":changes})
    return results


def review_notebook(browser, url):
    results = {}
    for label, viewport, touch in [
        ("desktop", {"width": 1440, "height": 1000}, False),
        ("mobile", {"width": 390, "height": 844}, True),
    ]:
        context = browser.new_context(viewport=viewport, has_touch=touch, is_mobile=touch, reduced_motion="no-preference")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("""(() => {
          window.__notebookZooms = [];
          const animate = Element.prototype.animate;
          Element.prototype.animate = function(frames, options) {
            if (this.matches('.category-notebook')) window.__notebookZooms.push({frames, duration: options.duration});
            return animate.call(this, frames, options);
          };
        })()""")
        page.goto(url + "#cakes")
        expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
        expect(page.locator("#cake-gallery")).to_be_hidden()
        expect(page.locator(".notebook-cover")).to_have_count(6)
        assert page.locator(".notebook-cover h3").all_text_contents() == [book["name"] for book in NOTEBOOKS]
        for category in NOTEBOOKS:
            if category["coverCakeId"]:
                image = page.locator(f'.notebook-cover[data-category="{category["id"]}"] picture img')
                expect(image).to_have_count(1)
                cover_id = category.get("coverStickerId", category["coverCakeId"] + "-sticker")
                assert f'assets/stickers/{cover_id}-' in image.get_attribute("src")
                assert image.evaluate("node => getComputedStyle(node).objectFit") == "contain"
        construction = page.locator(".notebook-cover").evaluate_all("""nodes => nodes.map(node => {
          const style = getComputedStyle(node), binding = getComputedStyle(node.querySelector('.spiral-binding'));
          const flags=node.querySelector('.notebook-cover-tabs');
          return {radius: style.borderTopLeftRadius, corners: getComputedStyle(node, '::after').content,
            flagsDecorative:flags.getAttribute('aria-hidden')==='true' && flags.textContent==='' && !flags.querySelector('a,button,[tabindex]'),
            flags:[...flags.children].map(flag=>{
              const b=flag.getBoundingClientRect(),s=getComputedStyle(flag);
              return {color:flag.dataset.tabColor,height:flag.offsetHeight,
                out:flag.offsetLeft+flag.offsetWidth-flags.clientWidth,
                fits:b.left>=0 && b.right<=innerWidth,events:s.pointerEvents};
            }),
            background: style.backgroundColor, ruling: style.backgroundImage, shadow: style.boxShadow,
            canvas: getComputedStyle(document.body).backgroundColor, opacity: style.opacity,
            text: [...node.querySelectorAll('h3, .notebook-cover-note, .notebook-cover-action')].map(element => {
              const text = getComputedStyle(element);
              return {label: element.tagName === 'H3' ? 'title' : element.className,
                color: text.color, background: text.backgroundColor, opacity: text.opacity};
            }),
            bindingRepeat: binding.backgroundRepeat, bindingSize: binding.backgroundSize,
            pairedWire: binding.backgroundImage.includes('M12 32C5 32') && binding.backgroundImage.includes('M17 32C10 32')};
        })""")
        for paper in construction:
            assert paper["flagsDecorative"] and 3 <= len(paper["flags"]) <= 5, paper
            assert len({flag["color"] for flag in paper["flags"]}) == len(paper["flags"]), paper
            for flag in paper["flags"]:
                assert 18 <= flag["out"] <= 26 and 38 <= flag["height"] <= 48 and flag["fits"] and flag["events"] == "none", flag
            assert paper["radius"] == "2px" and paper["corners"] == "none", paper
            assert paper["background"] == "rgb(251, 237, 242)" and paper["ruling"] == "none", paper
            assert paper["canvas"] == "rgb(245, 235, 221)" and paper["opacity"] == "1", paper
            paper["cover_to_canvas_contrast"] = color_contrast(paper["background"], paper["canvas"])
            # The requested very pale pink keeps the readable green backing and text.
            assert 1 < paper["cover_to_canvas_contrast"] < color_contrast("rgb(239, 183, 200)", paper["canvas"]), paper
            assert color_contrast("rgb(52, 72, 58)", paper["canvas"]) >= 4.5, paper
            assert color_contrast(paper["background"], "rgb(52, 72, 58)") >= 4.5, paper
            for text in paper["text"]:
                assert text["opacity"] == "1", text
                if text["label"] in ("title", "notebook-cover-note"):
                    assert text["background"] == "rgba(0, 0, 0, 0)", text
                    assert text["color"] == "rgb(52, 72, 58)", text
                background = paper["background"] if text["background"] == "rgba(0, 0, 0, 0)" else text["background"]
                text["contrast"] = color_contrast(text["color"], background)
                assert text["contrast"] >= 4.5, text
            assert "inset" not in paper["shadow"] and "0px 11px 0px 2px" in paper["shadow"], paper
            assert paper["bindingRepeat"] == "space no-repeat" and paper["bindingSize"] == "30px 40px", paper
            assert paper["pairedWire"], paper
        expected_motifs = {
            "birthday-cakes": ["birthday-balloons", "birthday-gift"],
            "tea-cakes": ["teacup", "loaf-cake"],
            "cream-cakes": ["mixing-bowl", "cream-cake-slice"],
            "decorated-cakes": ["piping-bag", "birthday-candles"],
            "doll-cakes": ["doll-dress", "tiara"],
            "chocolates": ["chocolate-bar", "wrapped-truffle"],
        }
        for category, motifs in expected_motifs.items():
            decorations = page.locator(f'.notebook-cover[data-category="{category}"] .notebook-doodle')
            assert decorations.evaluate_all("nodes => nodes.map(node => node.dataset.doodle)") == motifs
            assert decorations.evaluate_all("""nodes => nodes.every(node => {
              const svg = node.querySelector('svg'), bounds = svg.getBBox();
              return node.getAttribute('aria-hidden') === 'true' && getComputedStyle(node).pointerEvents === 'none' &&
                svg.getAttribute('focusable') === 'false' && bounds.width > 0 && bounds.height > 0 &&
                bounds.x >= 4.5 && bounds.y >= 4.5 &&
                bounds.x + bounds.width <= 75.5 && bounds.y + bounds.height <= 75.5;
            })"""), f"Missing, interactive or clipped category ornament: {category}"
        page.evaluate("document.fonts.ready")
        cover_paint = review_cover_tab_paint(page)
        info = page.locator("#cake-weight-info")
        expect(info).to_have_text(WEIGHT_TEXT)
        expect(info.get_by_role("list", name="Cake weights")).to_have_count(1)
        expect(info.get_by_role("listitem")).to_have_count(6)
        assert info.evaluate("""node => {
          const covers = document.getElementById('category-notebooks');
          return node.tabIndex === -1 && !node.querySelector('input, button, a') &&
            !!(node.compareDocumentPosition(covers) & Node.DOCUMENT_POSITION_FOLLOWING) &&
            node.getBoundingClientRect().bottom <= covers.getBoundingClientRect().top;
        }""")
        photo_links = page.locator(".cake-card a[data-photo]").evaluate_all("nodes => nodes.map(node => node.href)")
        expect(page.locator(".cake-card-actions,.cake-enquire,[data-enlarge-photo]")).to_have_count(0)
        info.click()
        assert page.locator(".cake-card a[data-photo]").evaluate_all("nodes => nodes.map(node => node.href)") == photo_links
        expect(page.locator("#notebook-dialog")).to_be_hidden()
        page.locator("#cakes").screenshot(path=str(OUTPUT / f"categories-{label}.png"))
        cover = page.locator('[data-open-notebook="notebook-decorated-cakes"]')
        cover.tap() if touch else cover.click()
        dialog = page.locator("#notebook-dialog")
        book = dialog.locator("#notebook-decorated-cakes")
        expect(dialog).to_be_visible()
        assert book.evaluate("""node => {
          const style = getComputedStyle(node);
          return style.borderTopLeftRadius === '2px' && !style.boxShadow.includes('inset');
        }""")
        assert book.evaluate("""node =>
          getComputedStyle(node).backgroundColor==='rgba(0, 0, 0, 0)' &&
          getComputedStyle(node.closest('dialog')).backgroundColor==='rgba(0, 0, 0, 0)' &&
          getComputedStyle(node.closest('dialog')).borderWidth==='0px' &&
          getComputedStyle(node.closest('dialog')).boxShadow==='none' &&
          [...node.querySelectorAll('.notebook-stage,.notebook-sheet')]
            .every(paper=>getComputedStyle(paper,'::before').backgroundColor==='rgb(245, 235, 221)')
        """), "Cream paper must be separate from the reserved outside-tab gutter."
        zooms = page.evaluate("window.__notebookZooms")
        assert zooms and "scale(" in zooms[-1]["frames"][0]["transform"] and zooms[-1]["duration"] > 0, zooms
        expect(book).to_have_attribute("data-page-index", "0")
        expect(book.locator('[data-page-kind="photos"]').first).to_be_visible()
        expect(book.locator(".cake-card:visible")).to_have_count(4)
        expect(book.locator('.weight-page, .weight-list, [data-page-kind="weights"]')).to_have_count(0)
        expect(book.locator("[data-page-previous]")).to_be_disabled()
        expect(book.locator("[data-page-counter]")).to_have_text(f"1 / {DECORATED_PAGES}")
        expect(book.locator("[data-page-counter]")).to_have_attribute("aria-label", f"Page 1 of {DECORATED_PAGES}")
        expect(book.locator("[data-page-announcement]")).to_have_text(f"Page 1 of {DECORATED_PAGES}")
        assert book.locator("[data-page-announcement]").evaluate("node => !node.closest('button')")
        assert book.locator("a[data-photo]").evaluate_all("""nodes=>nodes.every(n=>
          n.getAttribute('role')==='button' && n.getAttribute('aria-haspopup')==='dialog' &&
          n.getAttribute('aria-controls')==='photo-dialog' && n.pathname.includes('/assets/images/') &&
          getComputedStyle(n,'::after').content==='none')""")
        page.wait_for_function("document.querySelector('#notebook-dialog .category-notebook').getAnimations().length === 0")
        tabs = review_page_tabs(page)
        page.screenshot(path=str(OUTPUT / f"notebook-{label}-opening-photos.png"))
        book.locator("[data-page-next]").click()
        expect(book).to_have_attribute("data-turn-state", "turning")
        turning = book.locator(".is-turning-sheet")
        hinge = turning.evaluate("""node => {
          const book = node.closest('.category-notebook');
          const pivot = parseFloat(getComputedStyle(node).transformOrigin.split(' ')[1]);
          return {sheet: book.querySelector('.notebook-stage').getBoundingClientRect().top + pivot,
                  binding: book.querySelector('.spiral-binding').getBoundingClientRect().bottom - 8};
        }""")
        assert abs(hinge["sheet"] - hinge["binding"]) < 1, hinge
        motion = review_paper_turn_motion(page)
        page.screenshot(path=str(OUTPUT / f"notebook-{label}-turning-up.png"))
        turning.evaluate("node => node.closest('.notebook-stage').getAnimations({subtree:true}).forEach(a=>a.play())")
        expect(book).to_have_attribute("data-page-index", "1")
        expect(book.locator("[data-page-announcement]")).to_have_text(f"Page 2 of {DECORATED_PAGES}")
        expect(book).to_have_attribute("data-turn-state", "idle")
        expect(book.locator(".notebook-turn-shadow,.notebook-turn-sheen")).to_have_count(0)
        expect(book.locator(".notebook-sheet:visible")).to_have_count(1)
        expect(book.locator(".cake-card:visible")).to_have_count(4)
        expect(page.locator("#notebook-dialog-title")).to_be_focused()
        assert book.locator(".notebook-sheet").evaluate_all("nodes => nodes.every(node => !node.inert && !node.hasAttribute('aria-hidden'))")
        positions = book.locator(".cake-card:visible").evaluate_all(
            "nodes => nodes.map(node => ({x: Math.round(node.getBoundingClientRect().x), y: Math.round(node.getBoundingClientRect().y)}))"
        )
        columns, rows = len({point["x"] for point in positions}), len({point["y"] for point in positions})
        assert (columns, rows) == (2, 2), (columns, rows)
        assert dialog.evaluate("node => node.scrollHeight <= node.clientHeight + 1"), "Notebook must not scroll."
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUTPUT / f"notebook-{label}-four-cakes.png"))
        for index in range(2, DECORATED_PAGES):
            page.keyboard.press("ArrowRight")
            expect(book).to_have_attribute("data-page-index", str(index))
        final_page_count = DECORATED_COUNT - (DECORATED_PAGES - 1) * 4
        expect(book.locator(".cake-card:visible")).to_have_count(final_page_count)
        page.keyboard.press("ArrowUp")
        expect(book).to_have_attribute("data-page-index", str(DECORATED_PAGES - 1))
        expect(book.locator(".cake-card:visible")).to_have_count(final_page_count)
        expect(book.locator("[data-page-next]")).to_be_disabled()
        for target in range(DECORATED_PAGES - 2, 0, -1):
            book.locator("[data-page-previous]").click()
            expect(book).to_have_attribute("data-page-index", str(target))
            expect(book).to_have_attribute("data-turn-state", "idle")
        expect(book).to_have_attribute("data-page-index", "1")
        photo = book.locator(".cake-card:visible a[data-photo]").first
        photo.click()
        expect(page.locator("#photo-counter")).to_have_text(f"Photo 5 of {DECORATED_COUNT}")
        assert page.locator("#photo-image").get_attribute("src") == photo.evaluate("n=>n.href")
        page.wait_for_function("document.getElementById('photo-image').naturalWidth > 0")
        page.keyboard.press("ArrowRight")
        expect(page.locator("#photo-counter")).to_have_text(f"Photo 6 of {DECORATED_COUNT}")
        expect(book).to_have_attribute("data-page-index", "1")
        page.keyboard.press("Escape")
        expect(photo).to_be_focused()
        for key in ["Enter", "Space"]:
            photo.press(key)
            expect(page.locator("#photo-dialog")).to_be_visible()
            expect(page.locator("#photo-counter")).to_have_text(f"Photo 5 of {DECORATED_COUNT}")
            page.keyboard.press("Escape")
            expect(photo).to_be_focused()
        page.keyboard.press("ArrowLeft")
        expect(book).to_have_attribute("data-page-index", "0")
        page.keyboard.press("ArrowDown")
        expect(book).to_have_attribute("data-page-index", "0")

        handle = book.locator("[data-page-drag]")
        cdp = context.new_cdp_session(page) if touch else None
        threshold = book.locator(".notebook-sheet:visible").evaluate(
            "n=>Math.min(180,Math.max(72,n.offsetHeight*.25))")
        committed_distance = threshold + 12
        for distance, target in [(24, "0"), (-45, "0"), (committed_distance, "1")]:
            handle.scroll_into_view_if_needed()
            box = handle.bounding_box()
            x, y = box["x"] + box["width"] * .6, box["y"] + box["height"] - 6
            assert y - max(0, distance) >= 1, "The real gesture must remain inside the viewport."
            assert page.evaluate("([x,y]) => !!document.elementFromPoint(x,y)?.closest('[data-page-drag]')", [x, y])
            if touch:
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
                for step in range(1, 9):
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y - distance * step / 8}]})
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            else:
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x, y - distance, steps=8)
                page.mouse.up()
            expect(book).to_have_attribute("data-turn-state", "idle")
            expect(book).to_have_attribute("data-page-index", target)
        book.locator("[data-page-previous]").click()
        expect(book).to_have_attribute("data-page-index", "0")
        handle.scroll_into_view_if_needed()
        box = handle.bounding_box()
        x, y = box["x"] + box["width"] * .6, box["y"] + box["height"] - 6
        assert y - committed_distance >= 1
        if touch:
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y - committed_distance}]})
            expect(book).to_have_attribute("data-turn-state", "dragging")
            cdp.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
        else:
            handle.evaluate("node => node.addEventListener('pointerdown', event => { window.__reviewPointer = event.pointerId; }, {once: true})")
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x, y - committed_distance, steps=8)
            expect(book).to_have_attribute("data-turn-state", "dragging")
            handle.evaluate("node => node.releasePointerCapture(window.__reviewPointer)")
            page.mouse.up()
        expect(book).to_have_attribute("data-turn-state", "idle")
        expect(book).to_have_attribute("data-page-index", "0")
        assert book.locator(".notebook-sheet").evaluate_all("nodes => nodes.every(node => !node.inert)")
        page.locator("#notebook-close").click()
        expect(dialog).to_be_hidden()
        expect(cover).to_be_focused()
        expect(page.locator("#cake-gallery")).to_be_hidden()
        assert not page.locator("body").evaluate("node => node.classList.contains('has-notebook-dialog')")
        for key in ["Enter", "Space"]:
            cover.focus()
            page.keyboard.press(key)
            expect(dialog).to_be_visible()
            expect(dialog.locator('[data-page-kind="photos"]').first).to_be_visible()
            expect(dialog.locator(".cake-card:visible")).to_have_count(4)
            expect(dialog.locator(".weight-page, .weight-list")).to_have_count(0)
            page.keyboard.press("Escape")
            expect(dialog).to_be_hidden()
            expect(cover).to_be_focused()
        for category in NOTEBOOKS:
            page.locator(f'[data-open-notebook="notebook-{category["id"]}"]').click()
            opened = dialog.locator(".category-notebook")
            assert opened.locator(".notebook-sheet").evaluate_all(
                "nodes => nodes.every(node => getComputedStyle(node, '::before').backgroundColor === 'rgb(245, 235, 221)')"
            ), f"Cover colour leaked into inside pages: {category['id']}"
            expect(opened).to_have_attribute("data-page-index", "0")
            expect(opened.locator('.weight-page, .weight-list, [data-page-kind="weights"]')).to_have_count(0)
            if category["cakeIds"]:
                expect(opened.locator('[data-page-kind="photos"]').first).to_be_visible()
            expect(page.locator("#notebook-dialog-title")).to_be_focused()
            if len(category["cakeIds"]) <= 4:
                expect(opened.locator(".notebook-controls")).to_be_hidden()
                page.keyboard.press("ArrowRight")
                expect(opened).to_have_attribute("data-page-index", "0")
            if not category["cakeIds"]:
                expect(opened.locator(".notebook-empty-note")).to_be_visible()
                expect(opened.locator("[data-page-next]")).to_be_disabled()
                expect(opened.locator("[data-page-drag]")).to_be_hidden()
                expect(opened.locator(".cake-card")).to_have_count(0)
            if len(category["cakeIds"]) == 1:
                trigger = opened.locator("a[data-photo]")
                trigger.click()
                expect(page.locator("#photo-counter")).to_have_text("Photo 1 of 1")
                expect(page.locator("#photo-next")).to_be_disabled()
                page.keyboard.press("Escape")
                expect(trigger).to_be_focused()
            page.locator("#notebook-close").click()
        assert not errors, errors
        results[label] = {"categories": 6, "shared_cake_weights": 6,
                          "cake_weight_pages": 0, "all_notebooks_open_directly_to_photos": True,
                          "shared_weights_before_notebooks": True,
                          "weights_informational_only": True, "weight_click_does_not_change_photo_links": True,
                          "paper_construction": construction,
                          "closed_cover_attachment_paint": cover_paint,
                          "sticky_page_tabs": tabs,
                          "category_sticker_motifs": expected_motifs,
                          "decorated_photo_page_counts": [4, 4, 2], "photo_grid": [columns, rows],
                          "turn_axis": [frame["transform"] for frame in motion["frames"]],
                          "keyboard": ["Enter", "Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"],
                          "turn_hinge_aligned_with_spiral_slots": True, "physical_paper_motion": motion,
                          "drag": "native touch" if touch else "mouse", "short_downward_drags_do_not_turn": True,
                          "drag_threshold": threshold, "committed_drag_distance": committed_distance,
                          "direct_photo_click_enter_space_and_focus_return": True,
                          "one_advance_per_next_click_or_drag": True,
                          "interrupted_drag": "native touch cancellation" if touch else "lost pointer capture",
                          "photo_viewer_scoped_to_category": True,
                          "categories_awaiting_prepared_photos": sum(not book["cakeIds"] for book in NOTEBOOKS)}
        context.close()

    for case in ["no_animation_api", "animation_error", "lighting_animation_error", "cancelled", "lost_completion", "focus_moved",
                 "resize", "motion_during_turn", "close_during_turn", "dialog_error"]:
        context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="no-preference")
        page = context.new_page()
        if case == "no_animation_api":
            page.add_init_script("Element.prototype.animate = undefined")
        if case == "animation_error":
            page.add_init_script("Element.prototype.animate = function() { throw new Error('Review fixture: unavailable animation'); }")
        if case == "lighting_animation_error":
            page.add_init_script("""const animate=Element.prototype.animate;Element.prototype.animate=function(...args){
              if(this.matches('.notebook-turn-cast'))throw new Error('Review fixture: unavailable lighting animation');
              return animate.apply(this,args)}""")
        if case == "dialog_error":
            page.add_init_script("HTMLDialogElement.prototype.showModal = function() { throw new Error('Review fixture: unavailable dialog'); }")
        page.goto(url + "#cakes")
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        if case == "dialog_error":
            expect(page.locator(".cake-card:visible")).to_have_count(PHOTO_COUNT)
            expect(page.locator("#cake-gallery")).to_be_visible()
            results[case] = "All pages remain visible after a failed dialog."
            context.close()
            continue
        book = page.locator("#notebook-dialog .category-notebook")
        book.locator("[data-page-next]").click()
        if case in ["cancelled", "lost_completion"]:
            action = "cancel" if case == "cancelled" else "pause"
            book.locator(".is-turning-sheet").evaluate(f"node => node.getAnimations()[0].{action}()")
        elif case == "focus_moved":
            page.locator("#notebook-close").focus()
        elif case == "resize":
            page.set_viewport_size({"width": 760, "height": 1000})
        elif case == "motion_during_turn":
            page.emulate_media(reduced_motion="reduce")
        elif case == "close_during_turn":
            page.locator("#notebook-close").click()
        if case in ["motion_during_turn", "close_during_turn"]:
            expect(page.locator("#notebook-dialog")).to_be_hidden()
            if case == "motion_during_turn":
                expect(page.locator(".cake-card:visible")).to_have_count(PHOTO_COUNT)
            else:
                page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
                expect(page.locator("#notebook-dialog")).to_be_visible()
                expect(book).to_have_attribute("data-page-index", "0")
        else:
            expect(book).to_have_attribute("data-page-index", "1", timeout=3500)
            expect(book).to_have_attribute("data-turn-state", "idle")
            expect(book.locator(".cake-card:visible")).to_have_count(4)
        assert page.locator(".notebook-sheet").evaluate_all("nodes => nodes.every(node => !node.inert)")
        expect(page.locator(".notebook-turn-shadow,.notebook-turn-sheen")).to_have_count(0)
        if case == "focus_moved":
            expect(page.locator("#notebook-close")).to_be_focused()
        results[case] = "No hidden/inert trap or stolen focus."
        context.close()

    for case in ["module_failure", "main_module_failure", "stylesheet_failure", "forced_colors",
                 "reduced_motion", "direct_gallery_link", "direct_category_link", "direct_page_link",
                 "hash_from_covers", "hash_while_open", "print"]:
        context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="no-preference",
                                      forced_colors="active" if case == "forced_colors" else "none")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        if case == "module_failure":
            page.route(re.compile(r"/notebooks\.mjs(?:\?|$)"), lambda route: route.abort())
        if case == "main_module_failure":
            page.route(re.compile(r"/main\.mjs(?:\?|$)"), lambda route: route.abort())
        if case == "stylesheet_failure":
            page.route(re.compile(r"/styles\.css(?:\?|$)"), lambda route: route.abort())
        if case == "reduced_motion":
            page.emulate_media(reduced_motion="reduce")
        fragment = {"direct_gallery_link": "#cake-gallery", "direct_category_link": "#notebook-doll-cakes",
                    "direct_page_link": "#decorated-cakes-photos-3"}.get(case, "#cakes")
        page.goto(url + fragment)
        if case in ["hash_from_covers", "hash_while_open"]:
            expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
            if case == "hash_while_open":
                page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
            page.evaluate("location.hash = 'decorated-cakes-photos-3'")
            expect(page.locator("#decorated-cakes-photos-3")).to_be_visible()
        if case == "print":
            page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
            page.emulate_media(media="print")
        expect(page.locator("#notebook-dialog")).to_be_hidden()
        expect(page.locator("#cake-gallery")).to_be_visible()
        expect(page.locator(".cake-card:visible")).to_have_count(PHOTO_COUNT)
        assert page.locator(".notebook-sheet").evaluate_all("nodes => nodes.every(node => !node.inert)")
        assert not errors, errors
        results[case] = "Every category and photograph is shown directly; shared cake weights remain before the covers."
        context.close()

    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference")
    page = context.new_page()
    page.goto(url + "#cakes")
    expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
    page.evaluate("document.fonts.ready")
    widths = [320, 390, 600, 768, 1024, 1440]
    reflow_fallbacks = []
    expected_reflow_fallbacks = {("200%", 320), ("200%", 390), ("200%", 600)}
    actual_reflow_fallbacks = set()
    for size in ["100%", "200%"]:
        for width in widths:
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(url + f"?reflow={width}-{size.removesuffix('%')}#cakes")
            page.evaluate("size => document.documentElement.style.fontSize = size", size)
            page.evaluate("document.fonts.ready")
            expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Category cover overflow: {size}/{width}px"
            page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
            dialog = page.locator("#notebook-dialog")
            book = dialog.locator(".category-notebook")
            page.wait_for_function("(document.querySelector('#notebook-dialog .category-notebook')?.getAnimations().length ?? 0) === 0")
            page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            if not dialog.is_visible():
                assert (size, width) in expected_reflow_fallbacks, (
                    f"Unexpected reflow fallback: {size}/{width}px")
                reflow_fallbacks.append(check_static_fallback(page, f"{width}x900 {size}", NOTEBOOKS))
                actual_reflow_fallbacks.add((size, width))
                continue
            expect(book).to_have_attribute("data-page-index", "0")
            assert dialog.evaluate("node => node.scrollWidth <= node.clientWidth"), f"Notebook overflow: {size}/{width}px"
            assert page.locator("#cake-weight-info").evaluate(
                "node => parseFloat(getComputedStyle(node).fontSize) >= 16 && node.tabIndex === -1 && node.scrollWidth <= node.clientWidth + 1"
            ), f"Unreadable or interactive shared weight information: {size}/{width}px"
            for control in [page.locator("#notebook-close"), book.locator("[data-page-next]")]:
                control.focus()
                control.scroll_into_view_if_needed()
                assert control.bounding_box()["height"] >= 48
                assert control.evaluate("""node => {
                  const rect = node.getBoundingClientRect();
                  const visible = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
                  return rect.top >= 0 && rect.bottom <= innerHeight && (visible === node || node.contains(visible));
                }"""), f"Obscured notebook control: {size}/{width}px"
            if size == "200%" and width == 320:
                page.screenshot(path=str(OUTPUT / "notebook-mobile-text-200-percent.png"))
            book.locator("[data-page-next]").click()
            expect(book).to_have_attribute("data-page-index", "1")
            expect(book.locator(".cake-card:visible")).to_have_count(4)
            assert dialog.evaluate("node => node.scrollWidth <= node.clientWidth"), f"Photo page overflow: {size}/{width}px"
            for control in book.locator(".cake-card:visible a[data-photo]").all():
                control.focus()
                control.scroll_into_view_if_needed()
                assert control.bounding_box()["height"] >= 48
                assert control.evaluate("""node => {
                  const rect = node.getBoundingClientRect();
                  const visible = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
                  return rect.top >= 0 && rect.bottom <= innerHeight && (visible === node || node.contains(visible));
                }"""), f"Obscured direct cake-photo target: {size}/{width}px"
            page.locator("#notebook-close").click()
    assert actual_reflow_fallbacks == expected_reflow_fallbacks, "Measured larger-title reflow fallback set changed."
    results["cover_weight_and_photo_reflow"] = {"widths": widths, "text_sizes": ["100%", "200%"],
                                               "complete_static_fallbacks": reflow_fallbacks}
    context.close()
    return results


def review_direct_photo_links(browser, url):
    records = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference")
    page = context.new_page()
    for enhanced in (False, True):
        page.goto(url + ("#cakes" if enhanced else "#cake-gallery"))
        if enhanced:
            page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        link = page.locator("#notebook-decorated-cakes a[data-photo]").first
        link.scroll_into_view_if_needed()
        href = link.evaluate("n=>n.href")
        for modifiers, button in [(["Control"], "left"), (["Shift"], "left"), ([], "middle")]:
            with context.expect_page() as opened:
                link.click(modifiers=modifiers, button=button)
            popup = opened.value
            expect(popup).to_have_url(href)
            expect(page.locator("#photo-dialog")).to_be_hidden()
            popup.close()
            page.bring_to_front()
            records.append({"enhanced": enhanced, "modifiers": modifiers, "button": button,
                            "native_image_destination": href, "viewer_not_intercepted": True})
        for modifier in ["altKey", "ctrlKey", "metaKey", "shiftKey"]:
            prevented = link.evaluate("""(n, modifier)=>{
              let intercepted;
              n.addEventListener('click',e=>{intercepted=e.defaultPrevented;e.preventDefault();},{once:true});
              n.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,button:0,[modifier]:true}));
              return intercepted;
            }""", modifier)
            assert prevented is False, modifier
        link.press("Shift+Space")
        expect(page.locator("#photo-dialog")).to_be_hidden()
    context.close()
    for key in ("click", "Space"):
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        page = context.new_page()
        page.add_init_script("HTMLDialogElement.prototype.showModal=function(){throw new Error('Review fixture: dialog unavailable')}")
        page.goto(url + "#cake-gallery")
        link = page.locator("#notebook-decorated-cakes a[data-photo]").first
        href = link.evaluate("n=>n.href")
        link.click() if key == "click" else link.press(key)
        expect(page).to_have_url(href)
        records.append({"viewer_failure": key, "native_image_destination": href})
        context.close()
    return records


def run(url):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    findings = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        page = context.new_page()
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        assert page.goto(url).status == 200
        brand = "Whisk & Crumbs"
        expect(page).to_have_title(f"{brand} - Baked at home. Made with heart.")
        expect(page.locator(".brand")).to_have_accessible_name(f"{brand} - home")
        expect(page.locator(".wordmark")).to_have_text(brand)
        expect(page.locator(".brand-descriptor")).to_have_text("Home-baked vegetarian cakes")
        expect(page.locator('meta[property="og:site_name"]')).to_have_attribute("content", brand)
        assert "Homemade Veg Cakes" not in page.content()
        assert "whisk-and-crumbs-social-card.jpg" in page.locator('meta[property="og:image"]').get_attribute("content")
        if url.startswith("https://"):
            expect(page.locator('link[rel="canonical"]')).to_have_attribute("href", url)
            expect(page.locator('meta[property="og:url"]')).to_have_attribute("content", url)
            expect(page.locator('meta[property="og:image"]')).to_have_attribute("content", url + "assets/whisk-and-crumbs-social-card.jpg")
        icon_assets = ["favicon.svg", "favicon-16.png", "favicon-32.png", "favicon.ico", "apple-touch-icon.png"]
        for file in icon_assets:
            expect(page.locator(f'link[href="assets/{file}"]')).to_have_count(1)
            response = context.request.get(url + "assets/" + file)
            assert response.status == 200 and response.headers["content-type"].startswith("image/"), (file, response.status, response.headers)
        assert page.locator("main > section").evaluate_all("(nodes) => nodes.map(node => node.id)") == ["home", "story", "cakes", "order"]
        expect(page.locator("#story .eyebrow").first).to_have_text("OUR LITTLE STORY")
        assert page.locator(".cake-card").count() == PHOTO_COUNT
        expect(page.locator("#notebook-dialog")).to_be_hidden()
        expect(page.locator(".category-notebook:visible")).to_have_count(6)
        expect(page.locator("#order-contact")).to_have_accessible_name("Message on Instagram")
        expect(page.locator("#order-contact .instagram-logo")).to_have_attribute("aria-hidden", "true")
        assert page.locator("form, input, textarea, select, details").count() == 0
        expect(page.locator('.weight-page, .weight-list, [data-page-kind="weights"]')).to_have_count(0)
        expect(page.locator("#cake-weight-info")).to_have_count(1)
        expect(page.locator("#cake-weight-info")).to_have_text(WEIGHT_TEXT)
        assert page.locator("#cake-weight-info").evaluate("node => getComputedStyle(node).backgroundColor === 'rgb(245, 235, 221)'")
        assert page.locator("#cake-weight-info").evaluate("node => getComputedStyle(node).borderLeftColor === 'rgb(247, 219, 228)'")
        assert page.locator(".cake-weight-values li").evaluate_all(
            "nodes=>nodes.every(n=>getComputedStyle(n,'::before').backgroundColor==='rgb(247, 219, 228)')"
        )
        assert page.locator(".category-notebook > .notebook-heading h3").all_text_contents() == [book["name"] for book in NOTEBOOKS]
        assert page.locator(".cake-card").evaluate_all("nodes => nodes.map(node => node.dataset.cakeId)") == [
            image_id for book in NOTEBOOKS for image_id in book["cakeIds"]
        ]
        words = len(page.locator("main").inner_text().split())
        focus_words = sum(len(page.locator(selector).inner_text().split()) for selector in
                          ["#home", "#cakes > .section-heading", "#cake-weight-info", "#category-notebooks", "#order"])
        story_words = len(page.locator("#story").inner_text().split())
        assert focus_words <= 224, f"The category overview/ordering copy has grown to {focus_words} words."
        assert len(page.locator("#cake-weight-info").inner_text().split()) <= 30
        assert story_words <= 110, f"The restored story has grown to {story_words} words."
        assert page.evaluate("""() => [...document.querySelectorAll('a[href^="#"]')]
          .every(link => document.getElementById(link.hash.slice(1)))""")
        fully_load(page)
        typography = page.evaluate("""async () => {
          const loaded = await document.fonts.load('400 64px "Courgette"');
          return {
            cursiveLoaded: loaded.some(font => font.family === 'Courgette' && font.status === 'loaded'),
            headings: [...document.querySelectorAll('h1, h2, h3, h4, .wordmark, .note-quote')].map(node => getComputedStyle(node).fontFamily),
            body: getComputedStyle(document.querySelector('.story-copy > p:not(.eyebrow)')).fontFamily,
            button: getComputedStyle(document.getElementById('order-contact')).fontFamily
          };
        }""")
        assert typography["cursiveLoaded"] and all("Courgette" in family for family in typography["headings"]), typography
        assert "DM Sans" in typography["body"] and "DM Sans" in typography["button"], typography
        palette = page.evaluate("""() => ({
          canvas: getComputedStyle(document.body).backgroundColor,
          ink: getComputedStyle(document.body).color,
          hero: getComputedStyle(document.getElementById('home')).backgroundColor,
          story: getComputedStyle(document.getElementById('story')).backgroundColor,
          order: getComputedStyle(document.getElementById('order')).backgroundColor
        })""")
        assert palette == {"canvas": "rgb(245, 235, 221)", "ink": "rgb(52, 72, 58)",
                           "hero": "rgb(245, 235, 221)", "story": "rgb(52, 72, 58)", "order": "rgb(52, 72, 58)"}, palette
        assert page.locator("#story").evaluate("n=>getComputedStyle(n).boxShadow==='none'"), "No inset shadow seam at the scalloped edge."
        expect(page.locator(".site-awning")).to_have_attribute("aria-hidden", "true")
        assert page.locator(".site-awning").evaluate("""node => {
          const roof=node.getBoundingClientRect(),header=document.querySelector('.site-header').getBoundingClientRect(),
            home=document.getElementById('home').getBoundingClientRect();
          const fabric=node.querySelector('img').getBoundingClientRect();
          return roof.height>=150 && roof.height<=337.5 && Math.abs(roof.left)<1 && Math.abs(roof.right-innerWidth)<1 &&
            Math.abs(fabric.left)<1 && Math.abs(fabric.right-innerWidth)<1 &&
            roof.top>=header.bottom-1 && roof.bottom<=home.top+1 && getComputedStyle(node).pointerEvents==='none';
        }"""), "The decorative shop canopy must frame, not overlap, the navigation and hero."
        hero_section = page.locator("#home")
        expect(hero_section).to_have_class("hero-section")
        expect(hero_section.locator(".notebook-page, .spiral-binding, .page-corner")).to_have_count(0)
        hero_metrics = hero_section.evaluate("""node => {
          const style = getComputedStyle(node);
          const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
          const luminance = colour => rgb(colour).map(value => {
            const channel = value / 255;
            return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
          }).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
          const contrasts = [...node.querySelectorAll('h1, h1 em, .hero-description, .hero-actions a')].map(element => {
            const text = getComputedStyle(element), background = element.matches('a') ? text.backgroundColor : style.backgroundColor;
            const a = luminance(text.color), b = luminance(background);
            return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
          });
          return {width: node.getBoundingClientRect().width, viewport: innerWidth,
            border: style.borderTopWidth, radius: style.borderTopLeftRadius, shadow: style.boxShadow,
            transform: style.transform, text: style.color,
            emphasis: getComputedStyle(node.querySelector('h1 em')).color,
            description: getComputedStyle(node.querySelector('.hero-description')).color,
            buttons: [...node.querySelectorAll('.hero-actions a')].map(element => {
              const button = getComputedStyle(element);
              return {background: button.backgroundColor, text: button.color, border: button.borderTopColor};
            }),
            readingBackground: getComputedStyle(node.querySelector('.hero-copy'), '::before').backgroundColor,
            contrasts};
        }""")
        assert hero_metrics["width"] == hero_metrics["viewport"], hero_metrics
        assert hero_metrics["border"] == hero_metrics["radius"] == "0px", hero_metrics
        assert hero_metrics["shadow"] == hero_metrics["transform"] == "none", hero_metrics
        assert hero_metrics["text"] == "rgb(52, 72, 58)" and hero_metrics["readingBackground"] == "rgb(245, 235, 221)", hero_metrics
        assert hero_metrics["emphasis"] == "rgb(164, 81, 55)" and hero_metrics["description"] == "rgb(104, 99, 87)", hero_metrics
        assert hero_metrics["buttons"] == [
            {"background": "rgb(52, 72, 58)", "text": "rgb(255, 250, 241)", "border": "rgb(52, 72, 58)"},
            {"background": "rgb(255, 250, 241)", "text": "rgb(52, 72, 58)", "border": "rgb(52, 72, 58)"},
        ], hero_metrics
        assert min(hero_metrics["contrasts"]) >= 4.5, hero_metrics
        patterns = page.evaluate("""async () => {
          const result = [];
          const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
          const luminance = values => values.map(value => {
            const channel = value / 255;
            return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
          }).reduce((sum, channel, index) => sum + channel * [.2126, .7152, .0722][index], 0);
          for (const [selector, file] of [['body', 'bakery-pattern-cream.svg'], ['#home', 'bakery-pattern-cream.svg'], ['#story', 'bakery-pattern-green.svg']]) {
            const style = getComputedStyle(document.querySelector(selector));
            if (!style.backgroundImage.includes(file)) throw new Error('Missing themed outline pattern: ' + selector);
            const image = new Image();
            await new Promise((resolve, reject) => {
              image.onload = resolve; image.onerror = () => reject(new Error('Pattern could not load: ' + file));
              image.src = new URL('assets/' + file, document.baseURI).href;
            });
            const canvas = document.createElement('canvas');
            canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
            const context = canvas.getContext('2d');
            context.drawImage(image, 0, 0);
            const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
            let maxAlpha = 0, ink = 0;
            for (let index = 3; index < pixels.length; index += 4) {
              maxAlpha = Math.max(maxAlpha, pixels[index]);
              if (pixels[index]) ink++;
            }
            const background = rgb(style.backgroundColor), foreground = rgb(style.color);
            const mixed = background.map((channel, index) => channel + (foreground[index] - channel) * maxAlpha / 255);
            const a = luminance(background), b = luminance(mixed);
            result.push({selector, source: file, maxAlpha, inkFraction: ink / (canvas.width * canvas.height),
              strokeContrast: (Math.max(a, b) + .05) / (Math.min(a, b) + .05), backgroundSize: style.backgroundSize});
          }
          return result;
        }""")
        for pattern in patterns:
            assert 0 < pattern["maxAlpha"] <= 22, pattern
            assert 0.002 <= pattern["inkFraction"] <= 0.06, pattern
            assert pattern["strokeContrast"] <= 1.25 and pattern["backgroundSize"] == "640px 480px", pattern
        assert page.locator(".button:not(.nav-cta), .recipe-note, .site-header").evaluate_all(
            "(nodes) => nodes.every(node => getComputedStyle(node).backgroundImage === 'none')"
        ), "Controls and the reading note must keep quiet solid backgrounds."
        assert page.locator(".photo-link").evaluate_all("""nodes => nodes.every(node => {
          const style = getComputedStyle(node, '::after');
          if (node.closest('.category-notebook')) return style.content === 'none';
          return style.content === '"View larger photo"' && style.backgroundColor === 'rgb(245, 235, 221)' && style.backgroundImage === 'none' &&
            style.color === 'rgb(52, 72, 58)' && style.zIndex === '1';
        })"""), "Photo labels must stay rule-free and above the neighbouring text wash."
        static_tabs = review_page_tabs(page)
        expect(page.locator(".cake-card-actions,.cake-enquire,[data-enlarge-photo]")).to_have_count(0)
        transparency = page.locator("main a[data-photo] img").evaluate_all("""images => images.map(image => {
          const canvas = document.createElement('canvas');
          canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
          const context = canvas.getContext('2d');
          context.drawImage(image, 0, 0);
          const corners = [[0, 0], [canvas.width - 1, 0], [0, canvas.height - 1], [canvas.width - 1, canvas.height - 1]];
          return {source: image.currentSrc, transparentCorners: corners.every(([x, y]) => context.getImageData(x, y, 1, 1).data[3] === 0)};
        })""")
        assert len(transparency) == PHOTO_COUNT + 1 and all(item["transparentCorners"] and "/assets/stickers/" in item["source"] for item in transparency), transparency
        page.screenshot(path=str(OUTPUT / "desktop-full.png"), full_page=True)
        page.screenshot(path=str(OUTPUT / "desktop-hero.png"))
        page.locator("#story").screenshot(path=str(OUTPUT / "desktop-story.png"))
        page.locator("#cakes").evaluate("(node) => node.scrollIntoView({block: 'start'})")
        page.screenshot(path=str(OUTPUT / "desktop-cakes.png"))
        page.locator("#order").screenshot(path=str(OUTPUT / "desktop-order.png"))

        for width in [320, 390, 600, 768, 1024, 1440]:
            page.set_viewport_size({"width": width, "height": 900})
            page.evaluate("window.scrollTo(0, 0)")
            metrics = page.evaluate("""() => ({
              viewport: innerWidth, document: document.documentElement.scrollWidth,
              body: document.body.scrollWidth,
              instagramLogo: document.querySelector('.instagram-logo').getBoundingClientRect().height,
              instagramButton: document.getElementById('order-contact').getBoundingClientRect().height,
              smallestCopy: Math.min(...[...document.querySelectorAll(
                '.hero-description, .notebook-cover-note, .cake-weight-info, .small-note, .section-heading > p, .story-copy > p, .recipe-note .eyebrow, .note-signature'
              )].map(node => parseFloat(getComputedStyle(node).fontSize))),
              shortestControl: Math.min(...[...document.querySelectorAll(
                '.button, #site-nav > a, .cake-card a[data-photo], .story-copy .text-link'
              )].map(node => node.getBoundingClientRect().height))
            })""")
            assert metrics["document"] <= width and metrics["body"] <= width, metrics
            assert metrics["smallestCopy"] >= 16 and metrics["shortestControl"] >= 48, metrics
            assert metrics["instagramLogo"] >= 128 and metrics["instagramButton"] >= 230, metrics
            findings.append(metrics)
        page.set_viewport_size({"width": 390, "height": 844})
        fully_load(page)
        expect(page.locator("#site-nav")).to_be_visible()
        expect(page.locator(".mobile-enquire")).to_be_hidden()
        page.screenshot(path=str(OUTPUT / "mobile-full.png"), full_page=True)
        page.screenshot(path=str(OUTPUT / "mobile-hero.png"))
        page.locator("#story").screenshot(path=str(OUTPUT / "mobile-story.png"))
        page.evaluate("window.scrollTo(0, document.getElementById('cakes').offsetTop + 200)")
        expect(page.locator(".mobile-enquire")).to_be_visible()
        page.locator("#order").scroll_into_view_if_needed()
        expect(page.locator(".mobile-enquire")).to_be_hidden()
        page.locator("#order").screenshot(path=str(OUTPUT / "mobile-order.png"))

        page.set_viewport_size({"width": 1440, "height": 1000})
        photo = page.locator("#notebook-decorated-cakes .cake-grid a[data-photo]").first
        photo.click()
        expect(page.locator("#photo-dialog")).to_be_visible()
        expect(page.locator("#photo-image")).to_be_visible()
        assert "/assets/images/" in page.locator("#photo-image").get_attribute("src")
        expect(page.locator("#photo-counter")).to_have_text(f"Photo 1 of {DECORATED_COUNT}")
        page.keyboard.press("ArrowRight")
        expect(page.locator("#photo-counter")).to_have_text(f"Photo 2 of {DECORATED_COUNT}")
        page.locator("#photo-prev").click()
        expect(page.locator("#photo-counter")).to_have_text(f"Photo 1 of {DECORATED_COUNT}")
        page.keyboard.press("Escape")
        expect(page.locator("#photo-dialog")).not_to_be_visible()
        expect(photo).to_be_focused()
        assert all(request.startswith(url) for request in requests), requests

        # Intercept the deliberate external handoff; no real Instagram/account action.
        context.route("https://www.instagram.com/**", lambda route: route.fulfill(
            content_type="text/html", body="<h1>External contact handoff</h1>"
        ))
        for link in [page.locator("#order-contact")]:
            expect(link).to_have_attribute("href", "https://www.instagram.com/homemadevegcakes/")
            with page.expect_popup() as opened:
                link.click()
            popup = opened.value
            expect(popup.locator("h1")).to_have_text("External contact handoff")
            popup.close()

        hero_context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference")
        hero_page = hero_context.new_page()
        hero_page.goto(url + "#home")
        intro = hero_page.locator("#home")
        bounds = intro.bounding_box()
        hero_page.mouse.move(4, 4)
        hero_page.mouse.move(bounds["x"] + bounds["width"] * .82, bounds["y"] + bounds["height"] * .22, steps=8)
        hero_page.wait_for_timeout(250)
        assert intro.evaluate("node => getComputedStyle(node).transform === 'none' && !node.querySelector('.is-page-active')")
        expect(intro.locator(".spiral-binding")).to_have_count(0)
        hero_context.close()

        notebook_results = review_notebook(browser, url)
        notebook_results["direct_image_links"] = review_direct_photo_links(browser, url)

        no_js_context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        no_js = no_js_context.new_page()
        no_js.goto(url)
        expect(no_js.locator("#site-nav")).to_be_visible()
        expect(no_js.locator(".wordmark")).to_have_text(brand)
        expect(no_js.locator("#order-contact")).to_be_visible()
        assert no_js.locator(".cake-card:visible").count() == PHOTO_COUNT
        expect(no_js.locator(".category-notebook:visible")).to_have_count(6)
        expect(no_js.locator(".weight-page, .weight-list")).to_have_count(0)
        expect(no_js.locator("#cake-weight-info")).to_have_text(WEIGHT_TEXT)
        expect(no_js.locator("#notebook-dialog")).to_be_hidden()
        assert no_js.locator("form").count() == 0
        expect(no_js.locator(".cake-card-actions,.cake-enquire,[data-enlarge-photo]")).to_have_count(0)
        direct_photo = no_js.locator(".cake-card a[data-photo]").first
        assert direct_photo.get_attribute("role") is None
        image_url = direct_photo.get_attribute("href")
        direct_photo.click()
        expect(no_js).to_have_url(url + image_url)
        no_js.go_back()
        assert no_js.evaluate("document.documentElement.scrollWidth <= innerWidth")
        no_js.screenshot(path=str(OUTPUT / "mobile-no-javascript.png"))
        no_js_context.close()

        zoomed = context.new_page()
        zoomed.set_viewport_size({"width": 1280, "height": 900})
        zoomed.goto(url)
        zoomed.evaluate("document.documentElement.style.fontSize = '200%'")
        zoom_widths = [320, 390, 600, 1280]
        for width in zoom_widths:
            zoomed.set_viewport_size({"width": width, "height": 900})
            assert zoomed.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"200% text zoom overflow at {width}px"
            assert zoomed.locator(".skip-link").evaluate("(node) => node.getBoundingClientRect().bottom < 0"), "Unfocused skip link must stay offscreen when text grows."
            if width == 320:
                zoomed.locator("#story").evaluate("(node) => node.scrollIntoView({block: 'start'})")
                zoomed.screenshot(path=str(OUTPUT / "mobile-text-zoom-story-200-percent.png"))
        zoomed.locator("#story").evaluate("(node) => node.scrollIntoView({block: 'start'})")
        zoomed.screenshot(path=str(OUTPUT / "text-zoom-story-200-percent.png"))
        zoomed.locator("#order").screenshot(path=str(OUTPUT / "text-zoom-200-percent.png"))
        zoomed.close()

        keyboard = context.new_page()
        keyboard.set_viewport_size({"width": 390, "height": 844})
        keyboard.goto(url)
        keyboard.keyboard.press("Tab")
        expect(keyboard.locator(".skip-link")).to_be_focused()
        assert keyboard.locator(".skip-link").evaluate("(node) => getComputedStyle(node).clipPath === 'none' && node.getBoundingClientRect().top >= 0")
        keyboard.keyboard.press("Enter")
        expect(keyboard.locator("#main")).to_be_focused()
        for _ in range(70):
            keyboard.keyboard.press("Tab")
            keyboard.wait_for_timeout(40)
            overlap = keyboard.evaluate("""() => {
              const active = document.activeElement, bar = document.querySelector('.mobile-enquire');
              if (active === document.body || active === bar || !bar.getClientRects().length) return null;
              const a = active.getBoundingClientRect(), b = bar.getBoundingClientRect();
              return a.height > 0 && a.top < innerHeight && a.bottom > b.top + 1
                ? {tag: active.tagName, id: active.id, bottom: a.bottom, barTop: b.top} : null;
            }""")
            assert overlap is None, overlap
        keyboard.close()

        slow_context = browser.new_context(viewport={"width": 390, "height": 844})
        slow = slow_context.new_page()
        session = slow_context.new_cdp_session(slow)
        session.send("Network.enable")
        session.send("Network.emulateNetworkConditions", {
            "offline": False, "latency": 150,
            "downloadThroughput": 200_000, "uploadThroughput": 75_000,
        })
        slow.goto(url, wait_until="networkidle")
        assert slow.locator(".hero-photo img").evaluate("(node) => node.complete && node.naturalWidth > 0")
        expect(slow.locator("#site-nav")).to_be_visible()
        slow.screenshot(path=str(OUTPUT / "mobile-slow-network.png"))
        slow_context.close()
        assert not errors, errors
        assert context.request.get(url + ".local/photos/").status == 404
        assert context.request.get(url + "docs/").status == 404
        context.close()
        static_background = review_static_background(browser, url)
        cozy_decoration = review_cozy_decoration(browser, url)
        shop_sign = review_shop_sign(browser, url)
        browser.close()

    report = {
        "url": url, "status": "passed", "sections": ["home", "story", "cakes", "order"],
        "brand": brand, "favicon_assets": icon_assets, "background_patterns": patterns,
        "visible_main_word_count": words,
        "focus_word_count": focus_words, "story_word_count": story_words,
        "sticker_transparency": transparency,
        "typography": typography,
        "palette": palette,
        "standalone_hero": hero_metrics,
        "text_zoom_200_percent_widths": zoom_widths,
        "photo_record_count": PHOTO_COUNT, "categories": {book["name"]: len(book["cakeIds"]) for book in NOTEBOOKS},
        "notebook": notebook_results,
        "static_background": static_background,
        "cozy_decoration": cozy_decoration,
        "shop_sign": shop_sign,
        "viewport_checks": findings,
        "coverage": [
            "approved cream uses five full-width themed glass panes without individual text backplates, continues across visible window blur, respects explicit pause/reduced motion, and retains native notebook controls",
            "full-width cream hero without notebook framing, spiral or pointer tilt; original green text/buttons and terracotta emphasis, preserved cake/actions and 4.5:1+ text contrast",
            "restored story immediately after the hero; no message forms and all retained photo records",
            "at most 224 category-overview/ordering words, one short shared cake-weight line and a bounded restored story",
            f"{PHOTO_COUNT + 1} linked transparent stickers; full prepared photos in the viewer",
            "six top-bound category covers, photo-first zoom opening and one informational cake-weight line before the covers",
            "four photos per page, viewport-fitted media, previous/next controls and left/right/up/down arrow keys",
            "actual mouse/touch upward drag, rejected short/downward drag and category-scoped enlargement",
            "Enter/Space, safe focus handoff, all-categories return, reduced motion, print and enhancement failures",
            "loaded local cursive headings; readable sans-serif body and order controls",
            "consistent new brand, working SVG/PNG/ICO/touch icons and branded social metadata",
            "outline-only background tiles below 1.25:1 contrast and 6% coverage; controls stay solid",
            "minimum 16px key text and principal 48px controls",
            "200% text resizing, no-JavaScript links and content",
            "native photo viewer, keyboard focus and contextual mobile order link",
            "direct external contact links with intercepted destination",
            "giant 128px Instagram camera logo, 230px button and accessible visible action label",
            "cold 150ms / 200kB-per-second connection, no automatic third-party requests",
            "private folders excluded from document root",
        ],
        "limitations": [
            "Actual Instagram/WhatsApp messaging and native devices were not tested.",
            "Categories describe visible design, not unverified flavours or ingredients.",
            "The tea photograph contains two cakes; photo-record counts are not physical product counts.",
            "Captured screenshots require separate visual review; a passing browser run is not visual inspection.",
            "User visual and representative-customer acceptance remain unrecorded.",
        ],
    }
    (OUTPUT / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Category notebooks checked: {words} static main words, {PHOTO_COUNT} photo records. Artifacts: {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output
    run(args.url)
