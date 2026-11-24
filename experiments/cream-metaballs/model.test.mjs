import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createSceneRecipe,DEFAULT_SCENE,PLACEMENT_SLOTS,seedScoops,sampleScoops,expandScoops,scoopHeight,CREAM_PROFILE,MOTION_PROFILE,CLUMP_PROFILES,MAX_PRIMITIVES,smoothUnion,followPointer,outputSize,MAX_SCOOPS,SEED_SCOOPS,TRAIL_PROFILE,cursorRadius,resetTrail,followTrail,sampleTrail} from './model.mjs';
import {staticClumpCss} from './generate_static_clumps.mjs';

test('side pattern sits below associated-alpha cream while center etchings stay above glass',()=>{
  const css=readFileSync(new URL('./preview.css',import.meta.url),'utf8');
  const html=readFileSync(new URL('./index.html',import.meta.url),'utf8');
  const renderer=readFileSync(new URL('./preview.mjs',import.meta.url),'utf8');
  assert.match(css,/body \{[^}]*isolation: isolate/);
  assert.match(css,/\.side-background \{[^}]*z-index: -1;[^}]*bakery-pattern-cream\.svg[^}]*background-size: 640px 480px/);
  assert.match(css,/\.side-background::after \{[^}]*width: min\(760px, calc\(100% - var\(--preview-gutters\)\)\)[^}]*background: var\(--cream\)/);
  assert.match(css,/\.butter-paper \{ z-index: 2;[^}]*bakery-glass-etching\.svg/);
  assert.ok(html.indexOf('class="side-background"')<html.indexOf('id="material"'));
  assert.match(renderer,/alpha: true, premultipliedAlpha: true/);
  assert.match(renderer,/color=vec4\(clamp\(cream,0\.,1\.\)\*coverage,alpha\)/);
  assert.doesNotMatch(renderer,/vec3 background=paper/);
  const pattern=readFileSync(new URL('./assets/bakery-pattern-cream.svg',import.meta.url));
  assert.deepEqual(pattern,readFileSync(new URL('../../web/assets/bakery-pattern-cream.svg',import.meta.url)));
});

