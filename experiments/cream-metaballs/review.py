"""Numerically check the isolated shader study and generate one unviewed review sheet."""

import argparse
import base64
from collections import deque
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
SVG = "{http://www.w3.org/2000/svg}"

def fixed_seed(page, seed=2):
    page.add_init_script(f"crypto.getRandomValues=array=>{{array[0]={seed};return array}}")

def recipe_metrics(page):
    return page.evaluate("""async()=>{
      const model=await import('./model.mjs'),canvas=document.getElementById('material');
      const recipe=model.createSceneRecipe(Number(canvas.dataset.sceneSeed));
      return {count:recipe.clumps.length,groups:recipe.groupCount,droplets:recipe.dropletCount,
        primitives:model.expandScoops(model.seedScoops(innerWidth,innerHeight,recipe)).length,
        capacity:model.MAX_PRIMITIVES,placementSlots:model.PLACEMENT_SLOTS};
    }""")


def check_etching_asset():
    assets=Path(__file__).resolve().parent/"assets"
    original=ET.parse(assets/"bakery-pattern-cream.svg").getroot().find(SVG+"g")
    etched=ET.parse(assets/"bakery-glass-etching.svg").getroot()
    lines=etched.find(f"{SVG}defs/{SVG}g")
    def geometry(node,root=False):
        ignored={"stroke","opacity","id"} if root else set()
        return (node.tag,sorted((k,v) for k,v in node.attrib.items() if k not in ignored),
                [geometry(child) for child in node])
    assert geometry(original,True)==geometry(lines,True),"Etching must retain the original icon paths, not trace the reference image."
    ids={node.get("id") for node in etched.iter() if node.get("id")}
    for node in etched.iter():
        assert node.tag not in {SVG+"script",SVG+"image",SVG+"foreignObject",SVG+"animate",SVG+"animateTransform"}
        for key,value in node.attrib.items():
            assert not key.lower().startswith("on")
            if key.endswith("href"):
                assert value.startswith("#") and value[1:] in ids
    assert len(etched.findall(SVG+"use"))==3
    return {"original_geometry_retained":True,"recess_highlight_and_frost_layers":3,
            "external_or_embedded_reference_pixels":False}


def pixels(page):
    return page.locator("#material").evaluate("""canvas=>{
      const gl=canvas.getContext('webgl2'),data=new Uint8Array(canvas.width*canvas.height*4);
      gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,data);
      let hash=2166136261,min=255,max=0;
      for(let i=0;i<data.length;i++){hash=Math.imul(hash^data[i],16777619)>>>0;if(i%4!==3){min=Math.min(min,data[i]);max=Math.max(max,data[i]);}}
      const overlay=document.getElementById('cream-pointer');
      let pointer=null;
      if(overlay){
        const context=overlay.getContext('2d'),rgba=!overlay.hidden&&context?.getImageData(0,0,overlay.width,overlay.height).data;
        let overlayHash=2166136261,opaquePixels=0,pinkPixels=0;
        if(rgba)for(let i=0;i<rgba.length;i++){
          overlayHash=Math.imul(overlayHash^rgba[i],16777619)>>>0;
          if(i%4===0&&rgba[i+3]>=128){
            opaquePixels++;
            if(rgba[i]>rgba[i+1]+15&&rgba[i+2]>rgba[i+1]+5)pinkPixels++;
          }
        }
        pointer={hash:overlay.hidden?null:overlayHash,opaquePixels,pinkPixels,width:overlay.width,height:overlay.height,
          visible:!overlay.hidden,paints:Number(overlay.dataset.paintCount||0)};
      }
      return {hash,min,max,glError:gl.getError(),width:canvas.width,height:canvas.height,
        pointer,
        paints:Number(canvas.dataset.paintCount),scoops:Number(canvas.dataset.scoopCount),
        primitives:Number(canvas.dataset.primitiveCount),capacity:Number(canvas.dataset.primitiveCapacity),
        seedCount:Number(canvas.dataset.seedCount),sceneSeed:Number(canvas.dataset.sceneSeed),
        peaks:Number(canvas.dataset.peakCount),clock:Number(canvas.dataset.motionTime),state:canvas.dataset.state,
        cursorRadius:Number(canvas.dataset.cursorRadius),trailSegments:Number(canvas.dataset.trailSegments),
        positions:Array.from({length:Math.min(6,Number(canvas.dataset.scoopCount))},(_,i)=>
          Array.from(gl.getUniform(gl.getParameter(gl.CURRENT_PROGRAM),
            gl.getUniformLocation(gl.getParameter(gl.CURRENT_PROGRAM),'scoops['+i+']'))))};
    }""")


def check_focus_recovery(browser, url):
    page=browser.new_page(viewport={"width":1000,"height":800},reduced_motion="no-preference")
    fixed_seed(page)
    page.goto(url,wait_until="networkidle")
    expect(page.locator("#material")).to_have_attribute("data-state","moving")
    records=[]
    for action in ("resume-button","pointer","pageshow","visibility-return"):
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        expect(page.locator("#status")).to_contain_text("inactive")
        before=pixels(page)
        page.wait_for_timeout(250)
        assert pixels(page)==before,"An inactive preview must remain frozen."
        assert page.evaluate("document.hasFocus()"),"This fixture simulates a missed focus-return event."
        if action=="resume-button":
            page.locator("#pause").click()
            page.locator("#pause").click()
        elif action=="pointer":
            page.mouse.move(380,300)
        elif action=="pageshow":
            page.evaluate("window.dispatchEvent(new Event('pageshow'))")
        else:
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        expect(page.locator("#material")).to_have_attribute("data-state","moving")
        page.wait_for_timeout(180)
        after=pixels(page)
        assert after["clock"]>before["clock"] and after["paints"]>before["paints"]
        assert after["positions"]!=before["positions"] and after["hash"]!=before["hash"]
        assert after["clock"]-before["clock"]<.5,"Recovery must not replay elapsed inactive time."
        expect(page.locator("#status")).not_to_contain_text("inactive")
        records.append({"action":action,"clock_advance":after["clock"]-before["clock"],
                        "moving_pixels":True,"no_wall_clock_catchup":True})
    page.locator("#pause").click()
    page.evaluate("window.dispatchEvent(new Event('blur'));window.dispatchEvent(new Event('pageshow'))")
    expect(page.locator("#material")).to_have_attribute("data-state","still")
    held=pixels(page)
    page.mouse.move(390,310)
    page.wait_for_timeout(250)
    assert pixels(page)==held,"Focus recovery must not override an explicit user pause."
    page.locator("#pause").click()
    page.emulate_media(reduced_motion="reduce")
    expect(page.locator("#material")).to_have_attribute("data-state","still")
    page.evaluate("window.dispatchEvent(new Event('blur'));window.dispatchEvent(new Event('pageshow'))")
    expect(page.locator("#material")).to_have_attribute("data-state","still")
    reduced=pixels(page)
    page.mouse.move(400,320)
    page.wait_for_timeout(250)
    assert pixels(page)==reduced,"Focus recovery must respect reduced-motion preferences."
    expect(page.locator("#status")).to_contain_text("Reduced motion")
    page.close()
    return {"cases":records,"explicit_pause_retained":True,"reduced_motion_retained":True}


