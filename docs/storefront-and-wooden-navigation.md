# Architectural storefront and wooden navigation

Release: `3d86ad16057016b2e0f5590c87ac5463064105a0`  
Pages: [37841392015](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37841392015)  
Asset version: `f5adedeeb7c7`

All 174 live site files and the root README/ABOUT match committed bytes.
The 15-path release preserves all 120 product variants, notebook code and colours,
the baked interior, camera, entrance controller and page cloth model/artwork.

## Continuous wooden navigation

The cream strip was a separate navigation row outside `.shop-sign`. The same
three links now live inside that element, so the original continuous wood texture
extends underneath them. The main wordmark, logo and descriptor are unchanged.

Links use 18px rem-based DM Sans, the descriptor's cream colour and its quiet
directional text shadow. How to order uses the original wood texture with a
bevel, warm border and short raised shadow instead of the previous green pill.
Its destination and order semantics are unchanged.

The existing responsive wrapping and 48px targets remain. Light keyboard outlines
are visible against wood; forced-colour and print modes use readable system/plain
colours instead of texture or glow.

The actual rendered navigation-band sample contains zero cream-background pixels
with the labels temporarily hidden for measurement. Its wood RGB standard
deviation is 6.57 / 5.97 / 4.38. Sixteen width/text cases cover 320-2560px and
100%/200% text, including keyboard order, contrast and the raised button.

## A complete original building

The entrance is no longer a disconnected logo plate, awning and giant doors.
It now has a hipped tiled roof, chimney, eave, shaded return, recessed upper
windows, textured plaster, brick plinth, piers and a substantial cornice.
The illuminated wooden fascia uses the existing mark, Courgette and content-driven
brand text. Original architectural details are inspiration-led, not traced or copied
from the owner's reference photographs or illustrations.

The existing blush/cream canopy is supported by the framing. Wide layouts have
fixed display bays on either side of the paired doors; all panes reveal the same
continuous 3D room, never repeated room images. Narrow layouts use a separately
composed upper floor and retain wider doors while omitting the side bays.

Threshold, step and paved base meet, with restrained plants and contact shadows.
The outer building stays stationary both during pointer look-around and entry.
Only the paired doors and bell animate before the existing overlay dismissal.

The We are OPEN plaque remains behind the right door's reflection. Its compact
position preserves cake sightlines; it retains readable 16px/24px lettering.
The tiny extra plaque heart is hidden, while the original glass heart remains.
No business hours, physical-premises claim or new catalogue products are implied.

## Source and reproduction

Authoring files:

- `web\index.template.html`: entrance architecture and navigation containment.
- `web\entrance-shop.css`: entrance-only structure and responsive layout.
- `web\cozy-bakery.css`: main-header wooden navigation/button.
- `scripts\generate_facade_art.py`: original local SVG and plaster generation.

Four new public assets are explicit builder copy/version inputs:

- `bakery-facade-upper.svg`: 1200x360 upper building, 30,948 bytes.
- `bakery-facade-upper-mobile.svg`: 600x400 narrow composition, 25,545 bytes.
- `bakery-facade-ground.svg`: 1200x140 paving and plants, 9,316 bytes.
- `bakery-facade-plaster.webp`: opaque 768x768 pigment texture, 10,088 bytes.

The SVGs contain no external references, scripts, embedded photographs, foreign
objects or copied text/signage. Normal builds copy prebaked artwork; do not run the
generator unless intentionally revising it.

Use `review_architectural_facade.py` without `--source-overlay` for a built or
published release. Source-overlay evidence is useful during authoring but is not
deployment proof. The reviewer covers 12 viewport/text layouts and 13 safety cases,
including one shared room, projected cake visibility, stationary outer architecture,
wood lighting pixels, 48px controls and native/resource/preference escape paths.

## Current artwork and evidence

The new [launch gallery](../exports/website-launch-20261009-storefront/preview.html)
and [six-image Instagram ZIP](../exports/website-launch-20261009-storefront/Whisk-and-Crumbs-Instagram-3x4.zip)
reflect the current facade and main header. All six README images were refreshed.
Instagram remains 1080x1440, with phones only on posts 01/06 and device-free feature
layouts for the middle four. Older kits remain unchanged; nothing was posted.

ZIP SHA256: `38f3ec920d5501f3f62203cb5195d8e75c091597cc2089ca5c9af386cafa8d49`.

Receipts:

- `.local\architectural-facade-20261009\publication.json`
- `.local\architectural-facade-20261009\release-local.json`
- `.local\architectural-facade-20261009\built-facade-review\review.json`
- `.local\wooden-navigation-20261009\wood-row-review.json`
- `.local\architectural-facade-20261009\parent-delivery-review.json`

The combined build has 120 passing Node cases, 25 campaign and 9 asset cases.
Full-site, entrance, responsive-glazing and cloth reviews preserve existing
behavior. Public interaction reports are stored separately alongside the receipt.
The final live site, entry, architecture and cloth suites passed. The first live
plaque pixel comparison caught the room's initial paint inside its rotated bounds;
the reviewer now waits for the room to be ready after text resizing before the
unchanged exact-restoration assertion. No runtime or threshold was weakened.

No new image-tool inspection was performed: the session's previous allowance
remains exhausted. Generated screenshots and source/pixel/geometry evidence do
not establish an exact film-style likeness, aesthetic perfection or owner approval.