test('static baseline has six unequal groups plus seven new small droplets',()=>{
  const scoops=seedScoops(1440,1000);
  assert.equal(scoops.length,SEED_SCOOPS);
  assert.equal(scoops.filter(s=>s.kind==='group').length,6);
  assert.equal(scoops.filter(s=>s.kind==='droplet').length,7);
  assert.ok(scoops.length<MAX_SCOOPS);
  assert.ok(scoops.every(s=>s.x>0&&s.x<1440&&s.y>0&&s.y<1000&&s.radius>0));
  assert.equal(new Set(scoops.map(s=>s.radius)).size,scoops.length);
  assert.ok(Math.max(...scoops.map(s=>s.radius))/Math.min(...scoops.map(s=>s.radius))>4);
  assert.ok(scoops[0].radius>=280&&scoops[0].radius<=310);
  assert.ok(Math.abs(scoops[0].x-(1440-scoops[1].x))>10);
});
test('refresh recipes vary count and dimensions but are immutable and repeatable by seed',()=>{
  const counts=new Set(),groups=new Set(),droplets=new Set(),sizes=new Set();
  for(let seed=0;seed<256;seed++){
    const recipe=createSceneRecipe(seed);
    assert.deepEqual(recipe,createSceneRecipe(seed));
    assert.ok(Object.isFrozen(recipe)&&Object.isFrozen(recipe.clumps)&&recipe.clumps.every(Object.isFrozen));
    counts.add(recipe.clumps.length);sizes.add(recipe.clumps[0].radius);
    groups.add(recipe.groupCount);droplets.add(recipe.dropletCount);
    assert.equal(new Set(recipe.clumps.filter(s=>s.kind==='group').map(s=>s.clump)).size,recipe.groupCount);
    assert.equal(recipe.clumps.length,recipe.groupCount+recipe.dropletCount);
    assert.ok(recipe.clumps.filter(s=>s.kind==='droplet').every(s=>s.radius>=.032&&s.radius<=.040&&s.clump===undefined));
    assert.ok(recipe.clumps.some(s=>s.lobeMotion?.mode==='together'));
    assert.ok(recipe.clumps.some(s=>s.lobeMotion?.canDetach));
    assert.ok(recipe.clumps[0].radius>=.28&&recipe.clumps[0].radius<=.31);
    assert.ok(recipe.clumps.some(s=>s.radius<.072));
    for(const [w,h] of [[320,568],[1000,1000],[844,390]]){
      const samples=seedScoops(w,h,recipe),unit=Math.min(w,h);
      samples.forEach((s,i)=>{
        assert.ok(Math.abs(s.x/w-recipe.clumps[i].x)<1e-10);
        assert.ok(Math.abs(s.radius/unit-recipe.clumps[i].radius)<1e-10);
      });
      const placed=Array.from({length:PLACEMENT_SLOTS},()=>({x:0,y:0,radius:10,peak:0}));
      assert.ok(expandScoops([...samples,...placed]).length+1<=MAX_PRIMITIVES);
      assert.equal(expandScoops([...samples,...placed])[samples.length].radius,10);
    }
  }
  assert.deepEqual([...counts].sort((a,b)=>a-b),[9,10,11,12,13,14]);
  assert.deepEqual([...groups].sort(),[4,5,6]);
  assert.deepEqual([...droplets].sort(),[5,6,7,8]);
  assert.equal(sizes.size,256);
  for(const bad of [-1,1.1,NaN,Infinity,4294967296])assert.throws(()=>createSceneRecipe(bad),RangeError);
});
test('every default clump has connected lobes of unequal sizes within its envelope',()=>{
  const anchors=seedScoops(1440,1000),before=structuredClone(anchors);
  const forms=expandScoops(anchors);
  assert.equal(forms.length,15+DEFAULT_SCENE.dropletCount);
  assert.deepEqual(anchors,before);
  for(let index=0;index<anchors.length;index++){
    const group=forms.filter(s=>s.parent===index),anchor=anchors[index],main=group[0];
    if(anchor.kind==='droplet'){assert.equal(group.length,1);continue;}
    assert.ok(group.length>=2&&group.length<=3);
    assert.equal(main.lobe,0);
    assert.ok(new Set(group.map(s=>s.radius)).size>1);
    for(const lobe of group.slice(1)){
      const distance=Math.hypot(lobe.x-main.x,lobe.y-main.y);
      assert.ok(distance<main.radius+lobe.radius,'Joined parts must overlap without relying on blur.');
      assert.ok(distance+lobe.radius>main.radius*1.2,'Satellite lobes must visibly extend the main body.');
    }
    for(const lobe of group){
      assert.ok(Math.hypot(lobe.x-anchor.x,lobe.y-anchor.y)+lobe.radius<=anchor.radius+1e-8);
    }
  }
});
test('coherent lobes stay attached while divergent lobes follow their bounded relative transforms',()=>{
  for(const [width,height] of [[320,568],[1440,1000],[844,390]]){
    const seeds=seedScoops(width,height);
    for(const time of [0,.5,9,27,90,3600]){
      const anchors=sampleScoops(seeds,time,width,height),forms=expandScoops(anchors);
      for(const form of forms){
        const anchor=anchors[form.parent],profile=anchor.lobeState?.[form.lobe] ??
          (anchor.clump===undefined?[0,0,1]:CLUMP_PROFILES[anchor.clump][form.lobe]);
        assert.ok(Math.abs((form.x-anchor.x)/anchor.radius-profile[0])<1e-10);
        assert.ok(Math.abs((form.y-anchor.y)/anchor.radius-profile[1])<1e-10);
        assert.ok(Math.abs(form.radius/anchor.radius-profile[2])<1e-10);
        assert.ok(form.x-form.radius>=0&&form.x+form.radius<=width);
        assert.ok(form.y-form.radius>=0&&form.y+form.radius<=height);
      }
    }
  }
});
test('attached lobes do not consume placed-scoop slots or break stable logical indices',()=>{
  const seeds=seedScoops(1440,1000),placed=Array.from({length:12},(_,i)=>({x:300+i*10,y:500,radius:50,peak:0}));
  const primitives=expandScoops([...seeds,...placed]);
  assert.equal(MAX_SCOOPS,26);
  assert.ok(primitives.length+1<=MAX_PRIMITIVES);
  assert.equal(MAX_PRIMITIVES,36);
  assert.equal(primitives[seeds.length].x,placed[0].x);
  assert.equal(primitives[seeds.length+11].x,placed[11].x);
  assert.throws(()=>expandScoops([{x:0,y:0,radius:10,clump:6}]),RangeError);
  assert.throws(()=>expandScoops(Array.from({length:19},()=>seeds[0])),RangeError);
  assert.throws(()=>expandScoops(null),RangeError);
});
test('random large lobes peel in a different direction then merge back into the same parent',()=>{
  const selected=new Set(),modes=new Set();
  for(let seed=0;seed<64;seed++){
    const recipe=createSceneRecipe(seed),anchors=seedScoops(1000,1000,recipe);
    const index=anchors.findIndex(s=>s.lobeMotion?.canDetach);
    selected.add(index);
    const anchor=anchors[index],motion=anchor.lobeMotion;
    const start=expandScoops(anchors).filter(s=>s.parent===index);
    const period=motion.period/MOTION_PROFILE.lobeRate;
    const middleAnchors=sampleScoops(anchors,period/2,1000,1000);
    const middle=expandScoops(middleAnchors).filter(s=>s.parent===index);
    const finish=expandScoops(sampleScoops(anchors,period,1000,1000)).filter(s=>s.parent===index);
    const gap=group=>Math.hypot(group[motion.lobe].x-group[0].x,group[motion.lobe].y-group[0].y)-group[0].radius-group[motion.lobe].radius;
    assert.ok(gap(start)<0);
    assert.ok(gap(middle)>39,'Peeling must clear the 40px SDF blend, not only change metadata.');
    assert.ok(gap(finish)<0);
    const dt=.01,t=period*.25;
    const first=expandScoops(sampleScoops(anchors,t,1000,1000)).filter(s=>s.parent===index);
    const next=expandScoops(sampleScoops(anchors,t+dt,1000,1000)).filter(s=>s.parent===index);
    const body=[next[0].x-first[0].x,next[0].y-first[0].y];
    const lobe=[next[motion.lobe].x-first[motion.lobe].x,next[motion.lobe].y-first[motion.lobe].y];
    assert.ok(Math.hypot(lobe[0]-body[0],lobe[1]-body[1])>.001);
    for(const a of anchors.filter(s=>s.kind==='group'))modes.add(a.lobeMotion.mode);
    for(const form of middle){
      assert.ok(form.x-form.radius>=0&&form.x+form.radius<=1000&&form.y-form.radius>=0&&form.y+form.radius<=1000);
      const parent=middleAnchors[index];
      assert.ok(Math.hypot(form.x-parent.x,form.y-parent.y)+form.radius<=parent.radius*parent.envelope+1e-8);
    }
    assert.deepEqual(anchors,seedScoops(1000,1000,recipe));
  }
  assert.deepEqual([...selected].sort(),[0,1]);
  assert.deepEqual([...modes].sort(),['divergent','together']);
});
test('coherent groups share direction while extra droplets keep independent parent indices',()=>{
  const anchors=seedScoops(1000,1000),before=sampleScoops(anchors,2,1000,1000),after=sampleScoops(anchors,2.01,1000,1000);
  const a=expandScoops(before),b=expandScoops(after);
  for(let index=0;index<anchors.length;index++){
    const group=a.filter(s=>s.parent===index),next=b.filter(s=>s.parent===index);
    if(anchors[index].kind==='droplet'){assert.equal(group.length,1);assert.equal(group[0].lobe,0);}
    if(anchors[index].lobeMotion?.mode==='together'){
      for(let j=0;j<group.length;j++){
        const oldX=(group[j].x-before[index].x)/before[index].radius;
        const nextX=(next[j].x-after[index].x)/after[index].radius;
        assert.ok(Math.abs(oldX-nextX)<1e-10);
      }
    }
  }
  assert.throws(()=>expandScoops([{...anchors[0],lobeState:[[0,0,-1]]}]),RangeError);
  assert.throws(()=>sampleScoops([{...anchors[0],lobeMotion:{...anchors[0].lobeMotion,period:0}}],1,1000,1000),RangeError);
});
test('static fallback includes all model group lobes and extra individual droplets',()=>{
  const expected=staticClumpCss();
  assert.equal((expected.match(/radial-gradient/g)||[]).length,expandScoops(seedScoops(1000,1000)).length);
  assert.equal(readFileSync(new URL('./static-clumps.css',import.meta.url),'utf8'),expected);
  assert.match(readFileSync(new URL('./index.html',import.meta.url),'utf8'),/href="static-clumps\.css"/);
});
test('smooth union joins rounded surfaces without a seam',()=>{
  assert.ok(smoothUnion(0,0,40)<0);
  assert.equal(smoothUnion(0,100,40),0);
  assert.equal(smoothUnion(12,-4,30),smoothUnion(-4,12,30));
});
test('pointer follower converges without overshoot or changing a retained target',()=>{
  let position={x:0,y:0};const target={x:100,y:60};
  for(let i=0;i<100;i++)position=followPointer(position,target,16);
  assert.ok(Math.hypot(position.x-100,position.y-60)<.01);
  assert.ok(position.x<=100&&position.y<=60);
  assert.deepEqual(followPointer(target,target,500),target);
});
test('pixel budget preserves native resolution or selects an honest static fallback',()=>{
  assert.deepEqual(outputSize(1440,1000,1),{width:1440,height:1000,ratio:1});
  assert.equal(outputSize(1440,1000,2).ratio,2);
  assert.equal(outputSize(10000,10000,2),null);
  assert.throws(()=>seedScoops(0,0),RangeError);
  assert.throws(()=>followPointer({x:0,y:0},{x:NaN,y:3},16),RangeError);
});

