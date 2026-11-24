"""Numerical browser review of the original entrance building; never opens images."""

import argparse
import html
import json
import os
from io import BytesIO
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
CASES = [(320, 568), (390, 844), (768, 900), (1280, 720), (1440, 1000), (1024, 500)]
SELECTORS = [
    ".entrance-shop", ".entrance-masonry", ".entrance-upper-storey", ".entrance-sign",
    ".entrance-cornice", ".entrance-awning", ".entrance-pier-left", ".entrance-pier-right",
    ".entrance-doorway", ".entrance-doorframe", ".entrance-threshold", ".entrance-step",
    ".entrance-pavement", "#entrance-skip", "#entrance-enter>span",
]


def source_overlay(page):
    template = (ROOT / "web" / "index.template.html").read_text(encoding="utf-8")
    built = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    config = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    start, end = '<div class="entrance-art"', '    <a id="entrance-enter"'
    art = template[template.index(start):template.index(end)]
    version = re.search(r'entrance-shop\.css\?v=([^"]+)', built)[1]
    for key, value in {"ASSET_VERSION": version, "NAME": config["name"],
                       "WORDMARK": config["wordmark"], "DESCRIPTOR": config["descriptor"]}.items():
        art = art.replace("{{" + key + "}}", html.escape(value, quote=True))
    output = built[:built.index(start)] + art + built[built.index(end):]

    def route(request):
        path = urlparse(request.request.url).path
        if path == "/":
            request.fulfill(body=output, content_type="text/html")
        elif path.endswith("/entrance-shop.css"):
            request.fulfill(path=str(ROOT / "web" / "entrance-shop.css"),
                            content_type="text/css")
        elif Path(path).name.startswith("bakery-facade-"):
            asset = ROOT / "web" / "assets" / Path(path).name
            request.fulfill(path=str(asset),
                            content_type="image/svg+xml" if asset.suffix == ".svg" else "image/webp")
        else:
            request.continue_()
    page.route("**/*", route)


def changed(a, b, threshold=8):
    difference = ImageChops.difference(a, b).convert("L")
    return sum(difference.histogram()[threshold:]) / (difference.width * difference.height)


def geometry(page):
    return page.evaluate("""selectors=>{
      const rect=n=>{const b=n.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height,r:b.right,b:b.bottom}};
      const visible=n=>!!n.getClientRects().length && getComputedStyle(n).display!=='none';
      const boxes=Object.fromEntries(selectors.map(s=>[s,rect(document.querySelector(s))]));
      const word=document.querySelector('.entrance-wordmark'),sign=document.querySelector('.entrance-sign'),
        pane=document.querySelector('.entrance-door-right .entrance-glass'),
        plaque=document.querySelector('.entrance-open-sign');
      const range=document.createRange();range.selectNodeContents(word);
      const wb=range.getBoundingClientRect();
      return {boxes,viewport:[innerWidth,innerHeight],scrollWidth:document.documentElement.scrollWidth,
        panes:[...document.querySelectorAll('.entrance-glass,.entrance-display-glass')].filter(visible).map(n=>({selector:n.className,...rect(n)})),
        plaque:{...rect(plaque),board:rect(plaque.querySelector('.open-sign-board')),pane:rect(pane),behind:getComputedStyle(pane,'::after').zIndex>getComputedStyle(plaque).zIndex,
          letters:[...plaque.querySelectorAll('.open-sign-greeting,strong')].map(n=>({text:n.textContent,font:getComputedStyle(n).fontSize,
            fits:n.scrollWidth<=n.clientWidth+1&&n.scrollHeight<=n.clientHeight+1,...rect(n)}))},
        sign:{word:word.textContent,font:getComputedStyle(word).font,shadow:getComputedStyle(word).textShadow,
          background:getComputedStyle(sign).backgroundImage,opacity:getComputedStyle(sign).opacity,
          wordBounds:{x:wb.x,y:wb.y,w:wb.width,h:wb.height,r:wb.right,b:wb.bottom},box:rect(sign),
          descriptor:rect(document.querySelector('.entrance-descriptor')),mark:rect(document.querySelector('.entrance-sign-mark'))},
        rooms:document.querySelectorAll('.entrance-room').length,canvases:document.querySelectorAll('.bakery-interior').length,
        controls:['#entrance-skip','#entrance-enter>span'].map(s=>({s,font:getComputedStyle(document.querySelector(s)).fontSize,...rect(document.querySelector(s))})),
        paints:[...document.querySelectorAll('.entrance-upper-storey img,.entrance-pavement,.entrance-awning img')].map(n=>({src:n.currentSrc,loaded:n.complete&&n.naturalWidth>0}))};
    }""", SELECTORS)