def check_frosted_pane(page):
    pane=page.locator(".reading-surface")
    glass=page.locator(".glass-sheet")
    style=glass.evaluate("""n=>{
      const s=getComputedStyle(n);
      return {background:s.backgroundColor,backdrop:s.backdropFilter,filter:s.filter,
        shadow:s.boxShadow,bounds:{x:n.getBoundingClientRect().x,y:n.getBoundingClientRect().y,
          width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height}};
    }""")
    assert "blur(8px)" in style["backdrop"] and style["filter"]=="none",style
    assert float(re.findall(r"[\d.]+",style["background"])[-1])==.10,style
    bounds=pane.bounding_box()
    assert abs(style["bounds"]["x"]-bounds["x"])<1 and style["bounds"]["y"]==0
    assert abs(style["bounds"]["width"]-bounds["width"])<1 and style["bounds"]["height"]==page.viewport_size["height"]
    assert pane.evaluate("n=>getComputedStyle(n).backgroundColor==='rgba(0, 0, 0, 0)'&&getComputedStyle(n).backdropFilter==='none'")
    assert page.locator("header,footer").evaluate_all("nodes=>nodes.every(n=>getComputedStyle(n).backgroundImage==='none'&&getComputedStyle(n).backgroundColor==='rgba(0, 0, 0, 0)')")
    state=pixels(page)
    page.locator("#material").evaluate("""(canvas,box)=>{
      const gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),
        scoopLocation=gl.getUniformLocation(program,'scoops[0]'),
        countLocation=gl.getUniformLocation(program,'scoopCount'),
        trailLocation=gl.getUniformLocation(program,'trailCount'),
        count=gl.getUniform(program,countLocation),trailCount=gl.getUniform(program,trailLocation),
        original=new Float32Array(Number(canvas.dataset.primitiveCapacity)*4);
      for(let i=0;i<count;i++)original.set(gl.getUniform(program,gl.getUniformLocation(program,'scoops['+i+']')),i*4);
      const fixture=new Float32Array(Number(canvas.dataset.primitiveCapacity)*4);
      fixture.set([box.x+box.width*.5,box.y+box.height*.5,Math.min(innerWidth,innerHeight)*.18,.85]);
      window.__frostedProbe={
        show:()=>{gl.uniform4fv(scoopLocation,fixture);gl.uniform1i(countLocation,1);gl.uniform1i(trailLocation,0);gl.drawArrays(gl.TRIANGLES,0,3)},
        empty:()=>{gl.uniform1i(countLocation,0);gl.uniform1i(trailLocation,0);gl.drawArrays(gl.TRIANGLES,0,3)},
        restore:()=>{gl.uniform4fv(scoopLocation,original);gl.uniform1i(countLocation,count);gl.uniform1i(trailLocation,trailCount);gl.drawArrays(gl.TRIANGLES,0,3)}
      };
      window.__frostedProbe.show();
    }""",bounds)
    text_data=[]
    try:
        with_cream=Image.open(BytesIO(pane.screenshot())).convert("RGB")
        page.evaluate("window.__frostedProbe.empty()")
        without_cream=Image.open(BytesIO(pane.screenshot())).convert("RGB")
        difference=ImageChops.difference(with_cream,without_cream).convert("L")
        fraction=sum(difference.histogram()[4:])/(difference.width*difference.height)
        assert fraction>.05,f"The cream is still obscured by the reading pane: {fraction}"
        page.evaluate("window.__frostedProbe.show()")
        text_data=pane.evaluate("""n=>{
          const parent=n.getBoundingClientRect();
          const records=[...n.querySelectorAll('.eyebrow,h1,h1 em,.description,.hint')].map(t=>{
            const b=t.getBoundingClientRect(),s=getComputedStyle(t);
            return {tag:t.tagName,text:t.textContent,color:s.color,
              large:t.matches('h1,h1 em'),bounds:[b.x-parent.x,b.y-parent.y,b.width,b.height]};
          });
          window.__frostedText=[...n.children].map(t=>({node:t,visibility:t.style.visibility}));
          window.__frostedText.forEach(item=>item.node.style.visibility='hidden');
          return records;
        }""")
        backdrop=Image.open(BytesIO(pane.screenshot())).convert("RGB")
        def luminance(rgb):
            values=[c/255 for c in rgb]
            linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in values]
            return sum(value*weight for value,weight in zip(linear,(.2126,.7152,.0722)))
        scale_x,scale_y=backdrop.width/bounds["width"],backdrop.height/bounds["height"]
        for text in text_data:
            x,y,w,h=text["bounds"]
            sample=backdrop.crop((round(x*scale_x),round(y*scale_y),round((x+w)*scale_x),round((y+h)*scale_y)))
            sample.thumbnail((max(1,sample.width//3),max(1,sample.height//3)))
            foreground=luminance([float(v) for v in re.findall(r"[\d.]+",text["color"])[:3]])
            background_levels=[luminance(pixel) for pixel in sample.getdata()]
            minimum=min((max(foreground,value)+.05)/(min(foreground,value)+.05) for value in background_levels)
            assert minimum >= (3 if text["large"] else 4.5),(text,minimum)
            text["minimum_sampled_contrast"]=round(minimum,3)
    finally:
        page.evaluate("""()=>{
          window.__frostedText?.forEach(item=>item.node.style.visibility=item.visibility);
          window.__frostedProbe?.restore();
          delete window.__frostedText;delete window.__frostedProbe;
        }""")
    assert pixels(page)["hash"]==state["hash"],"The visibility fixture must restore the original paused frame."
    session=page.context.new_cdp_session(page)
    session.send("Emulation.setEmulatedMedia",{"features":[{"name":"prefers-reduced-transparency","value":"reduce"}]})
    try:
        assert glass.evaluate("n=>getComputedStyle(n).backdropFilter")=="none"
        assert glass.evaluate("n=>getComputedStyle(n).backgroundColor")=="rgba(245, 235, 221, 0.94)"
    finally:
        session.send("Emulation.setEmulatedMedia",{"features":[]})
        session.detach()
    return {"center_column_glass":style,"cream_changed_fraction":fraction,"reading_contrast":text_data,
            "text_and_controls_unblurred":True,"reduced_transparency_fallback":True}


def check_sides_and_etching(page):
    state=pixels(page)
    page.locator("#material").evaluate("""async canvas=>{
      const {expandScoops,seedScoops,createSceneRecipe}=await import('./model.mjs');
      const anchors=seedScoops(innerWidth,innerHeight,createSceneRecipe(Number(canvas.dataset.sceneSeed)));
      const membership=expandScoops(anchors).map(s=>anchors[s.parent].side);
      const gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),
        location=gl.getUniformLocation(program,'scoops[0]'),
        count=gl.getUniform(program,gl.getUniformLocation(program,'scoopCount')),
        original=new Float32Array(Number(canvas.dataset.primitiveCapacity)*4);
      for(let i=0;i<count;i++)original.set(gl.getUniform(program,gl.getUniformLocation(program,'scoops['+i+']')),i*4);
      window.__sideProbe={
        hide:side=>{const sample=new Float32Array(original);
          membership.forEach((parent,i)=>{if(parent===side){sample[i*4]=-10000;sample[i*4+1]=-10000}});
          gl.uniform4fv(location,sample);gl.drawArrays(gl.TRIANGLES,0,3)},
        restore:()=>{gl.uniform4fv(location,original);gl.drawArrays(gl.TRIANGLES,0,3)}
      };
    }""")
    baseline=Image.open(BytesIO(page.screenshot())).convert("RGB")
    side_changes={}
    try:
        for side in ("left","right"):
            page.evaluate("side=>window.__sideProbe.hide(side)",side)
            hidden=Image.open(BytesIO(page.screenshot())).convert("RGB")
            page.evaluate("window.__sideProbe.restore()")
            box=(0,0,round(baseline.width*.46),baseline.height) if side=="left" else (
               round(baseline.width*.54),0,baseline.width,baseline.height)
            difference=ImageChops.difference(baseline.crop(box),hidden.crop(box)).convert("L")
            fraction=sum(difference.histogram()[4:])/(difference.width*difference.height)
            assert fraction>.01,f"The {side} cream is not meaningfully visible: {fraction}"
            side_changes[side]=fraction
    finally:
        page.evaluate("window.__sideProbe.restore();delete window.__sideProbe")
    assert pixels(page)["hash"]==state["hash"]
    pattern=page.locator(".glass-etchings")
    pattern.evaluate("n=>n.style.visibility='hidden'")
    try:
        no_etching=Image.open(BytesIO(page.screenshot())).convert("RGB")
    finally:
        pattern.evaluate("n=>n.style.removeProperty('visibility')")
    difference=ImageChops.difference(baseline,no_etching).convert("L")
    etched_fraction=sum(difference.histogram()[2:])/(difference.width*difference.height)
    assert etched_fraction>.003,f"The etched layer does not affect visible pixels: {etched_fraction}"
    restored=Image.open(BytesIO(page.screenshot())).convert("RGB")
    assert ImageChops.difference(baseline,restored).getbbox() is None
    return {"side_cream_pixel_change":side_changes,"etched_pixel_fraction":etched_fraction,
            "paused_frame_restored":True,"recess_and_light_edge_layers":True}


def check_center_glass_scope(page):
    glass=page.locator(".glass-sheet").bounding_box()
    etchings=page.locator(".glass-etchings").bounding_box()
    assert glass==etchings, "Etchings must share the same bounded center pane."
    before=Image.open(BytesIO(page.screenshot())).convert("RGB")
    fixture=page.add_style_tag(content=".glass-sheet,.glass-etchings { visibility: hidden !important; }")
    try:
        without=Image.open(BytesIO(page.screenshot())).convert("RGB")
    finally:
        fixture.evaluate("n=>n.remove()")
    scale=before.width/page.viewport_size["width"]
    left,right=round(glass["x"]*scale),round((glass["x"]+glass["width"])*scale)
    difference=ImageChops.difference(before,without)
    for box in [(0,0,left,before.height),(right,0,before.width,before.height)]:
        assert difference.crop(box).getbbox() is None,"Glass or etched decoration leaks into a side column."
    center=difference.crop((left,0,right,before.height)).convert("L")
    changed=sum(center.histogram()[2:])/(center.width*center.height)
    assert changed>.005, "The center pane must actually retain its frosted/etched treatment."
    return {"center_bounds":glass,"outside_pane_pixel_changes":0,
            "center_changed_fraction":changed,"etchings_clipped_to_same_column":True}


def check_background_layers(page):
    pattern=page.locator(".side-background")
    expect(pattern).to_have_attribute("aria-hidden","true")
    properties=pattern.evaluate("""n=>{
      const style=getComputedStyle(n),center=getComputedStyle(n,'::after'),box=n.getBoundingClientRect(),
        transform=new DOMMatrixReadOnly(center.transform);
      return {image:style.backgroundImage,size:style.backgroundSize,z:style.zIndex,events:style.pointerEvents,
        opacity:style.opacity,centerLeft:box.left+parseFloat(center.left)+transform.m41,
        centerWidth:parseFloat(center.width),centerBackground:center.backgroundColor};
    }""")
    glass=page.locator(".glass-sheet").bounding_box()
    assert properties["size"]=="640px 480px" and "bakery-pattern-cream.svg" in properties["image"]
    assert properties["z"]=="-1" and properties["events"]=="none" and properties["opacity"]=="1"
    assert abs(properties["centerLeft"]-glass["x"])<.1 and abs(properties["centerWidth"]-glass["width"])<.1
    assert properties["centerBackground"]=="rgb(245, 235, 221)"
    canvas=page.locator("#material")
    data=canvas.evaluate("""n=>{
      const gl=n.getContext('webgl2');return {attributes:gl.getContextAttributes(),
        png:n.toDataURL('image/png').split(',')[1]};
    }""")
    assert data["attributes"]["alpha"] and data["attributes"]["premultipliedAlpha"]
    alpha=Image.open(BytesIO(base64.b64decode(data["png"]))).getchannel("A")
    assert alpha.getextrema()==(0,255),"The material canvas must have open ground and opaque cream."
    hidden_copy=page.add_style_tag(content="header,main,footer { visibility:hidden !important; }")
    try:
        with_pattern=Image.open(BytesIO(page.screenshot())).convert("RGB")
        pattern.evaluate("n=>n.style.visibility='hidden'")
        without_pattern=Image.open(BytesIO(page.screenshot())).convert("RGB")
        pattern.evaluate("n=>n.style.removeProperty('visibility')")
        canvas.evaluate("n=>n.style.visibility='hidden'")
        ground=Image.open(BytesIO(page.screenshot())).convert("RGB")
    finally:
        pattern.evaluate("n=>n.style.removeProperty('visibility')")
        canvas.evaluate("n=>n.style.removeProperty('visibility')")
        hidden_copy.evaluate("n=>n.remove()")
    scale=with_pattern.width/page.viewport_size["width"]
    left,right=round(glass["x"]*scale),round((glass["x"]+glass["width"])*scale)
    difference=ImageChops.difference(with_pattern,without_pattern)
    values=difference.convert("L")
    sides=[(0,0,left,values.height),(right,0,values.width,values.height)]
    visible=[]
    for box in sides:
        crop=values.crop(box)
        fraction=sum(crop.histogram()[2:])/(crop.width*crop.height)
        assert fraction>.001,f"Pattern is not visible behind a side column: {fraction}"
        visible.append(fraction)
    inset=round(32*scale)
    assert not difference.crop((left+inset,0,right-inset,values.height)).getbbox(), "Background pattern leaks into the center glass interior."
    core=alpha.resize(values.size,Image.Resampling.NEAREST).filter(ImageFilter.MinFilter(11))
    core=core.point(lambda value:255 if value==255 else 0)
    side_mask=Image.new("L",values.size)
    draw=ImageDraw.Draw(side_mask)
    for box in sides:
        draw.rectangle(box,fill=255)
    core=ImageChops.multiply(core,side_mask)
    ground_difference=ImageChops.difference(ground,Image.new("RGB",ground.size,"#f5ebdd")).convert("L")
    patterned_core=ImageChops.multiply(core,ground_difference.point(lambda value:255 if value>=2 else 0))
    covered_pixels=patterned_core.histogram()[255]
    assert covered_pixels>100,"The pattern-occlusion probe must include actual ink underneath opaque cream."
    assert not ImageChops.multiply(difference.convert("RGB"),core.convert("RGB")).getbbox(), "Pattern is drawn over the cream rather than behind it."
    return {"side_pattern_properties":properties,"left_right_visible_ink_fractions":visible,
            "center_interior_pattern_changes":0,"pattern_pixels_occluded_by_cream":covered_pixels,
            "pattern_changes_through_opaque_cream":0,"associated_alpha_canvas":True}


def coverage_components(image):
    width,height=image.size
    values=image.convert("L").tobytes()
    visited=bytearray(len(values))
    components=[]
    for start,value in enumerate(values):
        if value<128 or visited[start]:
            continue
        queue=deque([start])
        visited[start]=1
        area=0
        left=right=start%width
        top=bottom=start//width
        while queue:
            index=queue.popleft()
            x,y=index%width,index//width
            area+=1
            left,right=min(left,x),max(right,x)
            top,bottom=min(top,y),max(bottom,y)
            for next_y in range(max(0,y-1),min(height,y+2)):
                for next_x in range(max(0,x-1),min(width,x+2)):
                    neighbor=next_y*width+next_x
                    if not visited[neighbor] and values[neighbor]>=128:
                        visited[neighbor]=1
                        queue.append(neighbor)
        components.append({"area":area,"bounds":[left,top,right+1,bottom+1],"sample":[start%width,start//width]})
    return components


def check_ambient_separation(browser,url,seeds=(0,1,2)):
    records=[]
    for width,height in [(320,568),(844,390),(1440,1000)]:
        context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1)
        page=context.new_page()
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.add_init_script("""(()=>{
          const original=WebGL2RenderingContext.prototype.shaderSource;
          WebGL2RenderingContext.prototype.shaderSource=function(shader,source){
            if(source.includes('float creamHeight(')){
              const output='color=vec4(clamp(cream,0.,1.)*coverage,alpha);';
              if(!source.includes(output))throw new Error('Coverage fixture no longer matches the material shader.');
              source=source.replace(output,'color=vec4(vec3(coverage),1.);');
            }
            return original.call(this,shader,source);
          };
        })()""")
        page.goto(url,wait_until="networkidle")
        expect(page.locator("body")).to_have_class("ready")
        page.locator("#pause").click()
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        page.add_style_tag(content="header, main, footer, .glass-etchings { visibility: hidden !important; }")
        times=page.evaluate("""async seeds=>{
          const {createSceneRecipe,MOTION_PROFILE}=await import('./model.mjs');
          return seeds.flatMap(seed=>{
            const period=createSceneRecipe(seed).clumps.find(s=>s.lobeMotion?.canDetach).lobeMotion.period/MOTION_PROFILE.lobeRate;
            return [0,period/4,period/2,period,90,3600].map(seconds=>({seed,seconds}));
          });
        }""",list(seeds))
        for case in times:
            seed,seconds=case["seed"],case["seconds"]
            measured=page.evaluate("""async ({seed,seconds})=>{
              const {seedScoops,sampleScoops,expandScoops,MAX_PRIMITIVES,createSceneRecipe}=await import('./model.mjs'),
                recipe=createSceneRecipe(seed),
                anchors=sampleScoops(seedScoops(innerWidth,innerHeight,recipe),seconds,innerWidth,innerHeight),
                forms=expandScoops(anchors),
                canvas=document.getElementById('material'),gl=canvas.getContext('webgl2'),
                program=gl.getParameter(gl.CURRENT_PROGRAM),data=new Float32Array(MAX_PRIMITIVES*4);
              forms.forEach((s,i)=>data.set([s.x,s.y,s.radius,s.peak],i*4));
              gl.uniform4fv(gl.getUniformLocation(program,'scoops[0]'),data);
              gl.uniform1i(gl.getUniformLocation(program,'scoopCount'),forms.length);
              gl.uniform1i(gl.getUniformLocation(program,'trailCount'),0);
              gl.uniform1f(gl.getUniformLocation(program,'cursorTint'),0);
              gl.drawArrays(gl.TRIANGLES,0,3);gl.finish();
              const gaps=[];
              for(let i=0;i<anchors.length;i++)for(let j=i+1;j<anchors.length;j++){
                const a=anchors[i],b=anchors[j];gaps.push(Math.hypot(a.x-b.x,a.y-b.y)-a.radius*a.envelope-b.radius*b.envelope);
              }
              const topology=anchors.map((anchor,parent)=>{
                const lobes=forms.filter(s=>s.parent===parent),visited=new Set();
                let components=0;
                for(let first=0;first<lobes.length;first++){
                  if(visited.has(first))continue;
                  components++;const pending=[first];visited.add(first);
                  while(pending.length){
                    const i=pending.pop(),a=lobes[i];
                    for(let j=0;j<lobes.length;j++){
                      const b=lobes[j];
                      if(!visited.has(j)&&Math.hypot(a.x-b.x,a.y-b.y)-a.radius-b.radius<=Math.min(innerWidth,innerHeight)*.020){
                        visited.add(j);pending.push(j);
                      }
                    }
                  }
                }
                return components;
              });
              window.__clumpCoverage={gl,program,forms,anchors,data};
              return {minimumGap:Math.min(...gaps),radii:anchors.map(s=>s.radius),anchors,
                topology,groupCount:recipe.groupCount,dropletCount:recipe.dropletCount,
                primitiveCount:forms.length,error:gl.getError()};
            }""",{"seed":seed,"seconds":seconds})
            assert measured["error"]==0 and measured["minimumGap"]>min(width,height)*.024,measured
            image=Image.open(BytesIO(page.screenshot())).convert("RGB")
            components=coverage_components(image)
            count=len(measured["anchors"])
            assert len(components)>=count, (width,height,seed,seconds,components)
            areas=[component["area"] for component in components]
            assert min(areas)>0 and max(areas)/min(areas)>3,areas
            source=page.locator("#material").evaluate("n=>n.toDataURL('image/png').split(',')[1]")
            source_components=coverage_components(Image.open(BytesIO(base64.b64decode(source))).convert("RGB"))
            assert len(source_components)==sum(measured["topology"]),(width,height,seed,seconds,measured["topology"],source_components)
            memberships=[[] for _ in measured["anchors"]]
            for component in source_components:
                x,y=component["sample"]
                parents=[i for i,a in enumerate(measured["anchors"]) if
                         ((x-a["x"])**2+(y-a["y"])**2)**.5<=a["radius"]*a["envelope"]+2]
                assert len(parents)==1,("Ambiguous/escaped group",component,parents)
                memberships[parents[0]].append(component)
            assert [len(group) for group in memberships]==measured["topology"]
            page.evaluate("""()=>{
              const {gl,program,anchors}=window.__clumpCoverage;
              gl.uniform1i(gl.getUniformLocation(program,'scoopCount'),anchors.length);
              gl.drawArrays(gl.TRIANGLES,0,3);gl.finish();
            }""")
            source=page.locator("#material").evaluate("n=>n.toDataURL('image/png').split(',')[1]")
            main_image=Image.open(BytesIO(base64.b64decode(source))).convert("RGB")
            main_components=coverage_components(main_image)
            assert len(main_components)==count,(width,height,seconds,main_components)
            protrusions=[]
            for index,anchor in enumerate(measured["anchors"]):
                contains=lambda component: component["bounds"][0]<=anchor["x"]<component["bounds"][2] and component["bounds"][1]<=anchor["y"]<component["bounds"][3]
                assert any(contains(c) and c["area"]>=16 for c in components),"Every parent body must remain visible through the glass."
                group=next(c for c in memberships[index] if contains(c))
                main=next(c for c in main_components if contains(c))
                ratio=group["area"]/main["area"]
                if anchor.get("kind")=="group" and (seconds==0 or anchor.get("lobeMotion",{}).get("mode")=="together"):
                    assert ratio>1.20,("Attached lobes must add over 20% actual area to their parent",width,height,seconds,anchor["clump"],ratio)
                if anchor.get("kind")=="droplet":
                    assert len(memberships[index])==1 and group["area"]>100
                    assert any(contains(c) for c in components),"Each added droplet must remain visible through the glass."
                for piece in memberships[index]:
                    x0,y0,x1,y1=piece["bounds"]
                    bound=anchor["radius"]*anchor["envelope"]
                    assert x0>=anchor["x"]-bound-2 and x1<=anchor["x"]+bound+2
                    assert y0>=anchor["y"]-bound-2 and y1<=anchor["y"]+bound+2
                protrusions.append(ratio)
            giant_group=memberships[0]
            giant=max(max(c["bounds"][2] for c in giant_group)-min(c["bounds"][0] for c in giant_group),
                      max(c["bounds"][3] for c in giant_group)-min(c["bounds"][1] for c in giant_group))/min(width,height)
            assert giant>.40,("The actual giant silhouette must span over 40% of the shorter viewport",giant)
            records.append({"viewport":[width,height],"seed":seed,"seconds":seconds,**measured,
                            "largest_rendered_diameter_fraction":giant,
                            "separate_frosted_components":len(components),"component_areas":areas,
                            "joined_lobe_area_ratios":protrusions,
                            "lobe_geometry_measurement":"Native SDF component membership matches analytical circle/smooth-union connectivity; droplets and all parent groups remain visible after filters."})
        assert not errors,errors
        context.close()
    return {"cases":records,"coverage_method":"Actual material SDF rendered as coverage, through the canvas and center-column glass; eight-connected pixel components.",
            "cursor_and_user_placed_scoops_excluded_from_ambient_fixture":True,"image_tool_views":0}


def check_refresh_recipes(browser,url):
    records=[]
    for seed in (0,1,2):
        page=browser.new_page(viewport={"width":1000,"height":1000},reduced_motion="reduce")
        fixed_seed(page,seed)
        page.goto(url,wait_until="networkidle")
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        initial=pixels(page)
        metrics=recipe_metrics(page)
        count=metrics["count"]
        assert initial["sceneSeed"]==seed and initial["seedCount"]==count
        assert metrics["groups"]==4+seed and 5<=metrics["droplets"]<=8
        for index in range(12):
            page.mouse.click(450+index*4,400)
        expect(page.locator("#material")).to_have_attribute("data-scoop-count",str(count+12))
        placed=page.locator("#material").evaluate("""n=>{
          const gl=n.getContext('webgl2'),p=gl.getParameter(gl.CURRENT_PROGRAM);
          return Array.from(gl.getUniform(p,gl.getUniformLocation(p,'scoops['+n.dataset.seedCount+']')));
        }""")
        assert abs(placed[0]-450)<.001 and abs(placed[1]-400)<.001 and abs(placed[2]-75)<.001
        assert pixels(page)["primitives"]<=initial["capacity"]
        page.mouse.click(650,450)
        expect(page.locator("#status")).to_contain_text("limit")
        assert pixels(page)["scoops"]==count+12
        page.set_viewport_size({"width":390,"height":844})
        expect(page.locator("#material")).to_have_attribute("width","390")
        assert pixels(page)["sceneSeed"]==seed and pixels(page)["scoops"]==count+12
        page.set_viewport_size({"width":1000,"height":1000})
        page.locator("#reset").click()
        expect(page.locator("#material")).to_have_attribute("data-scoop-count",str(count))
        restored=pixels(page)
        assert restored["sceneSeed"]==seed and restored["hash"]==initial["hash"]
        records.append({"seed":seed,"initial_count":count,"groups":metrics["groups"],"droplets":metrics["droplets"],"placement_slots":12,
                        "logical_index_verified":True,"resize_reset_same_recipe_and_pixels":True})
        page.close()
    page=browser.new_page(viewport={"width":600,"height":600},reduced_motion="reduce")
    refresh=[]
    for _ in range(8):
        page.goto(url,wait_until="networkidle")
        expect(page.locator("body")).to_have_class("ready")
        state=pixels(page)
        refresh.append({"seed":state["sceneSeed"],"count":state["seedCount"],"positions":state["positions"]})
    assert len({item["seed"] for item in refresh})==len(refresh)
    assert len({json.dumps(item["positions"]) for item in refresh})==len(refresh)
    page.close()
    page=browser.new_page(reduced_motion="reduce")
    page.add_init_script("crypto.getRandomValues=()=>{throw new Error('Fixture: entropy API unavailable')};Math.random=()=>2/4294967296")
    page.goto(url,wait_until="networkidle")
    expect(page.locator("body")).to_have_class("ready")
    assert pixels(page)["sceneSeed"]==2 and pixels(page)["seedCount"]==recipe_metrics(page)["count"]
    page.close()
    return {"seeded_lifecycle":records,"actual_refreshes":refresh,"safe_rng_fallback":True}


def check_cursor_change(browser,url,baseline_model):
    records=[]
    for width,height in ((1440,1000),(390,844),(844,390)):
        page=browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce")
        fixed_seed(page)
        page.route("**/__previous-model.mjs",lambda route:route.fulfill(
            body=baseline_model.read_text(encoding="utf-8"),content_type="text/javascript"))
        page.goto(url,wait_until="networkidle")
        expect(page.locator("body")).to_have_class("ready")
        for speed in (.014,.035):
            result=page.evaluate("""async speed=>{
              const models=[await import('./__previous-model.mjs'),await import('./model.mjs')];
              const canvas=document.getElementById('material'),gl=canvas.getContext('webgl2'),
                program=gl.getParameter(gl.CURRENT_PROGRAM),unit=Math.min(innerWidth,innerHeight);
              const metrics=[];
              for(const model of models){
                let head={x:0,y:0},points=model.resetTrail(head);
                const radius=model.cursorRadius(innerWidth,innerHeight);
                for(let frame=1;frame<=40;frame++){
                  head=model.followPointer(head,{x:frame*unit*speed,y:0},1000/30);
                  points=model.followTrail(points,head,1000/30,radius);
                }
                const offset={x:innerWidth*.76-head.x,y:innerHeight*.5};
                head={x:head.x+offset.x,y:offset.y};
                points=points.map(p=>({x:p.x+offset.x,y:offset.y}));
                const path=model.sampleTrail(points,head),data=new Float32Array(Number(canvas.dataset.primitiveCapacity)*4),
                  tail=new Float32Array(8*4);
                data.set([head.x,head.y,radius,0]);
                let lead=head,length=0;
                path.forEach((point,i)=>{
                  tail.set([lead.x,lead.y,point.x,point.y],i*4);
                  length+=Math.hypot(point.x-lead.x,point.y-lead.y);lead=point;
                });
                gl.uniform4fv(gl.getUniformLocation(program,'scoops[0]'),data);
                gl.uniform1i(gl.getUniformLocation(program,'scoopCount'),1);
                gl.uniform4fv(gl.getUniformLocation(program,'trail[0]'),tail);
                gl.uniform1f(gl.getUniformLocation(program,'headRadius'),radius);
                const capture=count=>{
                  gl.uniform1i(gl.getUniformLocation(program,'trailCount'),count);
                  gl.drawArrays(gl.TRIANGLES,0,3);gl.finish();
                  const pixels=new Uint8Array(canvas.width*canvas.height*4);
                  gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
                  let left=canvas.width,right=0,area=0;
                  for(let i=0;i<pixels.length;i+=4)if(pixels[i+3]>=128){
                    const x=(i/4)%canvas.width;left=Math.min(left,x);right=Math.max(right,x);area++;
                  }
                  return {left,right,area,width:right-left+1,visibleBehindHead:head.x-left};
                };
                metrics.push({radius,pathLength:length,headFraction:model.TRAIL_PROFILE.headFraction,
                  tailEndRadius:model.TRAIL_PROFILE.endRadius,head:capture(0),withTrail:capture(8),error:gl.getError()});
              }
              return {before:metrics[0],after:metrics[1]};
            }""",speed)
            before,after=result["before"],result["after"]
            ratio=after["withTrail"]["visibleBehindHead"]/before["withTrail"]["visibleBehindHead"]
            assert before["error"]==after["error"]==0
            expected_head_ratio=after["headFraction"]/before["headFraction"]
            assert abs(after["radius"]/before["radius"]-expected_head_ratio)<1e-9
            assert abs(after["head"]["width"]-before["head"]["width"]*expected_head_ratio)<=2
            for frame in (before,after):
                expected_extent=max(frame["radius"],frame["pathLength"]+frame["radius"]*frame["tailEndRadius"])
                assert abs(frame["withTrail"]["visibleBehindHead"]-expected_extent)<=2,(width,height,speed,frame)
            expected_ratio=after["pathLength"]/before["pathLength"]
            assert abs(ratio-expected_ratio)<.08,(width,height,speed,result,ratio)
            assert after["withTrail"]["left"]>0 and after["withTrail"]["right"]<width-1
            records.append({"viewport":[width,height],"speed_per_frame_fraction":speed,**result,
                            "visible_trailing_extent_ratio":ratio})
        page.close()
    return {"cases":records,"method":"Same 40-frame pointer trace, original material shader, isolated head/tail; actual GPU alpha >= 128 excludes translucent shadows.",
            "baseline_model_sha256":sha256(baseline_model.read_bytes()).hexdigest(),"image_tool_views":0}


def check(url, out, baseline_model=None):
    out.mkdir(parents=True,exist_ok=True)
    frames=[]
    records={"etching_asset":check_etching_asset()}
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="msedge",headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1000})
        fixed_seed(page)
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.on("console",lambda message:errors.append(message.text) if message.type=="error" else None)
        page.goto(url,wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        expect(page.locator("body")).to_have_class("ready")
        before=pixels(page)
        metrics=recipe_metrics(page)
        ambient_count=metrics["count"]
        assert before["glError"]==0 and before["max"]-before["min"]>15,before
        assert before["primitives"]==metrics["primitives"] and before["capacity"]==36,before
        assert 9<=ambient_count<=14 and 5<=metrics["droplets"]<=8
        assert before["peaks"]==3,before
        assert before["cursorRadius"]==24,before
        pattern=page.locator(".butter-paper")
        expect(pattern).to_have_attribute("aria-hidden","true")
        assert pattern.evaluate("""n=>{
          const s=getComputedStyle(n);
          return s.backgroundImage.includes('assets/bakery-glass-etching.svg') &&
            s.backgroundSize==='640px 480px' && s.pointerEvents==='none' && s.zIndex==='2';
        }""")
        response=page.request.get(url.rstrip("/")+"/assets/bakery-pattern-cream.svg")
        original_pattern=(ROOT/"web"/"assets"/"bakery-pattern-cream.svg").read_bytes()
        assert response.ok and response.body()==original_pattern
        etched=page.request.get(url.rstrip("/")+"/assets/bakery-glass-etching.svg")
        assert etched.ok and b'etched-recess' in etched.body() and b'etched-light-edge' in etched.body()
        records["etched_pattern"]={"source_sha256":sha256(original_pattern).hexdigest(),"original_geometry_source_preserved":True,
                                  "etching_sha256":sha256(etched.body()).hexdigest(),
                                  "tile_css_pixels":[640,480],"above_glass_below_copy":True}
        motion_start=page.evaluate("performance.now()")
        motion_before=pixels(page)
        page.wait_for_timeout(700)
        drifting=pixels(page)
        motion_elapsed=page.evaluate("performance.now()")-motion_start
        assert drifting["hash"]!=motion_before["hash"] and drifting["paints"]>motion_before["paints"]+1
        assert drifting["positions"]!=motion_before["positions"] and drifting["clock"]>motion_before["clock"]
        displacements=[((later[0]-earlier[0])**2+(later[1]-earlier[1])**2)**.5
                       for earlier,later in zip(motion_before["positions"],drifting["positions"])]
        assert max(displacements[::2])>.3 and max(displacements[1::2])>.3,displacements
        for frame in (motion_before,drifting):
            assert all(s[0]-s[2]>=0 and s[0]+s[2]<=1440 and s[1]-s[2]>=0 and s[1]+s[2]<=1000 for s in frame["positions"])
        records["quarter_speed_side_motion"]={"interval_ms":motion_elapsed,"per_blob_displacement_px":displacements,
                                             "reserved_nonoverlapping_envelopes":True,"motion_rate_from_model":.6328125}
        assert drifting["paints"]-motion_before["paints"]<=motion_elapsed*.03+3,"Continuous rendering should respect its30fps ceiling."
        assert page.locator("#material").evaluate("n=>getComputedStyle(n).filter")=="blur(0.8px)"
        assert page.locator("header,main,footer,button").evaluate_all("nodes=>nodes.every(n=>getComputedStyle(n).filter==='none')")
        def freeze():
            if page.locator("#pause").get_attribute("aria-pressed")=="false":
                page.locator("#pause").click()
            expect(page.locator("#material")).to_have_attribute("data-state","still")
        def resume():
            if page.locator("#pause").get_attribute("aria-pressed")=="true":
                page.locator("#pause").click()
            expect(page.locator("#material")).to_have_attribute("data-state","moving")
        def capture(label,name):
            file=out/name
            page.screenshot(path=str(file))
            frames.append((label,file))
        freeze()
        capture("01 / Drifting pose held for inspection","01-initial.png")
        held=pixels(page)
        page.wait_for_timeout(700)
        assert pixels(page)==held,"Pause must freeze all forms and stop painting."
        records["frosted_pane"]=check_frosted_pane(page)
        records["both_sides_and_etchings"]=check_sides_and_etching(page)
        records["center_only_glass"]=check_center_glass_scope(page)
        records["background_layering"]=check_background_layers(page)
        peak_probe=page.locator("#material").evaluate("""canvas=>{
          const gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),
            location=gl.getUniformLocation(program,'scoops[0]'),
            count=gl.getUniform(program,gl.getUniformLocation(program,'scoopCount'));
          const original=new Float32Array(Number(canvas.dataset.primitiveCapacity)*4);
          for(let i=0;i<count;i++)original.set(gl.getUniform(program,gl.getUniformLocation(program,'scoops['+i+']')),i*4);
          const hash=()=>{
            const data=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,data);
            let h=2166136261;for(const value of data)h=Math.imul(h^value,16777619)>>>0;return h;
          };
          const peaked=hash(),flat=new Float32Array(original);
          for(let i=0;i<count;i++)flat[i*4+3]=0;
          gl.uniform4fv(location,flat);gl.drawArrays(gl.TRIANGLES,0,3);const rounded=hash();
          gl.uniform4fv(location,original);gl.drawArrays(gl.TRIANGLES,0,3);
          return {peaked,rounded,restored:hash(),error:gl.getError()};
        }""")
        assert peak_probe["peaked"]!=peak_probe["rounded"] and peak_probe["restored"]==peak_probe["peaked"]
        assert peak_probe["error"]==0
        softened=Image.open(BytesIO(page.screenshot())).convert("RGB")
        page.locator(".glass-sheet").evaluate("n=>{n.style.backdropFilter='none';n.style.webkitBackdropFilter='none'}")
        sharp=Image.open(BytesIO(page.screenshot())).convert("RGB")
        page.locator(".glass-sheet").evaluate("n=>{n.style.removeProperty('backdrop-filter');n.style.removeProperty('-webkit-backdrop-filter')}")
        blur_difference=ImageChops.difference(softened,sharp).convert("L")
        blur_fraction=sum(blur_difference.histogram()[2:])/(blur_difference.width*blur_difference.height)
        assert blur_fraction>.0001,"The blur must visibly affect the material rather than only set a flag."
        button=page.locator("#pause").bounding_box()
        interior=tuple(round(v) for v in (button["x"]+18,button["y"]+8,button["x"]+button["width"]-18,button["y"]+button["height"]-8))
        assert ImageChops.difference(softened.crop(interior),sharp.crop(interior)).getbbox() is None
        records["material_profile"]={"peak_uniform_probe":peak_probe,"canvas_blur_css_px":.8,
                                     "center_glass_blur_css_px":8,"blur_pixel_fraction":blur_fraction,"control_pixels_unchanged":True}
        resume()
        page.mouse.move(50,260,steps=12)
        page.wait_for_timeout(150)
        page.mouse.move(95,680,steps=3)
        page.wait_for_timeout(70)
        live_tail=pixels(page)
        assert live_tail["pointer"]["visible"] and live_tail["pointer"]["opaquePixels"]>0
        assert live_tail["pointer"]["pinkPixels"]>0,"The live overlay must contain actual strawberry pixels."
        freeze()
        trailed=pixels(page)
        assert trailed["cursorRadius"]==24 and trailed["trailSegments"]>=3,trailed
        trail_probe=page.locator("#material").evaluate("""canvas=>{
          const gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),
            location=gl.getUniformLocation(program,'trailCount'),count=gl.getUniform(program,location);
          const dataLocation=gl.getUniformLocation(program,'trail[0]'),
            scoopCount=gl.getUniform(program,gl.getUniformLocation(program,'scoopCount')),
            radius=gl.getUniform(program,gl.getUniformLocation(program,'headRadius')),
            scoopLocation=gl.getUniformLocation(program,'scoops[0]'),
            tintLocation=gl.getUniformLocation(program,'cursorTint'),
            tint=gl.getUniform(program,tintLocation),original=new Float32Array(8*4),
            ambient=new Float32Array(Number(canvas.dataset.primitiveCapacity)*4);
          for(let i=0;i<scoopCount;i++)ambient.set(gl.getUniform(program,gl.getUniformLocation(program,'scoops['+i+']')),i*4);
          for(let i=0;i<8;i++)original.set(gl.getUniform(program,gl.getUniformLocation(program,'trail['+i+']')),i*4);
          const head=[original[0],original[1],radius,0],pointer=new Float32Array(ambient.length);
          pointer.set(head);
          const gaps=Array.from({length:8},(_,i)=>Math.hypot(original[i*4]-original[i*4+2],original[i*4+1]-original[i*4+3]));
          const hash=()=>{
            const data=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,data);
            let h=2166136261;for(const value of data)h=Math.imul(h^value,16777619)>>>0;return h;
          };
          const ambientBefore=hash();
          gl.uniform4fv(scoopLocation,pointer);
          gl.uniform1i(gl.getUniformLocation(program,'scoopCount'),1);
          gl.uniform1f(tintLocation,1);
          gl.uniform1i(location,8);gl.drawArrays(gl.TRIANGLES,0,3);
          const withTrail=hash();
          gl.uniform1i(location,0);gl.drawArrays(gl.TRIANGLES,0,3);const withoutTrail=hash();
          gl.uniform1i(location,8);gl.drawArrays(gl.TRIANGLES,0,3);
          const expanded=new Float32Array(original);
          for(let i=0;i<expanded.length;i++)expanded[i]=head[i%2]+(expanded[i]-head[i%2])*3;
          gl.uniform4fv(dataLocation,expanded);gl.drawArrays(gl.TRIANGLES,0,3);const longerTrail=hash();
          gl.uniform4fv(dataLocation,original);gl.drawArrays(gl.TRIANGLES,0,3);
          const pointerRestored=hash();
          gl.uniform4fv(scoopLocation,ambient);
          gl.uniform1i(gl.getUniformLocation(program,'scoopCount'),scoopCount);
          gl.uniform1i(location,count);gl.uniform1f(tintLocation,tint);gl.drawArrays(gl.TRIANGLES,0,3);
          return {withTrail,withoutTrail,longerTrail,restored:pointerRestored,ambientBefore,ambientRestored:hash(),segments:8,error:gl.getError(),
            maximum_rendered_gap:Math.max(...gaps),headRadius:head[2],rendered_length:gaps.reduce((a,b)=>a+b,0),
            expanded_length:Array.from({length:8},(_,i)=>Math.hypot(expanded[i*4]-expanded[i*4+2],expanded[i*4+1]-expanded[i*4+3])).reduce((a,b)=>a+b,0)};
        }""")
        assert trail_probe["withTrail"]!=trail_probe["withoutTrail"] and trail_probe["restored"]==trail_probe["withTrail"]
        assert trail_probe["ambientRestored"]==trail_probe["ambientBefore"]
        assert trail_probe["longerTrail"]!=trail_probe["withTrail"],"Changing trail length must change actual rendered pixels."
        assert trail_probe["maximum_rendered_gap"]<=trail_probe["headRadius"]*3.2*.66+.001,trail_probe
        assert abs(trail_probe["expanded_length"]/trail_probe["rendered_length"]-3)<.001,trail_probe
        assert trail_probe["segments"]==8 and trail_probe["error"]==0
        held_tail=pixels(page);page.wait_for_timeout(300)
        assert pixels(page)==held_tail,"Pause must also freeze the trailing tail."
        assert not held_tail["pointer"]["visible"],"Pause restores the native pointer."
        resume()
        expect(page.locator("#material")).to_have_attribute("data-trail-segments","0",timeout=10000)
        assert pixels(page)["scoops"]==ambient_count
        records["cursor_trail"]={"radius_css_px":24,"previous_radius_css_px":32,"gpu_probe":trail_probe,
                                  "live_overlay":live_tail["pointer"],"ambient_excludes_pointer":True,
                                  "paused_tail_stays":True,"pause_restores_native_pointer":True,"tail_merges_into_head":True,"stored_scoops_unchanged":True}
        resume()
        page.mouse.move(1070,340,steps=12)
        page.wait_for_timeout(250);freeze()
        merged=pixels(page)
        assert merged["hash"]!=before["hash"] and merged["glError"]==0
        capture("02 / Pointer over the right side","02-merged.png")
        resume()
        page.mouse.move(750,260,steps=18)
        page.wait_for_timeout(250);freeze()
        capture("03 / Following the pointer","03-separated.png")
        page.mouse.click(780,520)
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        assert pixels(page)["scoops"]==ambient_count+1
        capture("04 / Placed scoop stays","04-scoop.png")
        rested=pixels(page)
        page.wait_for_timeout(500)
        assert pixels(page)==rested,"Paused retained forms must not change."
        page.locator("#clean").click()
        capture("05 / Copy hidden, glass and cream","05-material.png")
        paused=pixels(page)
        page.mouse.move(300,700,steps=16)
        page.wait_for_timeout(150)
        assert pixels(page)["hash"]==paused["hash"]
        resume()
        page.wait_for_timeout(500)
        assert pixels(page)["scoops"]==ambient_count+1,"Ambient movement must retain placed scoops."
        freeze()
        for index in range(11):
            page.mouse.click(620+(index%4)*70,280+(index//4)*75)
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        assert pixels(page)["scoops"]==ambient_count+12
        page.mouse.click(700,500)
        expect(page.locator("#status")).to_contain_text("limit")
        assert pixels(page)["scoops"]==ambient_count+12
        page.locator("#reset").click()
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        assert pixels(page)["scoops"]==ambient_count
        records["desktop"]={"initial":before,"autonomous_drift":drifting,"merged":merged,"placed":rested,
                            "paused_no_paints":True,"paused_pointer_no_change":True,"reset_restores_seed_count":True,
                            "retained_scoop_limit":ambient_count+12}
        resume()
        page.emulate_media(reduced_motion="reduce")
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        no_motion=pixels(page)
        page.mouse.move(900,600,steps=10)
        page.wait_for_timeout(120)
        assert pixels(page)["hash"]==no_motion["hash"]
        records["reduced_motion"]=True
        page.emulate_media(reduced_motion="no-preference")
        expect(page.locator("#material")).to_have_attribute("data-state","moving")
        page.wait_for_timeout(120)
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        blurred=pixels(page);page.wait_for_timeout(500)
        assert pixels(page)==blurred,"An inactive window must stop both paint and motion time."
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        page.wait_for_timeout(100)
        resumed=pixels(page)
        assert 0<resumed["clock"]-blurred["clock"]<.35,"Resume must not catch up the inactive wall clock."
        page.evaluate("""()=>{
          Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        hidden=pixels(page);page.wait_for_timeout(400)
        assert pixels(page)==hidden
        page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
        expect(page.locator("#material")).to_have_attribute("data-state","moving")
        records["inactive_clock_freezes"]={"blur":True,"injected_visibility_guard":True}
        records["missed_focus_recovery"]=check_focus_recovery(browser,url)
        page.bring_to_front()
        freeze()
        page.mouse.click(720,500)
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        assert pixels(page)["scoops"]==ambient_count+1
        placed_before=page.locator("#material").evaluate("""n=>{
          const gl=n.getContext('webgl2'),p=gl.getParameter(gl.CURRENT_PROGRAM);
          return Array.from(gl.getUniform(p,gl.getUniformLocation(p,'scoops['+n.dataset.seedCount+']')));
        }""")
        peak_count=pixels(page)["peaks"]
        page.set_viewport_size({"width":1000,"height":800})
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        page.wait_for_timeout(100)
        assert pixels(page)["peaks"]==peak_count and pixels(page)["scoops"]==ambient_count+1
        page.set_viewport_size({"width":1440,"height":1000})
        page.wait_for_timeout(100)
        assert pixels(page)["peaks"]==peak_count
        placed_after=page.locator("#material").evaluate("""n=>{
          const gl=n.getContext('webgl2'),p=gl.getParameter(gl.CURRENT_PROGRAM);
          return Array.from(gl.getUniform(p,gl.getUniformLocation(p,'scoops['+n.dataset.seedCount+']')));
        }""")
        assert max(abs(a-b) for a,b in zip(placed_before,placed_after))<.001
        records["resize_retains_peaks_and_placed_scoops"]=True
        for media in ("forced-colors","print"):
            if media=="forced-colors":page.emulate_media(forced_colors="active")
            else:page.emulate_media(media="print")
            expect(page.locator("#material")).to_be_hidden()
            state=pixels(page);page.wait_for_timeout(200)
            assert pixels(page)["paints"]==state["paints"]
            page.emulate_media(forced_colors="none",media="screen")
            expect(page.locator("#material")).to_have_attribute("data-state","still")
        records["forced_colors_print_no_render"]=True
        page.evaluate("""()=>{
          const gl=document.getElementById('material').getContext('webgl2');
          window.__contextLoss=gl.getExtension('WEBGL_lose_context');window.__contextLoss.loseContext();
        }""")
        expect(page.locator("#material")).to_be_hidden()
        page.wait_for_timeout(150)
        page.evaluate("window.__contextLoss.restoreContext()")
        page.wait_for_function("document.body.classList.contains('ready')")
        expect(page.locator("#material")).to_be_visible()
        assert pixels(page)["glError"]==0
        assert pixels(page)["peaks"]==peak_count
        records["context_loss_recovery"]=True
        page.close()
        page=browser.new_page(viewport={"width":1440,"height":1000},device_scale_factor=2)
        page.goto(url,wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        expect(page.locator("body")).to_have_class("ready")
        retina=pixels(page)
        assert retina["width"]==2880 and retina["height"]==2000 and retina["glError"]==0
        page.locator("#pause").click()
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        capture("06 / High-density layout","06-retina.png")
        records["retina"]=retina
        page.close()
        page=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        fixed_seed(page)
        page.goto(url,wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        expect(page.locator("body")).to_have_class("ready")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        touch_before=pixels(page);page.wait_for_timeout(600);touch_after=pixels(page)
        assert touch_after["hash"]!=touch_before["hash"] and touch_after["clock"]>touch_before["clock"]
        page.touchscreen.tap(200,480)
        page.wait_for_timeout(100)
        assert pixels(page)["scoops"]==ambient_count+1
        page.locator("#clean").click()
        page.locator("#pause").click()
        expect(page.locator("#material")).to_have_attribute("data-state","still")
        capture("07 / Touch material study","07-touch.png")
        records["touch"]={"no_horizontal_overflow":True,"autonomous_motion":True,"tap_adds_retained_scoop":True}
        page.close()
        page=browser.new_page()
        page.add_init_script("HTMLCanvasElement.prototype.getContext=function(){return null}")
        page.goto(url,wait_until="networkidle")
        expect(page.locator("#status")).to_contain_text("unavailable")
        expect(page.locator("#material")).to_be_hidden()
        expect(page.locator("#pause")).to_be_disabled()
        expect(page.locator(".side-background")).to_be_visible()
        assert page.locator(".static-material").evaluate(
            "n=>(getComputedStyle(n).backgroundImage.match(/radial-gradient/g)||[]).length")==metrics["primitives"]
        records["unavailable_webgl"]="Static visual fallback with visible explanation."
        page.close()
        context=browser.new_context(java_script_enabled=False,viewport={"width":390,"height":844})
        page=context.new_page();page.goto(url)
        expect(page.locator(".glass-sheet")).to_be_visible()
        expect(page.locator(".glass-etchings")).to_be_visible()
        expect(page.locator(".side-background")).to_be_visible()
        expect(page.locator("#status")).to_contain_text("JavaScript")
        expect(page.locator("#pause")).to_be_disabled()
        expect(page.locator("#reset")).to_be_disabled()
        records["no_javascript"]="Complete static glass, side forms and explicit inactive controls."
        context.close()
        page=browser.new_page(viewport={"width":1440,"height":1000},reduced_motion="reduce")
        page.goto(url,wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        layout_cases=[]
        for width in (320,390,600,768,900,1024,1440,1920):
            page.set_viewport_size({"width":width,"height":1000})
            metrics=page.evaluate("""()=>{
              const box=n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right,width:b.width}};
              const containers=[...document.querySelectorAll('.preview-container')].map(box);
              const copy=box(document.querySelector('.reading-surface'));
              return {containers,copy,scrollWidth:document.documentElement.scrollWidth,
                controlsFit:[...document.querySelectorAll('footer button,header a')].every(n=>{
                  const b=n.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth&&b.height>=48
                }),
                glass:(()=>{const r=document.querySelector('.glass-sheet').getBoundingClientRect();
                  return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}})()};
            }""")
            expected=min(1200,width-80) if width>900 else width-48 if width>600 else width-40
            assert len(metrics["containers"])==3,metrics
            for container in metrics["containers"]:
                assert abs(container["width"]-expected)<1 and abs(container["left"]-(width-expected)/2)<1,metrics
            assert abs((metrics["copy"]["left"]+metrics["copy"]["right"])/2-width/2)<1,metrics
            assert metrics["scrollWidth"]<=width,metrics
            assert metrics["controlsFit"],metrics
            glass_width=min(760,expected)
            assert metrics["glass"]=={"left":(width-glass_width)/2,"right":(width+glass_width)/2,"top":0,"bottom":1000},metrics
            background_center=page.locator(".side-background").evaluate("""n=>{
              const s=getComputedStyle(n,'::after'),b=n.getBoundingClientRect(),t=new DOMMatrixReadOnly(s.transform);
              return {left:b.left+parseFloat(s.left)+t.m41,width:parseFloat(s.width)};
            }""")
            assert background_center=={"left":(width-glass_width)/2,"width":glass_width},background_center
            page.evaluate("scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})")
            assert page.locator(".glass-sheet").evaluate("n=>{const r=n.getBoundingClientRect();return r.top===0&&r.bottom===innerHeight}"),metrics
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            layout_cases.append({"width":width,"content_width":expected,"gutter":(width-expected)/2})
        records["centered_layout"]=layout_cases
        page.close()
        records["separated_ambient_blobs"]=check_ambient_separation(browser,url)
        records["refresh_recipes"]=check_refresh_recipes(browser,url)
        if baseline_model:
            records["cursor_before_after"]=check_cursor_change(browser,url,baseline_model)
        assert not errors,errors
        browser.close()
    font=ImageFont.truetype(str(ROOT/"web"/"assets"/"fonts"/"dm-sans-regular.ttf"),17)
    sheet=Image.new("RGB",(2000,1820),"#f5ebdd")
    draw=ImageDraw.Draw(sheet)
    draw.text((16,14),"ISOLATED WEBGL CREAM STUDY / 15 VIEWS & DETAILS / LIVE BAKERY UNCHANGED",font=font,fill="#34483a")
    crops=[None]*7+[(20,170,660,850),(780,170,1420,850),(320,100,1120,730),(500,250,1050,830),(40,60,650,470),(790,490,1420,910),(65,220,695,730),(40,15,1100,200)]
    origins=list(range(7))+[0,1,2,3,4,4,5,0]
    for i,(source,crop) in enumerate(zip(origins,crops)):
        label,file=frames[source]
        with Image.open(file) as opened:
            image=opened.convert("RGB")
            if crop:
                scale=image.width/1440
                image=image.crop(tuple(round(v*scale) for v in crop))
            thumb=ImageOps.contain(image,(630,300),Image.Resampling.LANCZOS)
        x,y=(i%3)*665+15,(i//3)*350+62
        draw.text((x,y),f"{i+1:02d} | {label[5:]} | {'detail' if crop else 'full'}",font=font,fill="#34483a")
        sheet.paste(thumb,(x+(630-thumb.width)//2,y+30))
    path=out/"metaballs-review-15.jpg"
    sheet.save(path,quality=95,subsampling=0)
    manifest={"status":"numerical-checks-passed-visual-pending","url":url,"live_site_changed":False,
              "checks":records,"review_sheet":str(path.resolve()),"review_sheet_sha256":sha256(path.read_bytes()).hexdigest(),
              "thumbnails":15,"frames":[{"label":label,"path":str(file),"sha256":sha256(file.read_bytes()).hexdigest()} for label,file in frames]}
    (out/"review.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:manifest[key] for key in ("status","url","review_sheet","review_sheet_sha256")},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://127.0.0.1:4174/")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--baseline-model",type=Path,help="Preserved previous model for measured old/new cursor rendering.")
    args=parser.parse_args()
    check(args.url,args.output,args.baseline_model)
