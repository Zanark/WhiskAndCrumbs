const modelUrl = new URL('./model.mjs', import.meta.url);
modelUrl.search = new URL(import.meta.url).search;
const { PLACEMENT_SLOTS, MAX_PRIMITIVES, CREAM_PROFILE, TRAIL_PROFILE, createSceneRecipe, seedScoops, sampleScoops, expandScoops, followPointer, cursorRadius, resetTrail, followTrail, sampleTrail, outputSize } = await import(modelUrl.href);

const canvas = document.getElementById('material');
canvas.dataset.previewRevision = new URL(import.meta.url).searchParams.get('v') || 'unversioned';
const pointerCanvas = document.createElement('canvas');
pointerCanvas.id = 'cream-pointer';
pointerCanvas.setAttribute('aria-hidden','true');
pointerCanvas.hidden = true;
canvas.after(pointerCanvas);
const pointerContext = pointerCanvas.getContext('2d');
if (!pointerContext) console.warn('The cream pointer overlay is unavailable; retaining the normal pointer.');
const status = document.getElementById('status');
const pauseButton = document.getElementById('pause');
const resetButton = document.getElementById('reset');
const cleanButton = document.getElementById('clean');
cleanButton.disabled = false;
const motion = matchMedia('(prefers-reduced-motion: reduce)');
const forcedColors = matchMedia('(forced-colors: active)');
const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
const printing = matchMedia('print');
const gl = canvas.getContext('webgl2', {alpha: true, premultipliedAlpha: true, antialias: true, depth: false, preserveDrawingBuffer: true});
let frame;
let program;
let geometry;
let uniforms;
let scoops = [];
let cursor = {x: innerWidth * .48, y: innerHeight * .27};
let target = {...cursor};
let trail = resetTrail(cursor);
let lastTime = 0;
let paused = false;
let lost = false;
let output;
let paintCount = 0;
let blurred = false;
let stopped = false;
let viewWidth = 0;
let viewHeight = 0;
let motionTime = 0;
let recipe;
let sceneSeed;
let pointerPresent = false;
const FRAME_INTERVAL = 1000 / 30;
const data = new Float32Array(MAX_PRIMITIVES * 4);
const pointerData = new Float32Array(MAX_PRIMITIVES * 4);
const trailData = new Float32Array(TRAIL_PROFILE.links * 4);