def scene_geometry(page):
    return page.locator(".entrance-room").evaluate("""async room=>{
      const q=new URL(document.querySelector('script[src*="main.mjs"]').src).search;
      const {createBakeryScene}=await import(new URL('bakery-scene.mjs'+q,document.baseURI));
      const {bakeryView,projectPoint}=await import(new URL('bakery-view.mjs'+q,document.baseURI));
      const box=room.getBoundingClientRect(),canvas=room.querySelector('canvas'),gl=canvas.getContext('webgl2'),
        program=gl.getParameter(gl.CURRENT_PROGRAM),actual=gl.getUniform(program,gl.getUniformLocation(program,'viewMatrix')),
        look=[Number(room.dataset.lookX),Number(room.dataset.lookY)],expected=bakeryView(box.width,box.height,...look).matrix,
        scene=createBakeryScene(),panes=[...document.querySelectorAll('.entrance-glass,.entrance-display-glass')]
          .filter(n=>n.getBoundingClientRect().width>0).map(n=>n.getBoundingClientRect());
      const point=p=>{let v=projectPoint(actual,p,box.width,box.height);return {...v,x:v.x+box.x,y:v.y+box.y}};
      return {room:{x:box.x,y:box.y,w:box.width,h:box.height,b:box.bottom},
        matrixError:Math.max(...actual.map((v,i)=>Math.abs(v-expected[i]))),error:gl.getError(),look,
        floorContacts:scene.groups.filter(g=>g.floorContact).map(g=>({id:g.id,y:g.min[1]})),
        cakes:['lowerCakeLeftTop','lowerCakeRightTop','upperCakeLeftTop','upperCakeRightTop'].map(name=>{
          const p=point(scene.landmarkPoints[name]);
          return {name,...p,pane:panes.findIndex(b=>p.x>b.left+3&&p.x<b.right-3&&p.y>b.top+3&&p.y<b.bottom-3)};
        }),footing:point(scene.landmarkPoints.counterFootingCenterContact),
        front:point([0,1.25,-.5]),back:point([0,1.25,-6])};
    }""")


