"""Combine refreshed showcase images and storefront/tab details into one bounded sheet."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from prepare_prototype_photos import encoded, save_preserving_existing


ROOT = Path(__file__).resolve().parents[1]


def create(final=False):
    output = ROOT / ".local" / "entrance-shop-20261008" / ("combined-review-final" if final else "combined-review")
    exports = ROOT / ".local" / "readme-showcase-20261007" / ("shop-final-20261008" if final else "shop-20261008") / "exports"
    entrance = ROOT / ".local" / "entrance-shop-20261008" / ("responsive-final" if final else "responsive")
    tabs = ROOT / ".local" / "sticky-book-tabs-20261008"
    filenames = ["01-welcome.jpg","02-bakery-entrance.jpg","03-our-story.jpg",
                 "04-cake-notebooks.jpg","05-open-notebook.jpg","06-simple-ordering.jpg"]
    tiles = [(name, exports / name, None) for name in filenames]
    tiles += [
        ("Entrance / desktop", entrance / "entrance-1440x1000-center.png", None),
        ("Entrance / mobile", entrance / "entrance-390x844-center.png", None),
        ("Entrance / short viewport", entrance / "entrance-1024x500-center.png", None),
        ("Glass / centered room", entrance / "entrance-1440x1000-center.png", (245,366,1198,735)),
        ("Glass / looking left", entrance / "entrance-1440x1000-left.png", (235,356,1208,745)),
        ("Glass / looking right", entrance / "entrance-1440x1000-right.png", (235,356,1208,745)),
        ("Sticky tabs / cake actions", tabs / "captures" / "10-desktop-cake-tabs.png", None),
        ("Sticky tabs / mobile actions", tabs / "captures" / "13-mobile-cake-tabs.png", None),
        ("Sticky tabs / 200% text focus", tabs / "captures" / "14-text200-focus-tabs.png", None),
    ]
    canvas=Image.new("RGB",(2250,2050),"#f5ebdd")
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(str(ROOT/"web"/"assets"/"fonts"/"dm-sans-regular.ttf"),20)
    draw.text((18,15),"SHOP UPDATE / 15 LABELLED SCENES & DETAILS / ORIGINAL ART, NO STOCK PIXELS",font=font,fill="#34483a")
    records=[]
    for i,(label,path,crop) in enumerate(tiles):
        with Image.open(path) as opened:
            art=opened.convert("RGB")
            if crop: art=art.crop(crop)
            thumbnail=ImageOps.contain(art,(710,348),Image.Resampling.LANCZOS)
        x,y=i%3*750+16,i//3*390+68
        draw.text((x,y),f"{i+1:02d} | {label}",font=font,fill="#34483a")
        draw.rectangle((x,y+30,x+718,y+383),fill="#eee3d2",outline="#d2c3ad")
        canvas.paste(thumbnail,(x+(718-thumbnail.width)//2,y+32+(348-thumbnail.height)//2))
        records.append({"tile":i+1,"label":label,"path":str(path.relative_to(ROOT)),
                        "sha256":sha256(path.read_bytes()).hexdigest(),"crop":crop})
    payload=encoded(canvas,"JPEG",quality=94,subsampling=0)
    path=output/"shop-and-tabs-review-15.jpg"
    save_preserving_existing(path,payload)
    receipt={"status":"generated-unviewed","sheet":str(path),"sha256":sha256(payload).hexdigest(),
             "tiles":records,"tile_count":15,"scope":"Production appearance only; isolated cream preview not deployed."}
    save_preserving_existing(output/"sheet.json",(json.dumps(receipt,indent=2)+"\n").encode())
    print(json.dumps({k:receipt[k] for k in ("sheet","sha256","tile_count")},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final",action="store_true")
    create(parser.parse_args().final)
