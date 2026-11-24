"""Numerical half-size organic spawn, shared-field and actual-click review. No image views."""

import argparse
from base64 import b64decode
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import numpy as np
from playwright.sync_api import sync_playwright
from review_cream_contact import components, fields, merge, primitive_distance, rgba
from review_cream_effect import direct_url, new_context, snapshot, stopped, wait_state
from review_cream_liveness import parity


ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / ".local" / "group-motion-20261011" / "before-spawn-shapes"

GPU = r"""async options => {
  const root=document.getElementById('cream-effects'),revision=root.dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller,material]=await Promise.all([load('cream-model.mjs'),load('cream.mjs'),load('cream-material.mjs')]);
  const old=Function('model',options.beforeMaterial.replace('export function createCreamShaders','function createCreamShaders')+
    ';return createCreamShaders(model);')({...model,MAX_PRIMITIVES:48});
  const oldController=Function(options.beforeController.replace(/\bexport\s+(?=const|function|async function)/g,'')
    .replaceAll('import.meta.url',JSON.stringify(location.href))+';return {createProductionRecipe,sampleProductionScene};')();
  const sources=material.createCreamShaders({...model,MAX_PRIMITIVES:48});
  const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl2',
    {alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent spawn GPU probe unavailable');
  const shaders=[],programs=[],buffer=gl.createBuffer();
  const compile=fragment=>{
    const p=gl.createProgram();programs.push(p);
    for(const [kind,source] of [[gl.VERTEX_SHADER,sources.vertex],[gl.FRAGMENT_SHADER,fragment]]){
      const s=gl.createShader(kind);shaders.push(s);gl.shaderSource(s,source);gl.compileShader(s);
      if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));gl.attachShader(p,s);
    }
    gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p;
  };
  const original=compile(old.fragment),classic=compile(sources.fragment),oldPink=compile(old.strawberryFragment);
  const pink=compile(sources.spawnFragment),shared=compile(sources.spawnContactFragment);
  const oldShared=compile(old.contactFragment),plainShared=compile(sources.contactFragment);
  gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const draw=(program,background,start,view,cursor=null,shape=null,path=[],pass=null)=>{
    canvas.width=view[0];canvas.height=view[1];
    gl.useProgram(program);gl.viewport(0,0,...view);gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const loc=name=>gl.getUniformLocation(program,name),contact=pass!==null;
    const radius=model.cursorRadius(...view),parts=cursor?[...background,{...cursor,radius,peak:0}]:background;
    const data=new Float32Array(48*4),shapeData=new Float32Array(32),trailData=new Float32Array(32);
    const spawnCount=background.filter(p=>p.spawnShape).length;
    parts.forEach((p,i)=>data.set([p.x,p.y,p.radius,p.peak],i*4));
    background.forEach((p,i)=>{if(p.spawnShape){const s=p.spawnShape;shapeData.set([s.angle,s.aspect,s.phase,s.kind],(i-start)*4);}});
    let lead=cursor;path.forEach((p,i)=>{trailData.set([lead.x,lead.y,p.x,p.y],i*4);lead=p;});
    gl.uniform2f(loc('resolution'),...view);gl.uniform2f(loc('viewSize'),...view);gl.uniform1f(loc('pixelRatio'),1);
    gl.uniform1i(loc('scoopCount'),parts.length);gl.uniform4fv(loc('scoops[0]'),data);
    gl.uniform1i(loc('strawberryStart'),start);gl.uniform1i(loc('spawnShapeCount'),spawnCount);gl.uniform4fv(loc('spawnShapes[0]'),shapeData);
    gl.uniform1f(loc('headRadius'),radius);gl.uniform1i(loc('trailCount'),contact?0:path.length);gl.uniform4fv(loc('trail[0]'),trailData);
    gl.uniform1f(loc('cursorTint'),cursor&&!contact?1:0);
    gl.uniform4f(loc('cursorShape'),...(!contact&&shape?[shape.angle,shape.stretch,shape.phase,shape.energy]:[0,1,0,0]));
    gl.uniform1i(loc('ambientCount'),background.length);gl.uniform1i(loc('contactActive'),contact?1:0);
    gl.uniform1i(loc('contactPass'),pass??0);gl.uniform1i(loc('contactTrailCount'),path.length);
    gl.uniform4f(loc('contactShape'),...(shape?[shape.angle,shape.stretch,shape.phase,shape.energy]:[0,1,0,0]));
    gl.drawArrays(gl.TRIANGLES,0,3);
    const bytes=new Uint8Array(view[0]*view[1]*4);gl.readPixels(0,0,...view,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
    if(gl.getError()!==gl.NO_ERROR)throw new Error('Shaped spawn GPU error');
    const floats=background.map((p,i)=>{
      const v=Array.from(gl.getUniform(program,loc('scoops['+i+']'))),out={...p,x:v[0],y:v[1],radius:v[2],peak:v[3]};
      if(p.spawnShape){const s=gl.getUniform(program,loc('spawnShapes['+(i-start)+']'));out.spawnShape={angle:s[0],aspect:s[1],phase:s[2],kind:s[3]};}
      return out;
    });
    let unusedShapeValues=0;
    if(loc('spawnShapeCount'))for(let i=spawnCount;i<8;i++)unusedShapeValues+=Array.from(gl.getUniform(program,loc('spawnShapes['+i+']'))).filter(v=>v!==0).length;
    return {image:canvas.toDataURL(),bytes,parts:floats,unusedShapeValues};
  };
  const differing=(a,b)=>{let n=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i])n++;return n;};
  const rows=[],preserved=[],contacts=[],mixed=[];
  try{
    if(options.mode!=='actual'){
      for(const seed of [4,17])for(const seconds of [0,11,37]){
        const recipe=controller.createProductionRecipe(model,seed),view=[800,600];
        const scene=controller.sampleProductionScene(model,recipe,...view,seconds);
        const current=draw(classic,scene.primitives,-1,view),previous=draw(original,scene.primitives,-1,view);
        preserved.push({kind:'scene',seed,seconds,different:differing(current.bytes,previous.bytes)});
      }
      for(const vertical of [false,true])for(const pass of [0,1]){
        const view=[800,600],background=[{x:300,y:250,radius:80,peak:0}];
        const shape={...controller.createCursorShape(),phase:1.3},cursor={x:300+(vertical?0:100),y:250+(vertical?100:0)},path=model.resetTrail(cursor);
        const current=draw(plainShared,background,-1,view,cursor,shape,path,pass);
        const previous=draw(oldShared,background,-1,view,cursor,shape,path,pass);
        preserved.push({kind:'no-spawn-contact',vertical,pass,different:differing(current.bytes,previous.bytes)});
      }
      for(const view of [[390,844],[1000,800],[1440,1000]])for(const seed of [4,17])for(let id=1;id<=8;id++){
        const seconds=(id%3)*9,record=controller.appendCreamSpawn([],{id,x:.5,y:.5,born:0},seed)[0];
        const recipe=controller.createProductionRecipe(model,seed),scene=controller.sampleProductionScene(model,recipe,...view,seconds,[record]);
        const p=scene.primitives.at(-1),before=oldController.sampleProductionScene(model,oldController.createProductionRecipe(model,seed),...view,seconds,[record]).primitives.at(-1);
        const current=draw(pink,[p],0,view),previous=draw(oldPink,[before],0,view);
        const reset=draw(pink,[p],0,view);
        rows.push({source:'synthetic',view,seed,id,seconds,primitive:current.parts[0],oldRadius:before.radius,
          newImage:current.image,oldImage:previous.image,resetDifferences:differing(current.bytes,reset.bytes),
          unusedShapeValues:current.unusedShapeValues});
      }
      const view=[900,700],radius=model.cursorRadius(...view),blend=Math.min(...view)*.04;
      const shape={...controller.createCursorShape(),phase:1.3},byKind=new Map();
      for(let id=1;byKind.size<3&&id<50;id++){const s=controller.createSpawnShape(4,id);byKind.set(s.kind,s);}
      for(const [kind,spawnShape] of byKind)for(const vertical of [false,true])for(const gap of [5,70]){
        const p={x:350,y:300,radius:70,peak:0,spawnShape},dir={x:vertical?0:1,y:vertical?1:0};
        let low=0,high=1;for(let i=0;i<30;i++){const t=(low+high)/2,q=controller.spawnShapePoint(dir.x*t,dir.y*t,spawnShape);if(Math.hypot(q.x,q.y)<1)low=t;else high=t;}
        const boundary={x:p.x+dir.x*low*p.radius,y:p.y+dir.y*low*p.radius};
        const dx=controller.creamPrimitiveDistance(p,{x:boundary.x+.01,y:boundary.y})-controller.creamPrimitiveDistance(p,{x:boundary.x-.01,y:boundary.y});
        const dy=controller.creamPrimitiveDistance(p,{x:boundary.x,y:boundary.y+.01})-controller.creamPrimitiveDistance(p,{x:boundary.x,y:boundary.y-.01});
        const length=Math.hypot(dx,dy),normal={x:dx/length,y:dy/length},q=controller.cursorShapePoint(-normal.x,-normal.y,shape);
        const reach=radius/Math.hypot(q.x,q.y),cursor={x:boundary.x+normal.x*(reach+gap),y:boundary.y+normal.y*(reach+gap)},path=model.resetTrail(cursor);
        const state=controller.creamContactState(model,[p],cursor,shape,path,...view);
        const main=state.active?draw(shared,[p],0,view,cursor,shape,path,0):draw(pink,[p],0,view);
        const foreground=state.active?draw(shared,[p],0,view,cursor,shape,path,1):draw(classic,[],-1,view,cursor,shape,path);
        contacts.push({kind,vertical,gap,state,background:main.parts,cursor,shape,path,radius,blend,width:view[0],height:view[1],
          main:main.image,foreground:foreground.image});
      }
      for(const vertical of [false,true]){
        const p={x:350,y:300,radius:70,peak:0,spawnShape:controller.createSpawnShape(17,2)};
        const cursor={x:vertical?350:650,y:vertical?600:300};
        const path=Array.from({length:8},(_,i)=>({x:cursor.x-(vertical?0:(i+1)*60),y:cursor.y-(vertical?(i+1)*60:0)}));
        const state=controller.creamContactState(model,[p],cursor,shape,path,...view);
        const main=draw(shared,[p],0,view,cursor,shape,path,0),foreground=draw(shared,[p],0,view,cursor,shape,path,1);
        contacts.push({kind:'tail',vertical,gap:0,state,background:main.parts,cursor,shape,path,radius,blend,width:view[0],height:view[1],main:main.image,foreground:foreground.image});
      }
      for(const vertical of [false,true])for(const gap of [5,70]){
        const background=[{x:350,y:300,radius:70,peak:0},
          {x:750,y:560,radius:52,peak:0,spawnShape:controller.createSpawnShape(9,7)}];
        const dir={x:vertical?0:1,y:vertical?1:0},q=controller.cursorShapePoint(-dir.x,-dir.y,shape);
        const reach=radius/Math.hypot(q.x,q.y),cursor={x:350+dir.x*(70+reach+gap),y:300+dir.y*(70+reach+gap)},path=model.resetTrail(cursor);
        const state=controller.creamContactState(model,background,cursor,shape,path,...view);
        const main=state.active?draw(shared,background,1,view,cursor,shape,path,0):draw(pink,background,1,view);
        const foreground=state.active?draw(shared,background,1,view,cursor,shape,path,1):draw(classic,[],-1,view,cursor,shape,path);
        contacts.push({kind:'ivory-with-distant-spawn',additional_components:1,vertical,gap,state,background:main.parts,
          cursor,shape,path,radius,blend,width:view[0],height:view[1],main:main.image,foreground:foreground.image});
      }
      for(const seed of [4,17]){
        const recipe=controller.createProductionRecipe(model,seed),view=[1000,800];
        let records=[];for(let id=1;id<=8;id++)records=controller.appendCreamSpawn(records,{id,x:.14+id*.08,y:.44+(id%2)*.18,born:0},seed);
        const scene=controller.sampleProductionScene(model,recipe,...view,13,records),result=draw(pink,scene.primitives,scene.strawberryStart,view);
        mixed.push({seed,view,parts:result.parts,start:scene.strawberryStart,image:result.image,count:scene.primitives.length,unusedShapeValues:result.unusedShapeValues});
      }
    }else{
      const data={...root.dataset},view=[innerWidth,innerHeight],records=JSON.parse(data.spawnRecords);
      const recipe=controller.createProductionRecipe(model,Number(data.sceneSeed)),scene=controller.sampleProductionScene(model,recipe,...view,Number(data.sampleTime),records);
      const app=document.getElementById('cream-material').getContext('webgl2'),program=app.getParameter(app.CURRENT_PROGRAM);
      records.forEach((record,index)=>{
        const v=app.getUniform(program,app.getUniformLocation(program,'scoops['+(scene.strawberryStart+index)+']'));
        const s=app.getUniform(program,app.getUniformLocation(program,'spawnShapes['+index+']'));
        const p={x:v[0],y:v[1],radius:v[2],peak:v[3],spawnShape:{angle:s[0],aspect:s[1],phase:s[2],kind:s[3]}};
        const before={...p,radius:p.radius*2,spawnShape:undefined},current=draw(pink,[p],0,view),previous=draw(oldPink,[before],0,view);
        rows.push({source:'actual-upload',view,seed:Number(data.sceneSeed),id:record.id,seconds:Number(data.sampleTime),primitive:current.parts[0],
          oldRadius:before.radius,newImage:current.image,oldImage:previous.image,resetDifferences:0,unusedShapeValues:current.unusedShapeValues});
      });
    }
    return {revision,rows,preserved,contacts,mixed};
  }finally{
    gl.deleteBuffer(buffer);programs.forEach(p=>gl.deleteProgram(p));shaders.forEach(s=>gl.deleteShader(s));gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""


def analyze_shape(row):
    current, previous = rgba(row.pop("newImage")), rgba(row.pop("oldImage"))
    p = row["primitive"]
    mask, old_mask = current[:, :, 3] >= 128, previous[:, :, 3] >= 128
    y, x = np.indices(mask.shape, dtype=float)
    x += .5
    y += .5
    distance = primitive_distance(p, x, y)
    stable = np.abs(distance) > 1.25
    mismatches = int(np.count_nonzero(stable & (mask != (distance <= 0))))
    py, px = np.nonzero(mask)
    ox, oy = px+.5-p["x"], py+.5-p["y"]
    diameter_bound = float(2*np.hypot(ox, oy).max())
    old_y, old_x = np.nonzero(old_mask)
    old_diameter = float(2*np.hypot(old_x+.5-p["x"], old_y+.5-p["y"]).max())
    coords = np.stack((px+.5, py+.5), axis=0)
    eigen = np.linalg.eigvalsh(np.cov(coords))
    aspect = float(math.sqrt(eigen[-1]/eigen[0]))
    boundary = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    by, bx = np.nonzero(boundary)
    radial = np.hypot(bx+.5-coords[0].mean(), by+.5-coords[1].mean())
    radial_cv = float(radial.std()/radial.mean())
    opaque = current[:, :, 3] >= 245
    nonpink = int(np.count_nonzero(opaque & ((current[:, :, 2].astype(int) < current[:, :, 1].astype(int)-1) |
                                           (current[:, :, 0].astype(int) < current[:, :, 1].astype(int)-1))))
    sizes = components(mask)
    metrics = {"components": len(sizes), "opaque_pixels": int(mask.sum()), "area_over_old_circle": float(mask.sum()/old_mask.sum()),
               "area_over_new_radius_circle": float(mask.sum()/(math.pi*p["radius"]**2)), "moment_aspect": aspect,
               "centroid_radial_cv": radial_cv, "opaque_diameter_bound": diameter_bound, "old_circle_diameter": old_diameter,
               "diameter_ratio_upper_bound": diameter_bound/old_diameter, "stable_scalar_samples": int(stable.sum()),
               "scalar_mismatches": mismatches, "nonpink_opaque_pixels": nonpink,
               "hotspot_alpha": int(current[int(p["y"]), int(p["x"]), 3]), "alpha_sha256": sha256(current[:, :, 3].tobytes()).hexdigest()}
    row["metrics"] = metrics
    assert mismatches == nonpink == row["resetDifferences"] == row["unusedShapeValues"] == 0, row
    assert len(sizes) == 1 and metrics["hotspot_alpha"] >= 245, row
    assert abs(p["radius"]/row["oldRadius"]-.5) < 1e-7
    assert diameter_bound <= old_diameter*.5, row
    assert aspect > 1.05 or radial_cv > .055, row
    return row


def analyze_contact(row):
    main, foreground = rgba(row.pop("main")), rgba(row.pop("foreground"))
    background, own, shared, _ = fields(row)
    mask = 1-(1-main[:, :, 3]/255)*(1-foreground[:, :, 3]/255) >= .5
    expected = shared if row["state"]["active"] else np.minimum(background, own)
    mismatch = int(np.count_nonzero((np.abs(expected) > 1.25) & (mask != (expected <= 0))))
    sizes = components(mask)
    bridge = int(np.count_nonzero(mask & (background > .1) & (own > .1)))
    row["metrics"] = {"components": len(sizes), "scalar_mismatches": mismatch, "bridge_pixels": bridge}
    assert mismatch == 0, row
    assert len(sizes) == (1 if row["state"]["active"] else 2) + row.get("additional_components", 0), row
    if row["gap"] == 5:
        assert row["state"]["head"] and bridge > 0, row
    if row["gap"] == 70:
        assert not row["state"]["active"], row
    if row["kind"] == "tail":
        assert row["state"]["tail"] and not row["state"]["head"], row
    return row


def analyze_mixed(row):
    image = rgba(row.pop("image"))
    y, x = np.indices(image.shape[:2], dtype=float)
    x += .5
    y += .5
    base, pink = np.full(x.shape, 100000.0), np.full(x.shape, 100000.0)
    for i, p in enumerate(row["parts"]):
        value = primitive_distance(p, x, y)
        base = merge(base, value, min(row["view"])*.04)
        if i >= row["start"]:
            pink = merge(pink, value, min(row["view"])*.04)
    mismatch = int(np.count_nonzero((np.abs(base) > 1.25) & ((image[:, :, 3] >= 128) != (base <= 0))))
    pink_core = (pink < -2) & (image[:, :, 3] >= 245)
    nonpink = int(np.count_nonzero(pink_core & ((image[:, :, 2].astype(int) < image[:, :, 1].astype(int)-1) |
                                              (image[:, :, 0].astype(int) < image[:, :, 1].astype(int)-1))))
    row["metrics"] = {"scalar_mismatches": mismatch, "pink_core_pixels": int(pink_core.sum()), "nonpink_core_pixels": nonpink}
    assert mismatch == nonpink == 0 and row["count"]+1 <= 48, row
    assert pink_core.sum() > 100
    return row


def run(url, output):
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "review.json"
    assert not destination.exists()
    report = {"url": url, "passed": False, "image_tool_views": 0, "visual_approval": False, "shapes": [], "contacts": [], "mixed": [], "actual": []}
    arguments = {"beforeMaterial": (BEFORE / "cream-material.mjs").read_text(encoding="utf-8"),
                 "beforeController": (BEFORE / "cream.mjs").read_text(encoding="utf-8"), "mode": "synthetic"}
    save = lambda: destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context, page, errors = new_context(browser)
                console = []
                page.on("console", lambda message: console.append(message.text) if message.type in ["warning", "error"] else None)
                try:
                    page.goto(direct_url(url), wait_until="networkidle")
                    wait_state(page)
                    page.keyboard.press("Alt+Shift+P")
                    stopped(page, "paused", visible=True)
                    gpu = page.evaluate(GPU, arguments)
                    report["revision"] = gpu["revision"]
                    report["preserved"] = gpu["preserved"]
                    assert all(row["different"] == 0 for row in gpu["preserved"])
                    for row in gpu["rows"]:
                        report["shapes"].append(analyze_shape(row))
                        save()
                    for row in gpu["contacts"]:
                        report["contacts"].append(analyze_contact(row))
                        save()
                    for row in gpu["mixed"]:
                        report["mixed"].append(analyze_mixed(row))
                        save()
                    for seed in [4, 17]:
                        for view in [[390, 844], [1000, 800], [1440, 1000]]:
                            group = [row for row in report["shapes"] if row["seed"] == seed and row["view"] == view]
                            assert len({row["metrics"]["alpha_sha256"] for row in group}) == 8
                            areas = [row["metrics"]["area_over_new_radius_circle"] for row in group]
                            assert max(areas)-min(areas) > .025, "Area variation proves the shapes are not only rotations."
                    page.keyboard.press("Alt+Shift+P")
                    wait_state(page)
                    report["click_points"] = []
                    for index in range(12):
                        x = 1440*(.2+.2*(index % 4))
                        y = 1000*(.22+.16*(index // 4))
                        point = page.evaluate("""([x,y])=>{
                          for(const dy of [0,-24,24,-48,48,-72,72])for(const dx of [0,-30,30,-60,60,-120,120,-180,180,-240,240,-360,360,-480,480,-600,600]){
                            const xx=x+dx,yy=y+dy,n=document.elementFromPoint(xx,yy);
                            if(xx<innerWidth*.18||xx>innerWidth*.82||yy<innerHeight*.18||yy>innerHeight*.62)continue;
                            if(n&&!n.closest('header,button,a,input,textarea,select,dialog,[data-open-notebook]'))return {x:xx,y:yy};
                          }
                          return null;
                        }""", [x, y])
                        assert point is not None, {"index": index, "desired": [x, y]}
                        report["click_points"].append(point)
                        page.mouse.click(point["x"], point["y"])
                    page.wait_for_function("JSON.parse(document.getElementById('cream-effects').dataset.spawnRecords).at(-1)?.id===12")
                    records = json.loads(snapshot(page)["data"]["spawnRecords"])
                    assert [p["id"] for p in records] == list(range(5, 13))
                    assert len({json.dumps(p["shape"], sort_keys=True) for p in records}) == 8
                    report["fifo_records"] = records
                    page.keyboard.press("Alt+Shift+P")
                    stopped(page, "paused", visible=True)
                    held = snapshot(page)["data"]["sampleTime"]
                    for width, height in [(1440, 1000), (390, 844), (844, 390)]:
                        page.set_viewport_size({"width": width, "height": height})
                        page.wait_for_function("([w,h])=>Number(document.getElementById('cream-effects').dataset.viewportWidth)===w&&Number(document.getElementById('cream-effects').dataset.viewportHeight)===h", arg=[width, height])
                        assert snapshot(page)["data"]["sampleTime"] == held
                        assert json.loads(snapshot(page)["data"]["spawnRecords"]) == records
                        assert parity(page)["error"] == 0
                        values = page.evaluate(GPU, {**arguments, "mode": "actual"})
                        report["actual"].append({"viewport": [width, height], "shapes": [analyze_shape(row) for row in values["rows"]]})
                        save()
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    page.keyboard.press("Alt+Shift+P")
                    wait_state(page)
                    page.evaluate("""()=>{const canvas=document.getElementById('cream-material'),g=canvas.getContext('webgl2');
                      window.__spawnEvents=[];
                      for(const name of ['webglcontextlost','webglcontextrestored'])canvas.addEventListener(name,event=>
                        window.__spawnEvents.push({name,prevented:event.defaultPrevented,time:performance.now()}));
                      window.__spawnLoss=g.getExtension('WEBGL_lose_context');
                      const draw=g.drawArrays;g.drawArrays=function(...args){g.drawArrays=draw;
                        const result=draw.apply(g,args);window.__spawnLoss.loseContext();return result;};}""")
                    stopped(page, "context-lost")
                    page.evaluate("window.__spawnLoss.restoreContext()")
                    wait_state(page)
                    assert json.loads(snapshot(page)["data"]["spawnRecords"]) == records
                    assert parity(page)["error"] == 0
                    page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
                    page.wait_for_function("document.getElementById('notebook-dialog').open")
                    page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='false'")
                    assert snapshot(page)["native"] and not snapshot(page)["pointer"]
                    assert json.loads(snapshot(page)["data"]["spawnRecords"]) == records
                    assert parity(page)["error"] == 0
                    page.keyboard.press("Escape")
                    report["shape_retention_pause_resize_context_loss_viewer"] = True
                    report["context_events"] = page.evaluate("window.__spawnEvents")
                    report["context_loss_during_draw"] = True
                    assert not errors, errors
                    report["passed"] = True
                finally:
                    report["last_state"] = snapshot(page)
                    report["console"] = console
                    report["errors"] = errors
                    context.close()
            finally:
                browser.close()
    except Exception as error:
        report["error"] = repr(error)
        raise
    finally:
        save()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        parser.error("--output must remain under the repository private .local directory")
    result = run(args.url, output)
    print(json.dumps({"passed": result["passed"], "revision": result["revision"], "shapes": len(result["shapes"]),
                      "actual_viewports": len(result["actual"]), "report": str(output / "review.json")}))