def check(record):
    errors = []
    width, height = record["viewport"]
    boxes = record["boxes"]
    for name, b in boxes.items():
        if b["x"] < -1 or b["r"] > width+1 or b["y"] < -1 or b["b"] > height+1:
            errors.append(f"outside viewport: {name} {b}")
    if record["scrollWidth"] > width:
        errors.append("horizontal overflow")
    for control in record["controls"]:
        if control["h"] < 48 or control["w"] < 48:
            errors.append("control below 48px")
    shop, entry = boxes[".entrance-shop"], boxes["#entrance-enter>span"]
    if shop["b"] > entry["y"] - 3:
        errors.append("building overlaps enlarged entry label")
    sign, upper, canopy = boxes[".entrance-sign"], boxes[".entrance-upper-storey"], boxes[".entrance-awning"]
    if not (sign["y"] < upper["b"]+1 and canopy["y"] <= sign["b"]+20):
        errors.append("disconnected upper storey/fascia/canopy")
    pier, door, threshold, step = (boxes[s] for s in (
        ".entrance-pier-left", ".entrance-doorframe", ".entrance-threshold", ".entrance-step"))
    if not (pier["y"] < canopy["b"] and pier["b"] >= door["b"]-1
            and abs(threshold["y"]-door["b"]) < 12
            and step["y"] <= threshold["b"]+2):
        errors.append("unsupported storefront or disconnected steps")
    ground = boxes[".entrance-pavement"]
    record["painted_paving_top"] = ground["y"] + ground["h"] * 67/140
    if record["painted_paving_top"] > step["b"] + 2:
        errors.append("step floats above painted pavement")
    if boxes[".entrance-masonry"]["y"] > upper["b"]:
        errors.append("gap between upper storey and supporting masonry")
    word = record["sign"]["wordBounds"]
    if word["x"] < sign["x"] or word["r"] > sign["r"] or word["y"] < sign["y"] or word["b"] > sign["b"]:
        errors.append("wordmark does not fit")
    for name in ("descriptor", "mark"):
        part = record["sign"][name]
        if part["x"] < sign["x"] or part["r"] > sign["r"] or part["y"] < sign["y"] or part["b"] > sign["b"]:
            errors.append(f"sign {name} does not fit")
    if "bakery-sign-wood.webp" not in record["sign"]["background"] or record["sign"]["opacity"] != "1":
        errors.append("original unfaded wood missing")
    plaque = record["plaque"]
    if not all(item["fits"] for item in plaque["letters"]):
        errors.append("plaque text overflow")
    if float(plaque["letters"][0]["font"].removesuffix("px")) < 16 or float(plaque["letters"][1]["font"].removesuffix("px")) < 24:
        errors.append("plaque lettering too small")
    if not (plaque["x"] >= plaque["pane"]["x"] and plaque["r"] <= plaque["pane"]["r"]
            and plaque["y"] >= plaque["pane"]["y"] and plaque["b"] <= plaque["pane"]["b"]):
        errors.append("plaque outside right glass")
    if not record["plaque"]["behind"] or record["rooms"] != 1 or record["canvases"] != 1:
        errors.append("glass/continuous room contract")
    if not all(p["loaded"] for p in record["paints"]):
        errors.append("missing facade art")
    scene = record["scene"]
    if scene["matrixError"] > .0002 or scene["error"] or any(p["y"] != 0 for p in scene["floorContacts"]):
        errors.append("room camera/ground contact changed")
    if not all(cake["pane"] >= 0 for cake in scene["cakes"]):
        errors.append("cake landmark obscured by facade")
    board = plaque["board"]
    record["cake_landmarks_under_plaque"] = [
        cake["name"] for cake in scene["cakes"]
        if board["x"] <= cake["x"] <= board["r"] and board["y"] <= cake["y"] <= board["b"]
    ]
    if record["cake_landmarks_under_plaque"]:
        errors.append("hanging board covers a cake landmark")
    if not scene["room"]["y"] <= scene["footing"]["y"] <= scene["room"]["b"]:
        errors.append("counter footing outside room")
    return errors


def pane_pixels(page, panes):
    before = Image.open(BytesIO(page.screenshot())).convert("RGB")
    fixture = page.add_style_tag(content=".entrance-room { visibility: hidden !important; }")
    hidden = Image.open(BytesIO(page.screenshot())).convert("RGB")
    fixture.evaluate("n=>n.remove()")
    return [{
        "pane": i,
        "room_changed_fraction": changed(
            before.crop((round(p["x"]+4), round(p["y"]+4), round(p["r"]-4), round(p["b"]-4))),
            hidden.crop((round(p["x"]+4), round(p["y"]+4), round(p["r"]-4), round(p["b"]-4)))),
    } for i, p in enumerate(panes)]


BLOCKED_AUDIO = """(() => {
  window.__facadeAudio = {created:0,resume:0,oscillator:0};
  window.AudioContext = class {
    constructor(){this.state='suspended';window.__facadeAudio.created++;}
    close(){this.state='closed';return Promise.resolve();}
    resume(){window.__facadeAudio.resume++;throw Error('Must not resume blocked audio');}
    createOscillator(){window.__facadeAudio.oscillator++;throw Error('Must not schedule blocked audio');}
  };
})()"""


