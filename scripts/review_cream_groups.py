"""Numerical production group separation, rejoining and protected non-group review; no image views."""

import argparse
import hashlib
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
  const before=Function(options.before.replace(/\bexport\s+(?=const|function|async function)/g,'')
    .replaceAll('import.meta.url',JSON.stringify(location.href))+';return {createProductionRecipe,sampleProductionScene};')();
  const width=innerWidth,height=innerHeight,unit=Math.min(width,height),blend=unit*.04;
  const data={...root.dataset},appRecipe=controller.createProductionRecipe(model,Number(data.sceneSeed));
  const appScene=controller.sampleProductionScene(model,appRecipe,width,height,Number(data.sampleTime),JSON.parse(data.spawnRecords));
  const appGL=document.getElementById('cream-material').getContext('webgl2'),appProgram=appGL.getParameter(appGL.CURRENT_PROGRAM);
  const uploaded=appScene.primitives.map((p,i)=>{
    const v=appGL.getUniform(appProgram,appGL.getUniformLocation(appProgram,'scoops['+i+']'));
    return {...p,x:v[0],y:v[1],radius:v[2],peak:v[3]};
  });
  const previous=before.sampleProductionScene(model,before.createProductionRecipe(model,Number(data.sceneSeed)),
    width,height,Number(data.sampleTime),JSON.parse(data.spawnRecords));
  let nonGroupByteDifferences=0,nonGroupPrimitives=0;
  uploaded.forEach((p,i)=>{
    if(appRecipe.clumps[p.parent]?.kind==='group')return;
    const q=previous.primitives.find(q=>p.spawnId?q.spawnId===p.spawnId:q.parent===p.sourceParent&&q.lobe===p.lobe);
    const expected=new Float32Array([q.x,q.y,q.radius*(p.spawnId ? .5 : 1),0]);
    nonGroupPrimitives++;
    [p.x,p.y,p.radius,p.peak].forEach((value,index)=>{if((p.spawnId||index>=2)&&value!==expected[index])nonGroupByteDifferences++;});
  });
  const compactMetadata=(recipe,parent,time)=>{
    const motion=recipe.groupMotions[parent],group=recipe.clumps[parent];
    const base=controller.sampleProductionScoops(model,recipe,width,height,time)[parent];
    return {canonicalUnitBounds:[0,1].map(axis=>Math.max(...motion.lobes.map(p=>p[axis]+p[2]))-Math.min(...motion.lobes.map(p=>p[axis]-p[2]))),
      primaryRadiusFraction:motion.lobes[0][2],geometryMultiplier:motion.geometryMultiplier,
      expectedGeometryMultiplier:group.radius>=.14?2/3:4/3,
      previousCanonicalRadii:motion.lobes.map(p=>p[2]*base.radius*2)};
  };
  const cases=[];
  if(options.mode==='actual'){
    const parent=options.parent,motion=appRecipe.groupMotions[parent],state=controller.sampleGroupMotion(motion,Number(data.sampleTime));
    cases.push({seed:Number(data.sceneSeed),parent,profile:appRecipe.clumps[parent].clump,source:'actual-upload',
      time:Number(data.sampleTime),stage:state.stage,cycle:state.cycle,amount:state.amount,
      primitives:uploaded.filter(p=>p.parent===parent),members:motion.lobes.length,...compactMetadata(appRecipe,parent,Number(data.sampleTime))});
  }else{
    const chosen=new Map();
    for(let seed=0;seed<32;seed++){
      const recipe=controller.createProductionRecipe(model,seed);
      recipe.clumps.forEach((group,parent)=>{
        if(group.kind!=='group')return;
        const size=group.radius>=.24?'largest':group.radius>=.14?'large':'small',key=group.clump+'/'+size;
        if(!chosen.has(key))chosen.set(key,{seed,parent,size,recipe});
      });
      if(chosen.size===18)break;
    }
    if(chosen.size!==18)throw new Error('Every profile/size category must be represented');
    for(const {seed,parent,size,recipe} of chosen.values()){
      const motion=recipe.groupMotions[parent],cycleIndices=width===1440?[0,3,7]:[0];
      for(const index of cycleIndices){
        const cycle=motion.cycles[index],ramp=(1-cycle.joined-cycle.held)/2;
        const next=motion.cycles[(index+1)%motion.cycles.length];
        const times=[
          [cycle.start+cycle.period*cycle.joined/2-motion.offset+motion.duration,'joined'],
          [cycle.start+cycle.period*(cycle.joined+ramp+cycle.held/2)-motion.offset+motion.duration,'separated'],
          [next.start+next.period*next.joined/2-motion.offset+motion.duration*(index===motion.cycles.length-1?2:1),'joined']
        ];
        for(const [requestedTime,stage] of times){
          let time=requestedTime,found=false;
          for(let repeat=0;repeat<100;repeat++){
            const state=controller.sampleCohortMotion(recipe.cohortMotion,time);
            if(!state.cohorts.some(c=>c.parents.includes(parent)&&c.amount>0)){found=true;break;}
            time+=motion.duration;
          }
          if(!found)throw new Error('No unjoined cohort interval for independent internal-group proof');
          const scene=controller.sampleProductionScene(model,recipe,width,height,time);
          const state=controller.sampleGroupMotion(motion,time);
          if(state.stage!==stage)throw new Error('Review sample is not in its intended group stage');
          cases.push({seed,parent,size,profile:recipe.clumps[parent].clump,source:'production-sample',
            time,stage,cycle:state.cycle,amount:state.amount,cohort_amount:0,
            primitives:scene.primitives.filter(p=>p.parent===parent),members:motion.lobes.length,...compactMetadata(recipe,parent,time)});
        }
      }
    }
  }
  const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl2',
    {alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent group GPU probe unavailable');
  const sources=material.createCreamShaders({...model,MAX_PRIMITIVES:controller.CREAM_MAX_PRIMITIVES});
  const program=gl.createProgram(),buffer=gl.createBuffer(),shaders=[];
  const rows=[];
  try{
    for(const [kind,source] of [[gl.VERTEX_SHADER,sources.vertex],[gl.FRAGMENT_SHADER,sources.fragment]]){
      const shader=gl.createShader(kind);shaders.push(shader);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const uniform=name=>gl.getUniformLocation(program,name);
    gl.uniform2f(uniform('viewSize'),width,height);gl.uniform1f(uniform('headRadius'),model.cursorRadius(width,height));
    gl.uniform1i(uniform('trailCount'),0);gl.uniform4fv(uniform('trail[0]'),new Float32Array(32));
    gl.uniform1f(uniform('cursorTint'),0);gl.uniform4f(uniform('cursorShape'),0,1,0,0);
    for(const item of cases){
      const parts=item.primitives,margin=unit*.08+24;
      const left=Math.min(...parts.map(p=>p.x-p.radius))-margin,top=Math.min(...parts.map(p=>p.y-p.radius))-margin;
      const extentWidth=Math.max(...parts.map(p=>p.x+p.radius))+margin-left;
      const extentHeight=Math.max(...parts.map(p=>p.y+p.radius))+margin-top;
      const ratio=Math.min(1,Math.sqrt(1400000/(extentWidth*extentHeight)));
      canvas.width=Math.ceil(extentWidth*ratio);canvas.height=Math.ceil(extentHeight*ratio);
      gl.viewport(0,0,canvas.width,canvas.height);gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
      gl.uniform2f(uniform('resolution'),canvas.width,canvas.height);gl.uniform1f(uniform('pixelRatio'),ratio);
      const packed=new Float32Array(controller.CREAM_MAX_PRIMITIVES*4);
      parts.forEach((p,i)=>packed.set([p.x-left,p.y-top,p.radius,p.peak],i*4));
      gl.uniform4fv(uniform('scoops[0]'),packed);gl.uniform1i(uniform('scoopCount'),parts.length);
      gl.drawArrays(gl.TRIANGLES,0,3);
      const w=canvas.width,h=canvas.height,bytes=new Uint8Array(w*h*4);
      gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
      if(gl.getError()!==gl.NO_ERROR)throw new Error('Group GPU rendering failed');
      const mask=new Uint8Array(w*h),queue=new Int32Array(w*h);
      let opaque=0,borderAlpha=0,mismatches=0,stableSamples=0,minX=w,maxX=-1,minY=h,maxY=-1;
      for(let y=0;y<h;y++)for(let x=0;x<w;x++){
        const index=y*w+x,alpha=bytes[index*4+3];
        if(alpha>=128){mask[index]=1;opaque++;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
        if(x===0||y===0||x===w-1||y===h-1)borderAlpha=Math.max(borderAlpha,alpha);
        if(x%4===0&&y%4===0){
          const px=(x+.5)/ratio,py=(h-y-.5)/ratio;
          let d=100000;
          for(let i=0;i<parts.length;i++)d=model.smoothUnion(d,Math.hypot(px-packed[i*4],py-packed[i*4+1])-packed[i*4+2],blend);
          if(Math.abs(d)>1.5/ratio){stableSamples++;if((d<=0)!==(alpha>=128))mismatches++;}
        }
      }
      const sizes=[];
      for(let index=0;index<mask.length;index++){
        if(!mask[index])continue;
        let head=0,tail=1,size=0;queue[0]=index;mask[index]=0;
        while(head<tail){
          const p=queue[head++],x=p%w;size++;
          for(const q of [x>0?p-1:-1,x<w-1?p+1:-1,p-w,p+w]){
            if(q>=0&&q<mask.length&&mask[q]){mask[q]=0;queue[tail++]=q;}
          }
        }
        sizes.push(size);
      }
      sizes.sort((a,b)=>b-a);
      const expectedAreas=parts.map(p=>Math.PI*(p.radius*ratio)**2).sort((a,b)=>b-a);
      let gap=Infinity;
      for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++)
        gap=Math.min(gap,Math.hypot(parts[i].x-parts[j].x,parts[i].y-parts[j].y)-parts[i].radius-parts[j].radius);
      const {primitives,...metadata}=item;
      const previousCanonicalBounds=item.canonicalUnitBounds.map(value=>value*item.previousCanonicalRadii[0]/item.primaryRadiusFraction);
      const silhouetteBounds=[(maxX-minX+1)/ratio,(maxY-minY+1)/ratio];
      const uploadedRadiusRatios=parts.map((p,i)=>gl.getUniform(program,uniform('scoops['+i+']'))[2]/item.previousCanonicalRadii[i]);
      rows.push({...metadata,component_count:sizes.length,component_pixels:sizes,opaque_pixels:opaque,
        uploaded_piece_radius_ratios_to_live_canonical:uploadedRadiusRatios,
        opaque_silhouette_dimensions_css:silhouetteBounds,previous_canonical_circle_bounds_css:previousCanonicalBounds,
        silhouette_over_previous_canonical_circle_bounds:silhouetteBounds.map((value,axis)=>value/previousCanonicalBounds[axis]),
        separated_area_ratios:item.stage==='separated'?sizes.map((size,i)=>size/expectedAreas[i]):[],
        minimum_gap:gap,smooth_union_width:blend,stable_scalar_samples:stableSamples,
        stable_scalar_mismatches:mismatches,border_maximum_alpha:borderAlpha,
        probe_output:[w,h],probe_ratio:ratio});
    }
  }finally{
    gl.deleteBuffer(buffer);gl.deleteProgram(program);shaders.forEach(shader=>gl.deleteShader(shader));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
  return {revision,viewport:[width,height],groupScale:Number(data.groupGeometryMultiplier),largeGroupScale:Number(data.largeGroupGeometryMultiplier),sampleTime:Number(data.sampleTime),spawn_count:Number(data.spawnCount),
    non_group_reference:'Retained individual radii match source identities; their translations and peaks intentionally changed in86. Spawn coordinates/peak unchanged and radius half the pre-shape circle.',
    expected_non_group_primitives:appRecipe.dropletCount+Number(data.spawnCount),
    non_group_primitives:nonGroupPrimitives,non_group_uploaded_float_differences:nonGroupByteDifferences,rows};
}"""

PLAN = r"""async () => {
  const data=document.getElementById('cream-effects').dataset;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(data.revision),location.href).href);
  const [model,controller]=await Promise.all([load('cream-model.mjs'),load('cream.mjs')]);
  const recipe=controller.createProductionRecipe(model,Number(data.sceneSeed)),sample=Number(data.sampleTime);
  const parent=recipe.edgeGroups.find(e=>model.CLUMP_PROFILES[recipe.clumps[e.parent].clump].length===3)?.parent??recipe.edgeGroups[0].parent;
  const motion=recipe.groupMotions[parent],state=controller.sampleGroupMotion(motion,sample);
  let index=state.cycle,table=Math.floor((sample+motion.offset)/motion.duration);
  if(state.stage!=='joined'){index++;if(index===motion.cycles.length){index=0;table++;}}
  const cycle=motion.cycles[index],next=motion.cycles[(index+1)%motion.cycles.length],ramp=(1-cycle.joined-cycle.held)/2;
  const joined=table*motion.duration+cycle.start+cycle.period*cycle.joined/2-motion.offset;
  const separated=table*motion.duration+cycle.start+cycle.period*(cycle.joined+ramp+cycle.held/2)-motion.offset;
  const rejoined=(table+(index===motion.cycles.length-1?1:0))*motion.duration+
    next.start+next.period*next.joined/2-motion.offset;
  return {parent,targets:[{time:Math.max(sample,joined),stage:'joined'},{time:separated,stage:'separated'},{time:rejoined,stage:'joined'}]};
}"""


def validate(value):
    assert value["groupScale"] == 4/3
    assert value["largeGroupScale"] == 2/3
    assert value["non_group_primitives"] == value["expected_non_group_primitives"]
    assert value["non_group_uploaded_float_differences"] == 0
    for row in value["rows"]:
        expected = row["members"] if row["stage"] == "separated" else 1
        assert row["component_count"] == expected, row
        assert row["stable_scalar_mismatches"] == 0, row
        assert row["border_maximum_alpha"] <= 1, row
        assert row["geometryMultiplier"] == row["expectedGeometryMultiplier"], row
        assert all(abs(ratio-row["expectedGeometryMultiplier"]/2) < 1e-6 for ratio in row["uploaded_piece_radius_ratios_to_live_canonical"]), row
        if row["stage"] == "separated":
            assert row["minimum_gap"] > row["smooth_union_width"], row
            assert all(.9 < ratio < 1.1 for ratio in row["separated_area_ratios"]), row


def run(url, output, actual_only=False):
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "review.json"
    assert not destination.exists()
    before = (ROOT / ".local" / "group-motion-20261011" / "before" / "cream.mjs").read_bytes()
    report = {"url": url, "passed": False, "image_tool_views": 0, "visual_approval": False,
              "mode": "actual-only" if actual_only else "exhaustive",
              "before_controller_sha256": hashlib.sha256(before).hexdigest(), "viewports": [], "actual_cycle": []}
    arguments = {"before": before.decode("utf-8"), "mode": "synthetic"}
    save = lambda: destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
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
                    for width, height in ([] if actual_only else VIEWPORTS):
                        page.set_viewport_size({"width": width, "height": height})
                        page.wait_for_function("([w,h])=>Number(document.getElementById('cream-effects').dataset.viewportWidth)===w&&Number(document.getElementById('cream-effects').dataset.viewportHeight)===h", arg=[width, height])
                        value = page.evaluate(PROBE, arguments)
                        report["revision"] = value["revision"]
                        report["viewports"].append(value)
                        save()
                        validate(value)
                        assert parity(page)["error"] == 0
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===1440")
                    page.keyboard.press("Alt+Shift+P")
                    wait_state(page)
                    for _ in range(8):
                        page.locator("h1").click()
                    page.wait_for_function("JSON.parse(document.getElementById('cream-effects').dataset.spawnRecords).at(-1)?.id===8")
                    page.evaluate("document.documentElement.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}))")
                    page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='false'")
                    plan = page.evaluate(PLAN)
                    for target in plan["targets"]:
                        page.wait_for_function("t=>Number(document.getElementById('cream-effects').dataset.sampleTime)>=t", arg=target["time"], timeout=40000)
                        value = page.evaluate(PROBE, {**arguments, "mode": "actual", "parent": plan["parent"]})
                        report["revision"] = value["revision"]
                        report["actual_cycle"].append(value)
                        save()
                        assert value["rows"][0]["stage"] == target["stage"]
                        assert value["spawn_count"] == 8
                        validate(value)
                        assert parity(page)["error"] == 0
                        if target["stage"] == "separated":
                            page.keyboard.press("Alt+Shift+P")
                            stopped(page, "paused", visible=True)
                            held_time = snapshot(page)["data"]["sampleTime"]
                            page.set_viewport_size({"width": 390, "height": 844})
                            page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===390")
                            resized = page.evaluate(PROBE, {**arguments, "mode": "actual", "parent": plan["parent"]})
                            report["separated_paused_resize"] = resized
                            assert snapshot(page)["data"]["sampleTime"] == held_time
                            assert resized["rows"][0]["stage"] == "separated"
                            assert resized["spawn_count"] == 8
                            validate(resized)
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
    parser.add_argument("--actual-only", action="store_true", help="Verify actual uploaded split/rejoin and paused resize without repeating unchanged exhaustive group cases.")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        parser.error("--output must be under this repository's private .local directory")
    result = run(args.url, output, actual_only=args.actual_only)
    print(json.dumps({"passed": result["passed"], "revision": result["revision"],
                      "gpu_cases": sum(len(case["rows"]) for case in result["viewports"]),
                      "report": str(output / "review.json")}))
