"""Numerical production-cream checks. No image viewing or visual-approval claims."""

import argparse
import json
import math
from pathlib import Path
import time
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SELECTOR = "#cream-effects"


INSTRUMENT = r"""({seed, failure}) => {
  const originalRandom = crypto.getRandomValues.bind(crypto);
  crypto.getRandomValues = array => {
    if (array instanceof Uint32Array && array.length === 1) { array[0] = seed; return array; }
    return originalRandom(array);
  };
  window.__creamReview = {contexts: 0, draws: 0, uploads: 0, programs: 0, deletedPrograms: 0,
    buffers: 0, deletedBuffers: 0, shaders: 0, deletedShaders: 0, entranceOverlap: 0};
  const stats = window.__creamReview, wrapped = new WeakSet();
  const originalContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
    if (this.id === 'cream-material' && kind === 'webgl2' && failure === 'webgl') return null;
    const context = originalContext.call(this, kind, ...args);
    if (this.id !== 'cream-material' || kind !== 'webgl2' || !context || wrapped.has(context)) return context;
    wrapped.add(context); stats.contexts++;
    for (const [method, key] of Object.entries({drawArrays:'draws', uniform4fv:'uploads',
      createProgram:'programs', deleteProgram:'deletedPrograms', createBuffer:'buffers',
      deleteBuffer:'deletedBuffers', createShader:'shaders', deleteShader:'deletedShaders'})) {
      const original = context[method].bind(context);
      context[method] = (...values) => {
        stats[key]++;
        if (method === 'drawArrays') {
          const entry = document.getElementById('bakery-entrance');
          const room = entry?.querySelector('.bakery-interior');
          if (entry && !entry.hidden && getComputedStyle(entry).display !== 'none' &&
              getComputedStyle(entry).visibility !== 'hidden' && room && !room.hidden) stats.entranceOverlap++;
        }
        return original(...values);
      };
    }
    if (failure === 'shader') {
      const parameter = context.getShaderParameter.bind(context);
      context.getShaderParameter = (shader, key) => key === context.COMPILE_STATUS ? false : parameter(shader, key);
    }
    return context;
  };
}"""


SNAPSHOT = r"""gpu => {
  const root = document.getElementById('cream-effects'), canvas = document.getElementById('cream-material');
  const pointer = document.getElementById('cream-cursor'), control = document.getElementById('cream-motion-control');
  const button = document.getElementById('cream-motion-toggle');
  const shown = n => !!n && !n.hidden && getComputedStyle(n).display !== 'none' &&
    getComputedStyle(n).visibility !== 'hidden';
  const rect = n => { const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}; };
  const data = {...root?.dataset};
  const state = {data, layer:shown(root), pointer:shown(pointer), control:shown(control),
    native:!document.body.classList.contains('cream-cursor-active'),
    ready:document.body.classList.contains('has-cream-effects'), label:button?.textContent,
    pressed:button?.getAttribute('aria-pressed'), button:button ? rect(button) : null,
    canvas:canvas ? {width:canvas.width,height:canvas.height} : null,
    viewport:[innerWidth,innerHeight], hasFocus:document.hasFocus(),
    stats:{...window.__creamReview}, now:performance.now(),
    mainAvailable:!!document.querySelector('main') && !document.querySelector('main').hidden &&
      !document.querySelector('main').inert,
    overflow:document.documentElement.scrollWidth>innerWidth+1};
  if (state.pointer) {
    const context=pointer.getContext('2d'), bytes=context.getImageData(0,0,pointer.width,pointer.height).data;
    let pink=0,opaque=0,hash=2166136261;
    for(let i=0;i<bytes.length;i++) {
      hash=Math.imul(hash^bytes[i],16777619)>>>0;
      if(i%4===0&&bytes[i+3]>=128) {
        opaque++; if(bytes[i]>bytes[i+1]+12&&bytes[i+2]>bytes[i+1]+4)pink++;
      }
    }
    state.pointerPixels={pink,opaque,hash,bounds:rect(pointer),pixels:pointer.width*pointer.height,
      pointerEvents:getComputedStyle(pointer).pointerEvents};
  }
  if (gpu && Number(data.paintCount)>0 && data.state!=='context-lost' && data.state!=='failed') {
    const gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM);
    const bytes=new Uint8Array(canvas.width*canvas.height*4);
    gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
    let hash=2166136261,opaque=0;
    for(let i=0;i<bytes.length;i++) { hash=Math.imul(hash^bytes[i],16777619)>>>0;if(i%4===3&&bytes[i]>=128)opaque++; }
    const uniform=name=>{
      const location=gl.getUniformLocation(program,name);
      return location===null&&name==='strawberryStart'?-1:gl.getUniform(program,location);
    };
    const shapeLocation=gl.getUniformLocation(program,'cursorShape');
    const contactLocation=gl.getUniformLocation(program,'contactActive');
    const spawnLocation=gl.getUniformLocation(program,'spawnShapeCount');
    state.gpu={hash,opaque,error:gl.getError(),scissor:gl.isEnabled(gl.SCISSOR_TEST),
      shape:shapeLocation?Array.from(gl.getUniform(program,shapeLocation)):null,
      contact:contactLocation?{active:uniform('contactActive'),pass:uniform('contactPass'),
        count:uniform('ambientCount'),trail:uniform('contactTrailCount'),shape:Array.from(uniform('contactShape'))}:null,
      spawns:spawnLocation?{count:uniform('spawnShapeCount'),shapes:Array.from({length:8},(_,i)=>Array.from(uniform('spawnShapes['+i+']')))}:null,
      tint:uniform('cursorTint'),strawberryStart:uniform('strawberryStart'),trail:uniform('trailCount'),count:uniform('scoopCount'),
      positions:Array.from({length:Number(data.primitiveCount)},(_,i)=>Array.from(uniform('scoops['+i+']')))};
  }
  return state;
}"""