test('only some initial forms carry distinct soft whipped peaks',()=>{
  const scoops=seedScoops(1440,1000);
  assert.equal(scoops.filter(s=>s.peak>0).length,3);
  assert.ok(scoops.every(s=>s.peak>=0&&s.peak<=1));
  assert.ok(Object.isFrozen(CREAM_PROFILE));
});

test('ambient drift is deterministic, continuous and does not mutate retained anchors',()=>{
  const scoops=seedScoops(1440,1000),before=structuredClone(scoops);
  assert.deepEqual(sampleScoops(scoops,0,1440,1000),before);
  const first=sampleScoops(scoops,1,1440,1000);
  const next=sampleScoops(scoops,1.1,1440,1000);
  assert.deepEqual(first,sampleScoops(scoops,1,1440,1000));
  assert.ok(first.every((s,i)=>Math.hypot(s.x-next[i].x,s.y-next[i].y)>0.001));
  assert.ok(first.every((s,i)=>Math.hypot(s.x-next[i].x,s.y-next[i].y)<35));
  assert.deepEqual(scoops,before);
});

test('moving seed forms remain contained and bounded for portrait and landscape views',()=>{
  for(const [width,height] of [[1440,1000],[390,844],[844,390]]){
    const anchors=seedScoops(width,height);
    for(const time of [0,.5,4,12,45,120,3600,86400]){
      const forms=sampleScoops(anchors,time,width,height);
      const giant=expandScoops(forms).filter(s=>s.parent===0);
      const extent=Math.max(Math.max(...giant.map(s=>s.x+s.radius))-Math.min(...giant.map(s=>s.x-s.radius)),
        Math.max(...giant.map(s=>s.y+s.radius))-Math.min(...giant.map(s=>s.y-s.radius)));
      assert.ok(extent>Math.min(width,height)*.40,'Peeling must not collapse the massive group into a small silhouette.');
      forms.forEach((s,i)=>{
        assert.ok(s.x-s.radius>=0&&s.x+s.radius<=width);
        assert.ok(s.y-s.radius>=0&&s.y+s.radius<=height);
        assert.ok(s.radius>=anchors[i].radius*.95-1e-8&&s.radius<=anchors[i].radius*1.05+1e-8);
        assert.equal(s.peak,anchors[i].peak);
      });
    }
  }
});

