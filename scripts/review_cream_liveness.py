"""Trace real cream GPU progress without image views; optionally diagnose the old live blur gate."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs, urljoin, urlsplit

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright
from review_cream_effect import INSTRUMENT, direct_url, snapshot, stopped, wait_state


ROOT = Path(__file__).resolve().parents[1]
MODULES = ("cream.mjs", "cream-model.mjs", "cream-material.mjs")
VIEWPORTS = ((1440, 1000), (1920, 1080), (390, 844))

TRACE = r"""() => {
  const start=performance.now(),root=document.getElementById('cream-effects');
  const canvas=document.getElementById('cream-material'),data={...root.dataset};
  const visible=node=>!node.hidden&&getComputedStyle(node).display!=='none'&&getComputedStyle(node).visibility!=='hidden';
  let gpu=null;
  if(Number(data.paintCount)>0&&!['failed','context-lost'].includes(data.state)){
    const gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM);
    if(program){
      const read=name=>gl.getUniform(program,gl.getUniformLocation(program,name));
      gpu={error:gl.getError(),count:read('scoopCount'),tint:read('cursorTint'),trail:read('trailCount'),
        scissor:gl.isEnabled(gl.SCISSOR_TEST),
        positions:Array.from({length:Number(data.primitiveCount)},(_,i)=>Array.from(read('scoops['+i+']')))};
    }
  }
  return {now:performance.now(),readCost:performance.now()-start,data,gpu,stats:{...window.__creamReview},
    viewport:[innerWidth,innerHeight],visible:!document.hidden,focused:document.hasFocus(),
    layer:visible(root),control:visible(document.getElementById('cream-motion-control')),
    ready:document.body.classList.contains('has-cream-effects'),
    native:!document.body.classList.contains('cream-cursor-active'),
    pointer:visible(document.getElementById('cream-cursor')),scroll:scrollY,
    output:[canvas.width,canvas.height],heartbeatAge:Number(data.lastPaintTime)?performance.now()-Number(data.lastPaintTime):null};
}"""

PARITY = r"""async () => {
  const root=document.getElementById('cream-effects'),revision=root.dataset.revision;
  const url=new URL('cream-model.mjs',location.href);url.search='?v='+encodeURIComponent(revision);
  const model=await import(url.href);url.pathname=url.pathname.replace('cream-model.mjs','cream.mjs');
  const controller=await import(url.href);
  const data={...root.dataset},canvas=document.getElementById('cream-material'),gl=canvas.getContext('webgl2');
  const program=gl.getParameter(gl.CURRENT_PROGRAM);
  const recipe=controller.createProductionRecipe(model,Number(data.sceneSeed)),sample=Number(data.sampleTime);
  const scene=controller.sampleProductionScene(model,recipe,innerWidth,innerHeight,sample,JSON.parse(data.spawnRecords));
  const expected=scene.primitives;
  if(scene.ambientCount!==Math.ceil(recipe.sourceAutomaticPrimitiveCount/2)||
    Number(data.automaticPrimitiveCount)!==scene.ambientCount||recipe.groupCount!==Number(data.groupCount)||
    recipe.dropletCount!==Number(data.dropletCount))throw new Error('Automatic population is not the exact whole-piece half budget');
  const contact=data.contactActive==='true',count=expected.length+(contact?1:0);
  if(expected.length!==Number(data.scenePrimitiveCount)||count!==Number(data.primitiveCount))throw new Error('Production primitive count differs from uploaded scene');
  const tintLocation=gl.getUniformLocation(program,'strawberryStart');
  const tintStart=tintLocation===null?-1:gl.getUniform(program,tintLocation);
  if(tintStart!==scene.strawberryStart)throw new Error('Strawberry tint boundary was not restored');
  let error=0;const uploaded=[];
  expected.forEach((p,i)=>{
    const actual=gl.getUniform(program,gl.getUniformLocation(program,'scoops['+i+']'));
    const values=new Float32Array([p.x,p.y,p.radius,p.peak]);
    values.forEach((value,index)=>error=Math.max(error,Math.abs(value-actual[index])));
    uploaded.push({...p,x:actual[0],y:actual[1],radius:actual[2],peak:actual[3]});
  });
  if(uploaded.some(p=>p.peak!==0))throw new Error('A pointed peak remains in the uploaded scene');
  if(JSON.stringify(expected.slice(0,scene.ambientCount).map(p=>p.pieceId))!==data.backgroundPieceIds)
    throw new Error('Automatic piece identities differ from diagnostics');
  const spawnCount=scene.strawberryStart<0?0:expected.length-scene.strawberryStart;
  const shapeLocation=gl.getUniformLocation(program,'spawnShapeCount'),spawnShapes=[];
  if(spawnCount){
    if(shapeLocation===null||gl.getUniform(program,shapeLocation)!==spawnCount)throw new Error('Spawn shape count does not match scene');
    for(let i=0;i<8;i++){
      const actual=gl.getUniform(program,gl.getUniformLocation(program,'spawnShapes['+i+']'));
      const shape=i<spawnCount?expected[scene.strawberryStart+i].spawnShape:null;
      const values=new Float32Array(shape?[shape.angle,shape.aspect,shape.phase,shape.kind]:[0,0,0,0]);
      values.forEach((value,index)=>error=Math.max(error,Math.abs(value-actual[index])));
      if(shape)spawnShapes.push(Array.from(actual));
    }
  }else if(shapeLocation!==null&&gl.getUniform(program,shapeLocation)!==0)throw new Error('Stale spawn shape uniforms');
  if(contact){
    const pose=JSON.parse(data.pointerPose),actual=gl.getUniform(program,gl.getUniformLocation(program,'scoops['+expected.length+']'));
    new Float32Array([pose.x,pose.y,model.cursorRadius(innerWidth,innerHeight),0]).forEach((value,i)=>error=Math.max(error,Math.abs(value-actual[i])));
    if(gl.getUniform(program,gl.getUniformLocation(program,'contactActive'))!==1||
      gl.getUniform(program,gl.getUniformLocation(program,'contactPass'))!==0||
      gl.getUniform(program,gl.getUniformLocation(program,'ambientCount'))!==expected.length)throw new Error('Shared contact pass was not restored to main');
  }
  const edges=controller.productionEdgeLayout(model,recipe,innerWidth,innerHeight),blend=Math.min(innerWidth,innerHeight)*.04;
  const edgeBounds=edges.groups.map(group=>{
    const parts=uploaded.filter(p=>p.parent===group.parent);
    const left=parts.map(p=>p.x-p.radius).reduce((a,b)=>model.smoothUnion(a,b,blend))-group.otherUnionMargin-group.shadowLeft;
    const right=parts.map(p=>p.x+p.radius).reduce((a,b)=>-model.smoothUnion(-a,-b,blend))+group.otherUnionMargin+group.shadowRight;
    return {parent:group.parent,side:group.side,intrusion:Math.max(0,group.side==='left'?right-edges.glassLeft:edges.glassRight-left),limit:edges.intrusion};
  });
  const groupStates=recipe.groupMotions.filter(Boolean).map(motion=>controller.sampleGroupMotion(motion,sample));
  return {error,motion:Number(data.motionTime),sample,rate:Number(data.motionMultiplier),geometryScale:Number(data.geometryMultiplier),
    groupScale:Number(data.groupGeometryMultiplier),largeGroupScale:Number(data.largeGroupGeometryMultiplier),groupMotionCount:groupStates.length,
    spawns:Number(data.spawnCount),spawnScale:Number(data.spawnGeometryMultiplier),spawnShapes,primitiveCount:count,scenePrimitiveCount:expected.length,contact,edgeBounds,
    groups:recipe.groupCount,droplets:recipe.dropletCount,automaticCount:scene.ambientCount,
    sourceAutomaticCount:recipe.sourceAutomaticPrimitiveCount,sourceParents:recipe.sourceParents,
    maximumUploadedPeak:Math.max(...uploaded.map(p=>p.peak)),cohorts:scene.cohorts,
    groupStages:Object.fromEntries(['joined','repelling','separated','attracting'].map(stage=>[stage,groupStates.filter(state=>state.stage===stage).length]))};
}"""


def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def context_page(browser, viewport):
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                                  reduced_motion="no-preference",
                                  is_mobile=viewport[0] < 600, has_touch=viewport[0] < 600)
    context.add_init_script("(" + INSTRUMENT + ')({"seed":4,"failure":""})')
    page = context.new_page()
    errors, warnings = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: warnings.append(message.text) if message.type in ("warning", "error") else None)
    return context, page, errors, warnings


def trace(page):
    return page.evaluate(TRACE)


def parity(page):
    value = page.evaluate(PARITY)
    assert value["rate"] == 2 and value["geometryScale"] == 2 and abs(value["sample"] - value["motion"] * 2) < .00011, value
    assert value["error"] <= .001 and value["groupScale"] == 4/3 and value["groupMotionCount"] == value["groups"], value
    assert value["largeGroupScale"] == 2/3, value
    assert value["spawnScale"] == 1 and len(value["spawnShapes"]) == value["spawns"], value
    assert sum(value["groupStages"].values()) == value["groups"], value
    assert all(group["intrusion"] <= group["limit"] + .001 for group in value["edgeBounds"]), value
    return value


def advancing(before, after, native=True):
    assert after["data"]["state"] == "moving", after
    assert after["visible"] and after["layer"] and after["control"] and after["ready"], after
    assert after["stats"]["uploads"] > before["stats"]["uploads"], (before, after)
    assert int(after["data"]["paintCount"]) > int(before["data"]["paintCount"]), (before, after)
    assert float(after["data"]["motionTime"]) > float(before["data"]["motionTime"]), (before, after)
    assert after["gpu"]["positions"] != before["gpu"]["positions"], (before, after)
    assert not after["data"]["error"] and after["gpu"]["error"] == 0, after
    assert after["output"][0] * after["output"][1] <= 2_020_000, after
    assert after["gpu"]["tint"] == 0 and after["gpu"]["trail"] == 0 and not after["gpu"]["scissor"], after
    assert after["heartbeatAge"] is None or after["heartbeatAge"] < 1500, after
    if native:
        assert after["native"] and not after["pointer"], after


def sample_advance(page, milliseconds=1100):
    before = trace(page)
    page.wait_for_timeout(milliseconds)
    after = trace(page)
    advancing(before, after)
    return after


def diagnostic(browser, url, output):
    context, page, errors, warnings = context_page(browser, VIEWPORTS[0])
    report = {"url": url, "kind": "old-live numerical blur diagnostic",
              "native_address_bar_tested": False, "owner_event_sequence_known": False}
    try:
        page.goto(direct_url(url), wait_until="networkidle")
        wait_state(page)
        before = trace(page)
        page.wait_for_timeout(2100)
        normal = trace(page)
        page.evaluate("""Object.defineProperty(document,'hasFocus',{configurable:true,value:()=>false});
          window.dispatchEvent(new Event('blur'))""")
        blurred = trace(page)
        page.wait_for_timeout(1200)
        blurred_after = trace(page)
        page.evaluate("""Object.defineProperty(document,'hidden',{configurable:true,value:true});
          document.dispatchEvent(new Event('visibilitychange'));
          delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))""")
        returned = trace(page)
        page.wait_for_timeout(1200)
        returned_after = trace(page)
        page.evaluate("delete document.hasFocus;window.dispatchEvent(new Event('pageshow'))")
        wait_state(page)
        page.wait_for_timeout(300)
        recovered = trace(page)
        report.update({"normal_before": before, "normal_after": normal, "blur_before": blurred,
                       "blur_after": blurred_after, "visible_return_before": returned,
                       "visible_return_after": returned_after, "focused_recovery": recovered,
                       "errors": errors, "warnings": warnings,
                       "visible_blur_stopped": blurred_after["visible"] and
                       blurred_after["stats"]["uploads"] == blurred["stats"]["uploads"],
                       "unfocused_visible_return_stopped": returned_after["visible"] and
                       returned_after["stats"]["uploads"] == returned["stats"]["uploads"],
                       "normal_clock_fraction": (float(normal["data"]["motionTime"]) - float(before["data"]["motionTime"])) /
                       ((normal["now"] - before["now"]) / 1000)})
        assert not errors, errors
        return report
    finally:
        write(output / "baseline-diagnostic.json", report)
        context.close()


def warm_reload(page, context, url):
    client = context.new_cdp_session(page)
    client.send("Network.enable")
    responses = []
    client.on("Network.responseReceived", lambda event: responses.append({
        "url": event["response"]["url"],
        "disk": event["response"].get("fromDiskCache", False),
        "serviceWorker": event["response"].get("fromServiceWorker", False)}))
    revision = trace(page)["data"]["revision"]
    assert revision and revision != "unversioned", revision
    page.reload(wait_until="networkidle")
    wait_state(page)
    assert trace(page)["data"]["revision"] == revision
    modules = [record for record in responses if urlsplit(record["url"]).path.rsplit("/", 1)[-1] in MODULES]
    assert {urlsplit(record["url"]).path.rsplit("/", 1)[-1] for record in modules} == set(MODULES), modules
    for record in modules:
        assert parse_qs(urlsplit(record["url"]).query).get("v") == [revision], record
    hashes = {}
    for name in MODULES:
        response = page.request.get(urljoin(url, name) + "?v=" + revision)
        assert response.ok, (name, response.status)
        actual = response.body()
        expected = (ROOT / "web" / name).read_bytes()
        # Git publishes LF; local authoring and preview may retain Windows CRLF.
        assert actual.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        digest = sha256(actual).hexdigest()
        hashes[name] = digest
    client.detach()
    return {"revision": revision, "same_context_reload_without_clearing_cache": True,
            "observed_cache_responses": modules, "served_module_sha256": hashes, "parity": parity(page)}


def fill_spawn_queue(page):
    for _ in range(8):
        page.locator("h1").click()
    page.wait_for_function("Number(document.getElementById('cream-effects').dataset.spawnCount)===8")
    data = trace(page)["data"]
    return {"count": 8, "records": json.loads(data["spawnRecords"]), "primitive_count": int(data["primitiveCount"])}


def mixed_safety(page, viewport):
    page.locator("#cream-motion-toggle").click()
    held = stopped(page, "paused", visible=True, duration=400)
    page.evaluate("window.dispatchEvent(new Event('blur'));window.dispatchEvent(new Event('pageshow'))")
    stopped(page, "paused", visible=True)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1] - 16})
    page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportHeight) === innerHeight")
    resized = stopped(page, "paused", visible=True)
    assert resized["data"]["motionTime"] == held["data"]["motionTime"]
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportHeight) === innerHeight")
    stopped(page, "paused", visible=True)
    page.locator("#cream-motion-toggle").click()
    wait_state(page)
    page.evaluate("""Object.defineProperty(document,'hasFocus',{configurable:true,value:()=>false});
      window.dispatchEvent(new Event('blur'));
      Object.defineProperty(document,'hidden',{configurable:true,value:true});
      document.dispatchEvent(new Event('visibilitychange'))""")
    hidden = stopped(page, "hidden", duration=1100)
    page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
    wait_state(page)
    returned = sample_advance(page)
    assert returned["native"] and not returned["focused"]
    assert float(returned["data"]["motionTime"]) - float(hidden["data"]["motionTime"]) < 1.5
    page.evaluate("window.dispatchEvent(new Event('pagehide'))")
    stopped(page, "page-hidden")
    page.evaluate("window.dispatchEvent(new Event('pageshow'))")
    wait_state(page)
    sample_advance(page)
    page.evaluate("""const d=document.createElement('dialog');d.id='cream-liveness-dialog';
      d.textContent='Numerical dialog guard';document.body.append(d);d.showModal()""")
    sample_advance(page)
    page.evaluate("document.getElementById('cream-liveness-dialog').close();document.getElementById('cream-liveness-dialog').remove()")
    wait_state(page)
    sample_advance(page)
    page.evaluate("delete document.hasFocus;window.dispatchEvent(new Event('pageshow'))")
    return {"explicit_pause_zero_uploads": True, "pause_survives_blur_pageshow_resize": True,
            "hidden_zero_uploads": True, "unfocused_visible_return_without_pointer": True,
            "pagehide_guard": True, "native_dialog_keeps_ambient": True}


def long_trace(browser, url, output, viewport, seconds):
    context, page, errors, warnings = context_page(browser, viewport)
    path = output / f"trace-{viewport[0]}x{viewport[1]}.json"
    report = {"viewport": viewport, "requested_seconds": seconds, "samples": [],
              "passed": False, "native_address_bar_tested": False, "blur_fixture": "visible/unfocused document event semantics"}
    try:
        page.goto(direct_url(url), wait_until="networkidle")
        wait_state(page)
        page.evaluate("document.fonts.ready")
        report["warm_cache"] = warm_reload(page, context, url)
        report["full_spawn_queue"] = fill_spawn_queue(page)
        page.evaluate("document.documentElement.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}))")
        page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='false'")
        before = trace(page)
        initial_pixels = snapshot(page, True)["gpu"]["hash"]
        report["samples"].append({"second": 0, "section": "home", "state": before, "parity": parity(page)})
        sections = ["home", "story", "cakes", "order", "home", "cakes"]
        checkpoints = {max(1, seconds // 5): "blur", max(2, seconds * 2 // 5): "return",
                       max(3, seconds * 3 // 5): "blur", max(4, seconds * 4 // 5): "return"}
        first = before
        for second in range(1, seconds + 1):
            phase = checkpoints.get(second)
            if phase == "blur":
                page.evaluate("""Object.defineProperty(document,'hasFocus',{configurable:true,value:()=>false});
                  window.dispatchEvent(new Event('blur'))""")
            elif phase == "return":
                page.evaluate("delete document.hasFocus;window.dispatchEvent(new Event('pageshow'))")
            section = sections[((second - 1) // 5) % len(sections)]
            if second % 5 == 1:
                page.evaluate("""id=>document.getElementById(id).scrollIntoView({behavior:'instant',block:'start'})""", section)
            page.wait_for_timeout(1000)
            after = trace(page)
            record = {"second": second, "section": section, "event": phase, "state": after}
            report["samples"].append(record)
            write(path, report)
            advancing(before, after)
            record["parity"] = parity(page)
            assert not errors, errors
            assert not warnings, warnings
            before = after
        wall = (before["now"] - first["now"]) / 1000
        active = float(before["data"]["motionTime"]) - float(first["data"]["motionTime"])
        paints = int(before["data"]["paintCount"]) - int(first["data"]["paintCount"])
        report.update({"wall_seconds": wall, "active_seconds": active, "clock_fraction": active / wall,
                       "fps": paints / wall, "clamped_seconds": float(before["data"].get("clampedTime", 0)) -
                       float(first["data"].get("clampedTime", 0)),
                       "errors": errors, "warnings": warnings})
        assert wall > 30, wall
        assert 0 < report["fps"] <= 31.5, report["fps"]
        assert active / wall >= .8, f"Active clock is too slow; inspect measured frame clamp loss: {report['clock_fraction']}"
        assert snapshot(page, True)["gpu"]["hash"] != initial_pixels, "GPU pixels must change, not just the dataset."
        page.evaluate("delete document.hasFocus;window.dispatchEvent(new Event('pageshow'))")
        report["mixed_safety"] = mixed_safety(page, viewport)
        report["passed"] = True
        return report
    finally:
        report["errors"] = errors
        report["warnings"] = warnings
        write(path, report)
        context.close()


def viewer_trace(browser, url, output, viewport, seconds):
    context, page, errors, warnings = context_page(browser, viewport)
    path = output / f"viewers-{viewport[0]}x{viewport[1]}.json"
    report = {"viewport": viewport, "requested_seconds": seconds, "samples": [], "passed": False,
              "kind": "targeted ambient continuity behind actual nested native viewers"}
    try:
        page.goto(direct_url(url), wait_until="networkidle")
        wait_state(page)
        page.evaluate("document.fonts.ready")
        report["warm_cache"] = warm_reload(page, context, url)
        report["full_spawn_queue"] = fill_spawn_queue(page)
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        page.wait_for_function("document.getElementById('notebook-dialog').open")
        page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='false'")
        before = trace(page)
        initial_pixels = snapshot(page, True)["gpu"]["hash"]
        first = before
        viewer = "notebook"
        report["samples"].append({"second": 0, "viewer": viewer, "state": before, "parity": parity(page)})
        for second in range(1, seconds + 1):
            if second == seconds // 3:
                page.locator("#notebook-dialog .cake-card:visible a[data-photo]").first.click()
                page.wait_for_function("document.getElementById('photo-dialog').open")
                viewer = "photo-over-notebook"
            elif second == seconds * 2 // 3:
                page.locator("#photo-close").click()
                page.wait_for_function("!document.getElementById('photo-dialog').open")
                viewer = "notebook-after-photo"
            page.wait_for_timeout(1000)
            after = trace(page)
            record = {"second": second, "viewer": viewer, "state": after}
            report["samples"].append(record)
            write(path, report)
            advancing(before, after)
            assert after["data"]["viewerOpen"] == "true", after
            assert page.locator("#notebook-dialog").evaluate("node=>node.open")
            record["parity"] = parity(page)
            assert not errors and not warnings, (errors, warnings)
            before = after
        wall = (before["now"] - first["now"]) / 1000
        active = float(before["data"]["motionTime"]) - float(first["data"]["motionTime"])
        report.update({"wall_seconds": wall, "active_seconds": active, "clock_fraction": active / wall,
                       "fps": (int(before["data"]["paintCount"]) - int(first["data"]["paintCount"])) / wall})
        assert wall > 30 and .8 <= active / wall <= 1.05, report["clock_fraction"]
        assert 0 < report["fps"] <= 31.5, report["fps"]
        assert snapshot(page, True)["gpu"]["hash"] != initial_pixels
        page.locator("#notebook-dialog .cake-card:visible a[data-photo]").first.click()
        page.wait_for_function("document.getElementById('photo-dialog').open")
        page.evaluate("window.__creamShortcutFocus=document.activeElement")
        page.keyboard.press("Alt+Shift+P")
        stopped(page, "paused", visible=True, duration=1100)
        assert page.evaluate("document.activeElement===window.__creamShortcutFocus")
        page.locator("#photo-close").click()
        stopped(page, "paused", visible=True)
        page.keyboard.press("Escape")
        page.wait_for_function("!document.getElementById('notebook-dialog').open")
        stopped(page, "paused", visible=True)
        page.keyboard.press("Alt+Shift+P")
        wait_state(page)
        sample_advance(page)
        report["shortcut"] = {"native_viewer_pause_zero_uploads": True, "focus_retained": True,
                              "pause_retained_after_nested_closes": True, "resume_without_pointer": True}
        report["passed"] = True
        return report
    finally:
        report["errors"] = errors
        report["warnings"] = warnings
        write(path, report)
        context.close()


def run(url, output, seconds, baseline, dialogs_only=False):
    output.mkdir(parents=True, exist_ok=True)
    summary = {"url": url, "mode": "baseline-diagnostic" if baseline else "viewer-liveness" if dialogs_only else "candidate-liveness",
               "passed": False, "image_view_calls": 0, "visual_approval": False, "reports": []}
    start = time.monotonic()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                if baseline:
                    summary["baseline"] = diagnostic(browser, url, output)
                else:
                    for viewport in VIEWPORTS:
                        report = (viewer_trace if dialogs_only else long_trace)(browser, url, output, viewport, seconds)
                        summary["reports"].append({key: report[key] for key in
                                                   ["viewport", "wall_seconds", "active_seconds", "clock_fraction", "fps", "passed"]})
                        write(output / "summary.json", summary)
                summary["passed"] = True
            finally:
                browser.close()
    except Exception as error:
        summary["error"] = str(error)
        raise
    finally:
        summary["duration_seconds"] = round(time.monotonic() - start, 2)
        write(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--baseline-diagnostic", action="store_true")
    parser.add_argument("--dialogs-only", action="store_true", help="Target sustained motion behind actual notebook/photo viewers.")
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT / ".local"):
        parser.error("--output must be a private directory under this repository's .local")
    if args.seconds < 31:
        parser.error("--seconds must be at least 31 for a meaningful continuity trace")
    if args.baseline_diagnostic and args.dialogs_only:
        parser.error("--baseline-diagnostic and --dialogs-only are mutually exclusive")
    result = run(args.url, destination, args.seconds, args.baseline_diagnostic, args.dialogs_only)
    print(json.dumps({"passed": result["passed"], "mode": result["mode"], "summary": str(destination / "summary.json")}))