def safety_review(browser, url, overlay):
    records = []
    for mode in ("reduced-motion", "forced-colors", "short-screen", "direct-link", "no-javascript",
                 "background", "print", "missing-module", "missing-css", "missing-art", "poster-fallback",
                 "keyboard-enter", "escape"):
        settings = {"viewport": {"width": 390, "height": 844}, "reduced_motion": "no-preference"}
        if mode == "reduced-motion":
            settings["reduced_motion"] = "reduce"
        elif mode == "forced-colors":
            settings["forced_colors"] = "active"
        elif mode == "short-screen":
            settings["viewport"]["height"] = 450
        elif mode == "no-javascript":
            settings["java_script_enabled"] = False
        context = browser.new_context(**settings)
        page = context.new_page()
        page.add_init_script(BLOCKED_AUDIO)
        if overlay:
            source_overlay(page)
        if mode == "background":
            page.add_init_script("Object.defineProperty(document,'visibilityState',{get:()=> 'hidden'});")
        elif mode == "print":
            page.emulate_media(media="print")
        elif mode == "poster-fallback":
            page.add_init_script("""(() => {
              const original=HTMLCanvasElement.prototype.getContext;
              HTMLCanvasElement.prototype.getContext=function(type,...args){
                return type.startsWith('webgl')?null:original.call(this,type,...args);
              };
            })()""")
        elif mode.startswith("missing-"):
            blocked = {"missing-module": "**/main.mjs*", "missing-css": "**/entrance-shop.css*",
                       "missing-art": "**/bakery-facade-*"}[mode]
            page.route(blocked, lambda route: route.abort())
        page.goto(url + ("#cakes" if mode == "direct-link" else ""))
        record = {"mode": mode}
        if mode in ("missing-module", "missing-css", "missing-art", "poster-fallback", "keyboard-enter", "escape"):
            entrance = page.locator("#bakery-entrance")
            if mode != "missing-module":
                expect(entrance).to_have_attribute("data-state", "waiting")
            if mode == "keyboard-enter":
                building_before = page.locator(".entrance-shop").bounding_box()
                page.locator("#entrance-enter").focus()
                page.keyboard.press("Enter")
                expect(entrance).to_have_attribute("data-state", "opening")
                page.wait_for_timeout(420)
                record["door_motion"] = page.locator(".entrance-door-right").evaluate("""door=>{
                  const matrix=new DOMMatrix(getComputedStyle(door).transform);
                  const plaque=door.querySelector('.entrance-open-sign');
                  return {turn:Math.abs(matrix.m13),attached:!!plaque,ownAnimations:plaque.getAnimations().length};
                }""")
                assert record["door_motion"]["turn"] > .2 and record["door_motion"]["attached"]
                assert not record["door_motion"]["ownAnimations"]
                building_after = page.locator(".entrance-shop").bounding_box()
                record["building_motion"] = max(abs(building_after[k]-building_before[k]) for k in building_before)
                assert record["building_motion"] < .1
            elif mode == "escape":
                page.keyboard.press("Escape")
            elif mode == "missing-module":
                page.locator("#entrance-enter").click()
                assert urlparse(page.url).fragment == "home"
            else:
                if mode == "poster-fallback":
                    poster = page.locator(".entrance-room-poster")
                    expect(poster).to_be_visible()
                    poster.locator("img").evaluate("n=>n.decode()")
                    record["poster_loaded"] = poster.locator("img").evaluate("n=>n.naturalWidth>0")
                    assert record["poster_loaded"]
                page.locator("#entrance-skip").click()
            expect(entrance).to_be_hidden(timeout=3500)
            if mode == "keyboard-enter":
                expect(page.locator("#main")).to_be_focused()
        else:
            expect(page.locator("#bakery-entrance")).to_be_hidden()
        record["state"] = page.locator("#bakery-entrance").get_attribute("data-state")
        if mode != "no-javascript":
            record["audio"] = page.evaluate("window.__facadeAudio")
            assert record["audio"]["resume"] == record["audio"]["oscillator"] == 0
            assert record["audio"]["created"] == (1 if mode == "keyboard-enter" else 0)
        records.append(record)
        context.close()
    return records


