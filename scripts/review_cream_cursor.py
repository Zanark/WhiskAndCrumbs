"""Numerical living-cursor GPU review; no image-tool views or visual-approval claims."""

import argparse
import base64
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from review_cream_effect import direct_url, new_context, snapshot, stopped, wait_state


ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / ".local" / "interactive-cream-20261011" / "before-contact" / "cream-material.mjs"

CAPTURE = r"""() => {
  const canvas=document.getElementById('cream-cursor'),root=document.getElementById('cream-effects');
  const box=canvas.getBoundingClientRect();
  const gl=document.getElementById('cream-material').getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM);
  return {image:canvas.toDataURL(),width:canvas.width,height:canvas.height,left:box.left,top:box.top,
    cssWidth:box.width,cssHeight:box.height,hidden:canvas.hidden,data:{...root.dataset},
    pointerInputAge:window.__cursorReviewLastMove===undefined?null:performance.now()-window.__cursorReviewLastMove,
    trail:Array.from({length:8},(_,i)=>Array.from(gl.getUniform(program,gl.getUniformLocation(program,'trail['+i+']')))),
    native:!document.body.classList.contains('cream-cursor-active')};
}"""

GPU = r"""async beforeSource => {
  const revision=document.getElementById('cream-effects').dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,material,controller]=await Promise.all([load('cream-model.mjs'),load('cream-material.mjs'),load('cream.mjs')]);
  const specification={...model,MAX_PRIMITIVES:controller.CREAM_MAX_PRIMITIVES};
  const old=Function('model',beforeSource.replace('export function createCreamShaders','function createCreamShaders')+
    ';return createCreamShaders(model);')(specification),current=material.createCreamShaders(specification);
  const canvas=document.createElement('canvas');
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,antialias:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent WebGL2 A/B probe is unavailable');
  const programs=[],shaders=[],buffer=gl.createBuffer();
  const compile=sources=>{
    const program=gl.createProgram();programs.push(program);
    for(const [type,source] of [[gl.VERTEX_SHADER,sources.vertex],[gl.FRAGMENT_SHADER,sources.fragment]]){
      const shader=gl.createShader(type);shaders.push(shader);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    return program;
  };
  const pixels=(program,{w,h,viewW,viewH,ratio=1,primitives,shape=[0,1,0,0],tint=0,trail=[]})=>{
    canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);gl.useProgram(program);
    gl.disable(gl.BLEND);gl.disable(gl.DEPTH_TEST);gl.disable(gl.SCISSOR_TEST);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const loc=name=>gl.getUniformLocation(program,name),data=new Float32Array(controller.CREAM_MAX_PRIMITIVES*4);
    primitives.forEach((p,i)=>data.set([p.x,p.y,p.radius,p.peak],i*4));
    gl.uniform2f(loc('resolution'),w,h);gl.uniform2f(loc('viewSize'),viewW,viewH);gl.uniform1f(loc('pixelRatio'),ratio);
    gl.uniform1i(loc('scoopCount'),primitives.length);gl.uniform4fv(loc('scoops[0]'),data);
    gl.uniform1f(loc('headRadius'),model.cursorRadius(viewW,viewH));gl.uniform1f(loc('cursorTint'),tint);
    gl.uniform1i(loc('strawberryStart'),-1);
    const trailData=new Float32Array(model.TRAIL_PROFILE.links*4);
    trail.forEach((segment,i)=>trailData.set(segment,i*4));
    gl.uniform4fv(loc('trail[0]'),trailData);gl.uniform1i(loc('trailCount'),trail.length);
    const shapeLocation=loc('cursorShape');if(shapeLocation)gl.uniform4f(shapeLocation,...shape);
    gl.drawArrays(gl.TRIANGLES,0,3);
    const bytes=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
    if(gl.getError()!==gl.NO_ERROR)throw new Error('GPU comparison rendering failed');
    return bytes;
  };
  const png=(bytes,w,h)=>{
    const copy=document.createElement('canvas');copy.width=w;copy.height=h;const ctx=copy.getContext('2d');
    const image=ctx.createImageData(w,h);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const source=((h-y-1)*w+x)*4,target=(y*w+x)*4,alpha=bytes[source+3];
      for(let c=0;c<3;c++)image.data[target+c]=alpha?Math.min(255,Math.round(bytes[source+c]*255/alpha)):0;
      image.data[target+3]=alpha;
    }
    ctx.putImageData(image,0,0);return copy.toDataURL();
  };
  const result={ambient:[],shapes:[],crop:[],cursorMaterial:[],trailLength:{},beforeSourceLength:beforeSource.length,revision};
  try{
    const first=compile(old),second=compile(current);
    for(const [viewW,viewH] of [[1440,1000],[1920,1080],[390,844]]){
      const output=controller.creamOutputSize(viewW,viewH,1.5);
      for(const seed of [4,7])for(const time of [0,6,15]){
        const primitives=controller.sampleProductionScene(model,controller.createProductionRecipe(model,seed),viewW,viewH,time*2).primitives;
        const settings={w:output.width,h:output.height,viewW,viewH,ratio:output.ratio,primitives};
        const a=pixels(first,settings),b=pixels(second,{...settings,shape:[2.1,1.38,5.3,1]});
        let different=0,max=0;const samples=[];
        for(let i=0;i<a.length;i++){const delta=Math.abs(a[i]-b[i]);if(delta){
          different++;if(samples.length<16)samples.push({offset:i,channel:i%4,before:a[i],after:b[i]});
        }max=Math.max(max,delta);}
        let repeated=null;
        if(different){
          const again=pixels(second,{...settings,shape:[2.1,1.38,5.3,1]}),neutral=pixels(second,settings);
          repeated={sameProgram:0,neutralShape:0};
          for(let i=0;i<a.length;i++){if(again[i]!==b[i])repeated.sameProgram++;if(neutral[i]!==a[i])repeated.neutralShape++;}
        }
        result.ambient.push({view:[viewW,viewH],seed,time,bytes:a.length,different,max,samples,repeated});
      }
    }
    const radius=model.cursorRadius(1000,800);
    for(const energy of [0,1])for(let i=0;i<8;i++){
      const phase=i*Math.PI/4,angle=i*Math.PI/7,stretch=energy?1.38:1.13+.045*Math.sin(phase);
      const shape=[angle,stretch,phase,energy],settings={w:256,h:256,viewW:1000,viewH:800,
        primitives:[{x:128,y:128,radius,peak:0}],shape,tint:1};
      const bytes=pixels(second,settings),margin=radius*controller.CURSOR_SHAPE_PROFILE.maxExtent+14+800*.04;
      const previous=pixels(first,settings);
      let different=0;for(let n=0;n<bytes.length;n++)if(bytes[n]!==previous[n])different++;
      result.cursorMaterial.push({shape,different});
      let outsideAlpha=0,maximumOutsideAlpha=0;
      for(let y=0;y<256;y++)for(let x=0;x<256;x++)if(Math.abs(x-128)>Math.ceil(margin)||Math.abs(y-128)>Math.ceil(margin)){
        const alpha=bytes[((255-y)*256+x)*4+3];if(alpha>1)outsideAlpha++;maximumOutsideAlpha=Math.max(maximumOutsideAlpha,alpha);
      }
      result.shapes.push({shape,radius,image:png(bytes,256,256),centre:[128,128]});
      result.crop.push({shape,margin,outsideAlpha,maximumOutsideAlpha});
    }
    const head={x:700,y:400},stored=Array.from({length:8},(_,i)=>({x:700-(i+1)*radius*3.2,y:400+Math.sin(i)*radius}));
    const points=controller.sampleProductionTrail(model,stored,head),oldPoints=model.sampleTrail(stored,head);
    const tailExtent=points=>{
      let lead=head;const trail=points.map(point=>{const segment=[lead.x,lead.y,point.x,point.y];lead=point;return segment;});
      const bytes=pixels(second,{w:1000,h:800,viewW:1000,viewH:800,primitives:[{...head,radius,peak:0}],shape:[0,1.13,0,0],tint:1,trail});
      let left=1000;for(let y=0;y<800;y++)for(let x=0;x<1000;x++)if(bytes[(y*1000+x)*4+3]>=128)left=Math.min(left,x);
      return head.x-left;
    };
    const oldExtent=tailExtent(oldPoints),newExtent=tailExtent(points);
    result.trailLength={oldExtent,newExtent,visibleRatio:newExtent/oldExtent,
      centerlineRatio:Math.hypot(points[7].x-head.x,points[7].y-head.y)/Math.hypot(oldPoints[7].x-head.x,oldPoints[7].y-head.y)};
    let lead=head;const trail=points.map(point=>{const segment=[lead.x,lead.y,point.x,point.y];lead=point;return segment;});
    for(const angle of [0,Math.PI/2,Math.PI]){
      const bytes=pixels(second,{w:1000,h:800,viewW:1000,viewH:800,primitives:[{...head,radius,peak:0}],shape:[angle,1.38,2.7,1],tint:1,trail});
      const margin=radius*controller.CURSOR_SHAPE_PROFILE.maxExtent+14+800*.04,all=[head,...points];
      const left=Math.floor(Math.min(...all.map(p=>p.x))-margin),right=Math.ceil(Math.max(...all.map(p=>p.x))+margin),
        top=Math.floor(Math.min(...all.map(p=>p.y))-margin),bottom=Math.ceil(Math.max(...all.map(p=>p.y))+margin);
      let outsideAlpha=0;
      for(let y=0;y<800;y++)for(let x=0;x<1000;x++)if(x<left||x>=right||y<top||y>=bottom)if(bytes[((799-y)*1000+x)*4+3]>1)outsideAlpha++;
      result.crop.push({withTrail:true,angle,outsideAlpha,bounds:[left,top,right,bottom]});
    }
    return result;
  }finally{
    gl.deleteBuffer(buffer);programs.forEach(p=>gl.deleteProgram(p));shaders.forEach(s=>gl.deleteShader(s));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""


def rgba(data_url):
    return np.asarray(Image.open(BytesIO(base64.b64decode(data_url.split(",", 1)[1]))).convert("RGBA")).copy()


def metrics(image, centre, radius, scale=1):
    mask = image[:, :, 3] >= 128
    opaque = image[:, :, 3] >= 245
    ys, xs = np.where(mask)
    assert len(xs) > 20, "Opaque cursor head is missing."
    coordinates = np.column_stack(((xs + .5 - centre[0]) / scale, (ys + .5 - centre[1]) / scale))
    covariance = np.cov(coordinates, rowvar=False, bias=True)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    axis = eigenvectors[:, -1]
    rgb = image[:, :, :3].astype(float)
    pink = opaque & (rgb[:, :, 2] >= rgb[:, :, 1] - 1) & (rgb[:, :, 0] >= rgb[:, :, 1] - 1)
    tip = opaque & (((np.indices(mask.shape)[1] + .5 - centre[0]) ** 2 +
                   (np.indices(mask.shape)[0] + .5 - centre[1]) ** 2) > (radius * scale * 1.02) ** 2)
    return {"opaque_pixels": int(opaque.sum()), "silhouette_pixels": int(mask.sum()), "coverage_threshold": 128,
            "opaque_area_ratio": float(opaque.sum() / (math.pi * (radius * scale) ** 2)),
            "area_ratio": float(mask.sum() / (math.pi * (radius * scale) ** 2)),
            "aspect": float(math.sqrt(eigenvalues[-1] / eigenvalues[0])),
            "axis": [float(axis[0]), float(axis[1])],
            "centroid_radius": float(np.linalg.norm(coordinates.mean(axis=0)) / radius),
            "maximum_radius": float(np.linalg.norm(coordinates, axis=1).max() / radius),
            "pink_fraction": float(pink.sum() / opaque.sum()),
            "tip_pixels": int(tip.sum()), "nonpink_tip_pixels": int((tip & ~pink).sum()),
            "centre_alpha": int(image[min(image.shape[0]-1, int(centre[1])), min(image.shape[1]-1, int(centre[0])), 3])}


def actual_capture(page, record=None):
    if record is None:
        record = page.evaluate(CAPTURE)
    assert not record["hidden"] and not record["native"], record
    image = rgba(record.pop("image"))
    scale = record["width"] / record["cssWidth"]
    data = record["data"]
    centre = [(float(data["cursorX"]) - record["left"]) * scale,
              (float(data["cursorY"]) - record["top"]) * scale]
    record["metrics"] = metrics(image, centre, float(data["cursorRadius"]), scale)
    return record, image


def assert_head(value, maximum_area=1.12):
    assert .88 <= value["area_ratio"] <= maximum_area, value
    assert 1.04 <= value["aspect"] <= 2.2, value
    assert value["centroid_radius"] < .12 and value["maximum_radius"] < 1.55, value
    assert value["pink_fraction"] > .995 and value["nonpink_tip_pixels"] == 0, value
    assert value["centre_alpha"] >= 250, value


def movement_geometry(image, record):
    data = record["data"]
    scale = record["width"] / record["cssWidth"]
    radius = float(data["cursorRadius"])
    y, x = np.indices(image.shape[:2], dtype=float)
    x = record["left"] + (x + .5) / scale
    y = record["top"] + (y + .5) / scale
    dx, dy = x-float(data["cursorX"]), y-float(data["cursorY"])
    angle, stretch, phase, energy = [float(data[key]) for key in
                                    ["cursorAngle", "cursorStretch", "cursorPhase", "cursorEnergy"]]
    forward = dx*math.cos(angle) + dy*math.sin(angle)
    qx = forward / stretch
    qy = (-dx*math.sin(angle) + dy*math.cos(angle)) * stretch
    theta = np.arctan2(qy, qx)
    ramp = np.minimum(1, np.hypot(qx, qy) / (radius*.4))
    wave = (np.sin(2*theta+phase)*(.035+.012*energy) +
            np.cos(3*theta-2*phase)*(.024+.008*energy)) * ramp*ramp*(3-2*ramp)
    head = np.hypot(qx, qy) / (1+wave) - radius
    tail = np.full(head.shape, 100000.0)
    for index, (ax, ay, bx, by) in enumerate(record["trail"]):
        sx, sy = bx-ax, by-ay
        squared = sx*sx+sy*sy
        if squared < .25:
            continue
        progress = np.clip(((x-ax)*sx+(y-ay)*sy)/squared, 0, 1)
        r = radius * (.72 + (.12-.72)*(index+progress)/8)
        distance = np.hypot(x-(ax+progress*sx), y-(ay+progress*sy)) - r
        tail = np.minimum(tail, distance)
    k = radius*.4
    field = np.minimum(head, tail) - np.maximum(k-np.abs(head-tail), 0)**2 / (4*k)
    region = (forward >= radius*.35) & (np.hypot(dx, dy) <= radius*1.55)
    actual = image[:, :, 3] >= 128
    expected = field <= 0
    stable = region & (np.abs(field)*scale > 1)
    mismatches = int(np.count_nonzero(stable & (actual != expected)))
    assert mismatches == 0, {"geometry_mismatches": mismatches, "stable_pixels": int(stable.sum()), "data": data}
    extent = float(forward[actual & region].max() / radius)
    expected_extent = float(forward[expected & region].max() / radius)
    assert abs(extent-expected_extent)*radius*scale <= 1.5
    assert extent < 1.55
    return {"geometry_mismatches": mismatches, "stable_pixels": int(stable.sum()),
            "visible_forward_extension": extent, "expected_forward_extension": expected_extent,
            "coverage_threshold": 128}


def independent_gpu(page, before_source, checkpoint=None):
    page.keyboard.press("Alt+Shift+P")
    stopped(page, "paused", visible=True)
    result = page.evaluate(GPU, before_source)
    if checkpoint:
        checkpoint({**result, "shapes": [{k: v for k, v in row.items() if k != "image"} for row in result["shapes"]]})
    assert len(result["ambient"]) == 18
    assert all(row["different"] == 0 and row["max"] == 0 for row in result["ambient"]), result["ambient"]
    assert len(result["cursorMaterial"]) == 16 and all(row["different"] == 0 for row in result["cursorMaterial"]), result["cursorMaterial"]
    assert abs(result["trailLength"]["centerlineRatio"] - 1.5) < 1e-10, result["trailLength"]
    assert 1.45 < result["trailLength"]["visibleRatio"] < 1.52, result["trailLength"]
    for row in result["shapes"]:
        image = rgba(row.pop("image"))
        row["metrics"] = metrics(image, row["centre"], row["radius"])
        assert_head(row["metrics"])
    assert all(row["outsideAlpha"] == 0 for row in result["crop"]), result["crop"]
    page.keyboard.press("Alt+Shift+P")
    wait_state(page)
    return result


def live_cursor(page, viewport):
    width, height = viewport
    page.set_viewport_size({"width": width, "height": height})
    wait_state(page)
    page.mouse.move(width * .55, height * .52)
    page.wait_for_timeout(2400)
    idle, masks = [], []
    for _ in range(8):
        record, image = actual_capture(page)
        assert_head(record["metrics"])
        assert int(record["data"]["trailSegments"]) == 0
        idle.append(record)
        masks.append(image[:, :, 3] >= 128)
        page.wait_for_timeout(400)
    assert len({row["data"]["cursorPhase"] for row in idle}) == 8
    differences = [int(np.count_nonzero(masks[0] ^ mask)) for mask in masks[1:] if mask.shape == masks[0].shape]
    assert differences and max(differences) > max(6, idle[0]["metrics"]["silhouette_pixels"] * .02), differences
    directions = []
    for vertical in [False, True]:
        start = (width * .38, height * .43) if not vertical else (width * .5, height * .23)
        end = (width * .62, height * .43) if not vertical else (width * .5, height * .78)
        page.mouse.move(*start)
        page.wait_for_timeout(1500)
        page.evaluate("""() => {
          window.__cursorReviewPeak=null;
          const root=document.getElementById('cream-effects');
          window.__cursorReviewObserver=new MutationObserver(()=>{
            const energy=Number(root.dataset.cursorEnergy);
            if(root.dataset.contactActive==='false'&&!document.getElementById('cream-cursor').hidden&&
                (!window.__cursorReviewPeak||energy>Number(window.__cursorReviewPeak.data.cursorEnergy))){
              window.__cursorReviewPeak=(""" + CAPTURE + """)();
            }
          });
          window.__cursorReviewObserver.observe(root,{attributes:true,attributeFilter:['data-paint-count']});
        }""")
        for step in range(1, 21):
            page.mouse.move(start[0] + (end[0]-start[0])*step/20, start[1] + (end[1]-start[1])*step/20)
            page.wait_for_timeout(20)
        peak = page.evaluate("""() => {
          window.__cursorReviewObserver.disconnect();const result=window.__cursorReviewPeak;
          delete window.__cursorReviewObserver;delete window.__cursorReviewPeak;return result;
        }""")
        assert peak is not None, "No cursor frames were delivered during pointer movement."
        assert peak["data"]["contactActive"] == "false", "Standalone contour checks require a far, non-contact cursor."
        record, image = actual_capture(page, peak)
        angle = float(record["data"]["cursorAngle"])
        idle_at_phase = 1.13 + .045 * math.sin(float(record["data"]["cursorPhase"]))
        reactive_stretch = float(record["data"]["cursorStretch"]) - idle_at_phase
        assert float(record["data"]["cursorEnergy"]) > .35 and reactive_stretch > .04, record
        alignment = abs(math.sin(angle)) if vertical else abs(math.cos(angle))
        assert alignment > .92, record
        geometry = movement_geometry(image, record)
        assert record["metrics"]["nonpink_tip_pixels"] == 0
        directions.append({"vertical": vertical, "angle": angle, "alignment": alignment,
                           "geometry": geometry, "stretch_above_matched_idle": reactive_stretch,
                           "energy": record["data"]["cursorEnergy"],
                           "stretch": record["data"]["cursorStretch"], "pointer_input_age_ms": record["pointerInputAge"]})
    page.keyboard.press("Alt+Shift+P")
    held = stopped(page, "paused", visible=True, duration=350)
    phase = held["data"]["cursorPhase"]
    page.mouse.move(width * .5, height * .5)
    page.wait_for_timeout(250)
    assert snapshot(page)["data"]["cursorPhase"] == phase
    page.keyboard.press("Alt+Shift+P")
    wait_state(page)
    page.mouse.move(width * .51, height * .51)
    page.wait_for_timeout(150)
    assert snapshot(page)["data"]["cursorPhase"] != phase
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    state = snapshot(page)
    assert state["native"] and not state["pointer"] and state["layer"]
    page.evaluate("""() => {
      window.__cursorReviewReturnPaint=null;
      window.addEventListener('pointermove',event=>{
        const root=document.getElementById('cream-effects'),start=performance.now();
        const input={trusted:event.isTrusted,type:event.pointerType,focused:document.hasFocus(),
          paintBefore:Number(root.dataset.paintCount)};
        const observer=new MutationObserver(()=>{
          if(Number(root.dataset.paintCount)<=input.paintBefore)return;
          window.__cursorReviewReturnPaint={...input,elapsed:performance.now()-start,
            native:!document.body.classList.contains('cream-cursor-active'),
            pointerHidden:document.getElementById('cream-cursor').hidden};
          observer.disconnect();
        });
        observer.observe(root,{attributes:true,attributeFilter:['data-paint-count']});
      },{once:true});
    }""")
    page.mouse.move(width * .52, height * .52)
    page.wait_for_function("window.__cursorReviewReturnPaint!==null", timeout=1500)
    returned = page.evaluate("window.__cursorReviewReturnPaint")
    assert returned["trusted"] and returned["type"] == "mouse" and returned["focused"], returned
    assert not returned["native"] and not returned["pointerHidden"], returned
    return {"viewport": viewport, "idle": idle, "maximum_idle_outline_changed_pixels": max(differences),
            "directions": directions, "pause_freezes_shape": True, "blur_restores_native": True,
            "first_paint_after_focused_return": returned}


def run(url, output, before):
    output.mkdir(parents=True, exist_ok=True)
    report = {"url": url, "passed": False, "image_tool_views": 0, "visual_approval": False,
              "before_material_sha256": sha256(before.read_bytes()).hexdigest(), "live": []}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context, page, errors = new_context(browser)
                try:
                    page.add_init_script("window.addEventListener('pointermove',()=>{window.__cursorReviewLastMove=performance.now()},{passive:true})")
                    page.goto(direct_url(url), wait_until="networkidle")
                    wait_state(page)
                    page.evaluate("document.fonts.ready")
                    report["revision"] = snapshot(page)["data"]["revision"]
                    def checkpoint(value):
                        report["gpu"] = value
                        (output / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                    report["gpu"] = independent_gpu(page, before.read_text(encoding="utf-8"), checkpoint)
                    (output / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                    for viewport in [(1440, 1000), (1000, 800), (390, 844)]:
                        report["live"].append(live_cursor(page, viewport))
                        (output / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                    assert not errors, errors
                    report["passed"] = True
                finally:
                    context.close()
            finally:
                browser.close()
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        (output / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before-material", type=Path, default=BEFORE)
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT / ".local"):
        parser.error("--output must stay in the repository's private .local directory")
    result = run(args.url, destination, args.before_material.resolve())
    print(json.dumps({"passed": result["passed"], "revision": result["revision"],
                      "ambient_gpu_comparisons": len(result["gpu"]["ambient"]), "report": str(destination / "review.json")}))
