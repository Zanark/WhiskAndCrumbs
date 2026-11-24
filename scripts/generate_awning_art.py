"""Generate the original narrow-striped cloth and its separate rigid tension supports."""

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "web" / "assets"
PINK = "#ce7183"
CREAM = "#fffaf1"
STRIPES = 40


def generate():
    geometry = json.loads(subprocess.check_output([
        "node", "--input-type=module", "-e",
        "import {AWNING_GEOMETRY} from './web/awning-cloth.mjs';console.log(JSON.stringify(AWNING_GEOMETRY))",
    ], cwd=ROOT))
    height = geometry["height"]
    front = geometry["frontBarTop"]
    hanging = geometry["frontBarBottom"] - 2
    hem = geometry["hemBottom"]
    depth = hem - hanging + 2
    width = 1200 / STRIPES
    radius = width / 2
    curve = hem - radius

    def edge(x):
        top = 12 + x * .98
        middle = x + (top - x) * .45
        return f"{top:g} 13L{middle:g} {front * .62:g}Q{x:g} {front - 22} {x:g} {front + 2}"

    stripes = []
    seams = []
    for index in range(STRIPES):
        left, right = index * width, (index + 1) * width
        if index % 2:
            top_left = 12 + left * .98
            top_right = right if index == STRIPES - 1 else 12 + right * .98
            middle_left = left + (top_left - left) * .45
            middle_right = right + (top_right - right) * .45
            stripes.append(
                f'<path d="M{top_left:g} 13H{top_right:g}L{middle_right:g} {front*.62:g}'
                f'Q{right:g} {front-22} {right:g} {front+2}H{left:g}'
                f'Q{left:g} {front-22} {middle_left:g} {front*.62:g}Z"/>'
            )
        if index:
            seams.append(f'<path d="M{edge(left)}"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" preserveAspectRatio="none">
  <title>Original rose-pink narrow-striped bakery canopy</title>
  <desc>{STRIPES} alternating rose and cream stripes cover a projecting roof and a shaded vertical front valance. Upper-left light catches the rounded front edge; a rear contact shadow recesses the roof and the projecting lip casts a soft shadow onto the hanging fabric. Shallow semicircular ends and the overall geometry are retained. Separate fixed supports cast consistent down-right shadows.</desc>
  <defs>
    <linearGradient id="awning-slope-shade" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="#654d3b" stop-opacity=".18"/><stop offset=".18" stop-color="#654d3b" stop-opacity=".04"/>
      <stop offset=".45" stop-color="#ffffff" stop-opacity=".08"/><stop offset=".85" stop-color="#ffffff" stop-opacity=".18"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity=".28"/>
    </linearGradient>
    <linearGradient id="awning-valance-shade" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="#49382a" stop-opacity=".24"/><stop offset=".28" stop-color="#49382a" stop-opacity=".16"/>
      <stop offset=".75" stop-color="#49382a" stop-opacity=".10"/><stop offset="1" stop-color="#49382a" stop-opacity=".08"/>
    </linearGradient>
    <linearGradient id="awning-directional-light" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1200" y2="180">
      <stop stop-color="#fffaf1" stop-opacity=".08"/><stop offset=".5" stop-color="#fffaf1" stop-opacity="0"/>
      <stop offset="1" stop-color="#49382a" stop-opacity=".055"/>
    </linearGradient>
    <linearGradient id="awning-rear-contact" gradientUnits="userSpaceOnUse" x1="0" y1="16" x2="0" y2="40">
      <stop stop-color="#35271d" stop-opacity=".38"/><stop offset=".32" stop-color="#35271d" stop-opacity=".15"/>
      <stop offset="1" stop-color="#35271d" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="awning-fold-light" gradientUnits="userSpaceOnUse" x1="0" y1="{front-14}" x2="0" y2="{front+2}">
      <stop stop-color="#fffaf1" stop-opacity="0"/><stop offset=".72" stop-color="#fffaf1" stop-opacity=".42"/>
      <stop offset="1" stop-color="#fffaf1" stop-opacity=".12"/>
    </linearGradient>
    <linearGradient id="awning-lip-shadow" gradientUnits="userSpaceOnUse" x1="0" y1="{front+8}" x2="0" y2="{front+35}">
      <stop stop-color="#35271d" stop-opacity=".40"/><stop offset=".18" stop-color="#35271d" stop-opacity=".24"/>
      <stop offset=".6" stop-color="#35271d" stop-opacity=".065"/><stop offset="1" stop-color="#35271d" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="awning-front-roll" gradientUnits="userSpaceOnUse" x1="0" y1="{front}" x2="0" y2="{front+8}">
      <stop stop-color="#fff4df"/><stop offset=".18" stop-color="#f3dcc0"/>
      <stop offset=".52" stop-color="#b59572"/><stop offset=".82" stop-color="#70553d"/><stop offset="1" stop-color="#483a2c"/>
    </linearGradient>
    <linearGradient id="awning-rail" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="#71816b"/><stop offset=".3" stop-color="#415743"/><stop offset="1" stop-color="#283e30"/>
    </linearGradient>
    <clipPath id="awning-slope-clip"><rect y="13" width="1200" height="{front-11}"/></clipPath>
    <pattern id="awning-stripes" width="{width*2:g}" height="{height}" patternUnits="userSpaceOnUse">
      <rect width="{width:g}" height="{height}" fill="{CREAM}"/><rect x="{width:g}" width="{width:g}" height="{height}" fill="{PINK}"/>
    </pattern>
    <pattern id="awning-hanging-panels" width="{width:g}" height="{height}" patternUnits="userSpaceOnUse">
      <path d="M0 {hanging}H{width:g}V{curve:g}A{radius:g} {radius:g} 0 0 1 0 {curve:g}Z" fill="white"/>
    </pattern>
    <mask id="awning-valance-mask" maskUnits="userSpaceOnUse" x="0" y="{hanging}" width="1200" height="{depth}">
      <rect y="{hanging}" width="1200" height="{depth}" fill="url(#awning-hanging-panels)"/>
    </mask>
    <pattern id="awning-hem-stitch" width="{width:g}" height="{height}" patternUnits="userSpaceOnUse">
      <path d="M0 {hanging+4}V{curve:g}A{radius:g} {radius:g} 0 0 0 {width:g} {curve:g}V{hanging+4}" fill="none" stroke="#8e5d59" stroke-width="1.2"/>
      <path d="M4 {curve:g}A{radius-4:g} {radius-4:g} 0 0 0 {width-4:g} {curve:g}" fill="none" stroke="#fffaf1" stroke-width=".8" opacity=".55"/>
    </pattern>
  </defs>
  <g id="awning-sloped-fabric" data-stripe-count="{STRIPES}" clip-path="url(#awning-slope-clip)">
    <rect y="13" width="1200" height="{front-11}" fill="{CREAM}"/>
    <g fill="{PINK}">{''.join(stripes)}</g>
    <rect y="13" width="1200" height="{front-11}" fill="url(#awning-slope-shade)"/>
    <rect id="awning-slope-directional-light" y="13" width="1200" height="{front-11}" fill="url(#awning-directional-light)"/>
    <rect id="awning-rear-contact-shadow" y="16" width="1200" height="24" fill="url(#awning-rear-contact)"/>
    <g fill="none" stroke="#986662" stroke-width=".7" opacity=".35">{''.join(seams)}</g>
    <rect id="awning-rounded-fold-light" y="{front-14}" width="1200" height="16" fill="url(#awning-fold-light)"/>
  </g>
  <g id="awning-hanging-valance" data-scallop-count="{STRIPES}" data-curve-depth="{radius:g}" data-straight-depth="{curve-hanging:g}" mask="url(#awning-valance-mask)">
    <rect y="{hanging}" width="1200" height="{depth}" fill="url(#awning-stripes)"/>
    <rect y="{hanging}" width="1200" height="{depth}" fill="url(#awning-valance-shade)"/>
    <rect id="awning-front-directional-light" y="{hanging}" width="1200" height="{depth}" fill="url(#awning-directional-light)"/>
    <rect id="awning-front-lip-shadow" y="{front+8}" width="1200" height="27" fill="url(#awning-lip-shadow)"/>
    <rect y="{hanging}" width="1200" height="{depth}" fill="url(#awning-hem-stitch)"/>
  </g>
  <g id="awning-front-bar">
    <rect y="{front}" width="1200" height="8" fill="url(#awning-front-roll)"/>
    <path d="M0 {front+.7:g}H1200" stroke="#fffaf1" stroke-width="1" opacity=".7"/>
  </g>
  <g id="awning-wall-rail">
    <rect width="1200" height="16" fill="url(#awning-rail)"/>
    <path d="M0 3H1200" stroke="#b3bc9d" stroke-width="1.5" opacity=".65"/><path d="M0 15H1200" stroke="#263b2b" stroke-width="2"/>
  </g>
</svg>
'''
    supports = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" preserveAspectRatio="none">
  <title>Original fixed wall brackets and canopy tension rods</title>
  <desc>Two bolted wall plates carry rigid angled tension rods above the cloth, connected to clamps on the projecting front bar. Both rods cast soft down-right shadows from the same upper-left light. Hardware stays separate from the flexible fabric.</desc>
  <defs>
    <filter id="awning-support-shadow-softness" filterUnits="userSpaceOnUse" x="0" y="0" width="1200" height="{height}" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="1.6"/>
    </filter>
    <clipPath id="awning-support-shadow-clip"><rect y="16" width="1200" height="{front-8}"/></clipPath>
    <g id="awning-tension-support">
      <rect x="150" y="1" width="20" height="24" rx="2" fill="#34483a" stroke="#24392c" stroke-width="1.5"/>
      <path d="M160 16 90 {front+4}" fill="none" stroke="#263b2b" stroke-width="6" stroke-linecap="round"/>
      <path d="M123 101 116.5 117" fill="none" stroke="#536850" stroke-width="9" stroke-linecap="round"/>
      <rect x="77" y="{front-3}" width="27" height="14" rx="2" fill="#34483a" stroke="#24392c" stroke-width="1.5"/>
      <path d="M79 {front}H102" stroke="#91a38a" stroke-width="1.4"/>
      <g fill="#d7b783" stroke="#6d583f" stroke-width=".8"><circle cx="160" cy="7" r="2.4"/><circle cx="160" cy="20" r="2.4"/><circle cx="90" cy="{front+5}" r="2.8"/></g>
    </g>
  </defs>
  <g id="awning-support-cast-shadows" clip-path="url(#awning-support-shadow-clip)" filter="url(#awning-support-shadow-softness)" fill="none" stroke="#35271d" stroke-opacity=".27" stroke-width="7" stroke-linecap="round">
    <path d="M162 18Q149 109 92 {front+6}"/>
    <path d="M1042 18Q1099 109 1112 {front+6}"/>
  </g>
  <g id="awning-support-left"><use href="#awning-tension-support"/></g>
  <g id="awning-support-right" transform="translate(1200 0) scale(-1 1)"><use href="#awning-tension-support"/></g>
  <g id="awning-support-light-edges" fill="none" stroke="#91a38a" stroke-width="1.4" stroke-linecap="round">
    <path d="M158.5 16 88.5 {front+4}"/><path d="M1038.5 16 1108.5 {front+4}"/>
  </g>
</svg>
'''
    (ASSETS / "bakery-awning.svg").write_text(svg, encoding="utf-8", newline="\n")
    (ASSETS / "bakery-awning-supports.svg").write_text(supports, encoding="utf-8", newline="\n")
    print(json.dumps({"height": height, "slope_depth": front+2-13, "stripes": STRIPES,
                      "scallops": STRIPES, "panel_width": width, "curve_depth": radius,
                      "straight_depth": curve-hanging, "rose": PINK, "supports": 2, "image_views": 0}))


if __name__ == "__main__":
    generate()