test('all ambient rates run another 1.5 times faster, including split/rejoin cycles',()=>{
  assert.equal(MOTION_PROFILE.speedMultiplier,.421875*1.5);
  assert.equal(MOTION_PROFILE.breathRate,.03875*1.5*1.5);
  assert.equal(MOTION_PROFILE.lobeRate,1.5);
  assert.ok(Object.isFrozen(MOTION_PROFILE));
  const [form]=sampleScoops([{x:720,y:500,radius:100,peak:0}],16,1440,1000);
  assert.ok(Math.abs(form.x-(720+220*Math.sin(-16*1.5*.27*.421875)))<1e-9);
  assert.ok(Math.abs(form.y-(500+100*Math.sin(16*1.5*.20*.421875)))<1e-9);
  assert.ok(Math.abs(form.radius-100*(1+.025*Math.sin(16*1.5*.058125)))<1e-9);
});

test('random massive envelopes retain breathing spaces over viewports and long runs',()=>{
  for(let seed=0;seed<64;seed++){
  for(const [width,height] of [[320,568],[390,844],[844,390],[1440,1000],[2560,1440],[600,300]]){
    const anchors=seedScoops(width,height,createSceneRecipe(seed));
    for(const time of [0,.5,9,27,90,240,3600,86400]){
      const forms=sampleScoops(anchors,time,width,height);
      for(const side of ['left','right']){
        const group=forms.filter(s=>s.side===side&&s.kind==='group');
        assert.ok(group.length>=2&&group.length<=3);
        for(const s of group){
          assert.ok(s.x-s.radius>=0&&s.x+s.radius<=width);
          assert.ok(s.y-s.radius>=0&&s.y+s.radius<=height);
        }
      }
      for(let i=0;i<forms.length;i++)for(let j=i+1;j<forms.length;j++){
        const a=forms[i],b=forms[j],gap=Math.hypot(a.x-b.x,a.y-b.y)-a.radius*(a.envelope??1)-b.radius*(b.envelope??1);
        assert.ok(gap>Math.min(width,height)*.024,`${width}x${height} seed ${seed} at ${time}s: ${i}/${j} gap ${gap}`);
      }
      }
    }
  }
});