def snapshot(page, gpu=False):
    return page.evaluate(SNAPSHOT, gpu)


def direct_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, "home"))


def wait_state(page, state="moving"):
    expect(page.locator(SELECTOR)).to_have_attribute("data-state", state, timeout=15000)


def new_context(browser, seed=4, failure="", **options):
    context = browser.new_context(viewport={"width": 1440, "height": 1000},
                                  reduced_motion="no-preference", **options)
    context.add_init_script("(" + INSTRUMENT + ")(" + json.dumps({"seed": seed, "failure": failure}) + ")")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return context, page, errors


def navigate(page, url):
    page.goto(direct_url(url), wait_until="networkidle")
    wait_state(page)
    page.evaluate("document.fonts.ready")
    assert snapshot(page)["mainAvailable"], "The enhancement must not hide or inert the website."


def stopped(page, reason=None, visible=False, duration=220):
    if reason:
        wait_state(page, reason)
    before = snapshot(page)
    page.wait_for_timeout(duration)
    after = snapshot(page)
    assert before["stats"]["uploads"] == after["stats"]["uploads"], (before, after)
    assert before["stats"]["draws"] == after["stats"]["draws"], (before, after)
    assert float(before["data"].get("motionTime", 0)) == float(after["data"].get("motionTime", 0)), (before, after)
    assert after["native"] and not after["pointer"], after
    assert after["layer"] == visible and after["control"] == visible, after
    return after


def advancing(page, duration=300, native=False):
    wait_state(page)
    before = snapshot(page, True)
    page.wait_for_timeout(duration)
    after = snapshot(page, True)
    assert after["stats"]["uploads"] > before["stats"]["uploads"], (before, after)
    assert after["stats"]["draws"] > before["stats"]["draws"], (before, after)
    assert float(after["data"]["motionTime"]) > float(before["data"]["motionTime"]), (before, after)
    assert after["gpu"]["positions"] != before["gpu"]["positions"], (before, after)
    assert after["layer"] and after["control"] and after["ready"], after
    if native:
        assert after["native"] and not after["pointer"], after
    return after