const vertex = `#version 300 es
in vec2 position;
void main(){gl_Position=vec4(position,0.,1.);}
`;
const fragment = `#version 300 es
precision highp float;
uniform vec2 resolution;
uniform float pixelRatio;
uniform vec2 viewSize;
uniform int scoopCount;
uniform vec4 scoops[${MAX_PRIMITIVES}];
uniform vec4 trail[${TRAIL_PROFILE.links}];
uniform int trailCount;
uniform float headRadius;
uniform float cursorTint;
out vec4 color;

float merge(float a,float b,float k){
  float h=max(k-abs(a-b),0.)/k;
  return min(a,b)-h*h*k*.25;
}
vec2 tailSurface(vec2 p){
  vec2 nearest=vec2(100000.,0.);
  for(int i=0;i<${TRAIL_PROFILE.links};i++){
    if(i>=trailCount)break;
    vec2 a=trail[i].xy,b=trail[i].zw,axis=b-a;
    float lengthSquared=dot(axis,axis);
    if(lengthSquared<.25)continue;
    float t=clamp(dot(p-a,axis)/lengthSquared,0.,1.);
    float progress=(float(i)+t)/${TRAIL_PROFILE.links.toFixed(1)};
    float radius=headRadius*mix(${TRAIL_PROFILE.startRadius.toFixed(3)},${TRAIL_PROFILE.endRadius.toFixed(3)},progress);
    float distance=length(p-mix(a,b,t))-radius;
    if(distance<nearest.x)nearest=vec2(distance,radius);
  }
  return nearest;
}
float surface(vec2 p){
  float d=100000.;
  float blend=min(viewSize.x,viewSize.y)*.040;
  for(int i=0;i<${MAX_PRIMITIVES};i++){
    if(i>=scoopCount)break;
    vec4 s=scoops[i];
    d=merge(d,length(p-s.xy)-s.z,blend);
  }
  return merge(d,tailSurface(p).x,min(blend*.4,headRadius*.4));
}
float creamHeight(vec2 p,float distance,float scale){
  float totalWeight=0.;
  float totalHeight=0.;
  for(int i=0;i<${MAX_PRIMITIVES};i++){
    if(i>=scoopCount)break;
    vec4 s=scoops[i];
    vec2 q=(p-s.xy)/s.z;
    float q2=dot(q,q);
    if(q2>9.)continue;
    float weight=exp(-q2*${CREAM_PROFILE.weightFalloff.toFixed(3)});
    float dome=s.z*${CREAM_PROFILE.domeHeight.toFixed(3)}*exp(-q2*${CREAM_PROFILE.domeFalloff.toFixed(3)});
    float crown=0.;
    if(s.w>0.){
      float angle=float(i)*2.399963+.35;
      vec2 tip=s.xy+vec2(cos(angle)*.12,sin(angle)*.10)*s.z;
      vec2 peak=(p-tip)/(s.z*${CREAM_PROFILE.peakWidth.toFixed(3)});
      crown=exp(-${CREAM_PROFILE.peakFalloff.toFixed(3)}*(sqrt(dot(peak,peak)+${(CREAM_PROFILE.peakRoundness ** 2).toFixed(6)})-${CREAM_PROFILE.peakRoundness.toFixed(3)}));
    }
    totalHeight+=weight*(dome+s.z*${CREAM_PROFILE.peakHeight.toFixed(3)}*s.w*crown);
    totalWeight+=weight;
  }
  vec2 tail=tailSurface(p);
  if(tail.y>0.){
    float q=max(0.,tail.x+tail.y)/tail.y;
    float weight=exp(-q*q*${CREAM_PROFILE.weightFalloff.toFixed(3)});
    totalHeight+=weight*tail.y*.5*exp(-q*q*${CREAM_PROFILE.domeFalloff.toFixed(3)});
    totalWeight+=weight;
  }
  float rim=1.-exp(-max(-distance,0.)/(scale*${CREAM_PROFILE.rimWidth.toFixed(3)}));
  return rim*totalHeight/max(totalWeight,.00001);
}
void main(){
  vec2 p=vec2(gl_FragCoord.x,resolution.y-gl_FragCoord.y)/pixelRatio;
  float scale=min(viewSize.x,viewSize.y);
  float d=surface(p);
  float aa=max(fwidth(d),.55);
  float coverage=1.-smoothstep(-aa,aa,d);
  float shadowDistance=surface(p-vec2(6.,11.));
  float shadow=(1.-smoothstep(-5.,scale*.034,shadowDistance))*(1.-coverage)*.10;
  float height=creamHeight(p,d,scale);
  vec3 normal=normalize(vec3(-dFdx(height)*pixelRatio,dFdy(height)*pixelRatio,1.));
  vec3 light=normalize(vec3(-.55,-.78,.72));
  float diffuse=max(0.,dot(normal,light));
  vec3 halfway=normalize(light+vec3(0.,0.,1.));
  float gloss=pow(max(0.,dot(normal,halfway)),48.);
  float broad=pow(max(0.,dot(normal,halfway)),8.);
  vec3 ivory=vec3(255.,250.,238.)/255.;
  if(cursorTint>.5){
    float follower=min(length(p-scoops[scoopCount-1].xy)-headRadius,tailSurface(p).x);
    float strawberry=1.-smoothstep(-aa,aa,follower);
    ivory=mix(ivory,vec3(255.,224.,234.)/255.,strawberry);
  }
  vec3 cream=ivory*(.86+.14*diffuse);
  cream+=vec3(1.,.995,.97)*(.18*gloss+.035*broad);
  float grain=fract(sin(dot(floor(p*pixelRatio),vec2(12.9898,78.233)))*43758.5453);
  cream+=(grain-.5)*.003;
  // Associated alpha lets the patterned ground show only outside cream and through its shadow.
  float alpha=1.-(1.-shadow)*(1.-coverage);
  color=vec4(clamp(cream,0.,1.)*coverage,alpha);
}
`;

function fail(message) {
  if(frame!==undefined)cancelAnimationFrame(frame);
  frame = undefined;
  stopped = true;
  document.body.classList.remove('ready');
  document.body.classList.remove('cream-cursor-active');
  pointerCanvas.hidden=true;
  canvas.hidden = true;
  status.textContent = message;
  pauseButton.disabled = true;
  resetButton.disabled = true;
}

