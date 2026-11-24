"""Numerical shared-SDF contact, layer-isolation and actual-page review. No image-tool views."""

import argparse
from collections import deque
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
from review_cream_cursor import rgba
from review_cream_effect import direct_url, new_context, snapshot, stopped, wait_state
from review_cream_liveness import parity

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / ".local" / "interactive-cream-20261011" / "before-contact" / "cream-material.mjs"

HOLD = r"""(() => {
  const raf=window.requestAnimationFrame.bind(window),interval=window.setInterval.bind(window);
  window.__contactHeldFrames=[];
  window.requestAnimationFrame=callback=>raf(time=>{
    if(window.__contactReviewHold)window.__contactHeldFrames.push(callback);else callback(time);
  });
  window.setInterval=(callback,delay,...args)=>interval(()=>{
    if(!window.__contactReviewHold)callback(...args);
  },delay);
  window.__releaseContactReview=()=>{
    window.__contactReviewHold=false;
    const frames=window.__contactHeldFrames.splice(0);
    frames.forEach(callback=>callback(performance.now()));
  };
})()"""

PLAN = r"""async ({kind,colour}) => {
  const root=document.getElementById('cream-effects'),revision=root.dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller]=await Promise.all([load('cream-model.mjs'),load('cream.mjs')]);
  const data={...root.dataset},recipe=controller.createProductionRecipe(model,Number(data.sceneSeed));
  const scene=controller.sampleProductionScene(model,recipe,innerWidth,innerHeight,Number(data.sampleTime),JSON.parse(data.spawnRecords));
  const app=document.getElementById('cream-material').getContext('webgl2'),program=app.getParameter(app.CURRENT_PROGRAM);
  const parts=scene.primitives.map((p,i)=>{
    const v=app.getUniform(program,app.getUniformLocation(program,'scoops['+i+']'));
    if(p.spawnShape){
      const q=app.getUniform(program,app.getUniformLocation(program,'spawnShapes['+(i-scene.strawberryStart)+']'));
      p={...p,spawnShape:{angle:q[0],aspect:q[1],phase:q[2],kind:q[3]}};
    }
    return {...p,x:v[0],y:v[1],radius:v[2],peak:v[3]};
  });
  const radius=model.cursorRadius(innerWidth,innerHeight),blend=Math.min(innerWidth,innerHeight)*.04;
  const panes=[...document.querySelectorAll('.cream-glass')].map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};});
  const texts=[...document.querySelectorAll('h1,h2,p,nav a,button')].flatMap(n=>[...n.getClientRects()].map(r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom})));
  const header=document.querySelector('header').getBoundingClientRect();
  const distance=p=>{let d=100000;for(const s of parts)d=model.smoothUnion(d,controller.creamPrimitiveDistance(s,p),blend);return d;};
  const occupied=p=>{
    const n=document.elementFromPoint(p.x,p.y);
    return !n||!!n.closest('header,button,a,input,textarea,select,.recipe-note,.notebook-cover,.cake-card,[data-open-notebook]');
  };
  const hasText=p=>texts.some(r=>p.x>=r.left-10&&p.x<=r.right+10&&p.y>=r.top-10&&p.y<=r.bottom+10);
  const paneAt=p=>panes.find(r=>p.x>r.left+20&&p.x<r.right-20&&p.y>r.top+20&&p.y<r.bottom-20);
  if(kind==='spawn'){
    for(const pane of panes)for(let y=Math.max(header.bottom+90,pane.top+70);y<Math.min(innerHeight-100,pane.bottom-70);y+=75){
      for(const x of [pane.left+55,pane.right-55,(pane.left+pane.right)/2]){
        const p={x,y};if(!occupied(p)&&!hasText(p))return p;
      }
    }
    throw new Error('No ordinary, noninteractive glass point was available for a trusted spawn.');
  }
  const shape=JSON.parse(data.pointerPose).shape,candidates=[];
  for(const p of parts){
    if((colour==='pink')!==!!p.spawnId)continue;
    for(let i=0;i<48;i++){
      const angle=i*Math.PI/24,n={x:Math.cos(angle),y:Math.sin(angle)};
      let low=0,high=p.radius+blend*2;
      if(distance({x:p.x+n.x*high,y:p.y+n.y*high})<=0)continue;
      for(let j=0;j<20;j++){
        const mid=(low+high)/2;if(distance({x:p.x+n.x*mid,y:p.y+n.y*mid})<0)low=mid;else high=mid;
      }
      const boundary={x:p.x+n.x*high,y:p.y+n.y*high};
      const gx=distance({x:boundary.x+1,y:boundary.y})-distance({x:boundary.x-1,y:boundary.y});
      const gy=distance({x:boundary.x,y:boundary.y+1})-distance({x:boundary.x,y:boundary.y-1});
      const length=Math.hypot(gx,gy);if(length<.1)continue;
      const normal={x:gx/length,y:gy/length};
      const q=controller.cursorShapePoint(-normal.x,-normal.y,shape),reach=radius/Math.hypot(q.x,q.y);
      const target={x:boundary.x+normal.x*(reach+12),y:boundary.y+normal.y*(reach+12)};
      const neck={x:boundary.x+normal.x*6,y:boundary.y+normal.y*6};
      if(target.x<radius*2||target.x>innerWidth-radius*2||target.y<header.bottom+radius*2||target.y>innerHeight-radius*2)continue;
      const pane=paneAt(neck),inside=!!pane;
      const outside=neck.x<Math.min(...panes.map(r=>r.left))-12||neck.x>Math.max(...panes.map(r=>r.right))+12;
      if((kind==='outside'?!outside:!inside)||occupied(target)||hasText(neck)||distance(target)<radius*.4)continue;
      candidates.push({target,boundary,normal,neck,pane: pane||null,parent:p.parent,spawnId:p.spawnId??null,
        kind,colour,sampleTime:Number(data.sampleTime),score:Math.abs(target.y-innerHeight*.5)});
    }
  }
  candidates.sort((a,b)=>a.score-b.score);
  if(!candidates.length)throw new Error('No visible '+kind+' '+colour+' contact point found.');
  return candidates[0];
}"""

