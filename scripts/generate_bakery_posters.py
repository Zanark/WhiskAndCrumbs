"""Capture static fallbacks from the same original 3D room; never opens image viewers."""

from hashlib import sha256
from io import BytesIO
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "http://127.0.0.1:4173/__bakery_scene__/"


def fixture(route):
    name = urlsplit(route.request.url).path.split("/__bakery_scene__/", 1)[1]
    allowed = {
        "bakery-interior.mjs", "bakery-view.mjs", "bakery-scene.mjs",
        "assets/bakery-paint-atlas.png",
        "assets/bakery-light-bake.bin",
    }
    if name == "index.html":
        route.fulfill(content_type="text/html", body="""<!doctype html><html><head>
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <style>html,body{margin:0}canvas{display:block;width:100vw;height:100vh}</style>
          </head><body><canvas id="room"></canvas></body></html>""")
    elif name in allowed:
        route.fulfill(
            content_type="text/javascript" if name.endswith(".mjs") else
            "application/octet-stream" if name.endswith(".bin") else "image/png",
            body=(ROOT / "web" / name).read_bytes(),
        )
    else:
        route.abort()


def generate(output=None):
    evidence = output or ROOT / ".local" / "painterly-windowlight-20261008" / "posters"
    evidence.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        for label, width, height in [("wide", 1600, 1000), ("portrait", 640, 960), ("short", 1280, 480)]:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route(PREFIX + "**", fixture)
            page.goto(PREFIX + "index.html")
            metrics = page.evaluate("""async()=>{
              const {createBakeryScene}=await import('./bakery-scene.mjs');
              const {createBakeryRenderer,decodeBakeryLighting}=await import('./bakery-interior.mjs');
              const {bakeryView,projectPoint}=await import('./bakery-view.mjs');
              const image=new Image();image.src='assets/bakery-paint-atlas.png';await image.decode();
              const scene=createBakeryScene(),canvas=document.getElementById('room'),
                bytes=await fetch('assets/bakery-light-bake.bin').then(r=>r.arrayBuffer()),
                lighting=decodeBakeryLighting(scene,bytes),renderer=createBakeryRenderer(canvas,scene,image,lighting);
              if(!renderer)throw new Error('WebGL2 is required to generate the original fallback posters.');
              renderer.resize(innerWidth,innerHeight);renderer.render(0,0);
              const gl=canvas.getContext('webgl2');
              window.__sceneRenderer=renderer;
              return {vertices:scene.opaque.positions.length/3,transparent:scene.transparent.length,bakedBytes:bytes.byteLength,
                glError:gl.getError(),groups:scene.groups,
                landmarks:Object.fromEntries(Object.entries(scene.landmarkPoints).map(([name,point])=>
                  [name,{world:point,screen:projectPoint(bakeryView(innerWidth,innerHeight).matrix,point,innerWidth,innerHeight)}]))};
            }""")
            assert metrics["glError"] == 0 and not errors, (metrics, errors)
            payload = page.screenshot()
            image = Image.open(BytesIO(payload)).convert("RGB")
            assert min(ImageStat.Stat(image).stddev) > 12, "Poster must contain actual lit scene variation."
            target = ROOT / "web" / "assets" / f"bakery-interior-{label}.webp"
            image.save(target, "WEBP", quality=95, method=6)
            (evidence / f"{label}.png").write_bytes(payload)
            records.append({"label": label, "width": width, "height": height,
                            "file": str(target.relative_to(ROOT)), "sha256": sha256(target.read_bytes()).hexdigest(),
                            "bytes": target.stat().st_size, "metrics": metrics})
            page.close()
        browser.close()
    receipt = {"source": "Original geometry, layered paint atlas and matched baked window illumination rendered with the production renderer.",
               "source_hashes": {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in [
                   "web/bakery-scene.mjs", "web/bakery-interior.mjs", "web/bakery-view.mjs",
                   "web/assets/bakery-paint-atlas.png", "web/assets/bakery-light-bake.bin"]},
               "image_tool_views": 0, "visual_acceptance": "Not established.", "posters": records}
    (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"file": r["file"], "bytes": r["bytes"], "vertices": r["metrics"]["vertices"]} for r in records], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    generate(parser.parse_args().output)
