# Shallow awning curves and longer straight fabric

Release: `078067f8b831dbfd8668eb3d3bdb07ef970c3c08`  
Pages: [37928044903](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37928044903)  
Asset version: `5144b7e3b8c8`

The owner requested shorter rounded ends and more straight hanging fabric.
The forty elongated 53px curves are now true semicircles, each 30px wide and
15px deep. The straight valance extends from Y188 to Y279: 91px instead of 53px.
The rounded portion is about72%shallower; the same38pxwas added to the straight
section, so the hem still ends at Y294.

`generate_awning_art.py` derives the radius from half the stripe width. The
scallop mask and inset stitching use matching circular arcs. The 1200x300
canvas, projecting slope, filled side edges, rails, colours, hardware and cloth
physics are unchanged. This is a hem-proportion change, not a smaller awning.

## Evidence and preserved behavior

The new shape check first failed against the old artwork: 4,400 of 106,800
pixels in the required straight band were unfilled. The corrected local and
live artwork fills that band completely, with all forty aligned single-colour
tips, 664 opaque side samples and unchanged fixed-support samples.

131 Node, sixteen targeted cloth and nine asset cases pass. Full local site,
entrance and fabric checks pass; public shape and fabric checks also pass,
including fixed rails, finite idle, scroll response, resource/preference fallbacks
and exact static restoration.

All175live files and README/ABOUT match the commit. Only six public paths changed:
awning SVG, cache HTML, welcome/entrance showcase images and root documents.
Upper-slope/rail SVG groups and every other public asset remain unchanged,
including all120product variants, notebook controls and runtime modules.

## Current launch artwork

`exports\website-launch-20261009-shallow-awning\` contains current6wide/6portrait
images, preview, caption, alt text and the six-JPEG ZIP. It preserves the latest
lightly frosted foreground and distinct Gaussian-cream backgrounds, with phones
only in portraits01/06. Public01/02were refreshed; the other four remain identical.
Previous kits are preserved.

ZIP SHA256: `ec49b8665737f883e90ce1ad0c04c3d6c49217f539f5d5eba8e6c13539c6b303`.
Evidence: `.local\shallow-awning-curves-20261009\`, including `publication.json`,
`release-local.json`, `baseline-shape.log`, `local-shape\review.json`,
`local-site\review.json`, `local-entry\review.json`, `local-fabric\review.json`,
`public-shape\review.json`, `public-fabric\review.json` and `parent-delivery-review.json`.

No image-tool views, Instagram posting, live cream integration or new visual
acceptance are claimed.
