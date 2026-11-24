"""Draw the original entrance architecture. No source images or external services."""

import hashlib
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "assets"
RECEIPT = ROOT / ".local" / "architectural-facade-20261009"

DEFS = """
<defs>
 <linearGradient id="plaster" x2=".9" y2="1"><stop stop-color="#fff2d9"/><stop offset=".5" stop-color="#e8d7bb"/><stop offset="1" stop-color="#cbb99b"/></linearGradient>
 <linearGradient id="return" x2="1" y2=".3"><stop stop-color="#cdb99a"/><stop offset="1" stop-color="#b39a7a"/></linearGradient>
 <linearGradient id="roof" x2=".3" y2="1"><stop stop-color="#a0755b"/><stop offset=".45" stop-color="#876550"/><stop offset="1" stop-color="#634d41"/></linearGradient>
 <linearGradient id="wood" x2="0" y2="1"><stop stop-color="#bc9870"/><stop offset=".3" stop-color="#8c6e50"/><stop offset="1" stop-color="#5b4838"/></linearGradient>
 <linearGradient id="glass" x2=".6" y2="1"><stop stop-color="#fff0bd"/><stop offset=".45" stop-color="#e5cb95"/><stop offset="1" stop-color="#a29f7e"/></linearGradient>
 <linearGradient id="green" x2=".8" y2="1"><stop stop-color="#70806a"/><stop offset=".4" stop-color="#4d6250"/><stop offset="1" stop-color="#34483a"/></linearGradient>
 <linearGradient id="pot" x2="1" y2=".25"><stop stop-color="#b47a57"/><stop offset=".3" stop-color="#d4a17d"/><stop offset="1" stop-color="#895b42"/></linearGradient>
</defs>"""


def window(x, y, width, height):
    a = [
        f'<g id="upper-window-{int(x)}" transform="translate({x} {y})">',
        f'<path d="M-9 -8H{width+12}V{height+8}H-9Z" fill="#aa9777" opacity=".35"/>',
        f'<rect x="-6" y="-9" width="{width+12}" height="{height+14}" rx="3" fill="#ece0c6" stroke="#baa283" stroke-width="3"/>',
        f'<rect width="{width}" height="{height}" rx="2" fill="url(#green)" stroke="#4c5d47" stroke-width="3"/>',
        f'<rect x="9" y="9" width="{width-18}" height="{height-18}" fill="url(#glass)"/>',
        f'<path d="M12 10H{width*.31}L{width*.76} {height-10}H{width*.52}Z" fill="#fffaf1" opacity=".3"/>',
        f'<path d="M12 {height*.33}Q{width*.25} {height*.23} {width*.4} {height*.34}L{width*.28} {height-10}H12Z" fill="#f6edda" opacity=".74"/>',
        f'<path d="M{width-12} {height*.33}Q{width*.76} {height*.23} {width*.6} {height*.34}L{width*.72} {height-10}H{width-12}Z" fill="#f6edda" opacity=".7"/>',
        f'<path d="M{width/2} 5V{height-5}M6 {height*.48}H{width-6}" stroke="#586a51" stroke-width="7"/>',
        f'<path d="M{width/2-2} 8V{height-8}M9 {height*.48-2}H{width-9}" stroke="#c3c9a5" stroke-width="1.6"/>',
        f'<path d="M-14 {height+4}H{width+15}L{width+22} {height+13}H-19Z" fill="#f6e7c9" stroke="#b59b79" stroke-width="2"/>',
        f'<path d="M-19 {height+13}H{width+22}V{height+22}H-19Z" fill="#bda482"/>',
        f'<path d="M-18 {height+14}H{width+21}" stroke="#f1d8b0" stroke-width="2"/>',
        '</g>',
    ]
    return "".join(a)


