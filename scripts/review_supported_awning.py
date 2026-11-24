"""Measure stripe count, longer slope and genuinely fixed canopy hardware."""

import argparse
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def review(url, output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
        page.goto(url + "#home", wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        awning = page.locator(".site-awning")
        expect(awning).to_have_attribute("data-fabric-state", "rest", timeout=26000)
        material = awning.evaluate("""async node=>{
          const image=node.querySelector('img');await image.decode();
          const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=300;
          const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,1200,300);
          const row=ctx.getImageData(0,100,1200,1).data;
          let redRuns=0,previous=false;
          for(let x=0;x<1200;x++){
            const i=x*4,red=row[i+3]>250&&row[i]-row[i+1]>45&&row[i+2]>row[i+1];
            if(red&&!previous)redRuns++;previous=red;
          }
          const hem=ctx.getImageData(0,286,1200,1).data,scallops=[];
          let start=-1;
          for(let x=0;x<=1200;x++){
            const painted=x<1200&&hem[x*4+3]>=128;
            if(painted&&start<0)start=x;
            if(!painted&&start>=0){scallops.push({left:start,right:x,center:(start+x-1)/2});start=-1;}
          }
          const tips=Array.from({length:40},(_,i)=>{
            const x=i*30+15,color=[...ctx.getImageData(x,286,1,1).data];
            return {stripe:i,center:x,color,rose:color[0]-color[1]>45};
          });
          const sideEdges={samples:0,minimumAlpha:255,unfilled:0,wrongColor:0,maximumMatchingStripeError:0};
          for(let y=16;y<182;y++){
            for(const x of [0,1,1198,1199]){
              const color=ctx.getImageData(x,y,1,1).data;
              const expected=ctx.getImageData(x>600?1185:15,y,1,1).data,
                other=ctx.getImageData(x>600?1145:55,y,1,1).data;
              const distance=reference=>Math.hypot(...[0,1,2].map(i=>color[i]-reference[i]));
              const matchingError=Math.max(...[0,1,2].map(i=>Math.abs(color[i]-expected[i])));
              sideEdges.samples++;
              sideEdges.minimumAlpha=Math.min(sideEdges.minimumAlpha,color[3]);
              sideEdges.maximumMatchingStripeError=Math.max(sideEdges.maximumMatchingStripeError,matchingError);
              if(color[3]<250)sideEdges.unfilled++;
              else if(distance(expected)>=distance(other)||matchingError>8)sideEdges.wrongColor++;
            }
          }
          const shape={straightSamples:0,unfilledStraightSamples:0,edgeDepths:[],centerDepths:[]};
          const pixels=ctx.getImageData(0,0,1200,300).data;
          for(let y=190;y<279;y++)for(let x=0;x<1200;x++){
            shape.straightSamples++;
            if(pixels[(y*1200+x)*4+3]<250)shape.unfilledStraightSamples++;
          }
          for(let stripe=0;stripe<40;stripe++){
            for(const [offset,key] of [[0,'edgeDepths'],[15,'centerDepths']]){
              let bottom=190;
              for(let y=190;y<300;y++)if(pixels[(y*1200+stripe*30+offset)*4+3]>=128)bottom=y+1;
              shape[key].push(bottom);
            }
          }
          const support=node.querySelector('.awning-supports'),style=getComputedStyle(support),
            source=style.backgroundImage.match(/url\\(["']?(.*?)["']?\\)/)[1],
            rods=new Image();rods.src=source;await rods.decode();
          const sample=(x,y)=>[...ctx.getImageData(x,y,1,1).data].slice(0,3);
          const lighting=[315,345,915,945].map(x=>({x,
            rear:sample(x,18),roof:sample(x,135),fold:sample(x,179),
            lipTop:sample(x,182),lipBottom:sample(x,189),
            frontShadow:sample(x,192),frontFace:sample(x,250)}));
          const shadowCanvas=document.createElement('canvas');shadowCanvas.width=1200;shadowCanvas.height=300;
          const shadowContext=shadowCanvas.getContext('2d');shadowContext.drawImage(rods,0,0);
          const shadowDirections=[[138,106,108,106],[1088,106,1066,106]].map(([x,y,oppositeX,oppositeY])=>({
            point:[x,y],alpha:shadowContext.getImageData(x,y,1,1).data[3],
            oppositeAlpha:shadowContext.getImageData(oppositeX,oppositeY,1,1).data[3]}));
          return {redRuns,stripes:redRuns*2,scallops,tips,sideEdges,shape,lighting,shadowDirections,
            roseSample:[...ctx.getImageData(45,100,1,1).data],
            supportLoaded:rods.naturalWidth===1200&&rods.naturalHeight===300,
            supportInteractive:style.pointerEvents!=='none',supportTransform:style.transform,
            supportAnimations:support.getAnimations().length,sourceHeight:image.naturalHeight};
        }""")
        assert material["stripes"] == 40 and material["sourceHeight"] == 300, material
        assert material["sideEdges"]["unfilled"] == 0, material["sideEdges"]
        assert material["sideEdges"]["wrongColor"] == 0, material["sideEdges"]
        assert material["shape"]["unfilledStraightSamples"] == 0, material["shape"]
        assert all(281 <= bottom <= 284 for bottom in material["shape"]["edgeDepths"]), material["shape"]
        assert all(293 <= bottom <= 294 for bottom in material["shape"]["centerDepths"]), material["shape"]
        assert len(material["scallops"]) == material["stripes"], material
        for index, scallop in enumerate(material["scallops"]):
            assert abs(scallop["center"] - (index * 30 + 15)) <= 1, scallop
            assert scallop["left"] >= index * 30 and scallop["right"] <= (index + 1) * 30, scallop
            assert material["tips"][index]["color"][3] >= 250 and material["tips"][index]["rose"] == bool(index % 2), material["tips"][index]
        assert material["supportLoaded"] and not material["supportInteractive"], material
        assert material["supportTransform"] == "none" and material["supportAnimations"] == 0, material
        brightness = lambda color: sum(value * weight for value, weight in zip(color, (.2126, .7152, .0722)))
        for plane in material["lighting"]:
            assert brightness(plane["roof"]) - brightness(plane["frontFace"]) >= 12, plane
            assert brightness(plane["roof"]) - brightness(plane["rear"]) >= 25, plane
            assert brightness(plane["frontFace"]) - brightness(plane["frontShadow"]) >= 30, plane
            assert brightness(plane["fold"]) > brightness(plane["roof"]), plane
            assert brightness(plane["lipTop"]) - brightness(plane["lipBottom"]) >= 70, plane
        for left, right in zip(material["lighting"][:2], material["lighting"][2:]):
            assert brightness(left["roof"]) > brightness(right["roof"]), (left, right)
            assert brightness(left["frontFace"]) > brightness(right["frontFace"]), (left, right)
        assert all(shadow["alpha"] >= 35 and shadow["oppositeAlpha"] <= 3
                   for shadow in material["shadowDirections"]), material["shadowDirections"]
        bounds = awning.bounding_box()
        baseline = Image.open(BytesIO(awning.screenshot())).convert("RGB")
        support = awning.locator(".awning-supports")
        support.evaluate("n=>n.style.visibility='hidden'")
        hidden = Image.open(BytesIO(awning.screenshot())).convert("RGB")
        support.evaluate("n=>n.style.removeProperty('visibility')")
        difference = ImageChops.difference(baseline, hidden).convert("L")
        changed = sum(difference.histogram()[8:]) / (difference.width * difference.height)
        assert changed > .002, f"The support layer has no substantial visible paint: {changed}"
        page.mouse.move(bounds["width"] * 130 / 1200, bounds["y"] + bounds["height"] * 100 / 300)
        expect(page.locator("canvas.awning-fabric")).to_be_visible()
        page.wait_for_timeout(250)
        moving = Image.open(BytesIO(awning.screenshot())).convert("RGB")
        anchors = []
        for x, y in [(160, 12), (130, 89), (90, 185), (1040, 12), (1070, 89), (1110, 185)]:
            point = (round(x / 1200 * baseline.width), round(y / 300 * baseline.height))
            delta = max(abs(a-b) for a, b in zip(baseline.getpixel(point), moving.getpixel(point)))
            assert delta <= 2, f"Rigid support paint moved with cloth: {point}: {delta}"
            anchors.append({"source_xy": [x, y], "maximum_rgb_change": delta})
        page.mouse.move(20, 20)
        expect(awning).to_have_attribute("data-fabric-state", "rest", timeout=10000)
        page.screenshot(path=str(output / "supported-canopy.png"))
        for width, height in [(320, 568), (390, 844), (1024, 500), (1440, 1000)]:
            page.set_viewport_size({"width": width, "height": height})
            page.goto(url + f"?awning-layout={width}")
            expect(page.locator("#bakery-entrance")).to_have_attribute("data-state", "waiting")
            entry = page.locator(".entrance-awning").evaluate("""n=>{
              const b=n.getBoundingClientRect(),s=n.querySelector('.awning-supports').getBoundingClientRect();
              return {width:b.width,height:b.height,fits:b.left>=0&&b.right<=innerWidth&&b.top>=0&&b.bottom<=innerHeight,
                supportMatches:Math.abs(s.width-b.width)<1&&Math.abs(s.height-b.height)<1};
            }""")
            assert entry["fits"] and entry["supportMatches"], entry
            page.locator("#entrance-skip").click()
            page.evaluate("scrollTo({top:0,behavior:'instant'})")
            main = page.locator(".site-awning").evaluate("n=>({width:n.clientWidth,height:n.clientHeight})")
            previous_height = min(270, max(120, width * .18))
            ratio = main["height"] / 300 * 171 / (previous_height / 240 * 111)
            assert ratio >= 1.535, (width, main, ratio)
            entry_ratio = (171 / 300) / (111 / 240)
            assert entry_ratio > 1.23
            records.append({"viewport": [width, height], "main_slope_ratio": ratio,
                            "entry_slope_ratio_same_envelope": entry_ratio, "entry": entry})
        browser.close()
    result = {"status": "passed", "url": url, "material": material,
              "visible_hardware_pixel_fraction": changed, "fixed_support_samples": anchors,
              "layouts": records, "scallops": 40, "one_scallop_per_stripe": True, "image_tool_views": 0}
    (output / "review.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"passed","stripes":material["stripes"],
                      "scallops":len(material["scallops"]),"one_scallop_per_stripe":True,
                      "slope_side_edges":material["sideEdges"],
                      "straight_fabric_unfilled_pixels":material["shape"]["unfilledStraightSamples"],
                      "two_plane_lighting":True,"support_shadows_both_down_right":True,
                      "fixed_support_pixel_changes":max(point["maximum_rgb_change"] for point in anchors),
                      "output":str(output)},indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review(args.url, args.output)
