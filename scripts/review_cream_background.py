"""Numerical half-population, zero-peak and cross-parent grouping review; no image views."""

import argparse
import base64
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from review_cream_contact import HOLD, components, merge
from review_cream_effect import direct_url, new_context, snapshot, stopped, wait_state
from review_cream_liveness import parity


ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / ".local" / "smooth-grouping-20261011" / "before"
VIEWPORTS = [(320, 568), (390, 844), (667, 375), (768, 1024), (1024, 768), (1440, 1000), (1920, 1080)]

PROBE = r"""async options => {
  const root=document.getElementById('cream-effects'),revision=root.dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller,material]=await Promise.all([load('cream-model.mjs'),load('cream.mjs'),load('cream-material.mjs')]);
  const before=Function(options.before.replace(/\bexport\s+(?=const|function|async function)/g,'')
    .replaceAll('import.meta.url',JSON.stringify(location.href))+';return {createProductionRecipe,sampleProductionScene};')();
  const width=innerWidth,height=innerHeight,unit=Math.min(width,height),blend=unit*.04;
  const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl2',
    {alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent background GPU unavailable');
  const shaders=[],program=gl.createProgram(),buffer=gl.createBuffer();
  const populations=[],formations=[];
  try{
    const source=material.createCreamShaders({...model,MAX_PRIMITIVES:48});
    for(const [type,text] of [[gl.VERTEX_SHADER,source.vertex],[gl.FRAGMENT_SHADER,source.fragment]]){
      const shader=gl.createShader(type);shaders.push(shader);gl.shaderSource(shader,text);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));gl.attachShader(program,shader);
    }
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const uniform=name=>gl.getUniformLocation(program,name);
    gl.uniform2f(uniform('viewSize'),width,height);gl.uniform1f(uniform('headRadius'),model.cursorRadius(width,height));
    gl.uniform1i(uniform('trailCount'),0);gl.uniform4fv(uniform('trail[0]'),new Float32Array(32));
    gl.uniform1f(uniform('cursorTint'),0);gl.uniform4f(uniform('cursorShape'),0,1,0,0);
    const draw=(parts,crop)=>{
      const margin=unit*.06+24;
      const left=crop?Math.min(...parts.map(p=>p.x-p.radius))-margin:0,top=crop?Math.min(...parts.map(p=>p.y-p.radius))-margin:0;
      const w=crop?Math.max(...parts.map(p=>p.x+p.radius))+margin-left:width;
      const h=crop?Math.max(...parts.map(p=>p.y+p.radius))+margin-top:height;
      const ratio=Math.min(1,Math.sqrt((crop?1400000:1000000)/(w*h)));
      canvas.width=Math.ceil(w*ratio);canvas.height=Math.ceil(h*ratio);
      gl.viewport(0,0,canvas.width,canvas.height);gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
      gl.uniform2f(uniform('resolution'),canvas.width,canvas.height);gl.uniform1f(uniform('pixelRatio'),ratio);
      const packed=new Float32Array(48*4);
      parts.forEach((p,i)=>packed.set([p.x-left,p.y-top,p.radius,p.peak],i*4));
      gl.uniform4fv(uniform('scoops[0]'),packed);gl.uniform1i(uniform('scoopCount'),parts.length);
      gl.drawArrays(gl.TRIANGLES,0,3);
      const values=parts.map((p,i)=>{const v=gl.getUniform(program,uniform('scoops['+i+']'));
        return {...p,x:v[0],y:v[1],radius:v[2],peak:v[3]};});
      if(gl.getError()!==gl.NO_ERROR)throw new Error('Background probe GPU error');
      return {count:gl.getUniform(program,uniform('scoopCount')),parts:values,
        width:canvas.width,height:canvas.height,ratio,...(crop?{image:canvas.toDataURL()}: {})};
    };
    const add=(recipe,time,cohort,stage,actual=null)=>{
      const scene=actual||controller.sampleProductionScene(model,recipe,width,height,time);
      const world=scene.primitives.filter(p=>cohort.parents.includes(p.parent));
      formations.push({seed:recipe.seed,time,stage,parents:cohort.parents,
        kinds:cohort.parents.map(p=>recipe.clumps[p].kind),source:actual?'actual-upload':'production-sample',
        world,blend,...draw(world,true)});
    };
    if(options.mode==='actual'){
      const data={...root.dataset},recipe=controller.createProductionRecipe(model,Number(data.sceneSeed)),time=Number(data.sampleTime);
      const scene=controller.sampleProductionScene(model,recipe,width,height,time,JSON.parse(data.spawnRecords));
      const app=document.getElementById('cream-material').getContext('webgl2'),p=app.getParameter(app.CURRENT_PROGRAM);
      const actual={...scene,primitives:scene.primitives.map((part,i)=>{
        const v=app.getUniform(p,app.getUniformLocation(p,'scoops['+i+']'));
        return {...part,x:v[0],y:v[1],radius:v[2],peak:v[3]};})};
      add(recipe,time,{parents:options.parents},options.stage,actual);
    }else{
      for(let seed=0;seed<32;seed++){
        const recipe=controller.createProductionRecipe(model,seed),oldRecipe=before.createProductionRecipe(model,seed);
        const time=recipe.cohortMotion.duration*(seed%7)/7;
        const scene=controller.sampleProductionScene(model,recipe,width,height,time);
        const old=before.sampleProductionScene(model,oldRecipe,width,height,time),gpu=draw(scene.primitives,false);
        let radiusError=0;
        gpu.parts.forEach(p=>{const q=old.primitives.find(q=>q.parent===p.sourceParent&&q.lobe===p.lobe);
          if(!q)throw new Error('Missing stable source identity');radiusError=Math.max(radiusError,Math.abs(p.radius-Math.fround(q.radius)));});
        populations.push({seed,time,oldCount:old.ambientCount,newCount:scene.ambientCount,gpuCount:gpu.count,
          groups:recipe.groupCount,droplets:recipe.dropletCount,sourceParents:recipe.sourceParents,
          pieceIds:gpu.parts.map(p=>p.pieceId),peakMax:Math.max(...gpu.parts.map(p=>p.peak)),radiusError,
          participatingParents:recipe.cohortMotion.eligible,output:[gpu.width,gpu.height],ratio:gpu.ratio});
      }
      for(const seed of [0,4,17,31]){
        const recipe=controller.createProductionRecipe(model,seed);
        for(const index of (width===1440?[0,3,7]:[0])){
          const cycle=recipe.cohortMotion.cycles[index];
          const cohort=cycle.cohorts.find(c=>new Set(c.parents.map(p=>recipe.clumps[p].kind)).size>1)||cycle.cohorts[0];
          for(const [phase,stage] of [[cohort.start/2,'separated'],[(cohort.start+cohort.end)/2,'joined'],[(cohort.end+1)/2,'separated']])
            add(recipe,cycle.start+phase*cycle.period,cohort,stage);
        }
      }
    }
    return {revision,viewport:[width,height],populations,formations};
  }finally{
    gl.deleteBuffer(buffer);gl.deleteProgram(program);shaders.forEach(s=>gl.deleteShader(s));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""

PLAN = r"""async () => {
  const data=document.getElementById('cream-effects').dataset;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(data.revision),location.href).href);
  const [m,c]=await Promise.all([load('cream-model.mjs'),load('cream.mjs')]);
  const recipe=c.createProductionRecipe(m,Number(data.sceneSeed)),sample=Number(data.sampleTime),motion=recipe.cohortMotion;
  const offset=Math.floor(sample/motion.duration)*motion.duration;
  for(let i=0;i<motion.cycles.length;i++){
    const cycle=motion.cycles[i],options=cycle.cohorts.filter(co=>new Set(co.parents.map(p=>recipe.clumps[p].kind)).size>1);
    options.sort((a,b)=>{
      const cost=co=>{const scene=c.sampleProductionScene(m,recipe,innerWidth,innerHeight,offset+cycle.start+(co.start+co.end)/2*cycle.period);
        const p=scene.primitives.filter(p=>co.parents.includes(p.parent)&&p.lobe===0);
        const x=p.reduce((n,p)=>n+p.x,0)/p.length,y=p.reduce((n,p)=>n+p.y,0)/p.length;
        return Math.hypot(x-innerWidth*.2,y-innerHeight*.7);};
      return cost(a)-cost(b);
    });
    for(const co of options){
      const times=[cycle.start+co.start/2*cycle.period,cycle.start+(co.start+co.end)/2*cycle.period,cycle.start+(co.end+1)/2*cycle.period].map(t=>t+offset);
      if(times[0]>sample+.1)return {parents:co.parents,targets:times.map((time,i)=>({time,stage:i===1?'joined':'separated'}))};
    }
  }
  throw new Error('No upcoming real-time formation sequence');
}"""


def rgba(data):
    return np.array(Image.open(BytesIO(base64.b64decode(data.split(",", 1)[1]))).convert("RGBA"))


def scalar_fields(parts, x, y, blend):
    field = np.full(x.shape, 100000.0)
    parents = {}
    for p in parts:
        value = np.hypot(x-p["x"], y-p["y"])-p["radius"]
        field = merge(field, value, blend)
        parents[p["parent"]] = merge(parents.get(p["parent"], np.full(x.shape, 100000.0)), value, blend)
    return field, np.minimum.reduce(list(parents.values()))


def analyze(row):
    image = rgba(row.pop("image"))
    y, x = np.indices(image.shape[:2], dtype=float)
    x, y = (x+.5)/row["ratio"], (y+.5)/row["ratio"]
    field, separate = scalar_fields(row["parts"], x, y, row["blend"])
    mask = image[:, :, 3] >= 128
    stable = np.abs(field) > 1.5/row["ratio"]
    mismatches = int(np.count_nonzero(stable & (mask != (field <= 0))))
    sizes = components(mask)
    bridge = int(np.count_nonzero(mask & (field < -.3) & (separate > .15)))
    row["metrics"] = {"components": len(sizes), "opaque_pixels": int(mask.sum()), "bridge_pixels": bridge,
                      "stable_scalar_samples": int(stable.sum()), "scalar_mismatches": mismatches,
                      "peak_max": max(p["peak"] for p in row["parts"]),
                      "piece_ids": [p["pieceId"] for p in row["parts"]]}
    assert mismatches == 0 and row["metrics"]["peak_max"] == 0, row
    if row["stage"] == "joined":
        assert len(sizes) == 1 and bridge > 0, row
    else:
        assert len(sizes) >= len(row["parents"]), row
    return row


def page_bridge(page, row, output):
    actual = page.screenshot()
    try:
        page.evaluate("document.getElementById('cream-material').style.visibility='hidden'")
        baseline = page.screenshot()
    finally:
        page.evaluate("document.getElementById('cream-material').style.removeProperty('visibility')")
    a = np.array(Image.open(BytesIO(actual)).convert("RGB")).astype(int)
    b = np.array(Image.open(BytesIO(baseline)).convert("RGB")).astype(int)
    y, x = np.indices(a.shape[:2], dtype=float)
    field, separate = scalar_fields(row["world"], x+.5, y+.5, row["blend"])
    bridge = (field < -.3) & (separate > .15)
    changed = np.max(np.abs(a-b), axis=2)
    visible = int(np.count_nonzero(bridge & (changed >= 3)))
    (output / "actual-joined.png").write_bytes(actual)
    (output / "same-page-without-material.png").write_bytes(baseline)
    assert visible >= 20, {"visible": visible, "bridge_candidates": int(bridge.sum())}
    return {"visible_bridge_pixels": visible, "bridge_candidates": int(bridge.sum()), "channel_threshold": 3,
            "actual_sha256": sha256(actual).hexdigest(), "without_material_sha256": sha256(baseline).hexdigest(),
            "comparison": "Actual held runtime pose through the existing page glass versus the same page with only its material canvas hidden."}


def run(url, output):
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "review.json"
    assert not destination.exists()
    report = {"passed": False, "url": url, "viewports": [], "actual_cycle": [], "image_tool_views": 0, "visual_approval": False}
    arguments = {"before": (BEFORE / "cream.mjs").read_text(encoding="utf-8"), "mode": "synthetic"}
    save = lambda: destination.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            try:
                context, page, errors = new_context(browser)
                context.add_init_script(HOLD)
                try:
                    page.goto(direct_url(url), wait_until="networkidle")
                    wait_state(page)
                    page.keyboard.press("Alt+Shift+P")
                    stopped(page, "paused", visible=True)
                    for width, height in VIEWPORTS:
                        page.set_viewport_size({"width": width, "height": height})
                        page.wait_for_function("([w,h])=>Number(document.getElementById('cream-effects').dataset.viewportWidth)===w&&Number(document.getElementById('cream-effects').dataset.viewportHeight)===h", arg=[width, height])
                        value = page.evaluate(PROBE, arguments)
                        report["revision"] = value["revision"]
                        report["viewports"].append(value)
                        for row in value["populations"]:
                            assert row["gpuCount"] == row["newCount"] == (row["oldCount"]+1)//2, row
                            assert row["peakMax"] == row["radiusError"] == 0, row
                            assert len(set(row["pieceIds"])) == row["newCount"]
                        value["formations"] = [analyze(row) for row in value["formations"]]
                        save()
                        assert parity(page)["error"] == 0
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===1440")
                    page.keyboard.press("Alt+Shift+P")
                    wait_state(page)
                    plan = page.evaluate(PLAN)
                    report["actual_plan"] = plan
                    for target in plan["targets"]:
                        page.wait_for_function("time=>Number(document.getElementById('cream-effects').dataset.sampleTime)>=time",
                                               arg=target["time"], timeout=45000)
                        page.evaluate("window.__contactReviewHold=true")
                        try:
                            value = page.evaluate(PROBE, {**arguments, "mode": "actual", "parents": plan["parents"], "stage": target["stage"]})
                            row = analyze(value["formations"][0])
                            report["actual_cycle"].append(row)
                            if target["stage"] == "joined":
                                report["actual_page"] = page_bridge(page, row, output)
                            assert parity(page)["error"] == 0
                        finally:
                            page.evaluate("window.__releaseContactReview()")
                        save()
                        if target["stage"] == "joined":
                            page.keyboard.press("Alt+Shift+P")
                            stopped(page, "paused", visible=True)
                            held = snapshot(page)["data"]["sampleTime"]
                            page.set_viewport_size({"width": 390, "height": 844})
                            page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===390")
                            value = page.evaluate(PROBE, {**arguments, "mode": "actual", "parents": plan["parents"], "stage": "joined"})
                            report["paused_joined_resize"] = analyze(value["formations"][0])
                            assert snapshot(page)["data"]["sampleTime"] == held and parity(page)["error"] == 0
                            page.set_viewport_size({"width": 1440, "height": 1000})
                            page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===1440")
                            page.keyboard.press("Alt+Shift+P")
                            wait_state(page)
                    assert not errors, errors
                    report["passed"] = True
                finally:
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
        parser.error("--output must be a private .local directory")
    result = run(args.url, output)
    print(json.dumps({"passed": result["passed"], "revision": result["revision"],
                      "population_cases": sum(len(v["populations"]) for v in result["viewports"]),
                      "formation_cases": sum(len(v["formations"]) for v in result["viewports"]),
                      "report": str(output / "review.json")}))
