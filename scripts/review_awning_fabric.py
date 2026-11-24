"""Measure optional cloth motion, pinned rails, settling and static fallback safety."""

import argparse
from io import BytesIO
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageChops, ImageFilter
from playwright.sync_api import expect, sync_playwright


def pixels(payload):
    return Image.open(BytesIO(payload)).convert("RGB")


def changed(first, second, box=None, threshold=8):
    if box:
        first, second = first.crop(box), second.crop(box)
    difference = ImageChops.difference(first, second).convert("L")
    return sum(difference.histogram()[threshold:]) / (difference.width * difference.height)


def raster_color_errors(native, raster, radius, threshold=8):
    # Two linear-filter stages can reconstruct an edge within one CSS pixel,
    # but cannot legitimately create colors outside that local native range.
    low = native.filter(ImageFilter.MinFilter(radius * 2 + 1))
    high = native.filter(ImageFilter.MaxFilter(radius * 2 + 1))
    outside = ImageChops.lighter(ImageChops.subtract(raster, high), ImageChops.subtract(low, raster))
    red, green, blue = outside.split()
    difference = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return sum(difference.histogram()[threshold:])


def flat_gpu_frame(page, awning):
    # Replay the actual held mesh with constant zero offsets/unit shade. This
    # changes no model state, viewport, texture, density, CSS or native fallback.
    page.locator("canvas.awning-fabric").evaluate("""canvas => {
      const gl=canvas.getContext('webgl'), program=gl.getParameter(gl.CURRENT_PROGRAM);
      const attributes=['a_offset','a_shade'].map(name=>{
        const location=gl.getAttribLocation(program,name);
        if(location<0) throw new Error(`Missing cloth attribute: ${name}`);
        return {location,enabled:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_ENABLED),
          value:gl.getVertexAttrib(location,gl.CURRENT_VERTEX_ATTRIB)};
      });
      const count=gl.getBufferParameter(gl.ELEMENT_ARRAY_BUFFER,gl.BUFFER_SIZE)/Uint16Array.BYTES_PER_ELEMENT;
      if(!Number.isInteger(count)||count<=0) throw new Error('Missing cloth mesh indices.');
      const draw=()=>{
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawElements(gl.TRIANGLES,count,gl.UNSIGNED_SHORT,0);
        gl.finish();
        if(gl.getError()!==gl.NO_ERROR) throw new Error('Cloth control-frame draw failed.');
      };
      window.__restoreAwningReviewFrame=()=>{
        for(const {location,enabled,value} of attributes){
          gl.vertexAttrib4fv(location,value);
          if(enabled) gl.enableVertexAttribArray(location);
          else gl.disableVertexAttribArray(location);
        }
        draw();
        delete window.__restoreAwningReviewFrame;
      };
      for(const {location} of attributes) gl.disableVertexAttribArray(location);
      gl.vertexAttrib2f(attributes[0].location,0,0);
      gl.vertexAttrib1f(attributes[1].location,1);
      draw();
    }""")
    try:
        return pixels(awning.screenshot())
    finally:
        page.evaluate("window.__restoreAwningReviewFrame()")


def settled(page, state="rest"):
    expect(page.locator(".site-awning")).to_have_attribute("data-fabric-state", state, timeout=26000)
    page.wait_for_timeout(100)


