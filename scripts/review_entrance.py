"""Review the click-to-enter doorway and optional bell without audible playback."""

import argparse
from array import array
from io import BytesIO
import json
from pathlib import Path
import re
import time
import wave
from PIL import Image, ImageChops

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "entrance-review"
TRACK_AUDIO = """(() => {
  window.__bellContexts = [];
  window.__bellResumeCalls = 0;
  window.__bellOscillators = 0;
  const NativeAudioContext = window.AudioContext;
  window.AudioContext = class extends NativeAudioContext {
    constructor(...args) {
      super(...args);
      window.__bellContexts.push({context: this, initialState: this.state});
    }
    resume() { window.__bellResumeCalls++; return super.resume(); }
    createOscillator() { window.__bellOscillators++; return super.createOscillator(); }
  };
})()"""
BLOCKED_AUDIO = """(() => {
  window.__bellContexts = [];
  window.__bellResumeCalls = 0;
  window.__bellOscillators = 0;
  window.AudioContext = class {
    constructor() {
      this.state = 'suspended';
      window.__bellContexts.push({context: this, initialState: this.state});
    }
    close() { this.state = 'closed'; return Promise.resolve(); }
    resume() { window.__bellResumeCalls++; throw new Error('Blocked sound must never resume.'); }
    createOscillator() { window.__bellOscillators++; throw new Error('Blocked sound must never be scheduled.'); }
  };
})()"""


def new_page(browser, audio_script=TRACK_AUDIO, **settings):
    context = browser.new_context(
        viewport=settings.pop("viewport", {"width": 1440, "height": 1000}),
        reduced_motion=settings.pop("reduced_motion", "no-preference"),
        **settings,
    )
    page = context.new_page()
    page.add_init_script(audio_script)
    return context, page


def completed(page):
    expect(page.locator("#bakery-entrance")).to_be_hidden(timeout=3500)
    page.wait_for_function("""() => document.getElementById('bakery-entrance').dataset.state !== 'pending'
      && window.__bellContexts.every(item => item.context.state === 'closed')""", timeout=3500)
    return page.evaluate("""() => ({
      state: document.getElementById('bakery-entrance').dataset.state,
      audio: document.getElementById('bakery-entrance').dataset.audio,
      resumeCalls: window.__bellResumeCalls,
      oscillators: window.__bellOscillators,
      contexts: window.__bellContexts.map(item => ({initial: item.initialState, final: item.context.state}))
    })""")


def capture_frames(page):
    # Functional timing is checked separately; these freeze the real click-driven CSS timeline.
    for label, viewport in [("desktop", {"width": 1440, "height": 1000}), ("mobile", {"width": 390, "height": 844})]:
        page.set_viewport_size(viewport)
        page.evaluate("""() => {
          history.replaceState(null, '', location.pathname + location.search);
          scrollTo(0, 0);
          const entrance = document.getElementById('bakery-entrance');
          entrance.hidden = false;
          entrance.classList.remove('is-entering');
          entrance.dataset.state = 'waiting';
        }""")
        page.screenshot(path=str(OUTPUT / f"{label}-waiting.png"))
        for elapsed, stage in [(120, "closed"), (650, "opening"), (1100, "entering")]:
            page.evaluate("""elapsed => {
              history.replaceState(null, '', location.pathname + location.search);
              scrollTo(0, 0);
              const entrance = document.getElementById('bakery-entrance');
              entrance.hidden = false;
              entrance.classList.add('is-entering');
              entrance.getBoundingClientRect();
              for (const animation of entrance.getAnimations({subtree: true})) {
                animation.pause(); animation.currentTime = elapsed;
              }
            }""", elapsed)
            page.screenshot(path=str(OUTPUT / f"{label}-{stage}.png"))
        page.evaluate("document.getElementById('bakery-entrance').hidden = true")


