"""Exercise automatic and permission-gated entrance tilt with synthetic sensor events."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
MOCK = """mode=>{
  window.__motionPermissionCalls=0;window.__motionGestures=[];window.__motionListeners=0;
  window.__mockScreenAngle=0;window.__audioAttempts=0;
  Object.defineProperty(screen.orientation,'angle',{configurable:true,get:()=>window.__mockScreenAngle});
  const add=window.addEventListener.bind(window);
  window.addEventListener=(type,listener,options)=>{
    if(type==='deviceorientation'){
      window.__motionListeners++;
      options.signal.addEventListener('abort',()=>window.__motionListeners--,{once:true});
    }
    const result=add(type,listener,options);
    if(type==='deviceorientation'&&['legacy','auto-poster'].includes(mode)){
      queueMicrotask(()=>window.__emitMotion(45,0));
    }
    return result;
  };
  window.AudioContext=class{
    constructor(){window.__audioAttempts++;this.state='suspended'}
    close(){this.state='closed';return Promise.resolve()}
    resume(){throw Error('Motion must not unlock audio')}
  };
  class Orientation extends Event {}
  if(!['legacy','auto-poster','auto-no-samples','auto-invalid-samples'].includes(mode)){
    Orientation.requestPermission=()=>{
      window.__motionPermissionCalls++;window.__motionGestures.push(navigator.userActivation.isActive);
      if(mode==='deferred')return new Promise(r=>window.__resolveMotion=r);
      if(mode==='reject')return Promise.reject(new Error('Fixture permission unavailable'));
      return Promise.resolve(mode==='denied'?'denied':'granted');
    };
  }
  Object.defineProperty(window,'DeviceOrientationEvent',{configurable:true,value:mode==='unsupported'?undefined:Orientation});
  window.__emitMotion=(beta,gamma)=>window.dispatchEvent(Object.assign(new Event('deviceorientation'),{beta,gamma,alpha:null}));
}"""


def emit(page, beta, gamma, count=1):
    for _ in range(count):
        page.evaluate("([b,g])=>window.__emitMotion(b,g)", [beta, gamma])
        page.wait_for_timeout(40)


def look(page):
    return page.locator("#bakery-entrance").evaluate("""n=>({
      x:Number(n.style.getPropertyValue('--look-x'))||0,
      y:Number(n.style.getPropertyValue('--look-y'))||0,
      listeners:window.__motionListeners,permissions:window.__motionPermissionCalls,
      audio:window.__audioAttempts,state:n.dataset.state})""")


def review(url, output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])

        def open_case(mode="granted", width=390, height=844, text="100%", fragment="", reduced="no-preference"):
            context = browser.new_context(viewport={"width": width, "height": height}, has_touch=True,
                                          is_mobile=True, reduced_motion=reduced)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script(f"({MOCK})({json.dumps(mode)})")
            if mode in ("poster-fallback", "auto-poster"):
                page.add_init_script("""const get=HTMLCanvasElement.prototype.getContext;
                  HTMLCanvasElement.prototype.getContext=function(type,...args){
                    return type==='webgl2'?null:get.call(this,type,...args);
                  };""")
            page.goto(url + fragment, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.evaluate("size=>document.documentElement.style.fontSize=size", text)
            page.wait_for_timeout(100)
            return context, page, errors

        for mode in ("granted", "legacy"):
            context, page, errors = open_case(mode)
            button = page.locator("#entrance-motion")
            expect(button).to_be_visible()
            assert look(page)["permissions"] == 0
            if mode == "legacy":
                assert look(page)["listeners"] == 1
                expect(button).to_have_attribute("aria-pressed", "true")
            else:
                assert look(page)["listeners"] == 0
                emit(page, 60, 20)
                assert look(page)["x"] == 0 and look(page)["y"] == 0
            frame = page.locator(".entrance-shop").bounding_box()
            if mode != "legacy":
                button.click()
            page.wait_for_function("window.__motionListeners===1")
            assert look(page)["audio"] == 0 and look(page)["state"] == "waiting"
            emit(page, 45, 0)
            expect(button).to_have_attribute("aria-pressed", "true")
            assert look(page)["x"] == 0 and look(page)["y"] == 0
            emit(page, 60, 15, 20)
            state = look(page)
            assert .9 < state["x"] <= 1 and .9 < state["y"] <= 1, state
            expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=10000)
            assert page.locator(".entrance-room").evaluate("n=>Number(n.dataset.lookX)>.9&&Number(n.dataset.lookY)>.9")
            after = page.locator(".entrance-shop").bounding_box()
            assert all(abs(frame[key] - after[key]) < .1 for key in frame)
            page.evaluate("window.__mockScreenAngle=90")
            emit(page, 60, 15)
            assert look(page)["x"] == 0 and look(page)["y"] == 0, "Screen rotation must recalibrate."
            emit(page, 75, 15, 16)
            assert look(page)["x"] > .9 and abs(look(page)["y"]) < .001
            button.click()
            expect(button).to_have_attribute("aria-pressed", "false")
            assert look(page)["listeners"] == 0
            emit(page, -60, -60)
            assert look(page)["x"] == 0 and look(page)["y"] == 0
            page.set_viewport_size({"width": 394, "height": 844})
            page.wait_for_timeout(150)
            assert look(page)["listeners"] == 0, "Explicitly disabling tilt must survive layout changes."
            assert page.evaluate("window.__motionGestures.every(Boolean)")
            assert not errors, errors
            records.append({"mode": mode, "automatic_without_permission": mode == "legacy",
                            "gesture_required_for_permission": mode != "legacy", "screen_rotation": True,
                            "bounded_look": state, "fixed_building": True, "toggle_cleanup": True})
            context.close()

        context, page, errors = open_case("auto-poster")
        page.wait_for_function("window.__motionListeners===1")
        emit(page, 45, 0)
        emit(page, 55, 12, 20)
        page.wait_for_timeout(200)
        poster = page.locator(".entrance-room-poster")
        expect(poster).to_be_visible()
        assert poster.evaluate("n=>{const m=new DOMMatrix(getComputedStyle(n).transform);return Math.abs(m.m41)>1&&Math.abs(m.m42)>1}")
        page.locator("#entrance-motion").click()
        assert poster.evaluate("n=>getComputedStyle(n).transform==='none'")
        assert look(page)["listeners"] == 0 and not errors
        records.append({"mode": "auto-poster", "automatic_tilt_works_without_webgl": True})
        context.close()

        for mode in ("denied", "reject", "unsupported", "no-samples", "invalid-samples",
                     "auto-no-samples", "auto-invalid-samples"):
            context, page, errors = open_case(mode)
            button = page.locator("#entrance-motion")
            if mode == "unsupported":
                expect(button).to_be_hidden()
            else:
                if not mode.startswith("auto-"):
                    button.click()
                if mode in ("invalid-samples", "auto-invalid-samples"):
                    emit(page, None, None, 4)
                expect(button).to_have_text("Tilt not allowed" if mode == "denied" else "Tilt unavailable", timeout=4000)
                expect(button).to_have_attribute("aria-pressed", "false")
            state = look(page)
            assert state["listeners"] == 0 and state["audio"] == 0, state
            if mode.startswith("auto-"):
                assert state["permissions"] == 0
                page.set_viewport_size({"width": 394, "height": 844})
                page.wait_for_timeout(150)
                assert look(page)["listeners"] == 0, "No automatic retry loop after missing sensor data."
            page.locator("#entrance-skip").click()
            expect(page.locator("#bakery-entrance")).to_be_hidden()
            assert not errors, errors
            records.append({"mode": mode, "safe_fallback": True, "skip_works": True})
            context.close()

        for action in ("skip", "enter", "background", "reduced-motion", "forced-colors",
                       "print", "short-screen", "direct-link", "pagehide"):
            context, page, errors = open_case()
            page.locator("#entrance-motion").click()
            page.wait_for_function("window.__motionListeners===1")
            emit(page, 45, 0)
            emit(page, 50, 10, 4)
            if action == "skip":
                page.locator("#entrance-skip").click()
            elif action == "enter":
                page.locator("#entrance-enter").click(position={"x": 100, "y": 300})
            elif action == "background":
                page.evaluate("""()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});
                  document.dispatchEvent(new Event('visibilitychange'))}""")
            elif action == "reduced-motion":
                page.emulate_media(reduced_motion="reduce")
            elif action == "forced-colors":
                page.emulate_media(forced_colors="active")
            elif action == "print":
                page.emulate_media(media="print")
            elif action == "short-screen":
                page.set_viewport_size({"width": 844, "height": 390})
            elif action == "direct-link":
                page.evaluate("location.hash='home'")
            else:
                page.evaluate("window.dispatchEvent(new Event('pagehide'))")
            page.wait_for_function("window.__motionListeners===0")
            frozen = look(page)
            emit(page, -70, -80, 3)
            assert look(page)["x"] == frozen["x"] and look(page)["y"] == frozen["y"]
            expect(page.locator("#bakery-entrance")).to_be_hidden(timeout=4000)
            assert not errors, errors
            records.append({"stop": action, "listener_removed": True, "no_late_updates": True})
            context.close()

        context, page, errors = open_case("deferred")
        page.locator("#entrance-motion").click()
        page.wait_for_function("window.__motionPermissionCalls===1")
        page.locator("#entrance-skip").click()
        page.evaluate("window.__resolveMotion('granted')")
        page.wait_for_timeout(100)
        assert look(page)["listeners"] == 0 and not errors
        records.append({"mode": "late-permission-after-skip", "no_late_listener": True})
        context.close()

        for width, height, text in [(320, 568, "100%"), (390, 844, "100%"),
                                    (390, 844, "200%"), (320, 568, "200%")]:
            context, page, errors = open_case(width=width, height=height, text=text)
            entrance = page.locator("#bakery-entrance")
            if (width, height, text) == (320, 568, "200%"):
                expect(entrance).to_be_hidden()
                expect(entrance).to_have_attribute("data-state", "controls-fit")
                expect(page.locator("#site-nav")).to_be_visible()
                records.append({"viewport": [width, height], "text": text, "complete_site_fallback": True})
            else:
                expect(entrance).to_be_visible()
                metrics = page.locator(".entrance-tools").evaluate("""tools=>{
                  const r=tools.getBoundingClientRect(),shop=document.querySelector('.entrance-shop').getBoundingClientRect();
                  return {bottom:r.bottom,shopTop:shop.top,controls:[...tools.children].filter(n=>!n.hidden).map(n=>{
                    const b=n.getBoundingClientRect();return {left:b.left,right:b.right,height:b.height,
                      font:parseFloat(getComputedStyle(n).fontSize),fits:n.scrollWidth<=n.clientWidth+1};
                  }),width:innerWidth,scrollWidth:document.documentElement.scrollWidth};
                }""")
                assert metrics["bottom"] + 8 <= metrics["shopTop"] and metrics["scrollWidth"] <= width, metrics
                assert all(c["left"] >= 0 and c["right"] <= width and c["height"] >= 48 and c["fits"]
                           and c["font"] >= (32 if text == "200%" else 16) for c in metrics["controls"]), metrics
                page.screenshot(path=str(output / f"tilt-tools-{width}-{text.rstrip('%')}.png"))
                records.append({"viewport": [width, height], "text": text, "controls": metrics})
            assert not errors, errors
            context.close()
        for mode in ("legacy", "granted"):
            for fragment, reduced in [("#home", "no-preference"), ("", "reduce")]:
                context, page, errors = open_case(mode=mode, fragment=fragment, reduced=reduced)
                expect(page.locator("#bakery-entrance")).to_be_hidden()
                assert look(page)["permissions"] == 0 and look(page)["listeners"] == 0 and not errors
                records.append({"mode": mode, "fragment": fragment, "reduced_motion": reduced, "no_sensor_request": True})
                context.close()
        browser.close()
    result = {"status": "passed", "url": url, "cases": records, "image_tool_views": 0,
              "validation_type": "Synthetic orientation/permission events in mobile-emulated Edge.",
              "real_device_validation": "Not performed; actual browser/sensor support and permission policy vary.",
              "sensor_storage_or_upload": "None in the implementation."}
    (output / "review.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "cases": len(records), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review(args.url, args.output)
