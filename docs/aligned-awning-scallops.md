# Matching awning stripes and scallops

Release: `f313638c7168892b7c9462bba8588d196aeb4805`  
Pages: [37889702029](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37889702029)  
Asset version: `5f9daa8460ce`

The owner requested equally wide stripes and curved ends. Previously, forty
30pxcolour stripes crossed twenty-four scallops repeated every50px.
`scripts\generate_awning_art.py` now derives the colour pattern, scallop mask
and stitching from the same `1200 / STRIPES` width. Each of the forty stripes
ends in one30pxscallop, wholly within its own rose or cream colour.

The1200x300artboard, slope, hem depth, colours, separate rigid supports and
cloth motion are unchanged. Camera/posters, facade, notebooks, all120product
variants and the isolated4174experiment remain byte-identical.

## Evidence and delivery

- `tests\awning-cloth.test.mjs` and `tests\test_brand_assets.py` require matching
  colour/mask/stitch periods and forty scallops. The full131Node cases, sixteen
  targeted cloth/model cases and nine asset cases pass.
- `review_supported_awning.py` measures forty opaque tip runs at sourceY286.
  Centres align within one source pixel; each tip remains in its corresponding
  stripe with the correct alternating colour. Six rigid support samples are
  unchanged during motion.
- Full local site, entrance and fabric checks pass. Public alignment, fabric and
  entrance checks pass. All175live files and rootREADME/ABOUT match committed bytes.
- Six public paths changed: README, ABOUT, generated index cache references,
  canopy SVG and the welcome/entrance showcaseJPEGs. Other public assets are unchanged.

Evidence root: `.local\aligned-awning-scallops-20261009\`, including
`publication.json`, `release-local.json`, `local-alignment\review.json`,
`local-fabric\review.json`, `local-site\review.json`, `local-entry\review.json`,
`public-alignment\review.json`, `public-fabric\review.json`,
`public-entry\review.json` and `parent-delivery-review.json`.

The immutable kit is `exports\website-launch-20261009-aligned-awning\`, containing
six1600x1000landscapes, six1080x1440Instagram portraits, preview, caption, alt text
and a six-JPEGZIP. Only portrait01/06contain phones; nothing was posted to Instagram.
ZIP SHA256: `aa58515cffbc6ec93d79053f729f9d1ef4053b6666355ab4559c17309348b154`.

No image-tool views were added: the existing session allowance remains exhausted.
Generated captures and numerical checks are not owner visual approval.
