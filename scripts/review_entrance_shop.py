"""Check responsive awnings, visible illustrated rooms and safe depth parallax."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def check_glass_neon(page):
    selector = ".entrance-glass > img, .entrance-glass > svg"
    page.locator(".entrance-glass > img").evaluate("n=>n.decode()")
    record = page.evaluate("""selector=>{
      const rect=n=>{const b=n.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height,r:b.right,b:b.bottom}};
      return {
        icons:[...document.querySelectorAll(selector)].map(n=>{
          const pane=n.parentElement,style=getComputedStyle(n),spill=getComputedStyle(pane,'::before');
          return {...rect(n),pane:rect(pane),filter:style.filter,opacity:style.opacity,
            events:style.pointerEvents,animations:n.getAnimations().length,
            glowUnderReflection:Number(style.zIndex)<Number(getComputedStyle(pane,'::after').zIndex),
            spill:spill.backgroundImage,spillEvents:spill.pointerEvents,
            spillUnderTube:Number(spill.zIndex)<Number(style.zIndex),
            stroke:n.querySelector('path')?getComputedStyle(n.querySelector('path')).stroke:null};
        }),
        plaque:[...document.querySelectorAll('.entrance-open-sign,.open-sign-cord,.open-sign-board')]
          .map(n=>({filter:getComputedStyle(n).filter,animations:n.getAnimations().length})),
        artHidden:document.querySelector('.entrance-art').getAttribute('aria-hidden')
      };
    }""", selector)
    assert len(record["icons"]) == 2 and record["artHidden"] == "true", record
    assert all(n["filter"] == "none" and n["animations"] == 0 for n in record["plaque"]), record
    for icon in record["icons"]:
        assert icon["filter"].count("drop-shadow(") == 3, icon
        assert icon["opacity"] == "1" and icon["events"] == icon["spillEvents"] == "none", icon
        assert icon["animations"] == 0 and icon["glowUnderReflection"] and icon["spillUnderTube"], icon
        assert "radial-gradient" in icon["spill"], icon
        assert icon["x"] >= icon["pane"]["x"] and icon["r"] <= icon["pane"]["r"], icon
        assert icon["y"] >= icon["pane"]["y"] and icon["b"] <= icon["pane"]["b"], icon
    assert record["icons"][1]["stroke"] == "rgb(255, 243, 237)", record

    lit = Image.open(BytesIO(page.screenshot())).convert("RGB")
    fixture = page.add_style_tag(content="""
      .entrance-glass::before { background: none !important; }
      .entrance-glass > img { filter: brightness(0) invert(1) sepia(.12) !important; }
      .entrance-glass > svg { filter: none !important; }
    """)
    try:
        core_only = Image.open(BytesIO(page.screenshot())).convert("RGB")
    finally:
        fixture.evaluate("n=>n.remove()")
    restored = Image.open(BytesIO(page.screenshot())).convert("RGB")
    record["restoration_max_rgb_delta"] = max(
        high for low, high in ImageChops.difference(lit, restored).getextrema()
    )
    # Filter-layer recreation rounds twice; keep this well below the 8-level paint gate.
    assert record["restoration_max_rgb_delta"] <= 2, record
    for icon in record["icons"]:
        pane = icon["pane"]
        bounds = (round(pane["x"]+4), round(pane["y"]+4), round(pane["r"]-4), round(pane["b"]-4))
        delta = ImageChops.difference(lit.crop(bounds), core_only.crop(bounds))
        halo_pixels = sum(
            max(delta.getpixel((x, y))) >= 8
            for y in range(delta.height) for x in range(delta.width)
            if not (icon["x"] <= x+bounds[0] <= icon["r"] and icon["y"] <= y+bounds[1] <= icon["b"])
        )
        tube = lit.crop((round(icon["x"]), round(icon["y"]), round(icon["r"]), round(icon["b"])))
        bright_core_pixels = sum(min(pixel) >= 225 for pixel in tube.getdata())
        changed_fraction = sum(max(pixel) >= 8 for pixel in delta.getdata()) / (delta.width * delta.height)
        icon.update(halo_pixels=halo_pixels, bright_core_pixels=bright_core_pixels,
                    pane_changed_fraction=changed_fraction)
        assert halo_pixels >= 12 and bright_core_pixels >= 3, icon
        assert 0 < changed_fraction < .3, "Glow must be localized, not an opaque wash across the glass."
    return record


def check_cake_visibility(page):
    result=page.locator(".entrance-room").evaluate("""async room=>{
      const query=new URL(document.querySelector('script[src*="main.mjs"]').src).search;
      const {createBakeryScene}=await import(new URL('bakery-scene.mjs'+query,document.baseURI));
      const {bakeryView,projectPoint,bakeryLight}=await import(new URL('bakery-view.mjs'+query,document.baseURI));
      const scene=createBakeryScene(),box=room.getBoundingClientRect(),canvas=room.querySelector('canvas'),
        gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),
        actual=gl.getUniform(program,gl.getUniformLocation(program,'viewMatrix')),
        look=[Number(room.dataset.lookX),Number(room.dataset.lookY)],
        view=bakeryView(box.width,box.height,...look),expected=view.matrix,
        light=gl.getUniform(program,gl.getUniformLocation(program,'lightDirection')),
        windows=[...document.querySelectorAll('.entrance-glass,.entrance-display-glass')]
          .filter(n=>n.getClientRects().length && n.getBoundingClientRect().width>0).map(n=>n.getBoundingClientRect());
      const projected=point=>{const p=projectPoint(actual,point,box.width,box.height);return {...p,x:p.x+box.left,y:p.y+box.top}};
      return {look,vertices:scene.opaque.positions.length/3,
        camera:{eye:Array.from(gl.getUniform(program,gl.getUniformLocation(program,'eye'))),
          target:view.target,pitchDegrees:Math.atan2(view.target[1]-view.eye[1],
            Math.hypot(view.target[0]-view.eye[0],view.target[2]-view.eye[2]))*180/Math.PI,
          horizon:[-.5,-3,-6].map(z=>projected([0,view.eye[1],z]).y-box.top-box.height/2)},
        matrixError:Math.max(...actual.map((value,i)=>Math.abs(value-expected[i]))),
        lightError:Math.max(...light.map((value,i)=>Math.abs(value-bakeryLight().direction[i]))),
        floorContacts:scene.groups.filter(g=>g.floorContact).map(g=>({id:g.id,y:g.min[1]})),
        cakes:['lowerCakeLeftTop','lowerCakeRightTop','upperCakeLeftTop','upperCakeRightTop'].map(name=>{
          const p=projected(scene.landmarkPoints[name]);
          return {name,...p,pane:windows.findIndex(b=>p.x>b.left+4&&p.x<b.right-4&&p.y>b.top+10&&p.y<b.bottom-4)};
        }),
        front:projected([0,1.25,-.5]),back:projected([0,1.25,-6]),
        footing:projected(scene.landmarkPoints.counterFootingCenterContact),
        room:{left:box.left,right:box.right,top:box.top,bottom:box.bottom,width:box.width,height:box.height},
        pixels:canvas.width*canvas.height,canvasTransform:getComputedStyle(canvas).transform,error:gl.getError()};
    }""")
    assert result["matrixError"]<.0002 and result["lightError"]<.00001 and result["error"]==0,result
    assert result["look"]==[0,0] and abs(result["camera"]["pitchDegrees"])<.0001,result["camera"]
    assert abs(result["camera"]["eye"][1]-1.65)<.0001 and abs(result["camera"]["eye"][2]-8.4)<.0001,result["camera"]
    assert all(abs(y)<.001 for y in result["camera"]["horizon"]),result["camera"]
    assert result["floorContacts"] and all(contact["y"]==0 for contact in result["floorContacts"]),result
    assert result["canvasTransform"]=="none" and result["pixels"]<=2_020_000,result
    assert all(cake["pane"] >= 0 for cake in result["cakes"]),result["cakes"]
    assert len({cake["pane"] for cake in result["cakes"]}) >= 2, result["cakes"]
    assert result["room"]["top"]<=result["footing"]["y"]<=result["room"]["bottom"],result["footing"]
    return result


def check_full_width_awning(page):
    page.evaluate("scrollTo({top:0,behavior:'instant'})")
    page.locator(".site-awning img").evaluate("node=>node.decode()")
    result = page.locator(".site-awning").evaluate("""node=>{
        const image=node.querySelector('img'), box=node.getBoundingClientRect(),
          fabric=image.getBoundingClientRect(), header=document.querySelector('.site-header').getBoundingClientRect(),
          hero=document.getElementById('home').getBoundingClientRect();
        const canvas=document.createElement('canvas');
        canvas.width=Math.round(fabric.width);canvas.height=Math.round(fabric.height);
        const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,canvas.width,canvas.height);
        const samples=[0,.25,.5,.75,1].map(fraction=>{
          const x=Math.min(canvas.width-1,Math.round(fraction*canvas.width)),
            y=Math.floor(canvas.height*186/300);
          return [...ctx.getImageData(x,y,1,1).data];
        });
        return {width:innerWidth,left:box.left,right:box.right,height:box.height,
          imageLeft:fabric.left,imageRight:fabric.right,
          documentWidth:document.documentElement.scrollWidth,
          betweenHeaderAndHero:box.top>=header.bottom-1 && box.bottom<=hero.top+1,
          frontBarPixels:samples,
          lowerValancePixel:[...ctx.getImageData(Math.max(1,Math.round(canvas.width*25/1200)),Math.floor(canvas.height*.92),1,1).data],
          events:getComputedStyle(node).pointerEvents};
    }""")
    assert abs(result["left"]) < 1 and abs(result["right"] - result["width"]) < 1, result
    assert abs(result["imageLeft"]) < 1 and abs(result["imageRight"] - result["width"]) < 1, result
    assert result["documentWidth"] <= result["width"], result
    assert 150 <= result["height"] <= 337.5 and result["betweenHeaderAndHero"], result
    previous_height=min(270,max(120,result["width"]*.18))
    result["height_scale_from_previous"]=result["height"]/previous_height
    assert abs(result["height_scale_from_previous"]-1.25)<.002,result
    assert result["events"] == "none", result
    assert all(pixel[3] >= 250 for pixel in result["frontBarPixels"]), result
    assert result["lowerValancePixel"][3] >= 200, result
    return result


def look_points(page):
    result=page.locator(".entrance-room").evaluate("""room=>{
      const canvas=room.querySelector('canvas'),gl=canvas.getContext('webgl2'),
        m=gl.getUniform(gl.getParameter(gl.CURRENT_PROGRAM),gl.getUniformLocation(gl.getParameter(gl.CURRENT_PROGRAM),'viewMatrix')),
        width=room.getBoundingClientRect().width;
      const x=z=>((m[4]*1.25+m[8]*z+m[12])/(m[7]*1.25+m[11]*z+m[15])+1)*width/2;
      return {front:x(-.5),back:x(-6),width,error:gl.getError()};
    }""")
    assert result["error"]==0,result
    return result


def review(url, output):
    output.mkdir(parents=True, exist_ok=True)
    cases=[(1440,1000,False),(1280,720,False),(1024,500,False),(390,844,True),(320,568,True)]
    records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="msedge",headless=True,args=["--mute-audio"])
        for width,height,touch in cases:
            c=browser.new_context(viewport={"width":width,"height":height},has_touch=touch,is_mobile=touch,reduced_motion="no-preference")
            page=c.new_page();errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(url)
            expect(page.locator("#bakery-entrance")).to_have_attribute("data-state","waiting")
            page.wait_for_function("document.querySelector('.entrance-room-poster img').complete && document.querySelector('.entrance-room-poster img').naturalWidth > 0")
            page.locator(".entrance-room-poster img,.entrance-awning img").evaluate_all("nodes=>Promise.all(nodes.map(n=>n.decode()))")
            expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=15000)
            cake_visibility = check_cake_visibility(page)
            neon = check_glass_neon(page)
            geometry=page.locator("#bakery-entrance").evaluate("""node=>{
              const measured=[...node.querySelectorAll('.entrance-shop,.entrance-awning,.entrance-doorframe,.entrance-glass,#entrance-skip,#entrance-enter>span')].map(n=>{
                const b=n.getBoundingClientRect();return {class:n.className,id:n.id,left:b.left,top:b.top,right:b.right,bottom:b.bottom,width:b.width,height:b.height};
              });
              return {measured,viewport:[innerWidth,innerHeight],scrollWidth:document.documentElement.scrollWidth};
            }""")
            assert geometry["scrollWidth"]<=width,geometry
            for item in geometry["measured"]:
                assert item["left"]>=-1 and item["right"]<=width+1 and item["top"]>=-1 and item["bottom"]<=height+1,item
                if item["class"]=="entrance-glass":
                    assert item["width"]>=40 and item["height"]>=60,item
                if item["id"]=="entrance-skip" or item["class"]=="":
                    assert item["height"]>=48,item
            page.screenshot(path=str(output/f"entrance-{width}x{height}-center.png"))
            if not touch:
                frame_before=page.locator(".entrance-doorframe").bounding_box()
                page.mouse.move(width*.1,height*.4,steps=8)
                expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=3000)
                left=page.locator(".entrance-room").evaluate("n=>[Number(n.dataset.lookX),Number(n.dataset.lookY)]")
                left_points=look_points(page)
                left_pixels=Image.open(BytesIO(page.locator(".entrance-room").screenshot())).convert("RGB")
                page.screenshot(path=str(output/f"entrance-{width}x{height}-left.png"))
                page.mouse.move(width*.9,height*.4,steps=8)
                expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=3000)
                right=page.locator(".entrance-room").evaluate("n=>[Number(n.dataset.lookX),Number(n.dataset.lookY)]")
                right_points=look_points(page)
                right_pixels=Image.open(BytesIO(page.locator(".entrance-room").screenshot())).convert("RGB")
                difference=ImageChops.difference(left_pixels,right_pixels).convert("L")
                changed=sum(difference.histogram()[8:])/(difference.width*difference.height)
                front_shift=abs(right_points["front"]-left_points["front"])
                back_shift=abs(right_points["back"]-left_points["back"])
                assert front_shift>right_points["width"]*.1 and front_shift>back_shift,(left_points,right_points)
                assert changed>.06,f"Strong look-around must change actual room pixels, not just a style value: {changed}"
                cake_visibility["look_around"]={"front_shift_px":front_shift,"back_shift_px":back_shift,"changed_pixel_fraction":changed}
                assert left[0]==-1 and right[0]==1,(left,right)
                frame_after=page.locator(".entrance-doorframe").bounding_box()
                assert all(abs(frame_before[key]-frame_after[key])<.1 for key in frame_before)
                page.screenshot(path=str(output/f"entrance-{width}x{height}-right.png"))
            else:
                before=page.locator("#bakery-entrance").get_attribute("style")
                page.locator("#bakery-entrance").dispatch_event("pointermove",{"pointerType":"touch","clientX":width*.9,"clientY":height*.2})
                assert page.locator("#bakery-entrance").get_attribute("style")==before
                assert page.locator(".entrance-room").evaluate("n=>Number(n.dataset.lookX)===0 && Number(n.dataset.lookY)===0"), "Touch keeps the grounded center view."
            page.locator("#entrance-skip").click()
            expect(page.locator("#bakery-entrance")).to_be_hidden()
            page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
            page.evaluate("document.fonts.ready")
            expect(page.locator(".site-awning")).to_be_visible()
            awning = check_full_width_awning(page)
            page.screenshot(path=str(output/f"header-awning-{width}x{height}.png"))
            assert not errors,errors
            records.append({"viewport":[width,height],"touch":touch,"geometry":geometry,"cake_visibility":cake_visibility,"neon":neon,"full_width_awning":awning,"images_loaded":True,"skip_works":True})
            c.close()
        widths = []
        c=browser.new_context(viewport={"width":1440,"height":1000})
        page=c.new_page();page.goto(url+"#home")
        for width in (320,390,600,768,1024,1440,1920,2560):
            page.set_viewport_size({"width":width,"height":1000})
            for text_size in ("100%","200%"):
                page.evaluate("size=>document.documentElement.style.fontSize=size",text_size)
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(80)
                widths.append({"text_size":text_size,**check_full_width_awning(page)})
        c.close()
        c=browser.new_context(viewport={"width":390,"height":844},java_script_enabled=False)
        page=c.new_page();page.goto(url)
        expect(page.locator("#bakery-entrance")).to_be_hidden()
        expect(page.locator(".site-awning")).to_be_visible()
        expect(page.locator("#site-nav")).to_be_visible()
        check_full_width_awning(page)
        c.close()
        fallbacks=[]
        for failure in ("no-webgl2","module","atlas","all-art"):
            c=browser.new_context(viewport={"width":1440,"height":1000})
            page=c.new_page()
            if failure=="no-webgl2":
                page.add_init_script("""const original=HTMLCanvasElement.prototype.getContext;
                  HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:original.call(this,type,...args)};""")
            elif failure=="module":
                page.route(re.compile(r"/bakery-interior\.mjs(?:\?|$)"),lambda route:route.abort())
            elif failure=="atlas":
                page.route(re.compile(r"/bakery-paint-atlas\.png(?:\?|$)"),lambda route:route.abort())
            else:
                page.route(re.compile(r"/bakery-(?:paint-atlas\.png|interior-(?:wide|portrait|short)\.webp)(?:\?|$)"),lambda route:route.abort())
            page.goto(url,wait_until="networkidle")
            if failure!="all-art":
                image=page.locator(".entrance-room-poster img")
                image.evaluate("n=>n.decode()")
                assert image.evaluate("n=>n.naturalWidth>0 && getComputedStyle(n).visibility==='visible'")
            expect(page.locator("#entrance-skip")).to_be_visible()
            page.locator("#entrance-skip").click()
            expect(page.locator("#bakery-entrance")).to_be_hidden()
            fallbacks.append(failure)
            c.close()
        c=browser.new_context(viewport={"width":1440,"height":1000})
        page=c.new_page();page.goto(url)
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=15000)
        page.locator(".bakery-interior").evaluate("""n=>{
          window.__sceneLoss=n.getContext('webgl2').getExtension('WEBGL_lose_context');
          if(!window.__sceneLoss)throw new Error('Context-loss fixture unavailable');
          window.__sceneLoss.loseContext();
        }""")
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","context-lost")
        expect(page.locator(".entrance-room-poster img")).to_be_visible()
        page.wait_for_timeout(150);page.evaluate("window.__sceneLoss.restoreContext()")
        expect(page.locator(".entrance-room")).to_have_attribute("data-scene-state","ready",timeout=15000)
        c.close()
        browser.close()
    result={"status":"passed","url":url,"cases":records,"full_width_awning_cases":widths,"no_js_navigation_and_roof":True,"scene_fallbacks":fallbacks,"context_recovery":True,"new_visual_views":0}
    (output/"review.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"passed","responsive_entrance_cases":len(cases),"output":str(output)}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://127.0.0.1:4173/")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    review(args.url,args.output)
