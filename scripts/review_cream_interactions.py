"""Numerical group-aware geometry, strawberry placement and native-input review. No image views."""

import argparse
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from playwright.sync_api import expect, sync_playwright
from review_cream_effect import INSTRUMENT, direct_url, new_context, snapshot, stopped, wait_state
from review_cream_liveness import parity


ROOT = Path(__file__).resolve().parents[1]

GEOMETRY = r"""async () => {
  const revision=document.getElementById('cream-effects').dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller]=await Promise.all([load('cream-model.mjs'),load('cream.mjs')]);
  const rows=[];
  const bounds=items=>[Math.min(...items.map(p=>p.x-p.radius)),Math.min(...items.map(p=>p.y-p.radius)),
    Math.max(...items.map(p=>p.x+p.radius)),Math.max(...items.map(p=>p.y+p.radius))];
  for(const seed of [4,7,51])for(const [width,height] of [[1440,1000],[1920,1080],[390,844]])
    for(const time of [0,3,8,20]){
      const base=model.createSceneRecipe(seed),recipe=controller.createProductionRecipe(model,seed);
      const sampled=controller.sampleProductionScoops(model,recipe,width,height,time*2);
      const previous=model.expandScoops(sampled.map(s=>({...s,lobeState:undefined})));
      const next=controller.sampleProductionScene(model,recipe,width,height,time*2);
      const ratios=[];
      for(let parent=0;parent<recipe.clumps.length;parent++){
        const group=recipe.clumps[parent].kind==='group',motion=recipe.groupMotions[parent];
        const parts=next.primitives.filter(p=>p.parent===parent);
        const compact=group?parts.map(p=>({...p,
          x:parts[0].x+motion.lobes[p.lobe][0]*sampled[parent].radius*motion.geometryMultiplier,
          y:parts[0].y+motion.lobes[p.lobe][1]*sampled[parent].radius*motion.geometryMultiplier})):parts;
        const a=bounds(previous.filter(p=>p.parent===parent)),b=bounds(compact),current=bounds(parts);
        ratios.push({parent,sourceParent:recipe.sourceParents[parent],kind:recipe.clumps[parent].kind,reference:'canonical-joined; actual positions checked by full adapter parity',expectedScale:group?(recipe.clumps[parent].radius>=.14?2/3:4/3):2,
          width:(b[2]-b[0])/(a[2]-a[0]),height:(b[3]-b[1])/(a[3]-a[1]),
          currentWidth:(current[2]-current[0])/(a[2]-a[0]),currentHeight:(current[3]-current[1])/(a[3]-a[1])});
      }
      const spawns=Array.from({length:8},(_,i)=>({id:i+1,x:.3+i*.05,y:.5,born:time*2}));
      const full=controller.sampleProductionScene(model,recipe,width,height,time*2,spawns);
      rows.push({seed,viewport:[width,height],time,baseGroups:base.groupCount,groups:recipe.groupCount,
        sourceGroups:recipe.sourceGroupCount,sourceAutomaticCount:recipe.sourceAutomaticPrimitiveCount,
        automaticCount:next.ambientCount,droplets:recipe.dropletCount,ratios,fullPrimitiveCount:full.primitives.length,
        strawberryStart:full.strawberryStart,
        spawnRadiusRatios:full.primitives.slice(full.strawberryStart).map(p=>p.radius/(Math.min(width,height)*.075)),
        cursorRadius:model.cursorRadius(width,height),capacity:controller.CREAM_MAX_PRIMITIVES});
    }
  return rows;
}"""