function shader(type, source) {
  const result = gl.createShader(type);
  if (!result) throw new Error('Shader allocation failed.');
  gl.shaderSource(result, source);
  gl.compileShader(result);
  if (!gl.getShaderParameter(result, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(result);
    gl.deleteShader(result);
    throw new Error(`Material shader compilation failed: ${message}`);
  }
  return result;
}

function setup() {
  const v = shader(gl.VERTEX_SHADER, vertex);
  const f = shader(gl.FRAGMENT_SHADER, fragment);
  program = gl.createProgram();
  gl.attachShader(program, v);
  gl.attachShader(program, f);
  gl.linkProgram(program);
  gl.deleteShader(v);
  gl.deleteShader(f);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(`Material link failed: ${gl.getProgramInfoLog(program)}`);
  gl.useProgram(program);
  geometry = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, geometry);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,3,-1,-1,3]), gl.STATIC_DRAW);
  const location = gl.getAttribLocation(program, 'position');
  gl.enableVertexAttribArray(location);
  gl.vertexAttribPointer(location, 2, gl.FLOAT, false, 0, 0);
  uniforms = Object.fromEntries(['resolution','pixelRatio','viewSize','scoopCount','scoops','trail','trailCount','headRadius','cursorTint'].map(name =>
    [name, gl.getUniformLocation(program, ['scoops','trail'].includes(name) ? `${name}[0]` : name)]));
}