REFERENCE = r"""async beforeSource => {
  const root=document.getElementById('cream-effects'),data={...root.dataset},main=document.getElementById('cream-material');
  const pointer=document.getElementById('cream-cursor'),app=main.getContext('webgl2'),program=app.getParameter(app.CURRENT_PROGRAM);
  const read=name=>app.getUniform(program,app.getUniformLocation(program,name));
  const shapeLocation=app.getUniformLocation(program,'spawnShapeCount'),spawnCount=shapeLocation?app.getUniform(program,shapeLocation):0;
  const start=Number(data.strawberryStart),shapeData=new Float32Array(32);
  const count=Number(data.scenePrimitiveCount),background=Array.from({length:count},(_,i)=>{
    const v=read('scoops['+i+']'),p={x:v[0],y:v[1],radius:v[2],peak:v[3]};
    if(i>=start&&i<start+spawnCount){
      const shape=read('spawnShapes['+(i-start)+']');shapeData.set(shape,(i-start)*4);
      p.spawnShape={angle:shape[0],aspect:shape[1],phase:shape[2],kind:shape[3]};
    }
    return p;
  });
  const pose=JSON.parse(data.pointerPose),values=read('contactShape'),shape={angle:values[0],stretch:values[1],phase:values[2],energy:values[3]};
  const cursor={x:pose.x,y:pose.y},path=Array.from({length:8},(_,i)=>{const v=read('trail['+i+']');return {x:v[2],y:v[3]};});
  const radius=read('headRadius'),ratio=Number(data.pixelRatio),w=main.width,h=main.height;
  const model=await import(new URL('cream-model.mjs?v='+encodeURIComponent(data.revision),location.href).href);
  const old=Function('model',beforeSource.replace('export function createCreamShaders','function createCreamShaders')+
    ';return createCreamShaders(model);')({...model,MAX_PRIMITIVES:48});
  const current=(await import(new URL('cream-material.mjs?v='+encodeURIComponent(data.revision),location.href).href)).createCreamShaders({...model,MAX_PRIMITIVES:48});
  const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Same-pose reference context unavailable');
  const programs=[],shaders=[],buffer=gl.createBuffer();
  const compile=fragment=>{
    const p=gl.createProgram();programs.push(p);
    for(const [kind,source] of [[gl.VERTEX_SHADER,old.vertex],[gl.FRAGMENT_SHADER,fragment]]){
      const shader=gl.createShader(kind);shaders.push(shader);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(p,shader);
    }
    gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p;
  };
  const draw=(p,parts,isPointer)=>{
    gl.useProgram(p);gl.viewport(0,0,w,h);gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const a=gl.getAttribLocation(p,'position');gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);
    const loc=name=>gl.getUniformLocation(p,name),scoops=new Float32Array(48*4);
    parts.forEach((s,i)=>scoops.set([s.x,s.y,s.radius,s.peak],i*4));
    gl.uniform2f(loc('resolution'),w,h);gl.uniform2f(loc('viewSize'),innerWidth,innerHeight);
    gl.uniform1f(loc('pixelRatio'),ratio);gl.uniform1f(loc('headRadius'),radius);
    gl.uniform1i(loc('scoopCount'),parts.length);gl.uniform4fv(loc('scoops[0]'),scoops);
    gl.uniform1i(loc('strawberryStart'),isPointer?-1:Number(data.strawberryStart));
    gl.uniform1i(loc('spawnShapeCount'),isPointer?0:spawnCount);gl.uniform4fv(loc('spawnShapes[0]'),shapeData);
    gl.uniform1f(loc('cursorTint'),isPointer?1:0);gl.uniform4f(loc('cursorShape'),shape.angle,shape.stretch,shape.phase,shape.energy);
    const trail=new Float32Array(32);let lead=cursor;path.forEach((end,i)=>{trail.set([lead.x,lead.y,end.x,end.y],i*4);lead=end;});
    gl.uniform4fv(loc('trail[0]'),trail);gl.uniform1i(loc('trailCount'),isPointer?8:0);
    gl.drawArrays(gl.TRIANGLES,0,3);const bytes=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
    if(gl.getError()!==gl.NO_ERROR)throw new Error('Same-pose reference draw failed');return bytes;
  };
  const layer=(bytes,left,top,width,height)=>{
    const out=document.createElement('canvas');out.width=width;out.height=height;
    const ctx=out.getContext('2d'),image=ctx.createImageData(width,height);
    for(let y=0;y<height;y++)for(let x=0;x<width;x++){
      const source=((h-top-y-1)*w+left+x)*4,target=(y*width+x)*4,alpha=bytes[source+3];
      for(let c=0;c<3;c++)image.data[target+c]=alpha?Math.min(255,Math.round(bytes[source+c]*255/alpha)):0;
      image.data[target+3]=alpha;
    }
    ctx.putImageData(image,0,0);out.setAttribute('aria-hidden','true');return out;
  };
  try{
    const base=draw(compile(spawnCount?current.spawnFragment:Number(data.strawberryStart)>=0?old.strawberryFragment:old.fragment),background,false);
    const fg=draw(compile(old.fragment),[{...cursor,radius,peak:0}],true);
    const mainLayer=layer(base,0,0,w,h),left=Math.round(parseFloat(pointer.style.left)*ratio),top=Math.round(parseFloat(pointer.style.top)*ratio);
    const pointerLayer=layer(fg,left,top,pointer.width,pointer.height);
    mainLayer.style.cssText='position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0';
    pointerLayer.style.cssText=pointer.style.cssText+';position:fixed;pointer-events:none;z-index:70';
    const previousMainVisibility=main.style.visibility,previousPointerVisibility=pointer.style.visibility;
    main.style.visibility='hidden';pointer.style.visibility='hidden';
    main.parentElement.append(mainLayer);document.body.append(pointerLayer);
    window.__restoreContactReference=()=>{
      mainLayer.remove();pointerLayer.remove();main.style.visibility=previousMainVisibility;pointer.style.visibility=previousPointerVisibility;
      delete window.__restoreContactReference;
    };
    return {data,background,cursor,shape,path,radius,blend:Math.min(innerWidth,innerHeight)*.04,referenceCursorImage:pointerLayer.toDataURL(),
      view:[innerWidth,innerHeight],width:innerWidth,height:innerHeight,pixelRatio:ratio,
      textRects:[...document.querySelectorAll('h1,h2,p,nav a,button')].flatMap(n=>[...n.getClientRects()].map(r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom})))};
  }finally{
    gl.deleteBuffer(buffer);programs.forEach(p=>gl.deleteProgram(p));shaders.forEach(s=>gl.deleteShader(s));gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""

GPU = r"""async beforeSource => {
  const revision=document.getElementById('cream-effects').dataset.revision;
  const load=name=>import(new URL(name+'?v='+encodeURIComponent(revision),location.href).href);
  const [model,controller,material]=await Promise.all([load('cream-model.mjs'),load('cream.mjs'),load('cream-material.mjs')]);
  const spec={...model,MAX_PRIMITIVES:controller.CREAM_MAX_PRIMITIVES},current=material.createCreamShaders(spec);
  const previous=Function('model',beforeSource.replace('export function createCreamShaders','function createCreamShaders')+
    ';return createCreamShaders(model);')(spec);
  const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,depth:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error('Independent shared-field GPU probe unavailable');
  const programs=[],shaders=[],buffer=gl.createBuffer(),w=640,h=480,viewW=1000,viewH=800;
  const radius=model.cursorRadius(viewW,viewH),blend=Math.min(viewW,viewH)*.04;
  const compile=source=>{
    const program=gl.createProgram();programs.push(program);
    for(const [kind,text] of [[gl.VERTEX_SHADER,current.vertex],[gl.FRAGMENT_SHADER,source]]){
      const shader=gl.createShader(kind);shaders.push(shader);gl.shaderSource(shader,text);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    return program;
  };
  const pixels=(program,background,cursor,shape,path,start,pass)=>{
    gl.useProgram(program);gl.viewport(0,0,w,h);gl.disable(gl.BLEND);gl.disable(gl.SCISSOR_TEST);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const loc=name=>gl.getUniformLocation(program,name),contact=pass!==null;
    const primitives=cursor?[...background,{...cursor,radius,peak:0}]:background;
    const data=new Float32Array(controller.CREAM_MAX_PRIMITIVES*4);
    primitives.forEach((p,i)=>data.set([p.x,p.y,p.radius,p.peak],i*4));
    gl.uniform2f(loc('resolution'),w,h);gl.uniform2f(loc('viewSize'),viewW,viewH);gl.uniform1f(loc('pixelRatio'),1);
    gl.uniform1i(loc('scoopCount'),primitives.length);gl.uniform4fv(loc('scoops[0]'),data);
    gl.uniform1f(loc('headRadius'),radius);gl.uniform1i(loc('strawberryStart'),start);
    gl.uniform1i(loc('trailCount'),!contact&&cursor?8:0);gl.uniform1f(loc('cursorTint'),!contact&&cursor?1:0);
    gl.uniform4f(loc('cursorShape'),...(contact?[0,1,0,0]:[shape.angle,shape.stretch,shape.phase,shape.energy]));
    const tail=new Float32Array(32);let lead=cursor;
    if(cursor)path.forEach((p,i)=>{tail.set([lead.x,lead.y,p.x,p.y],i*4);lead=p;});
    gl.uniform4fv(loc('trail[0]'),tail);
    gl.uniform1i(loc('ambientCount'),background.length);gl.uniform1i(loc('contactActive'),contact?1:0);
    gl.uniform1i(loc('contactPass'),pass??0);gl.uniform1i(loc('contactTrailCount'),contact?8:0);
    gl.uniform4f(loc('contactShape'),shape.angle,shape.stretch,shape.phase,shape.energy);
    gl.drawArrays(gl.TRIANGLES,0,3);
    const bytes=new Uint8Array(w*h*4);gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
    if(gl.getError()!==gl.NO_ERROR)throw new Error('Shared-field GPU draw failed');
    return bytes;
  };
  const png=bytes=>{
    const copy=document.createElement('canvas');copy.width=w;copy.height=h;const context=copy.getContext('2d'),image=context.createImageData(w,h);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const source=((h-y-1)*w+x)*4,target=(y*w+x)*4,alpha=bytes[source+3];
      for(let c=0;c<3;c++)image.data[target+c]=alpha?Math.min(255,Math.round(bytes[source+c]*255/alpha)):0;
      image.data[target+3]=alpha;
    }
    context.putImageData(image,0,0);return copy.toDataURL();
  };
  const difference=(a,b)=>{let count=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i])count++;return count;};
  try{
    const classic=compile(current.fragment),pink=compile(current.strawberryFragment),shared=compile(current.contactFragment);
    const oldClassic=compile(previous.fragment),oldPink=compile(previous.strawberryFragment),rows=[];
    const shape={...controller.createCursorShape(),angle:.28,phase:1.2,energy:.25};
    const add=(kind,colour,direction,gap,background,cursor,path)=>{
      const start=colour==='pink'?0:-1,state=controller.creamContactState(model,background,cursor,shape,path,viewW,viewH);
      const base=pixels(start<0?classic:pink,background,null,shape,[],start,null);
      const oldBase=pixels(start<0?oldClassic:oldPink,background,null,shape,[],start,null);
      const oldCursor=pixels(oldClassic,[],cursor,shape,path,-1,null);
      const foreground=state.active?pixels(shared,background,cursor,shape,path,start,1):pixels(classic,[],cursor,shape,path,-1,null);
      const main=state.active?pixels(shared,background,cursor,shape,path,start,0):base;
      let baseAlphaDifferences=0;for(let i=3;i<base.length;i+=4)if(main[i]!==base[i])baseAlphaDifferences++;
      rows.push({kind,colour,direction,gap,state,background,cursor,shape,path,radius,blend,view:[viewW,viewH],
        width:w,height:h,baseDifference:difference(base,oldBase),farMainDifference:state.active?null:difference(main,oldBase),
        farCursorDifference:state.active?null:difference(foreground,oldCursor),baseAlphaDifferences,
        main:png(main),foreground:png(foreground),base:png(base),cursorOnly:png(oldCursor)});
    };
    for(const colour of ['ivory','pink'])for(const vertical of [false,true]){
      const direction=vertical?'vertical':'horizontal',background=[{x:220,y:180,radius:70,peak:0}];
      const q=controller.cursorShapePoint(vertical?0:-1,vertical?-1:0,shape),reach=radius/Math.hypot(q.x,q.y);
      for(const gap of [90,8,-12,8,90]){
        const cursor={x:220+(vertical?0:70+reach+gap),y:180+(vertical?70+reach+gap:0)};
        add('head',colour,direction,gap,background,cursor,model.resetTrail(cursor));
      }
      for(const gap of [30,2,30]){
        const background=[{x:vertical?260:280,y:220,radius:70,peak:0}];
        const progress=vertical?.5:(500-280)/420;
        const tailRadius=radius*(.72-.6*progress);
        const axis=(vertical?260:220)-70-tailRadius-gap;
        const cursor=vertical?{x:axis,y:400}:{x:500,y:axis};
        const path=Array.from({length:8},(_,i)=>vertical?{x:axis,y:400-(i+1)*45}:{x:500-(i+1)*52.5,y:axis});
        add('trail',colour,direction,gap,background,cursor,path);
      }
    }
    for(const colour of ['ivory','pink']){
      const cursor={x:300,y:240},background=[{x:300,y:240,radius:180,peak:0}];
      add('inside',colour,'center',-180,background,cursor,model.resetTrail(cursor));
    }
    return {revision,rows};
  }finally{
    gl.deleteBuffer(buffer);programs.forEach(p=>gl.deleteProgram(p));shaders.forEach(s=>gl.deleteShader(s));
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}"""


def merge(a, b, k):
    return np.minimum(a, b) - np.maximum(k-np.abs(a-b), 0)**2/(4*k)


def primitive_distance(p, x, y):
    shape = p.get("spawnShape")
    if not shape:
        return np.hypot(x-p["x"], y-p["y"])-p["radius"]
    c, s, r = math.cos(shape["angle"]), math.sin(shape["angle"]), p["radius"]
    dx, dy = x-p["x"], y-p["y"]
    qx, qy = (c*dx+s*dy)/r, (-s*dx+c*dy)/r/shape["aspect"]
    theta = np.arctan2(qy, qx)
    a, b, d = (.10 if shape["kind"] == 1 else .015), (.035 if shape["kind"] == 0 else .055), (.10 if shape["kind"] == 2 else .025)
    radial = .94*(1+a*np.cos(theta+shape["phase"])+b*np.cos(2*theta-shape["phase"])+d*np.sin(3*theta+2*shape["phase"]))/(1+a+b+d)
    distance = np.hypot(qx, qy)
    return (np.where(qx*qx+qy*qy < 1e-10, distance, distance/radial)-1)*r


def fields(row, x=None, y=None):
    if x is None:
        y, x = np.indices((row["height"], row["width"]), dtype=float)
        x += .5
        y += .5
    base = np.full(x.shape, 100000.0)
    for p in row["background"]:
        base = merge(base, primitive_distance(p, x, y), row["blend"])
    r, shape, cursor = row["radius"], row["shape"], row["cursor"]
    dx, dy = x-cursor["x"], y-cursor["y"]
    c, s = math.cos(shape["angle"]), math.sin(shape["angle"])
    qx, qy = (c*dx+s*dy)/shape["stretch"], (-s*dx+c*dy)*shape["stretch"]
    theta = np.arctan2(qy, qx)
    ramp = np.minimum(1, np.hypot(qx, qy)/(r*.4))
    wave = (np.sin(2*theta+shape["phase"])*(.035+.012*shape["energy"]) +
            np.cos(3*theta-2*shape["phase"])*(.024+.008*shape["energy"])) * ramp*ramp*(3-2*ramp)
    head = np.hypot(qx, qy)/(1+wave)-r
    tail = np.full(x.shape, 100000.0)
    distance_to_path = np.hypot(dx, dy)
    lead = cursor
    for i, end in enumerate(row["path"]):
        sx, sy = end["x"]-lead["x"], end["y"]-lead["y"]
        squared = sx*sx+sy*sy
        if squared >= .25:
            t = np.clip(((x-lead["x"])*sx+(y-lead["y"])*sy)/squared, 0, 1)
            distance = np.hypot(x-lead["x"]-t*sx, y-lead["y"]-t*sy)
            tail = np.minimum(tail, distance-r*(.72-.6*(i+t)/8))
            distance_to_path = np.minimum(distance_to_path, distance)
        lead = end
    return base, merge(head, tail, min(row["blend"]*.4, r*.4)), merge(merge(base, head, row["blend"]), tail, min(row["blend"]*.4, r*.4)), distance_to_path


def components(mask):
    visited = np.zeros(mask.shape, dtype=bool)
    sizes = []
    for y, x in np.argwhere(mask):
        if visited[y, x]:
            continue
        visited[y, x] = True
        queue = deque([(int(y), int(x))])
        size = 0
        while queue:
            py, px = queue.pop()
            size += 1
            for ny, nx in [(py-1, px), (py+1, px), (py, px-1), (py, px+1)]:
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def analyze(row):
    main, foreground, base_image, cursor_image = [rgba(row.pop(key)) for key in ["main", "foreground", "base", "cursorOnly"]]
    background, own, shared, proximity = fields(row)
    alpha = 1-(1-main[:, :, 3]/255)*(1-foreground[:, :, 3]/255)
    mask = alpha >= .5
    expected = (shared <= 0) if row["state"]["active"] else ((background <= 0) | (own <= 0))
    stable = np.abs(shared if row["state"]["active"] else np.minimum(background, own)) > 1.25
    mismatches = int(np.count_nonzero(stable & (mask != expected)))
    bridge = int(np.count_nonzero(mask & (background > .1) & (own > .1)))
    sizes = components(mask)
    body_reach = row["radius"]*1.51 + row["blend"] + 4
    crop_reach = body_reach + 14 + min(row["view"])*.034
    lifted = int(np.count_nonzero((foreground[:, :, 3] >= 128) & (base_image[:, :, 3] >= 128) & (proximity > body_reach)))
    clipped = int(np.count_nonzero((foreground[:, :, 3] > 1) & (proximity > crop_reach)))
    foreground_area = int(np.count_nonzero(foreground[:, :, 3] >= 128))
    old_area = int(np.count_nonzero(cursor_image[:, :, 3] >= 128))
    metrics = {"components": len(sizes), "component_sizes": sizes, "bridge_pixels": bridge,
               "stable_sdf_mismatches": mismatches, "far_ambient_lift_pixels": lifted,
               "outside_crop_support_pixels": clipped, "foreground_opaque_pixels": foreground_area,
               "old_cursor_opaque_pixels": old_area}
    assert row["baseDifference"] == 0
    assert row["baseAlphaDifferences"] == 0, row["baseAlphaDifferences"]
    assert mismatches == lifted == clipped == 0, metrics
    assert foreground_area <= max(old_area*6, old_area+row["blend"]*row["radius"]*6), metrics
    if row["gap"] in [90, 30]:
        assert not row["state"]["active"] and len(sizes) == 2, (row, metrics)
        assert row["farMainDifference"] == row["farCursorDifference"] == 0
    else:
        assert row["state"]["active"] and len(sizes) == 1, (row, metrics)
        if row["gap"] > 0:
            assert bridge > 0, metrics
        if row["kind"] == "trail":
            assert row["state"]["tail"] and not row["state"]["head"], row
        if row["kind"] == "inside":
            rim = np.abs(own) < .75
            metrics["inside_cursor_rim_max_alpha"] = int(foreground[:, :, 3][rim].max())
            assert metrics["inside_cursor_rim_max_alpha"] <= 8, metrics
    row["metrics"] = metrics
    return row


def capture_live_contact(page, kind, colour):
    plan = page.evaluate(PLAN, {"kind": kind, "colour": colour})
    page.evaluate("document.documentElement.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}))")
    page.evaluate("""() => {
      window.__contactFirstPaint=null;
      window.addEventListener('pointermove',event=>{
        const root=document.getElementById('cream-effects'),before=Number(root.dataset.paintCount),start=performance.now();
        const observer=new MutationObserver(()=>{
          if(Number(root.dataset.paintCount)<=before)return;
          window.__contactReviewHold=true;
          window.__contactFirstPaint={trusted:event.isTrusted,elapsed:performance.now()-start,
            contact:root.dataset.contactActive==='true',head:root.dataset.contactHead==='true'};
          observer.disconnect();
        });
        observer.observe(root,{attributes:true,attributeFilter:['data-paint-count']});
      },{once:true});
    }""")
    page.mouse.move(plan["target"]["x"], plan["target"]["y"])
    try:
        page.wait_for_function("window.__contactFirstPaint!==null", polling=20, timeout=1500)
        first_paint = page.evaluate("window.__contactFirstPaint")
        assert first_paint["trusted"] and first_paint["contact"] and first_paint["head"], first_paint
        actual_parity = parity(page)
        foreground = page.evaluate("""() => {
          const p=document.getElementById('cream-cursor'),r=p.getBoundingClientRect();
          return {image:p.toDataURL(),left:parseFloat(p.style.left),top:parseFloat(p.style.top),
            width:p.width,height:p.height,ratio:Number(document.getElementById('cream-effects').dataset.pixelRatio),
            hidden:p.hidden,native:!document.body.classList.contains('cream-cursor-active')};
        }""")
        assert not foreground["hidden"] and not foreground["native"]
        actual_png = page.screenshot()
        reference = page.evaluate(REFERENCE, BEFORE.read_text(encoding="utf-8"))
        reference_png = page.screenshot()
    finally:
        page.evaluate("window.__restoreContactReference?.();window.__releaseContactReview()")
    actual = np.asarray(Image.open(BytesIO(actual_png)).convert("RGBA"))
    previous = np.asarray(Image.open(BytesIO(reference_png)).convert("RGBA"))
    background, own, shared, _ = fields(reference)
    bridge = (background > 1) & (own > 1) & (shared < -1)
    changes = np.max(np.abs(actual[:, :, :3].astype(int)-previous[:, :, :3].astype(int)), axis=2)
    visible_bridge = int(np.count_nonzero(bridge & (changes >= 3)))
    assert visible_bridge >= 10, {"kind": kind, "colour": colour, "plan": plan, "bridge_candidates": int(bridge.sum()), "visible_bridge_pixels": visible_bridge}
    fg = rgba(foreground["image"])
    fy, fx = np.indices(fg.shape[:2], dtype=float)
    fx = foreground["left"]+(fx+.5)/foreground["ratio"]
    fy = foreground["top"]+(fy+.5)/foreground["ratio"]
    _, _, _, proximity = fields(reference, fx, fy)
    reach = reference["radius"]*1.51+reference["blend"]+4
    lifted = (fg[:, :, 3] >= 128) & (proximity > reach)
    text = np.zeros(lifted.shape, dtype=bool)
    for rect in reference["textRects"]:
        text |= (fx >= rect["left"]) & (fx <= rect["right"]) & (fy >= rect["top"]) & (fy <= rect["bottom"])
    assert not lifted.any(), int(lifted.sum())
    assert not (lifted & text).any()
    old_cursor = rgba(reference.pop("referenceCursorImage"))
    old_area = int(np.count_nonzero(old_cursor[:, :, 3] >= 128))
    new_area = int(np.count_nonzero(fg[:, :, 3] >= 128))
    assert new_area <= max(old_area*6, old_area+reference["blend"]*reference["radius"]*6)
    return {"kind": kind, "colour": colour, "plan": plan, "parity": actual_parity, "first_input_paint": first_paint,
            "visible_composited_bridge_pixels": visible_bridge, "bridge_candidates": int(bridge.sum()),
            "rgb_change_threshold": 3, "far_ambient_lift_pixels": int(lifted.sum()),
            "lifted_reading_text_pixels": int((lifted & text).sum()),
            "foreground_opaque_pixels": new_area, "before_cursor_opaque_pixels": old_area,
            "actual_screenshot_sha256": sha256(actual_png).hexdigest(),
            "same_pose_split_reference_sha256": sha256(reference_png).hexdigest(),
            "comparison_method": "Brief first-paint hold; same-pose split layers retain current spawn shapes and unchanged classic cursor material, removing only shared contact; original canvases restored.",
            "pointer_visible": True}


def live_review(browser, url, checkpoint):
    context, page, errors = new_context(browser)
    context.add_init_script(HOLD)
    record = {"composited": [], "progress": [], "passed": False}
    try:
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(direct_url(url), wait_until="networkidle")
        wait_state(page)
        record["revision"] = snapshot(page)["data"]["revision"]
        page.evaluate("document.fonts.ready")
        for kind in ["outside", "inside"]:
            record["composited"].append(capture_live_contact(page, kind, "ivory"))
            checkpoint(record)
        point = page.evaluate(PLAN, {"kind": "spawn", "colour": "pink"})
        page.mouse.click(point["x"], point["y"])
        page.wait_for_function("Number(document.getElementById('cream-effects').dataset.spawnCount)===1")
        record["composited"].append(capture_live_contact(page, "inside", "pink"))
        checkpoint(record)
        page.keyboard.press("Alt+Shift+P")
        held = stopped(page, "paused", visible=True)
        assert not held["pointer"] and held["data"]["contactActive"] == "false"
        assert snapshot(page, True)["gpu"]["contact"] is None
        page.keyboard.press("Alt+Shift+P")
        wait_state(page)
        page.locator('[data-open-notebook="notebook-decorated-cakes"]').click()
        page.wait_for_function("document.getElementById('notebook-dialog').open")
        page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='false'")
        before = snapshot(page)
        page.wait_for_timeout(400)
        after = snapshot(page, True)
        assert after["native"] and not after["pointer"] and after["gpu"]["contact"] is None
        assert int(after["data"]["paintCount"]) > int(before["data"]["paintCount"])
        page.keyboard.press("Escape")
        for _ in range(8):
            page.locator("h1").click()
        page.wait_for_function("Number(document.getElementById('cream-effects').dataset.spawnCount)===8")
        page.wait_for_function("JSON.parse(document.getElementById('cream-effects').dataset.spawnRecords).at(-1).id===9")
        for width, height in [(1920, 1080), (1440, 1000), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_function("Number(document.getElementById('cream-effects').dataset.viewportWidth)===innerWidth")
            center = page.evaluate("""() => {
              const d=document.getElementById('cream-effects').dataset,g=document.getElementById('cream-material').getContext('webgl2');
              const p=g.getParameter(g.CURRENT_PROGRAM),v=g.getUniform(p,g.getUniformLocation(p,'scoops['+d.ambientPrimitiveCount+']'));
              return {x:v[0],y:v[1]};
            }""")
            page.mouse.move(center["x"], center["y"])
            page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='true'")
            page.wait_for_timeout(200)
            start = previous = snapshot(page, True)
            samples = []
            for second in range(1, 11):
                page.wait_for_timeout(1000)
                value = snapshot(page, True)
                assert value["data"]["contactActive"] == "true" and int(value["data"]["spawnCount"]) == 8, {
                    "viewport": [width, height], "second": second, "target": center, "snapshot": value}
                assert value["pointer"] and not value["native"]
                assert value["gpu"]["contact"]["pass"] == 0 and value["gpu"]["tint"] == value["gpu"]["trail"] == 0
                assert value["stats"]["uploads"] > previous["stats"]["uploads"] and value["gpu"]["positions"] != previous["gpu"]["positions"]
                assert float(value["data"]["motionTime"]) > float(previous["data"]["motionTime"])
                samples.append({"second": second, "state": value["data"], "parity": parity(page)})
                previous = value
            wall = (previous["now"]-start["now"])/1000
            fps = (int(previous["data"]["paintCount"])-int(start["data"]["paintCount"]))/wall
            clock = (float(previous["data"]["motionTime"])-float(start["data"]["motionTime"]))/wall
            assert 0 < fps <= 31.5 and clock >= .8, {"fps": fps, "clock_fraction": clock}
            record["progress"].append({"viewport": [width, height], "windows": 10, "fps": fps,
                                       "clock_fraction": clock, "samples": samples})
            checkpoint(record)
        page.evaluate("window.dispatchEvent(new Event('blur'));Object.defineProperty(document,'hasFocus',{configurable:true,value:()=>false})")
        page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='false'")
        assert snapshot(page, True)["gpu"]["contact"] is None
        page.evaluate("delete document.hasFocus;window.dispatchEvent(new Event('pageshow'))")
        page.mouse.move(center["x"]+1, center["y"]+1)
        page.wait_for_function("document.getElementById('cream-effects').dataset.contactActive==='true'")
        page.evaluate("""const g=document.getElementById('cream-material').getContext('webgl2');
          window.__contactLoss=g.getExtension('WEBGL_lose_context');window.__contactLoss.loseContext()""")
        stopped(page, "context-lost")
        page.evaluate("window.__contactLoss.restoreContext()")
        wait_state(page)
        assert snapshot(page)["data"]["contactActive"] == "false"
        assert snapshot(page, True)["gpu"]["contact"] is None
        assert not errors, errors
        record.update({"pause_clears_contact_without_later_uploads": True,
                       "native_viewer_keeps_background_without_contact": True,
                       "blur_and_recovery_native_fallback": True, "context_loss_restores_no_contact": True,
                       "passed": True})
        return record
    finally:
        context.close()


def run(url, output, live_only=False):
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "review.json"
    report = {"url": url, "passed": False, "image_tool_views": 0, "visual_approval": False,
              "before_material_sha256": sha256(BEFORE.read_bytes()).hexdigest(), "gpu": [],
              "synthetic_run": not live_only}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                if not live_only:
                    context, page, errors = new_context(browser)
                    try:
                        page.goto(direct_url(url), wait_until="networkidle")
                        wait_state(page)
                        page.keyboard.press("Alt+Shift+P")
                        stopped(page, "paused", visible=True)
                        result = page.evaluate(GPU, BEFORE.read_text(encoding="utf-8"))
                        report["revision"] = result["revision"]
                        for row in result["rows"]:
                            report["gpu"].append(analyze(row))
                            destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
                        assert not errors, errors
                        report["synthetic_passed"] = True
                    finally:
                        context.close()
                def checkpoint(value):
                    report["live"] = value
                    report["revision"] = value["revision"]
                    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
                report["live"] = live_review(browser, url, checkpoint)
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
    parser.add_argument("--live-only", action="store_true", help="Run actual moving-page contact and safety without repeating unchanged synthetic material comparisons.")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        parser.error("--output must remain in this repository's private .local directory")
    result = run(args.url, output, live_only=args.live_only)
    print(json.dumps({"passed": result["passed"], "synthetic_passed": result.get("synthetic_passed"),
                      "revision": result.get("revision"), "report": str(output / "review.json")}))