def review_open_sign(browser, url):
    records = []
    for width, height in [(1440, 1000), (1280, 720), (1024, 500), (390, 844), (320, 568)]:
        context, page = new_page(browser, audio_script=BLOCKED_AUDIO, viewport={"width": width, "height": height})
        startup = []
        page.on("console", lambda message: startup.append({"type": message.type, "text": message.text})
                if message.type in {"warning", "error"} else None)
        page.on("requestfailed", lambda request: startup.append({"url": request.url, "failure": request.failure}))
        page.goto(url)
        page.evaluate("document.fonts.ready")
        if page.locator("#bakery-entrance").get_attribute("data-state") == "unavailable":
            print(json.dumps({"viewport": [width, height], "entrance_startup_failures": startup}), flush=True)
        expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
        sign = page.locator(".entrance-open-sign")
        board = sign.locator(".open-sign-board")
        expect(sign).to_have_count(1)
        expect(sign.locator(".open-sign-greeting")).to_have_text("We are")
        expect(sign.locator("strong")).to_have_text("OPEN")
        cases = []
        for text_size in ("100%", "200%"):
            page.evaluate("size=>document.documentElement.style.fontSize=size", text_size)
            geometry = sign.evaluate("""node=>{
              const box=n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height}};
              const pane=node.closest('.entrance-glass'),board=node.querySelector('.open-sign-board'),
                style=getComputedStyle(node),glass=getComputedStyle(pane,'::after');
              return {sign:box(node),pane:box(pane),board:box(board),transform:style.transform,
                ownAnimation:node.getAnimations().length,
                behindGlass:parseInt(glass.zIndex)>parseInt(style.zIndex)&&getComputedStyle(pane).isolation==='isolate',
                decorative:!!node.closest('[aria-hidden="true"]')&&!node.querySelector('a,button,[tabindex]')&&style.pointerEvents==='none',
                doorLocal:node.closest('.entrance-door')?.classList.contains('entrance-door-right')&&!node.closest('.entrance-room'),
                lettering:[...board.querySelectorAll('.open-sign-greeting,strong')].map(n=>({
                  text:n.textContent,font:parseFloat(getComputedStyle(n).fontSize),
                  fits:n.scrollWidth<=n.clientWidth+1&&n.scrollHeight<=n.clientHeight+1,
                  ...box(n)}))};
            }""")
            assert geometry["decorative"] and geometry["doorLocal"] and geometry["behindGlass"], geometry
            assert geometry["ownAnimation"] == 0, geometry
            pane, bounds = geometry["pane"], geometry["sign"]
            assert bounds["left"] >= pane["left"] + 1 and bounds["right"] <= pane["right"] - 1, geometry
            assert bounds["top"] >= pane["top"] + 1 and bounds["bottom"] <= pane["bottom"] - 1, geometry
            assert all(item["fits"] and item["font"] >= 16 for item in geometry["lettering"]), geometry
            assert geometry["lettering"][1]["font"] >= 24, geometry
            cases.append({"text_size": text_size, **geometry})
        page.evaluate("document.documentElement.style.fontSize='100%'")
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=15000)
        page.locator(".entrance-room").evaluate("""room=>new Promise((resolve,reject)=>{
          let previous='',stable=0,frame;
          const timeout=setTimeout(()=>{cancelAnimationFrame(frame);reject(new Error('Entrance render did not settle after text resize.'));},5000);
          const sample=()=>{
            const canvas=room.querySelector('canvas'),r=room.getBoundingClientRect();
            const state=JSON.stringify([r.x,r.y,r.width,r.height,canvas?.width,canvas?.height,
              room.dataset.lookX,room.dataset.lookY,room.dataset.sceneState,document.fonts.status]);
            stable=state===previous&&room.dataset.sceneState==='ready'&&document.fonts.status==='loaded'?stable+1:0;
            previous=state;
            if(stable>=8){clearTimeout(timeout);resolve();return;}
            frame=requestAnimationFrame(sample);
          };
          frame=requestAnimationFrame(sample);
        })""")
        original = Image.open(BytesIO(board.screenshot())).convert("RGB")
        fixture = page.add_style_tag(content=".entrance-glass::after { background: rgb(255 255 255 / 25%) !important; }")
        frosted = Image.open(BytesIO(board.screenshot())).convert("RGB")
        fixture.evaluate("node=>node.remove()")
        restored = Image.open(BytesIO(board.screenshot())).convert("RGB")
        difference = ImageChops.difference(original, frosted).convert("L")
        glass_changes = sum(difference.histogram()[4:]) / (difference.width * difference.height)
        assert glass_changes > .15, "The glass overlay must actually paint in front of the sign."
        assert ImageChops.difference(original, restored).getbbox() is None, "The controlled reflection fixture must restore exactly."
        before = sign.bounding_box()
        page.mouse.move(width * .9, height * .25)
        page.wait_for_timeout(120)
        after = sign.bounding_box()
        assert all(abs(before[key] - after[key]) < .1 for key in before), "The hanging sign must not follow room parallax."
        page.screenshot(path=str(OUTPUT / f"open-sign-{width}x{height}.png"))
        motion = page.evaluate("""()=>{
          const sign=document.querySelector('.entrance-open-sign'),door=sign.closest('.entrance-door'),
            before=sign.getBoundingClientRect(),own=getComputedStyle(sign).transform;
          document.getElementById('entrance-enter').click();
          document.getElementById('bakery-entrance').getBoundingClientRect();
          for(const animation of document.getElementById('bakery-entrance').getAnimations({subtree:true})){
            animation.pause();animation.currentTime=500;
          }
          const after=sign.getBoundingClientRect(),matrix=new DOMMatrix(getComputedStyle(door).transform);
          return {doorTurns:Math.abs(matrix.m13)>.2,ownTransformUnchanged:own===getComputedStyle(sign).transform,
            projectedWidthBefore:before.width,projectedWidthAfter:after.width};
        }""")
        assert motion["doorTurns"] and motion["ownTransformUnchanged"], motion
        assert abs(motion["projectedWidthBefore"] - motion["projectedWidthAfter"]) > 1, motion
        records.append({"viewport": [width, height], "layouts": cases,
                        "glass_overlay_fixture_pixel_change": glass_changes, "door_motion": motion})
        context.close()
    return {"cases": records, "image_tool_views": 0, "owner_visual_acceptance": "Not established."}


