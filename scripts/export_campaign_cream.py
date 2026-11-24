"""Export static, transparent campaign layers from the unchanged local cream shader."""

import argparse
import base64
from hashlib import sha256
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from playwright.sync_api import sync_playwright

from prepare_prototype_photos import encoded, save_preserving_existing
from campaign_gaussian import gaussian_recipe, validate_distinct_recipes


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments" / "cream-metaballs"
SCENES = ("01-welcome", "02-bakery-entrance", "03-our-story",
          "04-cake-notebooks", "05-open-notebook", "06-simple-ordering")
EXPORT_SHADER = """(() => {
  const context = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, options) {
    if (type === 'webgl2' && this.id === 'material')
      options = {...options, alpha:true, premultipliedAlpha:false};
    return context.call(this, type, options);
  };
  const original = WebGL2RenderingContext.prototype.shaderSource;
  WebGL2RenderingContext.prototype.shaderSource = function(shader, source) {
    if (source.includes('float creamHeight(')) {
      const output = 'color=vec4(clamp(cream,0.,1.)*coverage,alpha);';
      if (!source.includes(output) || !source.includes('out vec4 color;'))
        throw new Error('Cream export must be reviewed against the changed material shader.');
      source = source.replace('out vec4 color;', 'out vec4 color;\\nuniform int campaignPass;');
      source = source.replace(output, `
        if(campaignPass==1)color=vec4(vec3(coverage),1.);
        else if(campaignPass==2){
          vec3 paper=vec3(245.,235.,221.)/255.;
          color=vec4(mix(paper*(1.-shadow),clamp(cream,0.,1.),coverage),1.);
        }
        else {
          color=vec4(clamp(cream,0.,1.)*coverage/max(alpha,.000001),alpha);
        }`);
    }
    return original.call(this, shader, source);
  };
})()"""


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def export(url, output, gaussian=False):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Cream export is restricted to the local study.")
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".local") or output.exists():
        raise ValueError("Use a new private .local output directory.")
    output.mkdir(parents=True)
    sources = {str(path.relative_to(ROOT)): digest(path)
               for path in (STUDY / "model.mjs", STUDY / "preview.mjs", STUDY / "preview.css")}
    spec = importlib.util.spec_from_file_location("cream_coverage_review", STUDY / "review.py")
    coverage_review = importlib.util.module_from_spec(spec)
    previous_bytecode_policy = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(coverage_review)
    finally:
        sys.dont_write_bytecode = previous_bytecode_policy
    records, recipes, coverage_masks = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for edition_index, (edition, width, height) in enumerate((("wide", 1600, 1000), ("portrait", 1080, 1440))):
            context = browser.new_context(viewport={"width": width, "height": height},
                                          device_scale_factor=2, reduced_motion="reduce")
            page = context.new_page()
            errors, requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.add_init_script(EXPORT_SHADER)
            page.goto(url, wait_until="networkidle")
            page.wait_for_function("Number(document.querySelector('#material').dataset.paintCount)>0")
            for index, stem in enumerate(SCENES):
                recipe = gaussian_recipe(width, height, index * 2 + edition_index) if gaussian else None
                result = page.evaluate("""async ({index,portrait,supplied}) => {
                  const model=await import('./model.mjs'), canvas=document.querySelector('#material'),
                    gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM);
                  const recipe=portrait
                    ? [[.035,.20,.145],[.965,.15,.100],[0,.57,.165],[.99,.61,.195],[.17,.91,.092],[.88,.90,.070]]
                    : [[.025,.24,.155],[.94,.13,.18],[.01,.60,.165],[1.01,.68,.17],[.28,.97,.13],[.78,.97,.085]];
                  const forms=supplied ?? recipe.map(([x,y,radius],i)=>{
                    const shift=(index-2.5)*.006;
                    return {x:(x+(i%2?shift:-shift))*innerWidth,
                      y:(y+Math.sin(index*1.13+i)*.012)*innerHeight,
                      radius:Math.min(innerWidth,innerHeight)*radius*(1+.045*Math.cos(index*.8+i)),
                      peak:[0,.85,.6,0,.9,0][i]};
                  });
                  if(forms.length!==(supplied?17:6))throw new Error('Unexpected cream primitive count.');
                  const data=new Float32Array(model.MAX_PRIMITIVES*4);
                  forms.forEach((s,i)=>data.set([s.x,s.y,s.radius,s.peak],i*4));
                  gl.uniform4fv(gl.getUniformLocation(program,'scoops[0]'),data);
                  gl.uniform1i(gl.getUniformLocation(program,'scoopCount'),forms.length);
                  gl.uniform1i(gl.getUniformLocation(program,'trailCount'),0);
                  gl.uniform1f(gl.getUniformLocation(program,'cursorTint'),0);
                  const frames=[];
                  for(let mode=0;mode<3;mode++){
                    gl.uniform1i(gl.getUniformLocation(program,'campaignPass'),mode);
                    gl.drawArrays(gl.TRIANGLES,0,3);gl.finish();
                    frames.push(canvas.toDataURL('image/png').split(',')[1]);
                  }
                  return {frames,forms,error:gl.getError(),dimensions:[canvas.width,canvas.height]};
                }""", {"index": index, "portrait": edition == "portrait",
                       "supplied": recipe["forms"] if recipe else None})
                assert result["error"] == 0 and result["dimensions"] == [width * 2, height * 2]
                layer, mask, original = [Image.open(BytesIO(base64.b64decode(frame))).convert("RGBA")
                                         for frame in result["frames"]]
                reconstructed = Image.alpha_composite(Image.new("RGBA", layer.size, (245, 235, 221, 255)), layer)
                delta = np.asarray(ImageChops.difference(reconstructed.convert("RGB"), original.convert("RGB")))
                maximum, mean = int(delta.max()), float(delta.mean())
                assert maximum <= 2 and mean < .2, ("Incorrect transparent material export", maximum, mean)
                components = coverage_review.coverage_components(
                    mask.convert("L").resize((400, round(height * 400 / width)), Image.Resampling.LANCZOS))
                assert len(components) == (9 if gaussian else 6), components
                assert min(c["area"] for c in components) > (30 if gaussian else 100), components
                assert max(c["area"] for c in components) / min(c["area"] for c in components) > (8 if gaussian else 3), components
                if recipe:
                    recipes.append(recipe)
                    coverage_masks.append(np.asarray(mask.convert("L").resize((96, 128), Image.Resampling.LANCZOS)) >= 128)
                layer = layer.convert("RGBa").filter(ImageFilter.GaussianBlur(1.6)).convert("RGBA")
                target = output / edition / f"{stem}.png"
                data = encoded(layer, "PNG", optimize=True)
                save_preserving_existing(target, data)
                records.append({
                    "edition": edition, "stem": stem, "file": str(target.relative_to(output)),
                    "sha256": sha256(data).hexdigest(), "dimensions": list(layer.size),
                    "forms": result["forms"], "coverage_components": components,
                    "original_shader_reconstruction_maximum_error": maximum,
                    "original_shader_reconstruction_mean_error": mean,
                    "premultiplied_blur_css_pixels": .8,
                })
                if recipe:
                    records[-1]["gaussian_layout"] = {key: value for key, value in recipe.items() if key != "forms"}
                print(f"Exported {edition}/{stem}: {len(components)} material groups; RGB reconstruction error {maximum}")
            assert not errors, errors
            assert all(request.startswith(url) for request in requests), requests
            context.close()
        browser.close()
    assert all(digest(ROOT / path) == expected for path, expected in sources.items())
    manifest = {
        "schema_version": 1, "status": "exported-and-checked",
        "kind": "gaussian-cream-campaign-layers" if gaussian else "static-cream-campaign-layers",
        "source_hashes": sources, "generator_sha256": digest(Path(__file__)), "layers": records,
        "method": "Original local WebGL cream material/lighting; six composition-specific unequal side forms. "
                  "Transparent cream plus contact shadow, verified by reconstructing the unchanged shader's opaque output.",
        "scope": "Launch-image backgrounds only; no website or local-study source changes.",
        "image_tool_views": 0, "external_requests": 0, "static_not_animation": True,
    }
    if gaussian:
        uniqueness = validate_distinct_recipes(recipes)
        maximum_iou = max(float(np.logical_and(a, b).sum() / np.logical_or(a, b).sum())
                          for index, a in enumerate(coverage_masks) for b in coverage_masks[index + 1:])
        assert maximum_iou < .65, f"Cream layouts repeat too closely: {maximum_iou}"
        manifest["layout_validation"] = {**uniqueness, "maximum_normalized_coverage_iou": maximum_iou}
        manifest["method"] = "Original cream material/lighting with four Gaussian-varied multi-lobe clusters and five small droplets; twelve distinct orientations."
        recipe_source = ROOT / "scripts" / "campaign_gaussian.py"
        manifest["recipe_source_sha256"] = digest(recipe_source)
        save_preserving_existing(output / "gaussian-recipe-source.py", recipe_source.read_bytes())
    save_preserving_existing(output / "manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
    save_preserving_existing(output / "exporter-source.py", Path(__file__).read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4174/")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gaussian-clusters", action="store_true")
    args = parser.parse_args()
    export(args.url, args.output, gaussian=args.gaussian_clusters)