def review(url, output, overlay):
    output.mkdir(parents=True, exist_ok=True)
    runtime = output / "browser-runtime"
    runtime.mkdir(exist_ok=False)
    os.environ["TMP"] = os.environ["TEMP"] = str(runtime.resolve())
    records, failures = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
            for width, height in CASES:
                for text_size in (100, 200):
                    context = browser.new_context(viewport={"width": width, "height": height},
                                                  reduced_motion="no-preference",
                                                  has_touch=width < 600, is_mobile=width < 600)
                    page = context.new_page()
                    if overlay:
                        source_overlay(page)
                    page.goto(url)
                    page.evaluate("document.fonts.ready")
                    expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
                    page.evaluate("s=>document.documentElement.style.fontSize=s+'%'", text_size)
                    page.locator(".entrance-upper-storey img,.entrance-pavement,.entrance-awning img").evaluate_all(
                        "ns=>Promise.all(ns.map(n=>n.decode()))")
                    if (width, height, text_size) == (320, 568, 200) and not page.locator("#entrance-motion").evaluate("n=>n.hidden"):
                        expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "controls-fit")
                        expect(page.locator("#bakery-entrance")).to_be_hidden()
                        expect(page.locator("#site-nav")).to_be_visible()
                        expect(page.locator(".notebook-cover")).to_have_count(6)
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                        records.append({"viewport":[width,height],"text_size":text_size,
                                        "controls_fit_fallback":True,"complete_site_available":True,"errors":[]})
                        print(width, height, text_size, "COMPLETE SITE FALLBACK")
                        context.close()
                        continue
                    expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=20000)
                    page.wait_for_timeout(120)
                    record = geometry(page)
                    record.update(text_size=text_size, scene=scene_geometry(page))
                    record["errors"] = check(record)
                    record["pane_pixels"] = pane_pixels(page, record["panes"])
                    if any(p["room_changed_fraction"] < .02 for p in record["pane_pixels"]):
                        record["errors"].append("room is not painted through every glass pane")
                    page.screenshot(path=str(output / f"facade-{width}x{height}-text{text_size}.png"))
                    if text_size == 100:
                        original = Image.open(BytesIO(page.locator(".entrance-sign").screenshot())).convert("RGB")
                        fixture = page.add_style_tag(content=".entrance-wordmark { text-shadow: none !important; } .entrance-sign-mark { box-shadow: none !important; }")
                        plain = Image.open(BytesIO(page.locator(".entrance-sign").screenshot())).convert("RGB")
                        fixture.evaluate("n=>n.remove()")
                        record["raised_sign_changed_fraction"] = changed(original, plain)
                        if record["raised_sign_changed_fraction"] < .01:
                            record["errors"].append("raised sign has no meaningful pixel effect")
                        before = page.locator(".entrance-shop").bounding_box()
                        if width >= 600:
                            page.mouse.move(width*.1, height*.45, steps=6)
                            page.wait_for_timeout(200)
                            left = scene_geometry(page)
                            page.mouse.move(width*.9, height*.45, steps=6)
                            page.wait_for_timeout(200)
                            right = scene_geometry(page)
                            after = page.locator(".entrance-shop").bounding_box()
                            record["pointer"] = {"left":left["look"],"right":right["look"],
                                "front_shift":abs(left["front"]["x"]-right["front"]["x"]),
                                "back_shift":abs(left["back"]["x"]-right["back"]["x"]),
                                "outer_max_movement":max(abs(before[k]-after[k]) for k in before)}
                            if record["pointer"]["outer_max_movement"] > .1:
                                record["errors"].append("outer architecture follows pointer")
                            if record["pointer"]["front_shift"] <= record["pointer"]["back_shift"]:
                                record["errors"].append("depth parallax not retained")
                    page.locator("#entrance-skip").click()
                    expect(page.locator("#bakery-entrance")).to_be_hidden()
                    record["skip_works"] = True
                    records.append(record)
                    failures.extend([f"{width}x{height}/{text_size}: {e}" for e in record["errors"]])
                    print(width, height, text_size, "PASS" if not record["errors"] else record["errors"])
                    context.close()
            safety = safety_review(browser, url, overlay)
            browser.close()
    finally:
        shutil.rmtree(runtime)
    result = {"source_overlay":overlay,"image_views":0,"screenshots_visually_inspected":False,
              "records":records,"safety":safety,"failures":failures}
    (output / "review.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    if failures:
        raise SystemExit(f"{len(failures)} geometry/visibility checks failed; evidence saved.")
    print("All facade geometry cases passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-overlay", action="store_true")
    args = parser.parse_args()
    review(args.url, args.output.resolve(), args.source_overlay)