test('near-edge scoops have an inward orbit without clipping or an initial jump',()=>{
  const anchors=seedScoops(1440,1000);
  const first=sampleScoops(anchors,.00001,1440,1000);
  first.forEach((s,index)=>assert.ok(Math.hypot(s.x-anchors[index].x,s.y-anchors[index].y)<.01));
  const x=[];
  for(let time=0;time<120;time+=.4)x.push(sampleScoops(anchors,time,1440,1000)[4].x);
  assert.ok(Math.max(...x)-Math.min(...x)>20,'The clump must move while respecting its reserved envelope.');
  const clicked={x:0,y:0,radius:60,peak:.8};
  assert.deepEqual(sampleScoops([clicked],0,1440,1000),[clicked]);
  assert.equal(sampleScoops([clicked],2,1440,1000)[0].x,0);
});

test('added scoops and the pointer are retained without unbounded record creation',()=>{
  const anchors=Array.from({length:MAX_SCOOPS+1},(_,i)=>({x:80+i*45,y:500,radius:60,peak:i%2?.8:0}));
  const result=sampleScoops(anchors,30,1440,1000);
  assert.equal(result.length,MAX_SCOOPS+1);
  assert.deepEqual(result.map(s=>s.peak),anchors.map(s=>s.peak));
  assert.throws(()=>sampleScoops([...anchors,anchors[0]],0,1440,1000),RangeError);
});

test('rounded bodies have real height curvature instead of a clipped flat plateau',()=>{
  const body={x:0,y:0,radius:100,peak:0};
  const center=scoopHeight(body,0,0,0),inner=scoopHeight(body,0,20,0),outer=scoopHeight(body,0,45,0);
  assert.ok(center>inner&&inner>outer);
  assert.ok(center-inner>1);
  assert.ok(center-outer>5);
});

test('selected peaks rise above a rounded shoulder and taper continuously',()=>{
  const body={x:0,y:0,radius:100,peak:0},peaked={...body,peak:.85};
  const x=Math.cos(.35)*12,y=Math.sin(.35)*10;
  const top=scoopHeight(peaked,0,x,y),shoulder=scoopHeight(peaked,0,x+20,y);
  assert.ok(top>scoopHeight(body,0,x,y)+30);
  assert.ok(top>shoulder+10);
  assert.ok(Math.abs(top-scoopHeight(peaked,0,x+.01,y))<.02);
  for(let offset=-150;offset<=150;offset+=5){
    const height=scoopHeight(peaked,0,offset,20);
    assert.ok(Number.isFinite(height)&&height>=0&&height<100);
  }
});

test('invalid animated material inputs fail explicitly',()=>{
  const scoops=seedScoops(1440,1000);
  for(const time of [-1,NaN,Infinity])assert.throws(()=>sampleScoops(scoops,time,1440,1000),RangeError);
  for(const value of [0,NaN,Infinity])assert.throws(()=>sampleScoops(scoops,1,value,1000),RangeError);
  assert.throws(()=>sampleScoops([{x:0,y:0,radius:0}],1,1440,1000),RangeError);
  assert.throws(()=>sampleScoops([{x:0,y:0,radius:10,peak:2}],1,1440,1000),RangeError);
  assert.throws(()=>sampleScoops([{x:0,y:0,radius:10,side:'middle'}],1,1440,1000),RangeError);
  assert.throws(()=>sampleScoops([{x:0,y:0,radius:10,band:[.6,.2]}],1,1440,1000),RangeError);
  assert.throws(()=>scoopHeight(scoops[0],-.5,0,0),RangeError);
  assert.throws(()=>scoopHeight(scoops[0],0,NaN,0),RangeError);
});