def leaves(x, y, scale, seed):
    rng = random.Random(seed)
    a = [f'<g transform="translate({x} {y}) scale({scale})" stroke-linejoin="round">']
    a.append('<path d="M0 0C18 25 -13 40 5 66C28 89 -4 98 13 125" fill="none" stroke="#607247" stroke-width="3"/>')
    for i in range(11):
        yy = i * 11
        xx = math.sin(i * 1.6) * 7
        direction = -1 if i % 2 else 1
        size = rng.uniform(12, 20)
        fill = rng.choice(["#879567", "#718553", "#a0aa78", "#586f49"])
        a.append(f'<path d="M{xx:.1f} {yy}Q{xx+direction*size:.1f} {yy-15} {xx+direction*(size+6):.1f} {yy-3}Q{xx+direction*size:.1f} {yy+14} {xx:.1f} {yy}Z" fill="{fill}" stroke="#5d7049" stroke-width="1.1"/>')
        a.append(f'<path d="M{xx:.1f} {yy}L{xx+direction*size*.8:.1f} {yy-1}" stroke="#b3b88d" stroke-width="1" opacity=".5"/>')
    a.append('</g>')
    return "".join(a)


def upper(mobile=False):
    width, height = (600, 400) if mobile else (1200, 360)
    left, right = (30, 560) if mobile else (60, 1090)
    eave = 135 if mobile else 115
    peak = 34
    center = width / 2
    front = f"M{left} {eave}H{right}V{height}H{left}Z"
    roof = f"M{left-16} {eave}L{left+84} {peak}H{right-120}L{right+32} {eave}Z"
    rng = random.Random(51009 + int(mobile))
    a = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<title>Original decorative cream-plaster shop upper storey</title>',
         '<desc>Imaginary hand-painted architectural illustration, with a tiled roof, substantial eaves, cream plaster, recessed windows and a trailing plant. Not a real building or a copied reference.</desc>',
         DEFS,
         f'<defs><clipPath id="front-clip"><path d="{front}"/></clipPath><clipPath id="roof-clip"><path d="{roof}"/></clipPath></defs>',
         '<g stroke-linecap="round" stroke-linejoin="round">',
         f'<path id="side-return" d="M{right} {eave}L{width-20} {eave+22}V{height}H{right}Z" fill="url(#return)"/>',
         f'<path id="plaster-face" d="{front}" fill="url(#plaster)"/>',
         '<g clip-path="url(#front-clip)">']
    for _ in range(85):
        x, y = rng.uniform(left, right), rng.uniform(eave, height)
        w, h = rng.uniform(9, 95), rng.uniform(2, 19)
        a.append(f'<path d="M{x:.1f} {y:.1f}q{w*.5:.1f} {-h:.1f} {w:.1f} 0l{-w*.1:.1f} {h:.1f}q{-w*.5:.1f} {-h*.6:.1f} {-w*.9:.1f} 0Z" fill="{rng.choice(["#fff6e3","#c9b58e","#dfcba7"])}" opacity="{rng.uniform(.06,.18):.2f}"/>')
    a.append('</g>')
    a.extend([
        f'<path d="M{left} {eave+5}H{right}V{eave+36}L{left} {eave+21}Z" fill="#786349" opacity=".22"/>',
        f'<path d="M{right-25} {eave+10}V{height}" fill="none" stroke="#b9a180" stroke-width="3"/>',
        f'<path d="M{left+11} {eave+10}V{height}" fill="none" stroke="#fff1d1" stroke-width="5" opacity=".58"/>',
        f'<path id="chimney" d="M{left+110} {peak+10}V14H{left+157}V{peak+40}" fill="#b58a70" stroke="#886853" stroke-width="3"/>',
        f'<path d="M{left+103} 12H{left+164}V24H{left+103}Z" fill="#d2b291" stroke="#886853" stroke-width="2"/>',
        f'<path d="M{left+116} 31H{left+149}M{left+114} 43H{left+155}M{left+136} 25V31" stroke="#e2c4a5" stroke-width="2"/>',
        f'<path id="tiled-roof" d="{roof}" fill="url(#roof)" stroke="#6c5443" stroke-width="3"/>',
        '<g clip-path="url(#roof-clip)">',
    ])
    for row in range(5):
        y = peak + 10 + row * (eave - peak) / 5
        a.append(f'<path d="M0 {y:.1f}Q{center} {y+5:.1f} {width} {y:.1f}" fill="none" stroke="#c09b77" stroke-width="2" opacity=".64"/>')
        for x in range(0, width, 54):
            xx = x + (24 if row % 2 else 0)
            a.append(f'<path d="M{xx} {y-1:.1f}l-9 15" stroke="#493f35" stroke-width="2" opacity=".4"/>')
    for _ in range(60):
        x, y = rng.uniform(0, width), rng.uniform(peak, eave)
        a.append(f'<path d="M{x:.1f} {y:.1f}l{rng.uniform(10,35):.1f} -2" stroke="{rng.choice(["#d0ab84","#b8946e","#584839"])}" stroke-width="{rng.uniform(2,5):.1f}" opacity=".17"/>')
    a.extend(['</g>',
        f'<path id="roof-eave" d="M{left-18} {eave-3}Q{center} {eave+4} {right+34} {eave-3}V{eave+14}Q{center} {eave+22} {left-18} {eave+14}Z" fill="url(#wood)" stroke="#705a42" stroke-width="2"/>',
        f'<path d="M{left-12} {eave-2}Q{center} {eave+5} {right+27} {eave-2}" fill="none" stroke="#e1c19b" stroke-width="3"/>',
    ])
    if mobile:
        a.append(window(131, 188, 123, 133))
        a.append(window(348, 188, 123, 133))
        plant_x, plant_y = 514, 174
    else:
        for x in (193, 506, 819):
            a.append(window(x, 164, 142, 135))
        plant_x, plant_y = 1050, 147
        a.append('<path d="M1103 165L1160 181V299L1103 290Z" fill="#897b61" stroke="#ad9878" stroke-width="6"/>')
        a.append('<path d="M1111 174L1151 187V288L1111 282Z" fill="#bbc1a1"/>')
        a.append('<path d="M1131 182V285M1112 225L1150 233" stroke="#6e8064" stroke-width="5"/>')
    a.extend([
        f'<path d="M{left-2} {height-22}H{right+2}V{height}H{left-2}Z" fill="#d4b990"/>',
        f'<path d="M{left-2} {height-22}H{right+2}" stroke="#fff0ce" stroke-width="4"/>',
        f'<path d="M{left+22} {height-13}H{right-12}" stroke="#b29b79" stroke-width="2"/>',
        leaves(plant_x, plant_y, .9, 444),
        f'<path d="M{plant_x-15} {plant_y-13}h32l-4 24q-12 6-24 0Z" fill="url(#pot)" stroke="#9c7450" stroke-width="2"/>',
        '</g></svg>',
    ])
    return "".join(a)