UPLOADED_GEOMETRY = r"""async () => {
  const root=document.getElementById('cream-effects');
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(root.dataset.revision),location.href).href);
  const [model,controller]=await Promise.all([load('cream-model.mjs'),load('cream.mjs')]);
  const data={...root.dataset},seed=Number(data.sceneSeed),time=Number(data.sampleTime);
  const base=model.createSceneRecipe(seed),recipe=controller.createProductionRecipe(model,seed);
  const sampled=controller.sampleProductionScoops(model,recipe,innerWidth,innerHeight,time);
  const previous=model.expandScoops(sampled.map(s=>({...s,lobeState:undefined})));
  const scene=controller.sampleProductionScene(model,recipe,innerWidth,innerHeight,time,JSON.parse(data.spawnRecords));
  const gl=document.getElementById('cream-material').getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM);
  const actual=scene.primitives.map((p,i)=>{
    const values=gl.getUniform(program,gl.getUniformLocation(program,'scoops['+i+']'));
    return {...p,x:values[0],y:values[1],radius:values[2],peak:values[3]};
  });
  const bounds=items=>[Math.min(...items.map(p=>p.x-p.radius)),Math.min(...items.map(p=>p.y-p.radius)),
    Math.max(...items.map(p=>p.x+p.radius)),Math.max(...items.map(p=>p.y+p.radius))];
  const ratios=recipe.clumps.map((p,parent)=>{
    const group=p.kind==='group',motion=recipe.groupMotions[parent];
    const parts=actual.filter(p=>p.parent===parent);
    const compact=group?parts.map(p=>({...p,
      x:parts[0].x+motion.lobes[p.lobe][0]*sampled[parent].radius*motion.geometryMultiplier,
      y:parts[0].y+motion.lobes[p.lobe][1]*sampled[parent].radius*motion.geometryMultiplier})):parts;
    const a=bounds(previous.filter(p=>p.parent===parent)),b=bounds(compact),current=bounds(parts);
    return {parent,kind:p.kind,reference:'canonical-joined',expectedScale:group?(p.radius>=.14?2/3:4/3):2,
      width:(b[2]-b[0])/(a[2]-a[0]),height:(b[3]-b[1])/(a[3]-a[1]),
      currentWidth:(current[2]-current[0])/(a[2]-a[0]),currentHeight:(current[3]-current[1])/(a[3]-a[1])};
  });
  return {viewport:[innerWidth,innerHeight],seed,sampleTime:time,ratios,groupScale:Number(data.groupGeometryMultiplier),largeGroupScale:Number(data.largeGroupGeometryMultiplier),
    cursorRadius:gl.getUniform(program,gl.getUniformLocation(program,'headRadius')),
    edgeCrossingPrimitives:actual.filter(p=>p.x-p.radius<0||p.x+p.radius>innerWidth||p.y-p.radius<0||p.y+p.radius>innerHeight).length,
    error:gl.getError()};
}"""