def assert_running(state):
    assert state["data"]["state"] == "moving" and state["layer"] and state["control"] and state["ready"], state
    assert not state["data"]["error"] and state["mainAvailable"] and not state["overflow"], state
    assert int(state["data"]["capacity"]) == 48, state
    assert 3 <= int(state["data"]["groupCount"]) <= int(state["data"]["sourceGroupCount"]), state
    assert 2 <= int(state["data"]["dropletCount"]) <= int(state["data"]["sourceDropletCount"]), state
    assert int(state["data"]["automaticPrimitiveCount"]) == math.ceil(int(state["data"]["sourceAutomaticPrimitiveCount"])/2), state
    assert int(state["data"]["ambientPrimitiveCount"]) == int(state["data"]["automaticPrimitiveCount"]), state
    assert float(state["data"]["automaticPeakMax"]) == 0, state
    assert float(state["data"]["groupGeometryMultiplier"]) == 4/3 and state["data"]["groupMotionMode"] == "repel-attract", state
    assert float(state["data"]["largeGroupGeometryMultiplier"]) == 2/3, state
    assert 0 <= int(state["data"]["spawnCount"]) <= 8, state
    assert int(state["data"]["scoopCount"]) == int(state["data"]["groupCount"]) + int(state["data"]["dropletCount"]) + int(state["data"]["spawnCount"]), state
    assert int(state["data"]["geometryMultiplier"]) == 2 and float(state["data"]["trailLengthScale"]) == .99, state
    assert float(state["data"]["spawnGeometryMultiplier"]) == 1, state
    assert state["canvas"]["width"] * state["canvas"]["height"] <= 2_020_000, state
    assert .5 <= float(state["data"]["pixelRatio"]) <= 1.5, state
    assert int(state["data"]["motionMultiplier"]) == 2, state
    assert abs(float(state["data"]["sampleTime"]) - 2 * float(state["data"]["motionTime"])) <= .00011, state
    b = state["button"]
    assert b["width"] >= 48 and b["height"] >= 48 and b["x"] >= 0, state
    assert b["right"] <= state["viewport"][0] + .5, state


def check_motion_pointer_pause(browser, url):
    context, page, errors = new_context(browser)
    try:
        navigate(page, url)
        before = snapshot(page, True)
        assert_running(before)
        page.wait_for_timeout(1100)
        after = snapshot(page, True)
        assert page.locator("#cream-motion-control").evaluate("node=>!!node.closest('.site-footer')"), "Pause must live in the footer."
        expect(page.locator("#cream-motion-toggle")).to_have_attribute("aria-keyshortcuts", "Alt+Shift+P")
        assert before["button"]["y"] >= before["viewport"][1], "The initial offscreen footer must not prevent ambient progress."
        assert after["gpu"]["hash"] != before["gpu"]["hash"], "GPU material must actually move."
        assert after["gpu"]["positions"] != before["gpu"]["positions"]
        assert after["gpu"]["opaque"] > 1000 and after["gpu"]["error"] == 0
        fps = (int(after["data"]["paintCount"]) - int(before["data"]["paintCount"])) / ((after["now"]-before["now"])/1000)
        assert 0 < fps <= 31, fps
        page.mouse.move(300, 650)
        page.wait_for_timeout(120)
        page.mouse.move(690, 480, steps=7)
        page.wait_for_timeout(70)
        pink = snapshot(page, True)
        assert pink["pointer"] and not pink["native"], pink
        assert pink["pointerPixels"]["pink"] > 40 and pink["pointerPixels"]["opaque"] > 100, pink
        assert pink["pointerPixels"]["pointerEvents"] == "none", pink
        b = pink["pointerPixels"]["bounds"]
        assert b["x"] >= 0 and b["y"] >= 0 and b["right"] <= 1441 and b["bottom"] <= 1001, b
        assert pink["gpu"]["tint"] == 0 and pink["gpu"]["trail"] == 0 and not pink["gpu"]["scissor"], pink
        assert pink["gpu"]["shape"] == [0, 1, 0, 0], pink
        count = int(pink["data"]["scoopCount"])
        page.locator("h1").click()
        page.wait_for_function("Number(document.getElementById('cream-effects').dataset.spawnCount)===1")
        clicked = snapshot(page, True)
        assert int(clicked["data"]["scoopCount"]) == count + 1, "A trusted ordinary click must add one strawberry."
        assert clicked["pointer"] and not clicked["native"], "A primary click must retain the follower."
        assert clicked["gpu"]["strawberryStart"] == int(clicked["data"]["ambientPrimitiveCount"])
        page.locator("#cream-motion-toggle").scroll_into_view_if_needed()
        page.locator("#cream-motion-toggle").focus()
        reachable = page.locator("#cream-motion-toggle").bounding_box()
        assert reachable and reachable["y"] >= 0 and reachable["y"] + reachable["height"] <= page.viewport_size["height"] + 1
        page.keyboard.press("Space")
        paused = stopped(page, "paused", visible=True)
        assert paused["pressed"] == "true" and paused["label"] == "Resume cream motion", paused
        expect(page.locator("#cream-motion-toggle")).to_be_focused()
        held = snapshot(page, True)
        page.mouse.move(800, 600)
        page.wait_for_timeout(180)
        assert snapshot(page, True)["gpu"] == held["gpu"], "Pause must freeze the GPU pose."
        page.keyboard.press("Enter")
        wait_state(page)
        page.wait_for_timeout(150)
        assert float(snapshot(page)["data"]["motionTime"]) > float(paused["data"]["motionTime"])
        page.evaluate("document.documentElement.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}))")
        assert snapshot(page)["native"] and not snapshot(page)["pointer"]
        assert not errors, errors
        return {"measured_fps": fps, "gpu_motion": True, "pink_pixels": pink["pointerPixels"]["pink"],
                "pause_zero_uploads": True, "keyboard_focus_retained": True,
                "footer_pause_reachable": True, "offscreen_footer_does_not_block": True,
                "ambient_pointer_uniforms_restored": True, "ordinary_click_spawned_once": True,
                "ordinary_click_retained_follower": True}
    finally:
        context.close()