def ground():
    a = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="140" viewBox="0 0 1200 140">',
         '<title>Original decorative shop pavement and small planted pots</title>',
         '<desc>Warm irregular paving stones, a shallow contact shadow and two modest planted terracotta pots. Imaginary scenery with no product or premises claim.</desc>', DEFS,
         '<g stroke-linecap="round" stroke-linejoin="round">',
         '<path id="paving-base" d="M97 67H1095L1170 123Q606 143 29 123Z" fill="#d9c9ae"/>',
         '<path d="M100 71H1092L1148 114Q607 132 51 114Z" fill="#e8ddc8"/>',
         '<ellipse id="ground-contact-shadow" cx="600" cy="76" rx="500" ry="12" fill="#725b44" opacity=".16"/>']
    rng = random.Random(4198)
    for row in range(3):
        y = 81 + row*15
        for i in range(11):
            x = 55+i*100+(34 if row % 2 else 0)
            fill = rng.choice(["#e7ddcb", "#e0d4bd", "#d3c5ae", "#eee4d1"])
            a.append(f'<path d="M{x} {y}l76 -2 11 12-82 2Z" fill="{fill}" stroke="#bcad96" stroke-opacity=".5" stroke-width="1.4"/>')
    for x, s in ((107, .67), (1091, .76)):
        a.append(f'<g id="ground-pot-{x}" transform="translate({x} 7) scale({s})">')
        a.append('<ellipse cx="0" cy="109" rx="54" ry="8" fill="#69583e" opacity=".18"/>')
        a.append('<path d="M-36 58Q0 50 36 58L29 101Q0 118-28 101Z" fill="url(#pot)" stroke="#987050" stroke-width="2"/>')
        a.append('<path d="M-40 54Q0 45 40 54L38 65Q0 75-38 65Z" fill="#b87d59" stroke="#987050" stroke-width="2"/>')
        a.append('<path d="M-26 72Q-26 86-20 95" fill="none" stroke="#e4bb92" stroke-width="3" opacity=".7"/>')
        for i in range(8):
            xx = -36+i*10
            yy = rng.uniform(5, 35)
            a.append(f'<path d="M0 57Q{xx} 36 {xx} {yy:.1f}" fill="none" stroke="#5c724b" stroke-width="2"/>')
            a.append(f'<path d="M{xx} {yy+12:.1f}q-22-3-19-17q19-8 19 17q8-23 21-14q3 17-21 14" fill="{rng.choice(["#718654","#94a174","#61774d"])}" stroke="#566b44" stroke-width="1.2"/>')
        a.append('</g>')
    a.append('</g></svg>')
    return "".join(a)