function canPaint() { return !lost && !stopped && !document.hidden && !forcedColors.matches && !printing.matches; }
function canAnimate() { return canPaint() && !paused && !motion.matches && !blurred; }
function canFollowPointer() { return canAnimate() && finePointer.matches; }
function message() {
  if (lost || stopped) return;
  if (motion.matches) status.textContent = 'Reduced motion: static material preview.';
  else if (forcedColors.matches || printing.matches) status.textContent = 'Accessible static view: motion is disabled.';
  else if (paused) status.textContent = 'Motion paused. Shapes are retained.';
  else if (document.hidden || blurred) status.textContent = 'Motion paused while this window is inactive. Return to the preview to resume.';
  else status.textContent = `${scoops.length - recipe.clumps.length} of ${PLACEMENT_SLOTS} placed scoops. ${recipe.groupCount} groups and ${recipe.dropletCount} small blobs; refresh for a new mix.`;
}
function recoverFocus() {
  if (!blurred || document.hidden || !document.hasFocus()) return;
  blurred=false;
  lastTime=0;
  message();
  schedule();
}
function paintPointer(radius, path) {
  const margin=radius+14+Math.min(innerWidth,innerHeight)*.04;
  const points=[cursor,...path];
  const left=Math.max(0,Math.floor((Math.min(...points.map(p=>p.x))-margin)*output.ratio));
  const top=Math.max(0,Math.floor((Math.min(...points.map(p=>p.y))-margin)*output.ratio));
  const right=Math.min(canvas.width,Math.ceil((Math.max(...points.map(p=>p.x))+margin)*output.ratio));
  const bottom=Math.min(canvas.height,Math.ceil((Math.max(...points.map(p=>p.y))+margin)*output.ratio));
  const width=right-left,height=bottom-top;
  if (width<=0 || height<=0) return false;
  if (pointerCanvas.width!==width) pointerCanvas.width=width;
  if (pointerCanvas.height!==height) pointerCanvas.height=height;
  Object.assign(pointerCanvas.style,{left:`${left/output.ratio}px`,top:`${top/output.ratio}px`,
    width:`${width/output.ratio}px`,height:`${height/output.ratio}px`});
  pointerData.fill(0);
  pointerData.set([cursor.x,cursor.y,radius,0]);
  gl.uniform1i(uniforms.scoopCount,1);
  gl.uniform4fv(uniforms.scoops,pointerData);
  gl.uniform1i(uniforms.trailCount,trail.length);
  gl.uniform1f(uniforms.cursorTint,1);
  // Paint only the pointer's bounds, then copy that transparent pass above the page.
  gl.enable(gl.SCISSOR_TEST);
  gl.scissor(left,canvas.height-bottom,width,height);
  gl.clearColor(0,0,0,0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.drawArrays(gl.TRIANGLES,0,3);
  pointerContext.clearRect(0,0,width,height);
  pointerContext.drawImage(canvas,left,top,width,height,0,0,width,height);
  gl.disable(gl.SCISSOR_TEST);
  pointerCanvas.hidden=false;
  pointerCanvas.dataset.paintCount=String(Number(pointerCanvas.dataset.paintCount||0)+1);
  return true;
}
function render() {
  if (!gl || !canPaint() || !output) return;
  gl.viewport(0,0,canvas.width,canvas.height);
  gl.useProgram(program);
  gl.uniform2f(uniforms.resolution,canvas.width,canvas.height);
  gl.uniform1f(uniforms.pixelRatio,output.ratio);
  gl.uniform2f(uniforms.viewSize,innerWidth,innerHeight);
  data.fill(0);
  const radius=cursorRadius(innerWidth,innerHeight);
  let lead=cursor,activeSegments=0;
  const path=sampleTrail(trail,cursor);
  path.forEach((point,index)=>{
    trailData.set([lead.x,lead.y,point.x,point.y],index*4);
    if(Math.hypot(point.x-lead.x,point.y-lead.y)>=.5)activeSegments++;
    lead=point;
  });
  gl.uniform4fv(uniforms.trail,trailData);
  gl.uniform1f(uniforms.headRadius,radius);
  const pointerActive=!!pointerContext && canFollowPointer() && pointerPresent && paintPointer(radius,path);
  if (!pointerActive) pointerCanvas.hidden=true;
  const all = expandScoops(sampleScoops(scoops,motionTime,innerWidth,innerHeight));
  all.forEach((s,i)=>data.set([s.x,s.y,s.radius,s.peak],i*4));
  gl.uniform1i(uniforms.scoopCount,all.length);
  gl.uniform4fv(uniforms.scoops,data);
  gl.uniform1i(uniforms.trailCount,0);
  gl.uniform1f(uniforms.cursorTint,0);
  gl.drawArrays(gl.TRIANGLES,0,3);
  document.body.classList.toggle('cream-cursor-active',pointerActive);
  canvas.dataset.paintCount = String(++paintCount);
  canvas.dataset.scoopCount = String(scoops.length);
  canvas.dataset.seedCount = String(recipe.clumps.length);
  canvas.dataset.groupCount = String(recipe.groupCount);
  canvas.dataset.dropletCount = String(recipe.dropletCount);
  canvas.dataset.sceneSeed = String(sceneSeed);
  canvas.dataset.primitiveCount = String(all.length);
  canvas.dataset.primitiveCapacity = String(MAX_PRIMITIVES);
  canvas.dataset.pixelRatio = String(output.ratio);
  canvas.dataset.motionTime = motionTime.toFixed(4);
  canvas.dataset.peakCount = String(scoops.filter(s=>s.peak>0).length);
  canvas.dataset.cursorRadius = radius.toFixed(3);
  canvas.dataset.trailSegments = String(activeSegments);
  canvas.dataset.pointerActive = String(pointerActive);
}
function tick(time) {
  frame = undefined;
  if (!canPaint()) {lastTime=0;canvas.dataset.state='still';return;}
  const animated=canAnimate();
  const elapsed=lastTime ? time-lastTime : FRAME_INTERVAL;
  if (animated && lastTime && elapsed<FRAME_INTERVAL-1) {frame=requestAnimationFrame(tick);return;}
  if (animated) {
    motionTime+=Math.min(elapsed,50)/1000;
    if (canFollowPointer()) cursor=followPointer(cursor,target,elapsed);
    trail=followTrail(trail,cursor,elapsed,cursorRadius(innerWidth,innerHeight));
  }
  lastTime=animated?time:0;
  render();
  canvas.dataset.state=animated?'moving':'still';
  if (animated) frame=requestAnimationFrame(tick);
}
function schedule() {
  if (frame===undefined && canPaint()) {
    canvas.dataset.state='moving';
    frame=requestAnimationFrame(tick);
  }
}
function resize() {
  if (!gl || lost || stopped) return;
  output=outputSize(innerWidth,innerHeight,devicePixelRatio||1);
  if (!output) {fail('Viewport exceeds the preview resolution budget; showing a static fallback.');return;}
  canvas.width=output.width;
  canvas.height=output.height;
  if (!scoops.length) scoops=seedScoops(innerWidth,innerHeight,recipe);
  else if (viewWidth && viewHeight) {
    const sx=innerWidth/viewWidth, sy=innerHeight/viewHeight;
    const sr=Math.min(innerWidth,innerHeight)/Math.min(viewWidth,viewHeight);
    const seeds=seedScoops(innerWidth,innerHeight,recipe);
    scoops=scoops.map((s,index)=>index<recipe.clumps.length ? seeds[index] :
      {...s,x:s.x*sx,y:s.y*sy,radius:s.radius*sr});
    cursor={x:cursor.x*sx,y:cursor.y*sy};
    target={x:target.x*sx,y:target.y*sy};
    trail=trail.map(point=>({x:point.x*sx,y:point.y*sy}));
  }
  viewWidth=innerWidth;viewHeight=innerHeight;
  document.body.classList.add('ready');
  canvas.hidden=false;
  pauseButton.disabled=false;
  resetButton.disabled=false;
  schedule();
}
function reset() {
  scoops=seedScoops(innerWidth,innerHeight,recipe);
  cursor={x:innerWidth*.48,y:innerHeight*.27};
  target={...cursor};
  trail=resetTrail(cursor);
  motionTime=0;lastTime=0;
  message();schedule();
}

if (!gl) {
  fail('WebGL2 is unavailable. This device gets the static material fallback.');
} else {
  try {
    try {sceneSeed=crypto.getRandomValues(new Uint32Array(1))[0];}
    catch {sceneSeed=Math.floor(Math.random()*4294967296);}
    recipe=createSceneRecipe(sceneSeed);
    setup();resize();message();
  }
  catch(error) {console.error(error);fail('The material renderer could not start. The static preview is still available.');}
}

window.addEventListener('pointermove',event=>{
  recoverFocus();
  if (!canFollowPointer() || event.pointerType!=='mouse' || event.buttons) return;
  target={x:event.clientX,y:event.clientY};
  if (!pointerPresent) {cursor={...target};trail=resetTrail(cursor);}
  pointerPresent=true;
  schedule();
},{passive:true});
window.addEventListener('pointerdown',event=>{
  recoverFocus();
  if (!gl || lost || stopped || event.button!==0 || event.target.closest('header,footer,button,a')) return;
  if (scoops.length>=recipe.clumps.length+PLACEMENT_SLOTS) {status.textContent='Preview scoop limit reached. Existing forms remain; Reset shapes clears your scoops; refresh changes the mix.';return;}
  scoops.push({x:event.clientX,y:event.clientY,radius:Math.min(innerWidth,innerHeight)*.075,peak:scoops.length%2===0 ? .78 : 0});
  target={x:event.clientX,y:event.clientY};cursor={...target};trail=resetTrail(cursor);message();schedule();
},{passive:true});
pauseButton.addEventListener('click',()=>{
  paused=!paused;target={...cursor};lastTime=0;
  recoverFocus();
  pauseButton.setAttribute('aria-pressed',String(paused));
  pauseButton.textContent=paused?'Resume motion':'Pause motion';message();schedule();
});
document.documentElement.addEventListener('pointerleave',event=>{
  if(event.pointerType!=='mouse')return;
  pointerPresent=false;
  stopFrames();
  schedule();
},{passive:true});
resetButton.addEventListener('click',reset);
cleanButton.addEventListener('click',()=>{
  const clean=document.body.classList.toggle('material-only');
  cleanButton.setAttribute('aria-pressed',String(clean));cleanButton.textContent=clean?'Show layout':'Material only';
});
window.addEventListener('resize',resize,{passive:true});
function stopFrames() {
  if(frame!==undefined)cancelAnimationFrame(frame);
  frame=undefined;lastTime=0;canvas.dataset.state='still';
  document.body.classList.remove('cream-cursor-active');
  pointerCanvas.hidden=true;
}
window.addEventListener('blur',()=>{blurred=true;target={...cursor};stopFrames();message();});
window.addEventListener('focus',()=>{blurred=false;message();schedule();});
window.addEventListener('pagehide',stopFrames);
window.addEventListener('pageshow',()=>{lastTime=0;recoverFocus();message();schedule();});
document.addEventListener('visibilitychange',()=>{
  stopFrames();
  if(!document.hidden)recoverFocus();
  message();
  if(!document.hidden)schedule();
});
for(const query of [motion,forcedColors,finePointer,printing]) query.addEventListener('change',()=>{
  stopFrames();target={...cursor};message();schedule();
});
canvas.addEventListener('webglcontextlost',event=>{
  event.preventDefault();lost=true;stopFrames();canvas.hidden=true;
  document.body.classList.remove('ready');status.textContent='Graphics context paused. Stored shapes will return if it recovers.';
});
canvas.addEventListener('webglcontextrestored',()=>{
  lost=false;stopped=false;
  try {setup();resize();message();}
  catch(error) {console.error(error);fail('Graphics recovery failed; static preview remains available.');}
});