def prepare(browser, url, **options):
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, **options)
    page = context.new_page()
    page.add_init_script("""window.__frameCalls=0;
      const originalFrame=requestAnimationFrame;
      window.requestAnimationFrame=callback=>originalFrame(time=>{window.__frameCalls++;callback(time)});
    """)
    page.goto(url + "#home", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.evaluate("scrollTo({top:0,behavior:'instant'})")
    page.locator(".site-awning img").evaluate("node=>node.decode()")
    return context, page


def review(url, output):
    output.mkdir(parents=True, exist_ok=True)
    result = {"url": url, "image_tool_views": 0}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        context, page = prepare(browser, url, device_scale_factor=2)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        settled(page)
        expect(page.locator("canvas.awning-fabric")).to_have_count(1)
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        before_frames = page.evaluate("window.__frameCalls")
        page.wait_for_timeout(400)
        assert page.evaluate("window.__frameCalls") == before_frames, "Idle cloth must not run frames."
        awning = page.locator(".site-awning")
        bounds = awning.bounding_box()
        baseline = pixels(awning.screenshot())
        page.mouse.move(bounds["width"] * .5, bounds["y"] + bounds["height"] * .86)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.wait_for_timeout(220)
        moving = pixels(awning.screenshot())
        settled(page, "held")
        held = pixels(awning.screenshot())
        gpu_baseline = flat_gpu_frame(page, awning)
        assert pixels(awning.screenshot()).tobytes() == held.tobytes(), "Control-frame capture must restore the actual held mesh."
        raster_errors = raster_color_errors(baseline, gpu_baseline, math.ceil(baseline.width / bounds["width"]))
        assert raster_errors == 0, f"GPU raster invented colors beyond its native sampling footprint: {raster_errors}"
        # Native SVG and a budget-limited GPU texture have different sampling
        # grids. Measure motion against zero deformation on that SAME GPU grid.
        changed_fraction = changed(gpu_baseline, moving)
        # Locator screenshots can include the preceding header's fractional border row.
        rail_inset=max(1,round(2*baseline.width/bounds["width"]))
        rail = (0, rail_inset, baseline.width, max(rail_inset+1, int(baseline.height * 14 / 300)))
        front = (0, int(baseline.height * 185 / 300), baseline.width, int(baseline.height * 189 / 300))
        far = (0, int(baseline.height * .1), int(baseline.width * .2), baseline.height)
        rail_change, far_change = changed(baseline, moving, rail), changed(gpu_baseline, moving, far)
        front_change = changed(baseline, moving, front)
        assert changed_fraction > .001, f"Pointer should visibly deform cloth: {changed_fraction}"
        assert rail_change < .01, f"The top rail moved: {rail_change}"
        assert front_change < .01, f"The front bar moved: {front_change}"
        assert far_change < changed_fraction * .5, (far_change, changed_fraction)
        result["pointer"] = {"changed_fraction": changed_fraction, "fixed_rail_fraction": rail_change, "fixed_front_bar_fraction": front_change, "far_fraction": far_change}
        result["raster_control"] = {
            "native_to_gpu_zero_fraction": changed(baseline, gpu_baseline),
            "native_to_gpu_zero_far_fraction": changed(baseline, gpu_baseline, far),
            "native_to_motion_fraction": changed(baseline, moving),
            "native_to_motion_far_fraction": changed(baseline, moving, far),
            "colors_outside_native_sampling_footprint": raster_errors,
            "held_frame_exactly_restored": True,
        }
        expect(page.locator(".awning-fixed-rail")).to_have_count(2)
        assert page.locator(".awning-fixed-rail").evaluate_all(
            "nodes=>nodes.every(n=>n.getAttribute('aria-hidden')==='true' && getComputedStyle(n).pointerEvents==='none')"
        )
        settled(page, "held")
        before_frames = page.evaluate("window.__frameCalls")
        page.wait_for_timeout(400)
        assert page.evaluate("window.__frameCalls") == before_frames, "A held settled dent must not spin forever."
        page.mouse.move(20, 20)
        settled(page)
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        assert pixels(awning.screenshot()).tobytes() == baseline.tobytes(), "Release must restore exact original artwork."
        page.mouse.move(bounds["width"] * .55, bounds["y"] + bounds["height"] + 32)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.wait_for_timeout(220)
        near_change = changed(gpu_baseline, pixels(awning.screenshot()))
        assert near_change > .0005, f"A nearby cursor must affect the hem: {near_change}"
        result["near_cursor_fraction"] = near_change
        page.mouse.move(20, 20)
        settled(page)
        scroll_frames = []
        scroll_samples = []
        for delta in (60, -60):
            page.evaluate("delta=>scrollBy({top:delta,behavior:'instant'})", delta)
            expect(page.locator("canvas.awning-fabric")).to_be_visible()
            samples = []
            for delay in (80, 100, 120):
                page.wait_for_timeout(delay)
                shot = pixels(awning.screenshot())
                samples.append((changed(gpu_baseline, shot), shot))
            strongest = max(samples, key=lambda sample: sample[0])
            assert strongest[0] > .0005, f"Scroll should produce measurable fabric motion: {[value for value, _ in samples]}"
            scroll_frames.append(strongest[1])
            scroll_samples.append({"delta": delta, "changed_fractions": [value for value, _ in samples]})
            settled(page)
        assert changed(*scroll_frames) > .0005, "Up and down scrolling should not produce the same frame."
        result["scroll_bidirectional"] = True
        result["scroll_response_samples"] = scroll_samples
        result["canvas"] = page.locator("canvas.awning-fabric").evaluate("""n=>({
          width:n.width,height:n.height,hidden:n.hidden,
          ariaHidden:n.getAttribute('aria-hidden'),events:getComputedStyle(n).pointerEvents,
          viewportFits:document.documentElement.scrollWidth<=innerWidth
        })""")
        assert result["canvas"]["width"] * result["canvas"]["height"] <= 2_020_000
        assert result["canvas"]["ariaHidden"] == "true" and result["canvas"]["events"] == "none"
        assert result["canvas"]["viewportFits"]
        page.screenshot(path=str(output / "settled-page.png"))
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        expect(page.locator("#notebook-dialog")).to_be_visible()
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        page.locator("#notebook-close").click()
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        settled(page)
        page.mouse.move(bounds["width"] * .5, bounds["y"] + bounds["height"] * .65)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.emulate_media(reduced_motion="reduce")
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        assert page.locator(".site-awning img").evaluate("n=>getComputedStyle(n).opacity") == "1"
        page.emulate_media(reduced_motion="no-preference")
        page.mouse.move(bounds["width"] * .6, bounds["y"] + bounds["height"] * .7)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.emulate_media(forced_colors="active")
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        page.emulate_media(forced_colors="none", media="print")
        expect(awning).to_be_hidden()
        page.emulate_media(media="screen")
        page.mouse.move(bounds["width"] * .5, bounds["y"] + bounds["height"] * .8)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        settled(page)
        result["preferences_and_overlay_stop"] = True
        extension = page.locator("canvas.awning-fabric").evaluate("""n=>{
          const gl=n.getContext('webgl'),extension=gl.getExtension('WEBGL_lose_context');
          if(!extension) return false;
          window.__awningLoss=extension;extension.loseContext();return true;
        }""")
        assert extension, "This review requires controllable WebGL context loss."
        settled(page, "context-lost")
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        page.wait_for_timeout(150)
        page.evaluate("window.__awningLoss.restoreContext()")
        settled(page)
        bounds = awning.bounding_box()
        page.mouse.move(bounds["width"] * .4, bounds["y"] + bounds["height"] * .8)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.evaluate("scrollTo({top:document.body.scrollHeight,behavior:'instant'})")
        settled(page)
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        result["context_recovery_and_offscreen_stop"] = True
        resize_cases = []
        for width in (320, 768, 2560):
            page.set_viewport_size({"width": width, "height": 1000})
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            settled(page)
            box = awning.bounding_box()
            page.mouse.move(width * .5, box["y"] + box["height"] * .85)
            expect(page.locator("canvas.awning-fabric")).to_be_visible()
            metrics = page.locator("canvas.awning-fabric").evaluate("""n=>{
              const b=n.parentElement.getBoundingClientRect(),gl=n.getContext('webgl'),
                limit=gl.getParameter(gl.MAX_TEXTURE_SIZE),
                scale=Math.min(devicePixelRatio||1,2,limit/b.width,limit/(b.height+40),
                  Math.sqrt(2000000/(b.width*(b.height+40))));
              return {width:n.width,height:n.height,rootFits:document.documentElement.scrollWidth<=innerWidth,
                cssWidth:n.getBoundingClientRect().width,
                expectedWidth:Math.ceil(b.width*scale),expectedHeight:Math.ceil((b.height+40)*scale)};
            }""")
            assert metrics["rootFits"] and abs(metrics["cssWidth"] - width) < 1, metrics
            assert metrics["width"] == metrics["expectedWidth"] and metrics["height"] == metrics["expectedHeight"], metrics
            assert metrics["width"] * metrics["height"] <= 2_020_000, metrics
            resize_cases.append({"viewport": width, **metrics})
            page.mouse.move(0, 0)
            settled(page)
        result["resize_cases"] = resize_cases
        page.evaluate("""()=>{
          Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        box = awning.bounding_box()
        page.mouse.move(box["width"] * .5, box["y"] + box["height"] * .8)
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        result["injected_visibility_guard"] = True
        assert not errors, errors
        context.close()

        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = context.new_page()
        page.goto(url + "#home", wait_until="networkidle")
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        settled(page)
        box = page.locator(".site-awning").bounding_box()
        page.locator(".site-awning").dispatch_event("pointermove", {"pointerType": "touch", "clientX": 195, "clientY": box["y"] + 40})
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        page.evaluate("scrollBy({top:60,behavior:'instant'})")
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        settled(page)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        result["touch_pointer_ignored_scroll_supported"] = True
        context.close()

        for mode in ("no-webgl", "missing-module", "missing-stylesheet", "reduced-motion", "no-javascript"):
            options = {"java_script_enabled": mode != "no-javascript", "viewport": {"width": 390, "height": 844}}
            if mode == "reduced-motion":
                options["reduced_motion"] = "reduce"
            context = browser.new_context(**options)
            page = context.new_page()
            if mode == "no-webgl":
                page.add_init_script("""const getContext=HTMLCanvasElement.prototype.getContext;
                  HTMLCanvasElement.prototype.getContext=function(type,...args){
                    return type.startsWith('webgl')?null:getContext.call(this,type,...args)
                  };""")
            if mode == "missing-module":
                page.route(re.compile(r"/awning(?:-cloth)?\.mjs(?:\?|$)"), lambda route: route.abort())
            if mode == "missing-stylesheet":
                page.route(re.compile(r"/entrance-shop\.css(?:\?|$)"), lambda route: route.abort())
            page.goto(url + "#home", wait_until="networkidle")
            image = page.locator(".site-awning img")
            expect(image).to_be_visible()
            assert image.evaluate("n=>n.complete && n.naturalWidth>0 && getComputedStyle(n).opacity==='1'")
            expect(page.locator("canvas.awning-fabric:visible")).to_have_count(0)
            expect(page.locator("#site-nav")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            context.close()
        result["static_fallbacks"] = ["no-webgl", "missing-module", "missing-stylesheet", "reduced-motion", "no-javascript"]
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
        box = page.locator(".site-awning").bounding_box()
        page.mouse.move(720, box["y"] + box["height"] * .8)
        expect(page.locator("canvas.awning-fabric:visible")).to_have_count(0)
        page.locator("#entrance-skip").click()
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        result["entrance_blocks_underlying_motion"] = True
        context.close()
        browser.close()
    result["status"] = "passed"
    (output / "review.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review(args.url, args.output)