def plaster():
    rng = random.Random(20261009)
    size = 768
    image = Image.new("RGB", (size, size), (233, 218, 191))
    wash = Image.new("RGBA", image.size)
    brush = ImageDraw.Draw(wash)
    for _ in range(180):
        x, y = rng.randrange(-80, size), rng.randrange(-40, size)
        w, h = rng.randrange(45, 230), rng.randrange(15, 95)
        color = rng.choice([(255,247,222,22), (168,143,108,15), (215,188,149,20)])
        brush.ellipse((x,y,x+w,y+h),fill=color)
    wash = wash.filter(ImageFilter.GaussianBlur(13))
    image = Image.alpha_composite(image.convert("RGBA"), wash)
    brush = ImageDraw.Draw(image)
    for _ in range(2500):
        x, y = rng.randrange(size), rng.randrange(size)
        color = rng.choice([(250,239,216,24), (162,142,111,15), (213,192,159,18)])
        brush.line((x,y,x+rng.randrange(2,17),y+rng.randrange(-1,3)),fill=color,width=rng.choice([1,1,2]))
    # Composite translucent pigment onto an opaque support; never fade the wood sign.
    image = Image.alpha_composite(Image.new("RGBA",image.size,(233,218,191,255)),image).convert("RGB")
    image.save(OUT / "bakery-facade-plaster.webp", "WEBP", quality=93, method=6)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("bakery-facade-upper.svg", upper()),
        ("bakery-facade-upper-mobile.svg", upper(True)),
        ("bakery-facade-ground.svg", ground()),
    ]:
        (OUT / name).write_text(data + "\n", encoding="utf-8")
    plaster()
    names = ["bakery-facade-upper.svg", "bakery-facade-upper-mobile.svg",
             "bakery-facade-ground.svg", "bakery-facade-plaster.webp"]
    RECEIPT.mkdir(parents=True, exist_ok=True)
    (RECEIPT / "artwork.json").write_text(json.dumps({
        "provenance": "Original Python-authored SVG paths and locally painted Pillow plaster. No input photographs, reference pixels, external generation or uploads.",
        "lighting": "Upper-left sun, darker right return, eave/recess/contact shadows; warm cream glazing.",
        "visual_inspection": False, "image_view_calls": 0,
        "source_landmarks": {
            "bakery-facade-upper.svg": {
                "viewBox": [0,0,1200,360], "tiled-roof": [44,34,1122,115],
                "roof-eave": [42,112,1124,137], "plaster-face": [60,115,1090,360],
                "side-return": [1090,115,1180,360],
                "upper-window-centers": [[264,232],[577,232],[890,232]],
            },
            "bakery-facade-upper-mobile.svg": {
                "viewBox": [0,0,600,400], "tiled-roof": [14,34,592,135],
                "roof-eave": [12,132,594,157], "plaster-face": [30,135,560,400],
                "side-return": [560,135,580,400], "upper-window-centers": [[192.5,254.5],[409.5,254.5]],
            },
            "bakery-facade-ground.svg": {
                "viewBox": [0,0,1200,140], "paving-top": 67,
                "ground-contact-shadow": [100,64,1100,88],
                "pot-ground-centers": [[107,80],[1091,90]],
            },
            "note": "Bounds are approximate construction coordinates, excluding stroke expansion; source units are mapped by each image element without object-fit cropping.",
        },
        "files": [{"file": f"web\\assets\\{name}", "bytes": (OUT/name).stat().st_size,
                   "sha256": hashlib.sha256((OUT/name).read_bytes()).hexdigest()} for name in names],
    }, indent=2)+"\n", encoding="utf-8")
    print("Generated four original facade assets; no image views.")


if __name__ == "__main__":
    main()