def review(url):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = {}
    with sync_playwright() as playwright:
        allowed = playwright.chromium.launch(
            channel="msedge", headless=True,
            args=["--mute-audio", "--autoplay-policy=no-user-gesture-required"],
        )
        results["hanging_open_sign"] = review_open_sign(allowed, url)
        context, page = new_page(allowed)
        page.goto(url)
        expect(page.locator("#bakery-entrance")).to_be_visible()
        expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
        page.wait_for_function("document.querySelector('.entrance-room-poster img').complete && document.querySelector('.entrance-room-poster img').naturalWidth > 0")
        page.locator(".entrance-room-poster img").evaluate("node=>node.decode()")
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=15000)
        expect(page.locator(".bakery-interior")).to_have_count(1)
        assert page.locator(".entrance-glass").evaluate_all(
            "nodes=>nodes.every(node=>getComputedStyle(node).backgroundColor==='rgba(0, 0, 0, 0)')"
        )
        windows = []
        for glass in page.locator(".entrance-glass").all():
            bounds = glass.bounding_box()
            clip = {"x": bounds["x"] + bounds["width"] * .2, "y": bounds["y"] + bounds["height"] * .15,
                    "width": bounds["width"] * .6, "height": bounds["height"] * .6}
            visible = Image.open(BytesIO(page.screenshot(clip=clip))).convert("RGB")
            page.locator(".entrance-room").evaluate("node=>node.style.visibility='hidden'")
            hidden = Image.open(BytesIO(page.screenshot(clip=clip))).convert("RGB")
            page.locator(".entrance-room").evaluate("node=>node.style.removeProperty('visibility')")
            difference = ImageChops.difference(visible, hidden).convert("L")
            changed = sum(difference.histogram()[8:]) / (difference.width * difference.height)
            assert changed > .25, f"The room is not visible through the actual window pixels: {changed}"
            windows.append({"interior_pixel_change_fraction": changed})
        results["transparent_windows"] = windows
        before_parallax = page.locator("#bakery-entrance").evaluate(
            "element => [element.style.getPropertyValue('--look-x'), element.style.getPropertyValue('--look-y')]"
        )
        page.mouse.move(720, 500)
        page.wait_for_timeout(220)
        frame_before = page.locator(".entrance-doorframe").bounding_box()
        view_before = page.locator(".entrance-room").evaluate("n=>[Number(n.dataset.lookX),Number(n.dataset.lookY)]")
        page.mouse.move(1300, 180, steps=8)
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=3000)
        after_parallax = page.locator("#bakery-entrance").evaluate(
            "element => [element.style.getPropertyValue('--look-x'), element.style.getPropertyValue('--look-y')]"
        )
        assert after_parallax != before_parallax and after_parallax != ["0", "0"], (before_parallax, after_parallax)
        view_after = page.locator(".entrance-room").evaluate("n=>[Number(n.dataset.lookX),Number(n.dataset.lookY)]")
        assert abs(view_after[0]-view_before[0])>.8 and abs(view_after[1]-view_before[1])>.8
        frame_after=page.locator(".entrance-doorframe").bounding_box()
        assert all(abs(frame_before[key]-frame_after[key])<.1 for key in frame_before)
        results["interior_depth_parallax"] = {"before": view_before, "after": view_after, "fixed_storefront": True}
        page.locator("#entrance-enter").click(position={"x": 80, "y": 80})
        state = completed(page)
        assert state["state"] == "finished" and state["audio"] in {"started", "skipped"}, state
        assert state["resumeCalls"] == 0, state
        if state["audio"] == "started":
            assert state["oscillators"] == 4 and state["contexts"] == [{"initial": "running", "final": "closed"}], state
        results["click_entry_and_parallax"] = {"parallaxChanged": True, **state}
        capture_frames(page)

        rendered = page.evaluate("""async () => {
          const {createBellVoice, BELL_DURATION_SECONDS} = await import('./bell.mjs');
          const sampleRate = 24000;
          const audio = new OfflineAudioContext(1, Math.ceil(sampleRate * (BELL_DURATION_SECONDS + .1)), sampleRate);
          createBellVoice(audio);
          const buffer = await audio.startRendering();
          const samples = buffer.getChannelData(0);
          let peak = 0, energy = 0;
          for (const sample of samples) { peak = Math.max(peak, Math.abs(sample)); energy += sample * sample; }
          return {sampleRate, duration: buffer.duration, peak, rms: Math.sqrt(energy / samples.length),
            samples: Array.from(samples)};
        }""")
        samples = rendered.pop("samples")
        assert 1.0 <= rendered["duration"] <= 1.6 and 0.005 < rendered["peak"] <= 0.15, rendered
        assert rendered["rms"] > 0.001, rendered
        assert max(abs(sample) for sample in samples[-1200:]) < 0.0001, "Bell tail must end cleanly."
        pcm = array("h", (round(max(-1, min(1, sample)) * 32767) for sample in samples))
        with wave.open(str(OUTPUT / "bell-preview.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rendered["sampleRate"])
            wav.writeframes(pcm.tobytes())
        results["offline_waveform"] = rendered
        context.close()

        for case, target, settings in [
            ("reduced_motion", url, {"reduced_motion": "reduce"}),
            ("direct_order_link", url + "#order", {}),
            ("short_landscape", url, {"viewport": {"width": 844, "height": 390}}),
        ]:
            context, page = new_page(allowed, **settings)
            page.goto(target)
            state = completed(page)
            assert state["audio"] == "skipped" and not state["contexts"], state
            results[case] = state
            context.close()

        context, page = new_page(allowed)
        page.goto(url, wait_until="domcontentloaded")
        page.locator("#entrance-enter").focus()
        page.keyboard.press("Enter")
        state = completed(page)
        assert state["state"] == "finished", state
        expect(page.locator("#main")).to_be_focused()
        results["keyboard_entry"] = state
        context.close()

        context, page = new_page(allowed)
        page.goto(url)
        expect(page.locator("#bakery-entrance")).to_have_attribute("data-state","waiting")
        page.locator("#entrance-enter").focus()
        page.keyboard.press("Enter")
        page.locator(".site-header .brand").focus()
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        expect(page.locator(".site-header .brand")).to_be_focused()
        results["explicit_focus_choice_preserved"] = True
        context.close()

        context, page = new_page(allowed)
        page.goto(url, wait_until="domcontentloaded")
        clicked = page.locator("#entrance-skip").is_visible()
        if clicked:
            page.locator("#entrance-skip").click(timeout=1500)
        state = completed(page)
        assert state["state"] in {"skipped", "finished"}, state
        assert state["resumeCalls"] == 0, state
        results["skip_control"] = {"clicked": clicked, **state}
        context.close()

        context, page = new_page(allowed)
        def delay_logo(route):
            time.sleep(2.5)
            route.continue_()
        page.route("**/whisk-and-crumbs-mark.svg", delay_logo)
        page.goto(url, wait_until="domcontentloaded")
        expect(page.locator("#bakery-entrance")).to_be_visible()
        page.locator("#entrance-enter").click(position={"x": 100, "y": 100})
        state = completed(page)
        assert state["state"] == "finished", state
        results["slow_asset_load_click_entry"] = state
        context.close()

        context, page = new_page(allowed)
        page.route(re.compile(r"/entrance\.mjs(?:\?|$)"), lambda route: route.abort())
        page.goto(url)
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        expect(page.locator("#category-notebooks")).to_have_class("category-notebooks is-enhanced")
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        book = page.locator("#notebook-dialog .category-notebook")
        expect(book).to_have_attribute("data-page-index", "0")
        book.locator(".cake-grid a[data-photo]").first.click()
        expect(page.locator("#photo-dialog")).to_be_visible()
        results["optional_module_failure"] = "Main photo enhancement still works."
        context.close()

        context, page = new_page(allowed)
        page.route(re.compile(r"\.mjs(?:\?|$)"), lambda route: route.abort())
        page.goto(url)
        expect(page.locator("#bakery-entrance")).to_be_visible()
        page.locator("#entrance-enter").click()
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        expect(page.locator("#order-contact")).to_have_attribute("href", "https://www.instagram.com/homemadevegcakes/")
        results["css_only_fallback"] = "The native full-page link enters even when all modules fail."
        context.close()

        context, page = new_page(allowed)
        page.route(re.compile(r"\.mjs(?:\?|$)"), lambda route: route.abort())
        page.goto(url, wait_until="domcontentloaded")
        clicked = page.locator("#entrance-skip").is_visible()
        if clicked:
            page.locator("#entrance-skip").click(timeout=1500)
            assert page.url.endswith("#home")
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        results["native_skip_without_modules"] = {"clicked": clicked, "hidden": True}
        context.close()

        context = allowed.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844}, reduced_motion="no-preference")
        page = context.new_page()
        page.goto(url)
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        expect(page.locator("#order-contact")).to_be_visible()
        results["no_javascript"] = "Entrance absent; direct contact remains."
        context.close()
        allowed.close()

        blocked = playwright.chromium.launch(
            channel="msedge", headless=True,
            args=["--mute-audio"],
        )
        # Native autoplay policy may be permissive even under automation flags.
        context, page = new_page(blocked, audio_script=BLOCKED_AUDIO)
        page.goto(url)
        page.locator("#entrance-enter").click(position={"x": 100, "y": 100})
        state = completed(page)
        assert state["state"] == "finished" and state["audio"] in {"blocked", "skipped"}, state
        assert state["oscillators"] == 0 and state["resumeCalls"] == 0, state
        if state["audio"] == "blocked":
            assert state["contexts"] == [{"initial": "suspended", "final": "closed"}], state
        before = len(state["contexts"])
        page.locator('#site-nav a[href="#cakes"]').click()
        page.wait_for_timeout(450)
        after = completed(page)
        assert len(after["contexts"]) == before and after["oscillators"] == 0 and after["resumeCalls"] == 0, after
        results["suspended_context_fixture_no_later_replay"] = after
        context.close()
        blocked.close()

    report = {
        "url": url, "status": "passed", "results": results,
        "limitations": [
            "Test browsers are muted; a generated PCM waveform is not a claim of having heard device playback.",
            "The blocked-start browser case uses an injected suspended-context fixture; native Edge allowed audio even under a restrictive test flag.",
            "Audio is attempted only from the visitor's entry click; blocked playback stays silent.",
            "Visual frame PNGs freeze the real CSS timeline after separate click-completion checks.",
        ],
    }
    (OUTPUT / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Entrance review passed: parallax, click entry, optional bell and safe fallbacks. Evidence: {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output
    review(args.url)
