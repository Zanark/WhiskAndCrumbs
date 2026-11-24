# Filled sloped-awning side strips

Deployed site: `58febcc649a68dcdcb097ba7453fb33ae3fa5681`  
Current repository/documents: `8be7095995f5ad00676cf5fa3e16cd78a5c09ea6`  
Pages: [37896215170](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37896215170)  
Asset version: `6f4e7c3ab5aa`

The owner marked the narrow uncovered strip beside the sloped fabric. Its SVG
clip inset the top corners by 12 source pixels even though the rails spanned the
full width. The existing full-width rail check therefore missed this gap.

The slope now has a full-width rectangular clip. The last rose stripe also
extends to the right boundary, so both sides fill with their own fabric colour
rather than a mismatched backing. All interior perspective seams, forty aligned
scallops, shading, depth, rigid supports and cloth behavior are unchanged.

## Evidence

The new browser raster regression checks 664 side samples between the rails.
The old asset failed 656 samples, with minimum alpha 0. The corrected local and
live asset has alpha 255 at every sample and zero wrong-colour samples. All
forty scallops remain aligned and all six fixed hardware samples remain unchanged.

Exact native raster comparison changes only 2,450 pixels inside the two outer
13px-wide slope strips. No interior seam, rail or hem pixel changes. The full
131 Node cases, nine asset cases and local site/entrance/fabric reviews pass.
Public edge, fabric and entrance reviews also pass; their reports are stored
separately under the evidence root.

All 175 served files match the deployed commit. Its `site` Git tree is also
identical to current repository HEAD. README/ABOUT match current HEAD separately.
The later README-only commit corrects an accidental 13-character image cache key
to its exact 12-character fingerprint. It does not trigger Pages: the workflow
watches `site/**` and its own YAML. An optional dispatch was denied HTTP 403;
no permission change, retry or alternate deployment was attempted or needed.

Evidence: `.local\awning-edge-fill-20261009\`, including `publication.json`,
`release-local.json`, `baseline-gap.log`, `edge-pixel-comparison.json`,
`parent-delivery-review.json` and the local/public review directories.
The initial delivery-key failure and its captures remain separately recorded.

## Current artwork

`exports\website-launch-20261009-edge-fill\` contains six 1600x1000 landscapes,
six 1080x1440 portraits, preview, caption, alt text and the six-JPEG archive.
Only public welcome/entrance images were replaced; the other four remain unchanged.
Portraits keep phones only on 01/06. No Instagram posting occurred.

ZIP SHA256: `f520bda825eac232a4ba1ad2463afaf349072e84308cbdd01497315a93d9a63c`.
No new image-tool views or owner aesthetic acceptance are claimed. All product
media, runtime code, level-camera posters and the isolated 4174 study are unchanged.
