# Raised glass edges for Instagram phone mockups

[Review the updated images](../exports/website-launch-20261009-instagram-raised-glass/preview.html).

The phones in Instagram posts01and06 now have a rounded, raised glass edge rather
than a single flat outline. Three original shaded surfaces form the rear body,
metal surround and convex glass rim. Surface normals produce a coherent
upper-left highlight that rolls off across the7pxglass edge, with a3x4pxoffset
revealing the darker sidewall.

The surround is slightly wider; screen width and aspect ratio are unchanged.
The complete resized website viewport is pasted after the edge shading and
checked byte-for-byte before whole-device rotation. Nothing is cropped, warped,
recoloured or covered with a simulated glare patch. This is an original
2.5D illustration, not a photograph or a geometrically projected phone model.

The six background colours, ivory cream, lightly frosted panel, text and desktop
views remain unchanged. The four middle Instagram images and all six README
landscapes are byte-identical to the colour edition. No website or local cream
preview files were changed.

## Reproduction and evidence

Add `--raised-phone-glass` to `scripts\compose_launch_campaign.py`, retaining
`--portrait-colour-variance` and the existing `--frosted-cream` layers.
Use fresh output directories. `scripts\campaign_phone.py` supplies the surface
renderer and phone-only receipt validation; defaults reproduce the old surrounds.

The package verifies that only the two portrait phones carry the treatment, and
their actual viewport-preservation proof is present.49campaign tests and72JPEG
typography checks pass. Final JPEG edge-shading measurements cover native1080px
and540pxfeed widths for both phones; the gallery works at four widths.

Evidence: `.local\instagram-raised-phone-glass-20261009\validation.json`,
`gallery.json`, `tests-final.log` and `completion.json`. No new images were viewed,
posted or visually approved; all previous kits are preserved.
