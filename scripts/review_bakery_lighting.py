"""Numerically check the actual scene shader; captures are NOT visually inspected."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from generate_bakery_posters import ROOT, PREFIX, fixture


def review(output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        for width, height in [(1200, 750), (640, 960), (1280, 480)]:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route(PREFIX + "**", fixture)
            page.goto(PREFIX + "index.html")
            result = page.evaluate("""async()=>{
              const {createBakeryScene}=await import('./bakery-scene.mjs');
              const {createBakeryRenderer,decodeBakeryLighting}=await import('./bakery-interior.mjs');
              const {bakeryView,projectPoint}=await import('./bakery-view.mjs');
              const image=new Image();image.src='assets/bakery-paint-atlas.png';await image.decode();
              const scene=createBakeryScene(),canvas=document.getElementById('room'),
                binary=await fetch('assets/bakery-light-bake.bin').then(r=>r.arrayBuffer()),
                lighting=decodeBakeryLighting(scene,binary),renderer=createBakeryRenderer(canvas,scene,image,lighting);
              renderer.resize(innerWidth,innerHeight);
              const gl=canvas.getContext('webgl2'),draw=gl.drawArrays.bind(gl);
              let draws=0;gl.drawArrays=(...args)=>{draws++;return draw(...args)};
              const pixels=()=>{const bytes=new Uint8Array(canvas.width*canvas.height*4);
                gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,bytes);return bytes;};
              const render=(x=0,y=0,c=[1,1,1,1])=>{renderer.render(x,y,c);return pixels()};
              const center=render();
              const compare=bytes=>{
                let changed=0,total=0,maximum=0,brighter=0;
                for(let i=0;i<bytes.length;i+=4){let difference=0;
                  for(let j=0;j<3;j++)difference+=Math.abs(center[i+j]-bytes[i+j]);
                  if(difference>9)changed++;
                  if(center[i]+center[i+1]+center[i+2]>bytes[i]+bytes[i+1]+bytes[i+2]+9)brighter++;
                  total+=difference;maximum=Math.max(maximum,difference);
                }
                return {changedFraction:changed/(bytes.length/4),brighterFraction:brighter/(bytes.length/4),
                  meanChannelDifference:total/(bytes.length/4*3),maximum};
              };
              const direct=compare(render(0,0,[0,1,1,1]));
              const ao=compare(render(0,0,[1,0,1,1]));
              const bounce=compare(render(0,0,[1,1,0,1]));
              const reflection=compare(render(0,0,[1,1,1,0]));
              const look=compare(render(.85,.2));
              const restored=compare(render());
              let bright=0,dark=0,mean=[0,0,0];
              for(let i=0;i<center.length;i+=4){
                if(center[i]>248&&center[i+1]>248&&center[i+2]>248)bright++;
                if(center[i]<15&&center[i+1]<15&&center[i+2]<15)dark++;
                mean=mean.map((sum,j)=>sum+center[i+j]);
              }
              const drawCount=draws;
              await new Promise(r=>setTimeout(r,350));
              const stats={width:innerWidth,height:innerHeight,pixels:canvas.width*canvas.height,
                vertices:scene.opaque.materials.length,bakedBytes:binary.byteLength,direct,ao,bounce,reflection,look,restored,
                clippedWhiteFraction:bright/(center.length/4),nearBlackFraction:dark/(center.length/4),
                meanRGB:mean.map(sum=>sum/(center.length/4)),idleDraws:draws-drawCount,glError:gl.getError(),
                footing:projectPoint(bakeryView(innerWidth,innerHeight).matrix,scene.landmarkPoints.counterFootingCenterContact,innerWidth,innerHeight)};
              window.__renderer=renderer;
              return stats;
            }""")
            assert not errors and result["glError"] == 0, (result, errors)
            assert result["pixels"] <= 2_020_000 and result["idleDraws"] == 0, result
            assert result["direct"]["changedFraction"] > .015, result
            assert result["ao"]["changedFraction"] > .10, result
            assert result["bounce"]["changedFraction"] > .001, result
            assert result["look"]["changedFraction"] > .10, result
            # ANGLE/MSAA can round a boundary channel by one byte after an identical redraw.
            assert result["restored"]["changedFraction"] == 0 and result["restored"]["maximum"] <= 1, result
            assert result["restored"]["meanChannelDifference"] < .00001, result
            assert result["reflection"]["meanChannelDifference"] > .001, result
            assert result["clippedWhiteFraction"] < .05 and result["nearBlackFraction"] < .20, result
            assert 0 <= result["footing"]["y"] <= height, result
            page.screenshot(path=str(output / f"lighting-{width}x{height}.png"))
            records.append(result)
            page.evaluate("window.__renderer.dispose()")
            page.close()
        browser.close()
    receipt = {"image_tool_views": 0, "visual_acceptance": "Not established; captures NOT visually inspected.",
               "identical_redraw_tolerance": "At most one byte in any RGB channel; mean-channel difference below 0.00001; no pixels differ by more than nine RGB-sum units.",
               "checks": records}
    (output / "review.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / ".local" / "painterly-windowlight-20261008" / "shader-review")
    review(parser.parse_args().output)