TINT_GPU = r"""async () => {
  const revision=document.getElementById('cream-effects').dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller,material]=await Promise.all([load('cream-model.mjs'),load('cream.mjs'),load('cream-material.mjs')]);
  const source=material.createCreamShaders({...model,MAX_PRIMITIVES:controller.CREAM_MAX_PRIMITIVES});
  const canvas=document.createElement('canvas');canvas.width=1000;canvas.height=800;
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent strawberry GPU probe unavailable');
  const shaders=[],program=gl.createProgram(),buffer=gl.createBuffer();
  try{
    for(const [type,text] of [[gl.VERTEX_SHADER,source.vertex],[gl.FRAGMENT_SHADER,source.strawberryFragment]]){
      const shader=gl.createShader(type);shaders.push(shader);gl.shaderSource(shader,text);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');
    gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    gl.viewport(0,0,1000,800);gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
    const uniform=name=>gl.getUniformLocation(program,name);
    gl.uniform2f(uniform('resolution'),1000,800);gl.uniform2f(uniform('viewSize'),1000,800);
    gl.uniform1f(uniform('pixelRatio'),1);gl.uniform1f(uniform('headRadius'),19.2);
    gl.uniform1i(uniform('trailCount'),0);gl.uniform1f(uniform('cursorTint'),0);
    gl.uniform4f(uniform('cursorShape'),0,1,0,0);
    const draw=(primitives,start)=>{
      const data=new Float32Array(controller.CREAM_MAX_PRIMITIVES*4);
      primitives.forEach((p,i)=>data.set([p.x,p.y,p.radius,p.peak],i*4));
      gl.uniform4fv(uniform('scoops[0]'),data);gl.uniform1i(uniform('scoopCount'),primitives.length);
      gl.uniform1i(uniform('strawberryStart'),start);gl.drawArrays(gl.TRIANGLES,0,3);
      const bytes=new Uint8Array(1000*800*4);gl.readPixels(0,0,1000,800,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
      if(gl.getError()!==gl.NO_ERROR)throw new Error('Strawberry GPU rendering failed');
      return bytes;
    };
    const rows=[];
    for(const count of [1,2,8]){
      const primitives=[{x:180,y:400,radius:80,peak:0},
        ...Array.from({length:count},(_,i)=>({x:650+i*13,y:400+Math.sin(i)*15,radius:120,peak:0}))];
      const white=draw(primitives,-1),pink=draw(primitives,1),reset=draw(primitives,-1);
      let alphaDifferences=0,ivoryDifferences=0,resetDifferences=0,pinkPixels=0,nonpinkPixels=0;
      for(let y=0;y<800;y++)for(let x=0;x<1000;x++){
        const offset=(y*1000+x)*4;
        if(white[offset+3]!==pink[offset+3])alphaDifferences++;
        if(x<320)for(let c=0;c<4;c++)if(white[offset+c]!==pink[offset+c])ivoryDifferences++;
        for(let c=0;c<4;c++)if(white[offset+c]!==reset[offset+c])resetDifferences++;
        if(x>450&&pink[offset+3]>=245){
          pinkPixels++;
          if(pink[offset+2]<pink[offset+1]-1||pink[offset]<pink[offset+1]-1)nonpinkPixels++;
        }
      }
      rows.push({count,alphaDifferences,ivoryDifferences,resetDifferences,pinkPixels,nonpinkPixels});
    }
    const nested=draw([{x:500,y:400,radius:300,peak:0},{x:500,y:400,radius:120,peak:0}],1);
    let containedPink=0,containedNonpink=0;
    for(let y=0;y<800;y++)for(let x=0;x<1000;x++)if(Math.hypot(x+.5-500,y+.5-400)<115){
      const offset=(y*1000+x)*4;
      containedPink++;
      if(nested[offset+2]<nested[offset+1]-1||nested[offset]<nested[offset+1]-1)containedNonpink++;
    }
    // Exercise the actual largest recipe and all eight placements through the fixed 48-slot shader.
    const recipe=controller.createProductionRecipe(model,4);
    const spawns=Array.from({length:8},(_,i)=>({id:i+1,x:.2+i*.08,y:.5,born:0}));
    const full=controller.sampleProductionScene(model,recipe,1000,800,0,spawns);
    draw(full.primitives,full.strawberryStart);
    const capacityCases=[17,52].map(seed=>{
      const scene=controller.sampleProductionScene(model,controller.createProductionRecipe(model,seed),1000,800,0,spawns);
      draw(scene.primitives,scene.strawberryStart);
      return {seed,count:scene.primitives.length,error:gl.getError()};
    });
    return {rows,containedPink,containedNonpink,fullSceneCount:full.primitives.length,
      capacityCases,capacity:controller.CREAM_MAX_PRIMITIVES,error:gl.getError()};
  }finally{
    gl.deleteBuffer(buffer);gl.deleteProgram(program);shaders.forEach(shader=>gl.deleteShader(shader));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""

ARM_PAINT = r"""type => {
  window.__creamInteractionPaint=null;
  window.addEventListener(type,event=>{
    const root=document.getElementById('cream-effects'),start=performance.now(),before=Number(root.dataset.paintCount);
    const input={trusted:event.isTrusted,pointerType:event.pointerType,buttons:event.buttons,focused:document.hasFocus(),
      nativeImmediately:!document.body.classList.contains('cream-cursor-active')};
    const observer=new MutationObserver(()=>{
      if(Number(root.dataset.paintCount)<=before)return;
      const pointer=document.getElementById('cream-cursor');
      window.__creamInteractionPaint={...input,elapsed:performance.now()-start,data:{...root.dataset},
        native:!document.body.classList.contains('cream-cursor-active'),hidden:pointer.hidden};
      observer.disconnect();
    });
    observer.observe(root,{attributes:true,attributeFilter:['data-paint-count']});
  },{once:true});
}"""


def first_paint(page):
    page.wait_for_function("window.__creamInteractionPaint!==null", timeout=1500)
    value = page.evaluate("window.__creamInteractionPaint")
    assert value["trusted"] and value["focused"] and value["pointerType"] == "mouse", value
    assert not value["native"] and not value["hidden"], value
    return value


def spawn_count(page):
    return int(snapshot(page)["data"]["spawnCount"])


def wait_count(page, count):
    page.wait_for_function("n=>Number(document.getElementById('cream-effects').dataset.spawnCount)===n", arg=count)


def click_heading(page):
    page.locator("h1").click()


def desktop_flow(browser, url):
    context, page, errors = new_context(browser)
    try:
        page.goto(direct_url(url), wait_until="networkidle")
        wait_state(page)
        page.evaluate("document.fonts.ready")
        page.locator("h1").scroll_into_view_if_needed()
        box = page.locator("h1").bounding_box()
        x, y = box["x"] + box["width"]*.4, box["y"] + 25
        client = context.new_cdp_session(page)
        page.evaluate(ARM_PAINT, "pointerdown")
        client.send("Input.dispatchMouseEvent", {"type": "mousePressed", "button": "left", "buttons": 1,
                    "clickCount": 1, "x": x, "y": y})
        down = first_paint(page)
        assert spawn_count(page) == 0
        page.evaluate(ARM_PAINT, "pointerup")
        client.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "button": "left", "buttons": 0,
                    "clickCount": 1, "x": x, "y": y})
        up = first_paint(page)
        wait_count(page, 1)
        assert not up["nativeImmediately"], up
        scene = snapshot(page, True)
        assert scene["gpu"]["strawberryStart"] == int(scene["data"]["ambientPrimitiveCount"])
        radius = scene["gpu"]["positions"][int(scene["data"]["scenePrimitiveCount"])-1][2]
        spawn_radius_multiplier = radius / (min(page.viewport_size.values())*.075)
        assert abs(spawn_radius_multiplier - 1) < .01
        parity(page)
        # A held primary button keeps the follower, while text selection and drag cancellation stay native.
        page.mouse.move(x, y)
        page.mouse.down()
        page.evaluate(ARM_PAINT, "pointermove")
        page.mouse.move(x+80, y, steps=3)
        held = first_paint(page)
        page.mouse.move(x+140, y, steps=5)
        page.mouse.up()
        page.wait_for_timeout(150)
        assert spawn_count(page) == 1
        assert page.evaluate("getSelection().toString().length>0"), "Text selection must not be intercepted."
        page.evaluate("getSelection().removeAllRanges()")
        for _ in range(11):
            click_heading(page)
        wait_count(page, 8)
        page.wait_for_function("JSON.parse(document.getElementById('cream-effects').dataset.spawnRecords).at(-1).id===12", timeout=1500)
        queue = json.loads(snapshot(page)["data"]["spawnRecords"])
        assert [record["id"] for record in queue] == list(range(5, 13)), queue
        fifo_ids = [record["id"] for record in queue]
        before = snapshot(page)
        page.evaluate("""const input=document.createElement('input');input.id='cream-editable-review';
          input.setAttribute('aria-label','Temporary editable interaction fixture');
          input.style.cssText='position:fixed;left:60px;top:120px;width:220px;height:48px;z-index:30';
          document.body.append(input)""")
        page.locator("#cream-editable-review").click()
        page.keyboard.type("Native editing")
        page.keyboard.press("Enter")
        assert page.locator("#cream-editable-review").input_value() == "Native editing"
        assert snapshot(page)["data"]["spawnRecords"] == before["data"]["spawnRecords"]
        page.locator("#cream-editable-review").evaluate("node=>node.remove()")
        for _ in range(5):
            page.locator("h1").dispatch_event("click", {"clientX": x, "clientY": y, "detail": 1})
        page.wait_for_timeout(100)
        assert snapshot(page)["data"]["spawnRecords"] == before["data"]["spawnRecords"], "Untrusted events cannot place cream."
        page.keyboard.down("Control")
        click_heading(page)
        page.keyboard.up("Control")
        page.mouse.click(x, y, button="right")
        assert snapshot(page)["native"], "Secondary-button release must not replace the native context-menu cursor."
        page.keyboard.press("Escape")
        assert snapshot(page)["data"]["spawnRecords"] == before["data"]["spawnRecords"]
        # Existing navigation is tested with keyboard and mouse; only the mouse activation places a blob.
        link = page.locator('header a[href="#cakes"]').first
        link.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        assert snapshot(page)["data"]["spawnRecords"] == before["data"]["spawnRecords"]
        link.click()
        page.wait_for_function("JSON.parse(document.getElementById('cream-effects').dataset.spawnRecords).at(-1).id===13")
        page.wait_for_function("Math.abs(document.getElementById('cakes').getBoundingClientRect().top)<innerHeight", timeout=1500)
        queue = snapshot(page)["data"]["spawnRecords"]
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        expect(page.locator("#notebook-dialog")).to_be_visible()
        page.wait_for_timeout(150)
        assert snapshot(page)["data"]["spawnRecords"] == queue
        opener = page.locator("#notebook-dialog .cake-card:visible a[data-photo]").first
        href = opener.get_attribute("href")
        opener.click()
        expect(page.locator("#photo-dialog")).to_be_visible()
        assert snapshot(page)["native"] and not snapshot(page)["pointer"]
        assert snapshot(page)["data"]["spawnRecords"] == queue and href and ".jpg" in href
        page.keyboard.press("Alt+Shift+P")
        paused = stopped(page, "paused", visible=True)
        page.locator("#photo-close").click()
        page.keyboard.press("Escape")
        assert snapshot(page)["data"]["spawnRecords"] == queue
        page.set_viewport_size({"width": 1000, "height": 800})
        page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===1000")
        resized = stopped(page, "paused", visible=True)
        assert resized["data"]["spawnRecords"] == queue and resized["data"]["motionTime"] == paused["data"]["motionTime"]
        parity(page)
        page.evaluate("""window.dispatchEvent(new Event('blur'));window.dispatchEvent(new Event('pageshow'));
          const gl=document.getElementById('cream-material').getContext('webgl2');
          window.__creamInteractionLoss=gl.getExtension('WEBGL_lose_context');window.__creamInteractionLoss.loseContext()""")
        stopped(page, "context-lost")
        page.evaluate("window.__creamInteractionLoss.restoreContext()")
        stopped(page, "paused", visible=True)
        assert snapshot(page)["data"]["spawnRecords"] == queue
        page.keyboard.press("Alt+Shift+P")
        wait_state(page)
        page.mouse.move(650, 650)
        page.wait_for_timeout(100)
        assert not snapshot(page)["native"]
        page.evaluate("""document.documentElement.dispatchEvent(new PointerEvent('pointerleave'));
          Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))""")
        stopped(page, "hidden")
        page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
        wait_state(page)
        assert snapshot(page)["data"]["spawnRecords"] == queue
        start = snapshot(page)
        page.wait_for_timeout(2200)
        finish = snapshot(page)
        fps = (int(finish["data"]["paintCount"])-int(start["data"]["paintCount"])) / ((finish["now"]-start["now"])/1000)
        assert 0 < fps <= 31, fps
        full_parity = parity(page)
        assert full_parity["spawns"] == 8 and full_parity["primitiveCount"] <= 43
        page.reload(wait_until="networkidle")
        wait_state(page)
        assert spawn_count(page) == 0
        assert not errors, errors
        client.detach()
        return {"first_down_without_move": down, "first_up_and_spawn": up, "first_held_move": held,
                "first_spawn_gpu_radius": radius, "first_spawn_gpu_radius_multiplier": spawn_radius_multiplier,
                "fifo_ids_after_twelve_clicks": fifo_ids,
                "all_eight_survive_resize_pause_hidden_and_context_loss": True, "refresh_resets": True,
                "ordinary_navigation_and_native_viewers": True, "text_selection_preserved": True,
                "editable_control_preserved": True,
                "full_scene_fps": fps, "full_scene_parity": full_parity}
    finally:
        context.close()


def touch_flow(browser, url):
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                  has_touch=True, reduced_motion="no-preference")
    context.add_init_script("(" + INSTRUMENT + ')({"seed":4,"failure":""})')
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(direct_url(url), wait_until="networkidle")
        wait_state(page)
        page.locator("h1").tap()
        wait_count(page, 1)
        first = snapshot(page)
        assert first["native"] and not first["pointer"]
        records = first["data"]["spawnRecords"]
        client = context.new_cdp_session(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 180, "y": 620}]})
        for y in [580, 530, 480, 430]:
            client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 180, "y": y}]})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(180)
        assert snapshot(page)["data"]["spawnRecords"] == records
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 130, "y": 400, "id": 1}]})
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 130, "y": 400, "id": 1}, {"x": 250, "y": 400, "id": 2}]})
        client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 100, "y": 400, "id": 1}, {"x": 280, "y": 400, "id": 2}]})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(180)
        assert snapshot(page)["data"]["spawnRecords"] == records
        page.emulate_media(reduced_motion="reduce")
        page.locator("h1").tap()
        assert snapshot(page)["data"]["spawnRecords"] == records
        assert not errors, errors
        client.detach()
        return {"trusted_tap_spawns_once": True, "swipe_and_pinch_never_spawn": True,
                "coarse_cursor_native": True, "reduced_motion_tap_does_not_spawn": True}
    finally:
        context.close()


def run(url, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {"url": url, "passed": False, "image_tool_views": 0, "visual_approval": False}
    destination = output / "review.json"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context, page, errors = new_context(browser)
                try:
                    page.goto(direct_url(url), wait_until="networkidle")
                    wait_state(page)
                    report["revision"] = snapshot(page)["data"]["revision"]
                    page.keyboard.press("Alt+Shift+P")
                    stopped(page, "paused", visible=True)
                    report["uploaded_geometry"] = []
                    for width, height in [(1440, 1000), (1920, 1080), (390, 844)]:
                        page.set_viewport_size({"width": width, "height": height})
                        page.wait_for_function("([w,h])=>Number(document.getElementById('cream-effects').dataset.viewportWidth)===w&&Number(document.getElementById('cream-effects').dataset.viewportHeight)===h", arg=[width, height])
                        uploaded = page.evaluate(UPLOADED_GEOMETRY)
                        assert uploaded["error"] == 0
                        assert uploaded["groupScale"] == 4/3
                        assert uploaded["largeGroupScale"] == 2/3
                        assert all(abs(row[axis]-row["expectedScale"]) < 1e-5 for row in uploaded["ratios"] for axis in ["width", "height"]), uploaded
                        assert abs(uploaded["cursorRadius"]-min(width, height)*.024) < 1e-4
                        report["uploaded_geometry"].append(uploaded)
                    report["geometry"] = page.evaluate(GEOMETRY)
                    for row in report["geometry"]:
                        assert row["sourceGroups"] == math.ceil(row["baseGroups"]*1.5)
                        assert row["automaticCount"] == math.ceil(row["sourceAutomaticCount"]/2)
                        assert row["fullPrimitiveCount"] == row["automaticCount"] + 8
                        assert 3 <= row["groups"] <= row["sourceGroups"] and 2 <= row["droplets"] <= 8
                        assert row["fullPrimitiveCount"] + 1 <= row["capacity"] == 48
                        assert all(abs(r[axis]-r["expectedScale"]) < 1e-10 for r in row["ratios"] for axis in ["width", "height"])
                        assert all(abs(r-1) < 1e-10 for r in row["spawnRadiusRatios"])
                        assert abs(row["cursorRadius"] - min(row["viewport"])*.024) < 1e-10
                    report["tint_gpu"] = page.evaluate(TINT_GPU)
                    assert report["tint_gpu"]["error"] == 0
                    assert report["tint_gpu"]["capacityCases"] == [
                        {"seed": 17, "count": 24, "error": 0}, {"seed": 52, "count": 17, "error": 0}]
                    assert report["tint_gpu"]["containedPink"] > 1000 and report["tint_gpu"]["containedNonpink"] == 0
                    for row in report["tint_gpu"]["rows"]:
                        assert row["pinkPixels"] > 1000 and row["nonpinkPixels"] == 0, row
                        assert row["alphaDifferences"] == row["ivoryDifferences"] == row["resetDifferences"] == 0, row
                    assert not errors, errors
                finally:
                    context.close()
                destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
                report["desktop"] = desktop_flow(browser, url)
                destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
                report["touch"] = touch_flow(browser, url)
                report["passed"] = True
            finally:
                browser.close()
    except Exception as error:
        report["error"] = repr(error)
        raise
    finally:
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        parser.error("--output must be under the repository's private .local directory")
    result = run(args.url, output)
    print(json.dumps({"passed": result["passed"], "revision": result["revision"], "report": str(output / "review.json")}))