def check_lifecycle(browser, url):
    context, page, errors = new_context(browser)
    records = []
    try:
        navigate(page, url)
        for preference, enabled, disabled, reason in [
            ("reduced_motion", "reduce", "no-preference", "reduced-motion"),
            ("forced_colors", "active", "none", "forced-colors"),
            ("media", "print", "screen", "print")]:
            before = snapshot(page)
            page.emulate_media(**{preference: enabled})
            held = stopped(page, reason)
            page.emulate_media(**{preference: disabled})
            wait_state(page)
            page.wait_for_timeout(120)
            after = snapshot(page)
            assert after["data"]["sceneSeed"] == before["data"]["sceneSeed"]
            assert 0 <= float(after["data"]["motionTime"]) - float(held["data"]["motionTime"]) < .5
            records.append(reason)
        for leave, restore, reason in [
            ("window.dispatchEvent(new Event('pagehide'))", "window.dispatchEvent(new Event('pageshow'))", "page-hidden"),
            ("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))",
             "delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))", "hidden"),
            ("window.dispatchEvent(new Event('beforeprint'))", "window.dispatchEvent(new Event('afterprint'))", "print")]:
            page.evaluate(leave)
            held = stopped(page, reason)
            page.evaluate(restore)
            wait_state(page)
            page.wait_for_timeout(120)
            after = snapshot(page)
            assert 0 <= float(after["data"]["motionTime"]) - float(held["data"]["motionTime"]) < .5
            records.append(reason)
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        advancing(page, native=True)
        page.mouse.move(600, 550)
        wait_state(page)
        page.evaluate("""window.dispatchEvent(new Event('blur'));
          Object.defineProperty(document,'hasFocus',{configurable:true,value:()=>false})""")
        page.mouse.move(610, 560)
        advancing(page, native=True)
        page.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,value:true});
          document.dispatchEvent(new Event('visibilitychange'))""")
        stopped(page, "hidden")
        page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
        advancing(page, native=True)
        page.evaluate("delete document.hasFocus;window.dispatchEvent(new Event('pageshow'))")
        wait_state(page)
        page.locator("#cream-motion-toggle").click()
        stopped(page, "paused", visible=True)
        page.evaluate("window.dispatchEvent(new Event('blur'));window.dispatchEvent(new Event('pageshow'))")
        stopped(page, "paused", visible=True)
        page.emulate_media(reduced_motion="reduce")
        stopped(page, "reduced-motion")
        page.emulate_media(reduced_motion="no-preference")
        stopped(page, "paused", visible=True)
        assert not errors, errors
        return {"inactive_paths": records, "focused_pointer_recovers_stale_blur": True,
                "visible_blur_keeps_ambient": True, "unfocused_pointer_stays_native": True,
                "visible_return_without_focus_resumes_ambient": True, "explicit_pause_survives": True}
    finally:
        context.close()


def check_dialogs_entrance(browser, url):
    context, page, errors = new_context(browser)
    try:
        page.goto(url.split("#")[0], wait_until="networkidle")
        expect(page.locator("#bakery-entrance")).to_be_visible()
        held = stopped(page, "entrance")
        assert held["stats"]["contexts"] == 0, "Cream GPU allocation must wait for the entrance."
        page.locator("#entrance-skip").click()
        wait_state(page)
        page.evaluate("document.fonts.ready")
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        expect(page.locator("#notebook-dialog")).to_be_visible()
        held = advancing(page, native=True)
        assert held["data"]["viewerOpen"] == "true"
        opener = page.locator("#notebook-dialog .cake-card:visible a[data-photo]").first
        href = opener.get_attribute("href")
        opener.click()
        expect(page.locator("#photo-dialog")).to_be_visible()
        advancing(page, native=True)
        page.evaluate("window.__creamShortcutFocus=document.activeElement")
        page.keyboard.press("Alt+Shift+P")
        stopped(page, "paused", visible=True)
        assert page.evaluate("document.activeElement===window.__creamShortcutFocus"), "Shortcut must not move viewer focus."
        page.locator("#photo-close").click()
        expect(page.locator("#photo-dialog")).not_to_be_visible()
        stopped(page, "paused", visible=True)
        page.keyboard.press("Escape")
        expect(page.locator("#notebook-dialog")).not_to_be_visible()
        stopped(page, "paused", visible=True)
        assert snapshot(page)["data"]["sceneSeed"] == held["data"]["sceneSeed"]
        page.keyboard.press("Alt+Shift+P")
        wait_state(page)
        page.evaluate("""const n=document.createElement('dialog');n.id='cream-review-dialog';
          n.innerHTML='<input aria-label="Shortcut editable fixture"><button type="button">Shortcut target</button>';
          document.body.append(n);n.showModal();n.querySelector('input').focus()""")
        page.keyboard.press("Alt+Shift+P")
        advancing(page, native=True)
        page.locator("#cream-review-dialog button").focus()
        page.keyboard.press("Alt+Shift+P")
        stopped(page, "paused", visible=True)
        page.evaluate("document.getElementById('cream-review-dialog').close();document.getElementById('cream-review-dialog').remove()")
        stopped(page, "paused", visible=True)
        assert snapshot(page)["stats"]["entranceOverlap"] == 0
        assert href and ".jpg" in href, href
        assert not errors, errors
        return {"entrance_defers_context": True, "nested_photo_and_notebook_keep_ambient": True,
                "new_dialog_keeps_ambient": True, "viewer_pointer_native": True,
                "shortcut_preserves_focus": True, "shortcut_ignores_editable": True,
                "pause_survives_dialog": True, "photo_url_retained": href}
    finally:
        context.close()


def check_resize_counts(browser, url):
    records = []
    for seed, count, old_pieces, new_pieces in [(7, 5, 21, 11), (4, 9, 31, 16)]:
        context, page, errors = new_context(browser, seed=seed, device_scale_factor=2)
        try:
            navigate(page, url)
            for width, height in [(1440, 1000), (390, 844), (320, 568), (667, 375), (1920, 1080), (2560, 1440)]:
                before = snapshot(page)
                page.set_viewport_size({"width": width, "height": height})
                wait_state(page)
                page.wait_for_timeout(150)
                state = snapshot(page, True)
                assert_running(state)
                assert int(state["data"]["scoopCount"]) == count and int(state["data"]["sceneSeed"]) == seed, state
                assert int(state["data"]["sourceAutomaticPrimitiveCount"]) == old_pieces, state
                assert int(state["data"]["automaticPrimitiveCount"]) == state["gpu"]["count"] == new_pieces, state
                assert float(state["data"]["motionTime"]) >= float(before["data"]["motionTime"]), state
                # Kept edge geometry may cross the canvas; do not silently rescale or recenter it.
                for x, y, radius, peak in state["gpu"]["positions"]:
                    assert all(math.isfinite(v) for v in [x, y, radius, peak]) and radius > 0 and peak == 0
                assert int(state["data"]["primitiveCount"]) <= 43
                records.append({"seed": seed, "count": count, "viewport": [width, height],
                                "output": state["canvas"], "ratio": state["data"]["pixelRatio"],
                                "edge_crossing_primitives": sum(x-r < 0 or x+r > width or y-r < 0 or y+r > height
                                    for x,y,r,_ in state["gpu"]["positions"])})
            page.locator("#cream-motion-toggle").click()
            held = stopped(page, "paused", visible=True)
            page.set_viewport_size({"width": 1000, "height": 800})
            wait_state(page, "paused")
            resized = snapshot(page)
            assert resized["data"]["motionTime"] == held["data"]["motionTime"]
            assert resized["data"]["sceneSeed"] == held["data"]["sceneSeed"]
            assert not errors, errors
        finally:
            context.close()
    context, page, errors = new_context(browser)
    try:
        navigate(page, url)
        page.set_viewport_size({"width": 3840, "height": 2160})
        fallback = stopped(page, "failed")
        assert "budget" in fallback["data"]["error"], fallback
        assert not errors, errors
    finally:
        context.close()
    return {"states": records, "paused_resize_preserves_clock": True, "oversized_static_fallback": True}


def check_graphics_recovery(browser, url):
    context, page, errors = new_context(browser)
    try:
        navigate(page, url)
        page.locator("#cream-motion-toggle").click()
        original = stopped(page, "paused", visible=True)
        original_gpu = snapshot(page, True)["gpu"]
        page.evaluate("""const gl=document.getElementById('cream-material').getContext('webgl2');
          window.__creamLoss=gl.getExtension('WEBGL_lose_context');
          if(!window.__creamLoss)throw new Error('Real context-loss extension is required for this check');
          window.__creamLoss.loseContext()""")
        stopped(page, "context-lost")
        page.evaluate("window.__creamLoss.restoreContext()")
        restored = stopped(page, "paused", visible=True, duration=300)
        gpu = snapshot(page, True)["gpu"]
        assert restored["data"]["sceneSeed"] == original["data"]["sceneSeed"]
        assert restored["data"]["motionTime"] == original["data"]["motionTime"]
        assert gpu == original_gpu, "Restored handles must render the same held recipe and pose."
        stats = restored["stats"]
        assert stats["programs"] == stats["deletedPrograms"] + 4, stats
        assert stats["buffers"] == stats["deletedBuffers"] + 1, stats
        assert stats["shaders"] == stats["deletedShaders"], stats
        page.locator("#cream-motion-toggle").click()
        wait_state(page)
        assert not errors, errors
        return {"real_context_loss": True, "identical_recovered_pose": True, "resources": stats}
    finally:
        context.close()


def check_fallbacks(browser, url):
    records = []
    for failure in ["webgl", "shader", "cream-module", "model-module", "material-module", "styles"]:
        context, page, errors = new_context(browser, failure=failure)
        try:
            module = {"cream-module": "cream.mjs", "model-module": "cream-model.mjs",
                      "material-module": "cream-material.mjs"}.get(failure)
            if module:
                page.route("**/" + module + "*", lambda route: route.abort())
            if failure == "styles":
                page.route("**/*.css*", lambda route: route.abort())
            page.goto(direct_url(url), wait_until="networkidle")
            page.wait_for_timeout(250)
            state = stopped(page)
            assert not state["ready"] and state["mainAvailable"], state
            assert state["data"].get("state") not in ["moving", "paused"], state
            assert page.locator("a[href='#cakes']").count() > 0, "Baseline navigation must remain."
            assert page.locator("a[data-photo][href]").count() > 0, "Full photo links must remain."
            if failure == "shader":
                assert state["stats"]["programs"] == state["stats"]["deletedPrograms"]
                assert state["stats"]["shaders"] == state["stats"]["deletedShaders"]
            assert not errors, (failure, errors)
            records.append({"failure": failure, "state": state["data"].get("state"),
                            "native_pointer": state["native"], "baseline_available": state["mainAvailable"]})
        finally:
            context.close()
    for preference, value in [("reduced_motion", "reduce"), ("forced_colors", "active")]:
        options = {preference: value}
        context = browser.new_context(viewport={"width": 1000, "height": 800}, **options)
        context.add_init_script("(" + INSTRUMENT + ')({"seed":4,"failure":""})')
        page = context.new_page()
        try:
            page.goto(direct_url(url), wait_until="networkidle")
            baseline = stopped(page)
            assert baseline["stats"]["contexts"] == 0 and baseline["mainAvailable"], baseline
            page.emulate_media(**{preference: "no-preference" if preference == "reduced_motion" else "none"})
            wait_state(page)
            records.append({"initial_preference": preference, "no_initial_gpu": True, "normal_return": True})
        finally:
            context.close()
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                  has_touch=True, reduced_motion="no-preference")
    context.add_init_script("(" + INSTRUMENT + ')({"seed":4,"failure":""})')
    page = context.new_page()
    try:
        navigate(page, url)
        page.dispatch_event("body", "pointermove", {"pointerType": "touch", "clientX": 150, "clientY": 400})
        page.wait_for_timeout(180)
        state = snapshot(page)
        assert_running(state)
        assert state["native"] and not state["pointer"]
        records.append({"coarse_touch": True, "ambient_and_pause_available": True, "native_pointer": True})
    finally:
        context.close()
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(direct_url(url), wait_until="networkidle")
        expect(page.locator(SELECTOR)).not_to_be_visible()
        expect(page.locator("#cream-motion-control")).not_to_be_visible()
        assert page.locator("a[data-photo][href]").count() > 0
        records.append({"javascript_disabled": True, "full_photo_links_retained": True})
    finally:
        context.close()
    return records


def check_versioning(browser, url):
    context, page, errors = new_context(browser)
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    try:
        navigate(page, url)
        expected = snapshot(page)["data"]["revision"]
        assert expected != "unversioned" and expected, expected
        modules = [item for item in requests if urlsplit(item).path.rsplit("/", 1)[-1] in
                   {"cream.mjs", "cream-model.mjs", "cream-material.mjs"}]
        assert len(modules) == 3, modules
        for item in modules:
            assert "v=" + expected in urlsplit(item).query, (expected, item)
        assert not errors, errors
        return {"revision": expected, "modules": modules}
    finally:
        context.close()


def run(url, output):
    report = {"url": url, "kind": "numerical browser/GPU review", "visual_approval": False,
              "image_view_calls": 0, "checks": {}, "passed": False}
    output.mkdir(parents=True, exist_ok=True)
    report_file = output / "review.json"
    started = time.monotonic()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                for name, check in [
                    ("versions", check_versioning),
                    ("motion_pointer_pause", check_motion_pointer_pause),
                    ("lifecycle", check_lifecycle),
                    ("entrance_dialogs", check_dialogs_entrance),
                    ("resize_populations_budget", check_resize_counts),
                    ("graphics_recovery", check_graphics_recovery),
                    ("fallbacks", check_fallbacks)]:
                    report["checks"][name] = check(browser, url)
                    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
                report["passed"] = True
            finally:
                browser.close()
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        report["duration_seconds"] = round(time.monotonic() - started, 2)
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT / ".local"):
        parser.error("--output must be a private directory under this repository's .local")
    result = run(args.url, destination)
    print(json.dumps({"passed": result["passed"], "checks": len(result["checks"]),
                      "report": str(destination / "review.json"), "visual_approval": False}))
