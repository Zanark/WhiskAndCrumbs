# Awning plane depth and coherent shadows

Release: `9f51bc3cca618d35dbabb5c36bb571d02fd9d085`  
Pages: [37930956117](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37930956117)  
Asset version: `1825f6cd99c4`

The owner's side-view sketch identifies two connected surfaces: the roof
receding toward the wall and the vertical hanging fabric at the projecting
front. Blue/yellow were explanatory annotations, not requested fabric colours.

## Lighting treatment

- A localized rear contact shadow places the upper attachment against the wall.
- The upward-facing roof is brighter than the vertical front, with a soft
  highlight where the fabric bends over the front edge.
- The existing eight-pixel front bar has a rounded highlight-to-shadow profile.
  A separate 27px falloff casts its lip shadow onto the hanging fabric below.
- Both support rods cast soft down-right shadows from the same upper-left light.
  Shadow and highlight paths are separate from the mirrored hardware geometry;
  the old mirrored group incorrectly reversed their light direction on the right.

The base rose/cream stripe colours, forty-stripe alignment, 15px semicircular
ends, 91px straight valance, canvas dimensions, filled side edges and rigid
hardware geometry are unchanged. This is original illustrative shading, not
a new camera, structural simulation or runtime ray tracer.

## Evidence

The old artwork failed the new roof/front separation check. Local and public
measurements now confirm a brighter roof, dark rear contact, highlighted fold,
rounded front bar and lip-shadow falloff on both cream and rose stripes.
Both shadow samples have alpha66/67, while opposite-direction controls have0.
All six fixed hardware samples remain unchanged during cloth motion.

Bright fold lighting desaturates rose, so the old fixed red-minus-green colour
classifier was unsuitable. The edge check now compares each sample with matching
and opposite neighbouring stripes at the same height. The maximum matching-channel
difference is3, below its8-level limit. It still requires all664edge samples to be
opaque and correctly matched, plus the complete straight band and forty hem tips.

132Node, seventeen cloth and ten asset cases pass. Full local site/entrance/fabric
and public lighting/fabric reviews pass, retaining fixed rails, finite idle,
exact static restoration, input and resource/preference fallbacks.

All175live files and root README/ABOUT match the commit. Seven public paths
changed: the cloth and support SVGs, cache HTML, welcome/entrance showcase images
and root docs. Every other public asset, runtime module, control and product
variant is unchanged.

## Current artwork

`exports\website-launch-20261009-awning-depth\` contains the current six
landscape/portrait launch images, preview, caption, alt text and six-JPEG ZIP.
Only public01/02were replaced; the other four are byte-identical. The latest
lightly frosted foreground and unique Gaussian-cream backgrounds remain.

ZIP SHA256: `57ab8a5e9884b3160bc3c51e4992ebca76951b64d3e79153bf843260d72d8cf2`.
Evidence: `.local\awning-plane-depth-20261009\`, including `publication.json`,
`release-local.json`, `local-lighting-matched-stripes\review.json`,
`public-lighting\review.json`, local site/entry/fabric reports, `public-fabric\review.json`
and `parent-delivery-review.json`. Initial baseline/colour-classifier failures remain.

No image-tool views, Instagram posting, website cream integration or new owner
visual acceptance are claimed.