test('cursor head is 25 percent smaller than the previous 3.2 percent head and the tail tapers',()=>{
  for(const [width,height] of [[1440,1000],[390,844],[2560,1440]]){
    assert.ok(Math.abs(cursorRadius(width,height)/(Math.min(width,height)*.032)-.75)<1e-10);
  }
  assert.equal(TRAIL_PROFILE.links,8);
  assert.ok(TRAIL_PROFILE.startRadius>TRAIL_PROFILE.endRadius&&TRAIL_PROFILE.endRadius>0);
});

test('a bounded viscous tail follows sequentially rather than moving as one rigid blob',()=>{
  const initial=resetTrail({x:0,y:0}),snapshot=structuredClone(initial);
  const head={x:300,y:90},radius=32;
  const moved=followTrail(initial,head,16,radius);
  assert.equal(moved.length,8);
  assert.ok(moved[0].x>moved[1].x&&moved[1].x>moved[2].x);
  let lead=head;
  for(const point of moved){
    assert.ok(Math.hypot(lead.x-point.x,lead.y-point.y)<=radius*TRAIL_PROFILE.maxGap+1e-8);
    lead=point;
  }
  assert.deepEqual(initial,snapshot);
});

test('stopped trails catch up and merge into the head without fading stored scoops',()=>{
  const head={x:800,y:400};
  let trail=resetTrail({x:0,y:0});
  for(let i=0;i<480;i++)trail=followTrail(trail,head,1000/60,32);
  assert.ok(trail.every(point=>point.x===head.x&&point.y===head.y));
  assert.deepEqual(followTrail(trail,{x:0,y:0},0,32),trail);
});

test('displayed trail is 1.5 times the previous .44 path without changing head size or lag',()=>{
  const head={x:500,y:350};
  const points=Array.from({length:8},(_,i)=>({x:480-i*20,y:340-i*5}));
  const original=structuredClone(points),sampled=sampleTrail(points,head);
  const length=trail=>{
    let lead=head,total=0;
    for(const point of trail){total+=Math.hypot(point.x-lead.x,point.y-lead.y);lead=point}
    return total;
  };
  assert.equal(TRAIL_PROFILE.lengthScale,.66);
  assert.ok(Math.abs(length(sampled)/(length(points)*.44)-1.5)<1e-10);
  assert.deepEqual(points,original);
  assert.deepEqual(head,{x:500,y:350});
  assert.deepEqual(sampleTrail(resetTrail(head),head),resetTrail(head));
  assert.equal(cursorRadius(1440,1000),24);
  assert.ok(Math.abs(cursorRadius(1440,1000)*TRAIL_PROFILE.maxGap-32*2.4)<1e-10);
});

test('rapid pointer movement retains a fixed finite trail and bounded segment gaps',()=>{
  let trail=resetTrail({x:100,y:100});
  for(let step=0;step<1000;step++){
    const head={x:step%2?2000:0,y:step%3?0:1000};
    trail=followTrail(trail,head,step%7?16:1000,24);
    let lead=head;
    for(const point of trail){
      assert.ok(Number.isFinite(point.x)&&Number.isFinite(point.y));
      assert.ok(Math.hypot(lead.x-point.x,lead.y-point.y)<=24*TRAIL_PROFILE.maxGap+1e-7);
      lead=point;
    }
    assert.equal(trail.length,TRAIL_PROFILE.links);
  }
});

test('invalid cursor and trail inputs fail rather than corrupting the renderer',()=>{
  assert.throws(()=>cursorRadius(0,1000),RangeError);
  assert.throws(()=>resetTrail({x:NaN,y:0}),RangeError);
  const points=resetTrail({x:0,y:0});
  assert.throws(()=>followTrail([], {x:0,y:0},16,20),RangeError);
  assert.throws(()=>followTrail(points,{x:Infinity,y:0},16,20),RangeError);
  assert.throws(()=>followTrail(points,{x:0,y:0},-1,20),RangeError);
  assert.throws(()=>followTrail(points,{x:0,y:0},16,0),RangeError);
  assert.throws(()=>sampleTrail([], {x:0,y:0}),RangeError);
  assert.throws(()=>sampleTrail(points,{x:NaN,y:0}),RangeError);
});
