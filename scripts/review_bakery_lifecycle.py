"""Check installed bakery lifecycle and failed-bake escape paths; no image viewing."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PROBE = """(()=>{
  window.__bakeryGpu={draws:0,shadowDraws:0,uploads:0,deletedTextures:0};
  const prototype=WebGL2RenderingContext.prototype;
  for(const [name,key] of [['drawArrays','draws'],['bufferData','uploads'],['deleteTexture','deletedTextures']]){
    const original=prototype[name];
    prototype[name]=function(...args){
      if(this.canvas.classList.contains('bakery-interior')){
        window.__bakeryGpu[key]++;
        if(name==='drawArrays'&&this.getParameter(this.FRAMEBUFFER_BINDING))window.__bakeryGpu.shadowDraws++;
      }
      return original.apply(this,args);
    };
  }
})()"""


def assert_fallback(page):
    page.wait_for_function("""()=>{
      const image=document.querySelector('.entrance-room-poster img');
      return image?.complete&&image.naturalWidth>0;
    }""")
    result = page.locator(".entrance-room").evaluate("""room=>{
      const image=room.querySelector('.entrance-room-poster img'),canvas=room.querySelector('canvas'),
        box=image.getBoundingClientRect(),style=getComputedStyle(image),poster=getComputedStyle(image.closest('.entrance-room-poster'));
      return {ready:room.classList.contains('is-3d-ready'),canvasHidden:!canvas||canvas.hidden,
        naturalWidth:image.naturalWidth,width:box.width,height:box.height,display:style.display,
        visibility:style.visibility,opacity:style.opacity,posterDisplay:poster.display,posterOpacity:poster.opacity};
    }""")
    assert not result["ready"] and result["canvasHidden"], result
    assert result["naturalWidth"] > 0 and result["width"] > 0 and result["height"] > 0, result
    assert result["display"] != "none" and result["visibility"] != "hidden", result
    assert result["posterDisplay"] != "none" and float(result["posterOpacity"]) > 0, result
    return result


def assert_escape(page):
    page.locator("#entrance-skip").click()
    expect(page.locator("#bakery-entrance")).to_be_hidden(timeout=4000)
    assert page.locator("main").is_visible()


def review(url, output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    payload = (ROOT / "web" / "assets" / "bakery-light-bake.bin").read_bytes()
    stale_geometry = bytearray(payload)
    stale_geometry[8] ^= 1
    stale_sun = bytearray(payload)
    stale_sun[12:16] = b"\x00\x00\x00\x00"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        for label, body in [
            ("missing-bake", None), ("corrupt-bake", payload[:31]),
            ("stale-geometry-bake", bytes(stale_geometry)), ("stale-sun-bake", bytes(stale_sun)),
        ]:
            context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="no-preference")
            context.add_init_script(PROBE)
            page = context.new_page()
            errors, intercepted = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def replace(route):
                intercepted.append(route.request.url)
                if body is None:
                    route.abort()
                else:
                    route.fulfill(status=200, content_type="application/octet-stream", body=body)

            page.route("**/assets/bakery-light-bake.bin*", replace)
            page.goto(url)
            expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
            page.wait_for_function("document.querySelector('.entrance-room-poster img')?.complete")
            # Observe the settled rejection, not merely the pre-initialization poster.
            page.wait_for_timeout(1200)
            assert intercepted and not errors, (label, intercepted, errors)
            fallback = assert_fallback(page)
            gpu = page.evaluate("window.__bakeryGpu")
            assert gpu["draws"] == 0 and gpu["uploads"] == 0, (label, gpu)
            assert_escape(page)
            records.append({"case": label, "intercepted": len(intercepted), "fallback": fallback,
                            "gpu": gpu, "skip_escape": True, "page_errors": errors})
            context.close()

        context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="no-preference")
        context.add_init_script(PROBE)
        page = context.new_page()
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        page.goto(url)
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=15000)
        page.mouse.move(1040, 520, steps=5)
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=5000)
        first = page.evaluate("({...window.__bakeryGpu})")
        page.wait_for_timeout(500)
        idle = page.evaluate("({...window.__bakeryGpu})")
        assert idle == first and first["shadowDraws"] == 1, (first, idle)
        page.set_viewport_size({"width": 900, "height": 720})
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=5000)
        resize = page.evaluate("({...window.__bakeryGpu})")
        assert resize["shadowDraws"] == 1 and resize["uploads"] == first["uploads"], resize
        page.evaluate("""()=>{
          const canvas=document.querySelector('.bakery-interior'),gl=canvas.getContext('webgl2');
          window.__bakeryLose=gl.getExtension('WEBGL_lose_context');
          if(!window.__bakeryLose)throw new Error('Context-loss extension unavailable for lifecycle check.');
          window.__bakeryLose.loseContext();
        }""")
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "context-lost")
        lost = assert_fallback(page)
        page.wait_for_timeout(250)
        page.evaluate("window.__bakeryLose.restoreContext()")
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state", "ready", timeout=15000)
        restored = page.evaluate("({...window.__bakeryGpu})")
        assert restored["shadowDraws"] == 2, restored
        page.wait_for_timeout(500)
        assert page.evaluate("window.__bakeryGpu.draws") == restored["draws"]
        assert not any("generate_bakery" in request or "/scripts/" in request for request in requests), requests
        assert not errors, errors
        assert_escape(page)
        expect(page.locator(".bakery-interior")).to_have_count(0)
        released = page.evaluate("({...window.__bakeryGpu})")
        assert released["deletedTextures"] >= 2, released
        records.append({"case": "installed-idle-resize-context-release", "first": first, "idle": idle,
                        "resize": resize, "context_lost_fallback": lost, "restored": restored,
                        "released": released, "runtime_generator_requests": 0, "page_errors": errors})
        context.close()
        browser.close()
    receipt = {"url": url, "image_tool_views": 0,
               "visual_acceptance": "Not established; lifecycle assertions are not visual approval.",
               "cases": records}
    (output / "review.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, default=ROOT / ".local" / "painterly-windowlight-20261008" / "lifecycle")
    args = parser.parse_args()
    review(args.url, args.output)
