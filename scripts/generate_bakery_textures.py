"""Paint a deterministic original material atlas; no reference images are read."""

from hashlib import sha256
import json
from pathlib import Path
import random
import math

from PIL import Image, ImageDraw, ImageFilter, ImageStat


ROOT = Path(__file__).resolve().parents[1]
PALETTE = [
    ("plaster", (225, 211, 184)), ("wood", (163, 112, 65)),
    ("darkWood", (104, 70, 46)), ("greenPaint", (89, 111, 84)),
    ("brass", (187, 148, 80)), ("glass", (208, 225, 219)),
    ("ceramic", (235, 228, 208)), ("bread", (209, 146, 69)),
    ("icing", (248, 234, 209)), ("chocolate", (99, 62, 45)),
    ("leaf", (98, 123, 72)), ("linen", (235, 224, 198)),
    ("window", (218, 234, 230)), ("stone", (169, 160, 144)),
    ("berry", (166, 73, 68)), ("spare", (240, 229, 209)),
]


def generate():
    atlas = Image.new("RGB", (1024, 1024))
    metrics = []
    for index, (name, colour) in enumerate(PALETTE):
        rng = random.Random(7319 + index)
        tile = Image.new("RGBA", (256, 256), (*colour, 255))
        wood = name in {"wood", "darkWood", "greenPaint"}

        def shade(delta, cool=0):
            return tuple(max(0, min(255, value + delta + offset)) for value, offset in
                         zip(colour, (-cool, 0, cool)))

        # Broad translucent pigment washes precede the dry-brush strands.
        for count, blur, alpha, span in [(18, 7, 72, 130), (62, 1.6, 52, 65)]:
            paint = Image.new("RGBA", tile.size)
            draw = ImageDraw.Draw(paint)
            for _ in range(count):
                x, y = rng.randint(-60, 230), rng.randint(-30, 250)
                width, height = rng.randint(span // 2, span * 2), rng.randint(8, 34)
                delta = rng.choice((-28, -18, -9, 10, 20, 30))
                points = [(x, y + 3), (x + width * .3, y), (x + width, y + 5),
                          (x + width - 5, y + height), (x + width * .3, y + height + 3),
                          (x - 4, y + height - 2)]
                if not wood and name not in {"linen", "icing"}:
                    points = [(px + math.sin(py * .04) * 12, py) for px, py in points]
                draw.polygon(points, fill=(*shade(delta, -2 if delta > 0 else 3), alpha))
            tile = Image.alpha_composite(tile, paint.filter(ImageFilter.GaussianBlur(blur)))

        paint = Image.new("RGBA", tile.size)
        detail = ImageDraw.Draw(paint)
        if wood:
            for row in range(-6, 270, 10):
                phase = rng.uniform(0, math.tau)
                points = [(x, row + math.sin(x * .021 + phase) * 3.5 +
                           math.sin(x * .061 + row) * .7) for x in range(-4, 262, 3)]
                detail.line(points, fill=(*shade(rng.choice((-30, -21, 23))), 66), width=rng.choice((1, 1, 2)))
            for x, y in [(70, 75), (191, 183)]:
                for radius in [7, 13, 19]:
                    detail.arc((x - radius * 2.8, y - radius, x + radius * 2.8, y + radius),
                               8, 330, fill=(*shade(-29), 52), width=1)
            # Worn paint reveals restrained warm underlayers, never uniform white noise.
            if name == "greenPaint":
                for y in [18, 119, 219]:
                    detail.line([(8, y), (37, y + 2), (52, y)], fill=(176, 137, 87, 60), width=2)
        elif name == "linen":
            for row in range(0, 256, 5):
                detail.line((0, row, 255, row), fill=(253, 244, 224, 40))
                detail.line((row, 0, row, 255), fill=(131, 116, 94, 23))
        elif name in {"bread", "chocolate"}:
            for _ in range(42):
                x, y = rng.randrange(256), rng.randrange(256)
                detail.arc((x, y, x + rng.randrange(6, 18), y + rng.randrange(3, 8)), 10, 240,
                           fill=(*shade(-37), 58), width=1)
            for _ in range(26):
                x, y = rng.randrange(256), rng.randrange(256)
                detail.line((x, y, x + rng.randrange(5, 13), y + 1), fill=(*shade(33), 48), width=2)
        elif name in {"plaster", "stone", "ceramic", "icing"}:
            for _ in range(26):
                x, y = rng.randrange(256), rng.randrange(256)
                detail.line([(x, y), (x + 8, y - 1), (x + rng.randrange(16, 40), y + 1)],
                            fill=(*shade(rng.choice((-18, 21))), 38), width=1)
        tile = Image.alpha_composite(tile, paint.filter(ImageFilter.GaussianBlur(.35))).convert("RGB")
        # The shader samples the 4%-96% inner tile; gutters contain same-material paint.
        atlas.paste(tile, ((index % 4) * 256, (index // 4) * 256))
        metrics.append({"name": name, "mean": ImageStat.Stat(tile).mean, "stddev": ImageStat.Stat(tile).stddev})
    target=ROOT/"web"/"assets"/"bakery-paint-atlas.png"
    atlas.save(target,optimize=True)
    evidence=ROOT/".local"/"painterly-windowlight-20261008"
    evidence.mkdir(parents=True,exist_ok=True)
    receipt={"source":"Original deterministic procedural brush/wood/linen marks; no input photographs.",
             "file":str(target.relative_to(ROOT)),"sha256":sha256(target.read_bytes()).hexdigest(),
             "size":list(atlas.size),"mode":atlas.mode,
             "materials":[{"index":i,"name":n,"base_rgb":c} for i,(n,c) in enumerate(PALETTE)],
             "layering":"18 broad translucent washes, 62 directional brush strokes, sparse material-specific grain/wear.",
             "statistics":metrics,"image_tool_views":0,"visual_acceptance":"Not established."}
    (evidence/"texture-atlas.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"texture":str(target),"bytes":target.stat().st_size,"sha256":receipt["sha256"]}))


if __name__=="__main__":
    generate()
