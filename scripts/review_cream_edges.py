"""Measure isolated large-group edge pixels, full envelopes and clear central space; no image views."""

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright
from review_cream_effect import direct_url, new_context, snapshot, stopped, wait_state
from review_cream_liveness import parity


ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(320, 568), (390, 844), (667, 375), (768, 1024), (1024, 768), (1440, 1000), (1920, 1080)]

PROBE = r"""async options => {
  const root=document.getElementById('cream-effects'),revision=root.dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller,material]=await Promise.all([load('cream-model.mjs'),load('cream.mjs'),load('cream-material.mjs')]);
  const width=innerWidth,height=innerHeight,output=controller.creamOutputSize(width,height,devicePixelRatio);
  const canvas=document.createElement('canvas');canvas.width=output.width;canvas.height=output.height;
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent edge GPU probe unavailable');
  const sources=material.createCreamShaders({...model,MAX_PRIMITIVES:controller.CREAM_MAX_PRIMITIVES});
  const program=gl.createProgram(),buffer=gl.createBuffer(),shaders=[];
  try{
    for(const [kind,source] of [[gl.VERTEX_SHADER,sources.vertex],[gl.FRAGMENT_SHADER,sources.fragment]]){
      const shader=gl.createShader(kind);shaders.push(shader);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);gl.viewport(0,0,canvas.width,canvas.height);
    gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const uniform=name=>gl.getUniformLocation(program,name);
    gl.uniform2f(uniform('resolution'),canvas.width,canvas.height);
    gl.uniform2f(uniform('viewSize'),width,height);gl.uniform1f(uniform('pixelRatio'),output.ratio);
    gl.uniform1f(uniform('headRadius'),model.cursorRadius(width,height));gl.uniform1i(uniform('trailCount'),0);
    gl.uniform4fv(uniform('trail[0]'),new Float32Array(32));
    gl.uniform1f(uniform('cursorTint'),0);gl.uniform4f(uniform('cursorShape'),0,1,0,0);
    const bytes=new Uint8Array(canvas.width*canvas.height*4);
    const render=(primitives,layout)=>{
      const data=new Float32Array(controller.CREAM_MAX_PRIMITIVES*4);
      primitives.forEach((p,i)=>data.set([p.x,p.y,p.radius,p.peak],i*4));
      gl.uniform1i(uniform('scoopCount'),primitives.length);gl.uniform4fv(uniform('scoops[0]'),data);
      gl.drawArrays(gl.TRIANGLES,0,3);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
      if(gl.getError()!==gl.NO_ERROR)throw new Error('Large-group edge rendering failed');
      let visible=0,opaque=0,left=0,right=0,center=0,centerMaxAlpha=0,leftIntrusion=0,rightIntrusion=0;
      for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++){
        const alpha=bytes[(y*canvas.width+x)*4+3],cssX=(x+.5)/output.ratio;
        if(cssX>layout.leftLimit&&cssX<layout.rightLimit){
          centerMaxAlpha=Math.max(centerMaxAlpha,alpha);if(alpha>=2)center++;
        }
        if(alpha<2)continue;
        visible++;if(alpha>=128)opaque++;
        if(cssX<width/2){left++;leftIntrusion=Math.max(leftIntrusion,cssX-layout.glassLeft);}
        else{right++;rightIntrusion=Math.max(rightIntrusion,layout.glassRight-cssX);}
      }
      return {visibleEdgePixels:visible,opaqueEdgePixels:opaque,leftVisiblePixels:left,rightVisiblePixels:right,
        centerVisiblePixels:center,centerMaxAlpha,leftIntrusion,rightIntrusion,alphaThreshold:2};
    };
    const rows=[];
    for(const seed of (options?.actualOnly?[4]:[4,7,17,52])){
      const recipe=controller.createProductionRecipe(model,seed),layout=controller.productionEdgeLayout(model,recipe,width,height);
      const large=new Set(recipe.edgeGroups.map(g=>g.parent));
      const parts=time=>controller.sampleProductionScene(model,recipe,width,height,time).primitives.filter(p=>large.has(p.parent));
      // In addition to regular phases, explicitly measure the most visible body pose in a broad motion cycle.
      let peakTime=0,peakVisibility=-Infinity;
      for(let time=0;time<=360;time+=2){
        const primitives=parts(time);
        const visible=Math.max(...primitives.map(p=>recipe.edgeGroups.find(g=>g.parent===p.parent).side==='left'
          ? p.x+p.radius : width-(p.x-p.radius)));
        if(visible>peakVisibility){peakVisibility=visible;peakTime=time;}
      }
      const cyclePeaks=recipe.edgeGroups.flatMap(({parent})=>{
        const motion=recipe.groupMotions[parent];
        return motion.cycles.map(cycle=>cycle.start+cycle.period*(1+cycle.joined)/2-motion.offset);
      });
      for(const time of (options?.actualOnly?[peakTime]:[...new Set([0,3,8,16,24,36,60,90,120,peakTime,...cyclePeaks])])){
        const primitives=parts(time),metrics=render(primitives,layout);
        rows.push({source:'sampled',seed,time,visibilityPeakSample:time===peakTime,layout,
          groupPhases:recipe.edgeGroups.map(({parent})=>{
            const state=controller.sampleGroupMotion(recipe.groupMotions[parent],time);
            return {parent,cycle:state.cycle,stage:state.stage,amount:state.amount};
          }),primitiveCount:primitives.length,...metrics});
      }
    }
    // Re-render the actual uploaded large primitives as well, not only independently sampled recipes.
    const data={...root.dataset},recipe=controller.createProductionRecipe(model,Number(data.sceneSeed));
    const layout=controller.productionEdgeLayout(model,recipe,width,height);
    const full=controller.sampleProductionScene(model,recipe,width,height,Number(data.sampleTime),JSON.parse(data.spawnRecords));
    const appGL=document.getElementById('cream-material').getContext('webgl2'),appProgram=appGL.getParameter(appGL.CURRENT_PROGRAM);
    const actual=full.primitives.flatMap((p,i)=>{
      if(!recipe.edgeGroups.some(g=>g.parent===p.parent))return [];
      const values=appGL.getUniform(appProgram,appGL.getUniformLocation(appProgram,'scoops['+i+']'));
      return [{...p,x:values[0],y:values[1],radius:values[2],peak:values[3]}];
    });
    rows.push({source:'actual-upload',seed:Number(data.sceneSeed),time:Number(data.sampleTime),layout,
      primitiveCount:actual.length,...render(actual,layout)});
    return {revision,viewport:[width,height],output,rows};
  }finally{
    gl.deleteBuffer(buffer);gl.deleteProgram(program);shaders.forEach(shader=>gl.deleteShader(shader));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""


def run(url, output, actual_only=False):
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "review.json"
    report = {"url": url, "passed": False, "image_tool_views": 0, "visual_approval": False,
              "mode": "actual-and-visibility-peak" if actual_only else "exhaustive", "cases": []}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context, page, errors = new_context(browser)
                try:
                    page.goto(direct_url(url), wait_until="networkidle")
                    wait_state(page)
                    page.keyboard.press("Alt+Shift+P")
                    stopped(page, "paused", visible=True)
                    held_time = snapshot(page)["data"]["motionTime"]
                    for width, height in VIEWPORTS:
                        page.set_viewport_size({"width": width, "height": height})
                        page.wait_for_function("([w,h])=>Number(document.getElementById('cream-effects').dataset.viewportWidth)===w&&Number(document.getElementById('cream-effects').dataset.viewportHeight)===h", arg=[width, height])
                        assert snapshot(page)["data"]["motionTime"] == held_time
                        assert int(snapshot(page)["data"]["largeGroupCount"]) == 2
                        value = page.evaluate(PROBE, {"actualOnly": actual_only})
                        report["revision"] = value["revision"]
                        report["cases"].append(value)
                        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
                        for row in value["rows"]:
                            assert row["centerVisiblePixels"] == 0 and row["centerMaxAlpha"] <= 1, row
                            assert row["leftIntrusion"] <= row["layout"]["intrusion"] + .001, row
                            assert row["rightIntrusion"] <= row["layout"]["intrusion"] + .001, row
                            assert [g["side"] for g in row["layout"]["groups"]] == ["left", "right"]
                        for seed in ([] if actual_only else [4, 7, 17, 52]):
                            rows = [row for row in value["rows"] if row["source"] == "sampled" and row["seed"] == seed]
                            assert sum(row["visibleEdgePixels"] for row in rows) > 0, (value["viewport"], seed, rows)
                            assert sum(row["opaqueEdgePixels"] for row in rows) > 0, (value["viewport"], seed, rows)
                        if actual_only:
                            assert sum(row["visibleEdgePixels"] for row in value["rows"]) > 0
                            assert sum(row["opaqueEdgePixels"] for row in value["rows"]) > 0
                        assert parity(page)["error"] == 0
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
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--actual-only", action="store_true", help="Check actual uploaded edges plus each viewport's seed-four visibility peak without repeating exhaustive endpoints.")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        parser.error("--output must be under this repository's private .local directory")
    result = run(args.url, output, actual_only=args.actual_only)
    print(json.dumps({"passed": result["passed"], "revision": result["revision"],
                      "viewports": len(result["cases"]), "report": str(output / "review.json")}))
