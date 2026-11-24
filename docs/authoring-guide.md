# Whisk & Crumbs authoring guide

This detailed local guide preserves the former working README, release history,
private-media boundaries and maintenance links. The repository-root README is now
the separately reviewed public project overview. Command paths below are relative
to the repository root.

A warm, personal website for home-baked vegetarian cakes.
**Renamed website: https://zanark.github.io/WhiskAndCrumbs/**
**Deployment receipt: [publishing guide](github-pages-publishing.md).**
The generated website contains **175 public files** and fifteen
photograph records. Tea, Birthday and Chocolate now have actual selected cutouts,
not placeholders. The twelve earlier records and 96 earlier image variants are
unchanged. See [the bounded review record](owner-cover-candidates.md) for the
eight sequential sheets, rejected masks and final reflective-face repair.

Canonical repository: [Zanark/WhiskAndCrumbs](https://github.com/Zanark/WhiskAndCrumbs).
The local root remains `C:\devdesk\homedesk\B-Bakery`.
GitHub verified the owner's Oct7rename. The README is now six linked landscape
images only; [ABOUT.md](../ABOUT.md) preserves its public-safe written overview.
The exact pre-edit README bytes stay in `.local\readme-showcase-20261007\before\`.

## Launch artwork workflow

The current six README visuals are a coordinated desktop/mobile launch campaign,
not the earlier section-crop compositions. Use the new pipeline for future updates:

```powershell
$revision = "next-revision"
$captures = ".local\launch-campaign-20261008\captures\$revision"
$composed = ".local\launch-campaign-20261008\composed\$revision"
$cream = ".local\cream-launch-$revision\layers"
python .\scripts\capture_launch_views.py --output $captures
python .\scripts\export_campaign_cream.py --gaussian-clusters --output $cream
python .\scripts\compose_launch_campaign.py --captures $captures --frosted-cream $cream --output $composed
python .\scripts\package_launch_campaign.py --source $composed --output "exports\$revision"
```

The current frosted-glass edition uses the actual original local study material
in static launch artwork only. Keep the study at4174running for layer export.
If the website is unchanged, reuse its latest checked captures instead of recapturing.
Use `--frosted-cream` for one lightly tinted panel over unique Gaussian cream
clusters. The older `--cream-backgrounds` mode has rejected text-shaped masks;
do not restore it. Omitting both flags reproduces the historical studio backdrop.
See [frosted Gaussian cream](frosted-gaussian-cream-art.md) for scope and evidence.

Capture actual complete1280x800desktop and390x844touch-mobile viewports atDPR2,
without editing the page CSS/DOM or substituting section crops. Six1600x1000wide
compositions supply the named`web\assets\showcase\`files; six1080x1440portraits
are independently composed3:4Instagram exports. Only Instagram01and06use phone
mockups;02-05use distinct feature-led compositions. The capture manifest also
records four genuine component captures, including their dimensions, selectors
and hashes. Recipe-note/cover captures include their decorative envelope and
shadows in an explicitly recorded full-page crop; they are not fake full screens.
Do not overwrite them with the
older`generate_readme_showcase.py`layout unless explicitly returning to that design.
Keep raw captures, metadata and unviewed proof sheets private. The upload ZIP
contains only six numberedJPEGs, not the proof sheet or PNGalternatives.

The current motion-follow-up/frosted-glass delivery is`exports\website-launch-20261009-physical-page-turn\`:
offline`preview.html`, `instagram-3x4\`, `readme-landscape\`, caption/alt text and the
six-imageZIP. Earlier original/raised-sign/taller-awning/paler-cover/editorial/
storefront/rose-tilt/studio/level-camera/aligned-awning/edge-fill/readable-opaque deliveries remain unchanged.
The initial cream-background edition also remains intact; the
[Order-label record](order-action-label.md) describes the current notebook update.
Its Order-label delivery is preserved too; [centered cake captions](centered-cake-labels.md)
records the latest alignment-only website revision. Its centered-label delivery
is preserved as history; its old text-masked cream background is now rejected.
The first frosted-glass kit is also preserved; [shallow awning curves](shallow-awning-curves.md)
records the current welcome/entrance refresh with shorter rounded ends.
That kit is preserved too; [awning plane lighting](awning-plane-lighting.md)
describes the latest roof/front separation and consistently directed support shadows.
That kit remains intact; [Back to category covers](back-category-label.md)
records the latest notebook return-label refresh.
That delivery is preserved too. [Catalogue and right-side arrows](catalogue-right-page-tags.md)
records the later removal of per-photo controls and the direct image interaction.
That catalogue kit is preserved too; [physical top-spiral turning](physical-notebook-turn.md)
records the slower1800ms sheet lift, synchronized lighting and fresh source-bound kit.
Device frames are original editorial illustrations, not hardware photographs.
Use the existing bakery mark/palette/fonts and verified websiteURL; do not invent
an Instagram handle or claim a configured bio link. Creating the files is not posting.
README image URLs carry their individual12-character content-hash cache keys.
Image-only releases leave the application cache version and all other site bytes intact.
Header-appearance changes refresh the affected welcome pair without changing the
other five compositions. Capture manifests now explicitly record whether source
files differ from the base commit, alongside exact working-file hashes.
Roof changes also refresh the entrance pair. JPEG privacy checks inspect actual
APP/COM metadata; do not scan compressed pixel bytes as if they were text paths.
The regression command is`python -m unittest discover -s .\tests -p test_launch_campaign.py -v`.
The[readable opaque notebook record](notebook-readable-opaque.md)describes the
larger titles, unchanged controls and solid tab pigment. The[side-gap record](awning-side-gap.md)describes the continuous sloped edges
and current showcase pair. The[aligned-awning record](aligned-awning-scallops.md)describes the matching stripe/
curve widths and refreshed welcome/entrance images. The[level-camera record](level-entrance-camera.md)describes the retained entrance
framing and its refreshed image. The[studio refresh record](studio-launch-refresh.md)describes the image design,
72actualJPEGtypography checks and SHA-bound packaging. Supporting copy is48pxwide/
32pxportrait, at least16pxat540pxdisplaywidth. The[cloth response record](cloth-response-tuning.md)
documents the unchanged current interaction. The[phone-tilt and canopy record](phone-tilt-and-supported-canopy.md),
[storefront record](storefront-and-wooden-navigation.md)
and earlier[October9editorial record](editorial-launch-20261009.md)
preserves the mixed-layout design and review limits.

<p align="center">
  <img src="../site/assets/whisk-and-crumbs-social-card.jpg" width="760" alt="Whisk &amp; Crumbs sharing card with the whisk mark, handwritten wordmark and ribbon cake sticker">
</p>
<p align="center"><em>The current sharing card uses the approved whisk-and-crumb mark and a real reviewed cake sticker.</em></p>

## Run the prototype

```powershell
npm run build
python .\scripts\serve_site.py --port 4173
```

Open **http://127.0.0.1:4173/**. The preview server serves only `site/`, not this
repository or the private photo archive. Node 22+ and Python 3 are required;
the site build has no npm dependencies to install.

The approved order is **home, Our little story, cakes we've made, and how to
order**. The original story and recipe-note illustration are restored immediately
below the hero at the user's request; the earlier three-section restriction is
superseded. All fifteen photograph records use transparent white-outlined stickers, short
design labels and direct full-photo links. Main ordering/contact remains separate.
FAQs, extra custom-cake sections and
message forms remain out. Large reading text, visible mobile navigation and a
keyboard-accessible photo viewer keep it simple to use.
Core content and contact links work without JavaScript; images and fonts are local.
The entrance now uses an original3Droom behind genuinely transparent door glass.
`bakery-scene.mjs` defines grounded geometry; `bakery-view.mjs` owns the common
perspective camera/light matrix; `bakery-interior.mjs` renders the textured scene.
Its cabinet/footings meetY0, with explicit shelf/plate/cake contact points. There
is no independent counter lift or compressed layered artwork.
The default camera now uses eye[0,1.65,8.4]andtarget[0,1.65,-2.5]:level0degree
pitch and a2-scene-unit pullback. Bounded look travel is eye-X1.3/target-X1.8/
target-Y1.25 to compensate for the viewing distance. Camera-only revisions must
regenerate all three posters, but do not rebake illumination or stretch the facade.
The warm room is decorative fiction, not a real-premises or product claim.
Generate original materials with`python .\scripts\generate_bakery_textures.py`,
bake fixed-room illumination with`node .\scripts\generate_bakery_lighting.mjs`,
then static wide/portrait/short fallbacks with`python .\scripts\generate_bakery_posters.py`.
The latter uses the same renderer/model; it never opens images or copies references.
Normal builds copy prebaked assets and need no graphics tools.
The renderer validates the WBL1lighting header against geometry and sun direction.
Rebake after either changes; a stale/missing bake must retain the static poster.
Ray tracing is an offline generation step, not runtime animation. The static
shadow map and world-space window aperture keep direct light independent of the
pointer camera. All scene modules and the explicit thirteen storefront/scene/facade/support assets
participate in the shared version.
`review_entrance_shop.py` checks actual shader camera matrices, grounded contacts,
cake landmarks through both panes, fixed frame bounds and visible depth-dependent
movement; unsupported graphics/resources must preserve the poster and entry escape.
Current revision evidence:.local\painterly-windowlight-20261008\; the earlier
.local\painted-bakery-scene-20261008\preserves the first grounded-room release.
Retired SVGs are preserved
there and excluded from public output. Their former source-coordinate/lift rules
are historical, not guidance for the new room.
The current entrance is a complete original building, not a floating logo/canopy.
`generate_facade_art.py` reproduces three SVGs (wide upper floor, mobile upper
floor, paved base) and a plaster texture. These four assets are explicit builder
copy/version inputs; normal builds never run the artwork generator.
The fixed display bays share the single room canvas and are omitted at600pxand
below while the paired doors remain. CSS coordinates connect the roof, fascia,
cornice, awning, piers, threshold, step and pavement. The entire outer building
stays still during look-around and entry; only the doors/bell perform their motion.
Use`review_architectural_facade.py`against built output (without`--source-overlay`)
for the twelve viewport/text layouts and thirteen safety cases.

The right door contains one decorative "We are OPEN" plaque. Its DOM stays inside
the glass and below the reflection pseudo-element, so it moves with the door and
does not follow camera parallax. Decorative lettering uses bounded artwork sizes;
reading/navigation text retains the rem-based accessibility rules. It is not an
hours/availability claim. `review_entrance.py` covers sign fitting and layering.
Optional phone tilt is controlled by `entrance.mjs`, not by the room renderer.
Only a supported secure coarse-pointer browser exposes the initially-off button.
Request permission from its tap, calibrate the first finite sample, preserve
screen-relative bounded input, and remove listeners on dismissal/preferences.
Never save or upload readings or silently remember opt-in. The wrapped tool row
reserves actual art space; extremely small/enlarged-text cases bypass the optional
entrance instead of clipping controls. `review_phone_tilt.py` uses simulated
sensor/permission events and does not establish native-phone sensor compatibility.
The later whole-site request is recorded in`.local\cozy-bakery-20261008\`.
`web\cozy-bakery.css` loads after entrance-shop.css and before readability.css.
It adds optional original shelf art, timber edges, layered recipe paper,
a quiet linen table surround and order framing. Keep those static and separate
from copy; no gradients/texture behind reading controls or new business claims.
Base styles hide the shelf if this stylesheet fails. The owner explicitly rejected
the hero window; it is no longer in markup, styles or public output, and its
source is preserved privately under`.local\full-width-awning-20261008\`.
The page-header awning is full width, without container padding/max-width.
The SVG uses preserveAspectRatio="none" so its front bar actually reaches both
rendered edges; a100%-wide image box alone would not eliminate SVG letterboxing.
Keep the entrance's separate viewport padding. The current cloth has a1200x300
artboard,40narrow#ce7183rose/creamstripes and40matching shallow semicircular scallops. Its slope runs13-184,
frontbar182-190 andhem188-294. Page height150-337.5pxpreserves the former physical
hem depth while making the slope about54%longer. The entrance keeps its building
envelope while its relative slope grows23%. The separate original
bakery-awning-supports.svg is rigid hardware, not part of the cloth mesh.
`generate_awning_art.py` reads AWNING_GEOMETRY to regenerate both vector assets.
Each stripe and curved end is30source pixels wide. Colour repeats, the scallop
mask and hem stitching all derive from1200/STRIPES; do not restore independent
50pxcurve/30pxstripe periods. `review_supported_awning.py` checks forty actual
alpha-tip runs, aligned centres and alternating single-colour tips, as well as
rigid hardware. The correction changes neither physical hem depth nor motion.
The later proportion correction makes each30px-wide rounded end15pxdeep rather
than53px. Straight hanging fabric now runsY188-279 (91px), with the same final
hemY294. Use true circular arcs and matching inset stitching; do not restore
the long narrow U-shaped ends. The slope and overall canopy dimensions stay fixed.
The roof/front perspective is now conveyed by separate lighting layers: rear
contact shade, a lit upward-facing roof and fold, an eight-pixel rolled front
edge, and a soft lip shadow over the darker vertical valance. Both rod shadows
fall down-right under the same upper-left light; their shadow/highlight paint
lives outside the mirrored hardware group. This is original illustrative shading,
not a new camera, structural model or runtime lighting engine.
The later side-gap correction replaces the inset trapezoid clip with full-width
slope coverage. Only the outermost rose stripe extends to the right edge; interior
perspective seams remain unchanged. The reviewer checks664actual side pixels
between the rails for full alpha and their correct cream/rose colour.
Do not copy supplied shop photographs or watermarks.
`awning-cloth.mjs` models a bounded damped97-by17point spring field; `awning.mjs`
renders the existing SVG texture as a WebGL mesh. Top/front rails and side anchors
remain fixed. The separate metal supports are native static paint. Premultiplied
texture/context alpha plus associated-colour clamping avoids dark or glowing
transparent edges. Compare motion against the reviewer's matched zero-deformation
GPU control, not native-SVG raster differences; retain its locality, colour-footprint
and exact-native-rest guards.
Native SVG paint overlays preserve the two rigid rails. Shared source
geometry keeps the mesh fractions aligned to the SVG. Pointer influence extends112pxaround the page canopy; signed scroll
impulses flutter its cloth. Coarse pointers do not grab it; touch scrolling still
works. The stronger response caps model displacement at min(26px,14%ofheight);
the shader's maximum projected vertical offset is19.5px, inside the20pxdraw gutter.
Broader influence and stronger neighbour coupling spread the wave; reduced damping
lets it linger, reaching exact rest in about4.7seconds in the canonical comparison.
The canvas uses at most approximately2million pixels and DPR2; no frame loop runs
at rest or after a stationary dent settles. Original SVG returns exactly after release.
Motion is disabled for reduced motion, forced colours, print, background/offscreen
states and open dialogs/entrance. Missing CSS, modules or WebGL stays static.
The two modules are independently optional and share the existing asset version.
Use review_awning_fabric.py for actual pixel/locality, rail, scroll, idle, GPU-loss,
resize and fallback coverage. The user-rejected cream effects remain removed.
The story inset shadow was removed separately to match its flat-green scalloped edge.
The original cream/deep-green palette is restored. Courgette supplies clearer,
lightly handwritten headings; heart doodles, scallops and rounded buttons remain.
The main header is a larger centered wooden shop sign, with the unchanged mark on
a cream medallion and sharp cream Courgette lettering. The owner explicitly
rejected the center fade: original opaque grain now runs beneath the whole
identity, with raised letter edges, directional drop shadows and warm static
backlighting. Navigation is now inside the same `.shop-sign`, below the identity,
so its background shares continuous wood instead of a separate cream band.
Its cream18pxlinks match the descriptor; How to order has the existing original
wood texture with a bevel/shadow. Retain48pxtargets, wrapping and light focus rings.
Forced-colour and print modes replace the texture with readable system/plain colours.
`generate_sign_wood.py` produces the original1600x600grain/plank texture without
reference photographs. It is versioned through the builder and a CSS custom
property on the sign; do not add a mask or texture wash behind the name.
Use88/60.8/44.8px rem-based desktop/tablet/mobile lettering and128/96pxmark boxes.
Do not cap text enlargement with viewport-only sizing or animate the glow.
The public welcome showcase is the only image updated for header-only revisions.
Reading copy and ordering controls retain DM Sans. The user has now chosen
**Whisk & Crumbs**, with descriptor **Home-baked vegetarian cakes**.

<p align="center">
  <img src="../site/assets/stickers/ribbon-and-pearl-cake-sticker-480.png" width="360" alt="Transparent ribbon and pearl cake sticker with a white contour">
</p>
<p align="center"><em>Gallery cakes are separate transparent sticker derivatives; select a cake image to open its full prepared photograph.</em></p>

## The category notebooks

The section heading stays **Cakes we've made**, above six top-bound notepads:
Birthday Cakes, Tea cakes, Cream cakes, Decorated cakes, Doll cakes and Chocolates.
The cover opens with a short zoom into a native modal. Small original
category-specific stickers surround a reviewed category photograph where one is available.
The cover is now extra-pale blush pink `#fbedf2`, another50%white blend of
previous`#f7dbe4`, following the owner's further lightening request,
with deep-green text and no cream label
rectangles. Inner pages and the website stay cream. Nearly square edges, thin paper layers
and a subtle green backing board are retained. The rejected wide left-spine strip and oversized
folded cover corner are removed; paired wires pass through top-edge holes.
The weight-note accent remains#f7dbe4under`--weight-note-accent`; only notebook
faces use`--cover-paper`. Do not globally replace older pink values in the roof,
artwork, tabs or historical records when changing covers.

Every notebook opens directly to photographs, without a weight page.
The available **cake weights, 1/2 KG to 3 KG** in half-kilo steps, appear once as
plain information above the cover grid. There is nothing to choose and no weight
added to enquiries. Unused pagination is hidden on one-page books.
Photo pages hold four
photos at most. The owner explicitly retained four rather than adaptive fewer-photo
pages. Open notebooks fit the viewport without vertical scrolling: two-by-two on
desktop/portrait phones, four across on short landscape screens. Images and
spacing adapt while readable text and 48px controls remain.
Use the two left/right arrow tags attached on the RIGHT edge, keyboard arrow keys,
or optionally drag the next-page arrow upward. Single-page books hide pagination.
The top Back button closes the notebook and returns focus to its cover.
Its accessible name is Back to cake categories, distinct from Previous page.
Closed covers now show3-5text-free pastel index markers, with fixed per-category
colour/height/placement variation. Only the18-26pxoutside section is painted;
there is no attachment rectangle over the pink paper. A32pxreserved grid gutter
contains the decoration; never use runtime randomness or interactive
elements for decoration.
The native open-book dialog is transparent, borderless and shadowless. Paper and
its thin backing are painted by the toolbar/stage/sheet pseudo-elements, leaving
real exterior space. The default6remright gutter exposes96pxofcategory-return Back
and both page arrows, with16pxattached to the paper. There is no left action
gutter, bottom action footer or separate Turn control. The page counter stays
outside the two buttons. Short landscape keeps the same right-side navigation.
Labels, not just flag tips, sit beyond the visible backing; no overflow clipping.
Cake-section description is1.5rem(24px); cake names and enlarged-photo titles
are1.75rem(28px), open category titles2.125rem(34px), and cover/static category
titles2.25rem(36px). Text button labels stay1.25rem(20px), helpers1.125rem(18px);
the new arrow glyphs are1.75rem(28px).
Cake captions use full-width labels and centered text beneath their image frames,
in both enhanced and static notebooks. Other headings/control alignment is unchanged.
Tabs and attachment strips now use uniform opaque pastel pigment; their previous
pale gradients simulated translucent tape over an already opaque cream backing.
Closed cover flags also use100%pigment rather than96%alpha. The paper stays
opaque, while logical gutters outside it remain transparent for the exterior tabs.
Targets stay at least48px. Catalogue photos have no Enlarge/Ask/Order controls or
pseudo-labels. Their native full-JPG anchors open the existing category-scoped
viewer on click/Enter/Space, restoring focus to the exact image on close.
Modified clicks remain native; noJS and a failed viewer still follow the image URL.
The next arrow is also the drag handle, with one advancing click listener.
Do not shrink text to hide viewport limits. The measured20-case matrix now has
twelve fallback category/viewport/text combinations: seven Decorated and five
narrow200%single-photo cases. Decorated360x640100%now retains four photos.
All remaining fallbacks retain explicit measured reasons and complete static pages.
See`review_notebook_fit.py`and workstream62; older matrices remain historical.
The separate900px-height reflow sweep also checks all six widths at100%/200%;
its fallback set is now Decorated320/390/600at200%only. At100%,320pxfits, and
768pxat200%also fits. The catalogue record preserves exact before/after evidence.

<p align="center">
  <img src="../.local/category-notebooks/pastel-blue-covers/local-site/categories-desktop.png" width="900" alt="Automated capture of six pastel-blue notebook covers with the existing category stickers">
</p>
<p align="center"><em>Historical automated capture of the now-rejected blue covers. Current cover faces are light pink; this capture is preserved as history, not current appearance.</em></p>

<p align="center">
  <img src="../.local/category-notebooks/viewport-fit-confirmed-weight/birthday-cakes-390x844-100-page0.png" width="390" alt="The fitted image-free weight page with half a kilo selected and all controls visible">
</p>
<p align="center"><em>Historical weight-selection capture. Selection controls and all notebook weight pages have since been removed; cake weights are now mentioned once before the covers.</em></p>

Reduced motion, forced colours, no JavaScript and missing styles/scripts show the
complete notebooks directly. Interrupted animations cannot leave pages hidden or inert.
The hero is separate from the notebooks: a full-width cream section with
deep-green copy, terracotta emphasis and the original cake/actions. Its spiral, paper frame, fold and
pointer tilt are removed; Our little story is unchanged below it.
The previous single-sheet images remain unchanged in `docs\images\` as historical
release evidence, not current category screenshots.

**Current contact channel: Instagram, still @homemadevegcakes.** No WhatsApp number, prices, delivery
area, testimonials or baker's portrait have been invented. The gallery names are
descriptive labels for past bakes, not confirmed menu products.

Edit `content/site.json` for business/contact details, `content/cakes.json` for
the cake records, `content/notebooks.json` for category membership/covers, and `web/`
for the design. Run `npm run build` after edits. Do not
edit generated `site/` files directly.

## Start here

- [TODO catalogue and workstreams](../TODO/00_INDEX.todo)
- [Prototype maintenance and release guide](prototype-guide.md)
- [GitHub Pages publishing and release evidence](github-pages-publishing.md)
- [Whisk & Crumbs identity, quiet backgrounds and reproduction](brand-and-backgrounds.md)
- [Website design and ordering plan](website-plan.md)
- [Layout references and readability direction](layout-reference-review.md)
- [Instagram photo acquisition guide](instagram-photo-import.md)
- [Prepared prototype cake photos](../assets/images/cakes/README.md)
- [Cake-sticker provenance and local reproduction](../assets/images/cake-stickers/README.md)
- [Original design specification](references/home-bakery-design-specification.pdf)
- [Kitchen mood references and provenance](../assets/references/README.md)

## Brand and quiet backgrounds

The original tilted balloon-whisk mark has three crumb dots. A complete transparent
logo, SVG/PNG/ICO favicons, apple touch icon and
`whisk-and-crumbs-social-card.jpg` replace the previous public identity. Sparse
outline bakery patterns use the existing cream/deep-green palette, at whole-layer
opacity 0.075 and 0.065 respectively. Header, buttons and recipe note stay solid;
the story, real cake stickers and large Instagram action remain unchanged. The
category notebooks read as cream paper with top spiral binding
and light inner-page rules only in open space. Page paper matches the surrounding cream;
fully opaque local backgrounds remove both rules and pattern outlines behind text.
Thin layered paper edges and a backing board give the category sheets depth.
The hero instead uses an unframed full-width layout on its original cream background, with no binding,
paper edge or tilt; category notebooks retain the page turns described above.
The later owner request supersedes ordinary scrolling inside enhanced notebooks:
fit four contained photos to the screen, without shrinking text or hiding controls.
The entrance now behaves like a real arrival rather than an automatic splash:
the padded bakery doors fill the viewport, respond gently to pointer movement and
open only after clicking anywhere or activating the entry link by keyboard. That
same gesture attempts the short local bell; skip and no-enhancement paths remain.

Artwork regeneration is separate from an ordinary build:

```powershell
python .\scripts\generate_brand_assets.py
python .\scripts\generate_social_card.py
npm run build
```

Generation uses Pillow plus existing Playwright/Edge, with no new dependencies.
Normal `npm run build` only copies prebaked artwork. Six supplied pattern references,
the prior site/review archive and `.local\branding\` review images/hash receipt remain
private. [Workstream 12](../TODO/12_WHISK_AND_CRUMBS_BRAND.todo) records the original delivered
request: 25 passing Node cases, four passing branding cases, 66 public files and
passing local/public browser reviews. The parent inspected the complete desktop page,
mobile hero, dark story, identity/native-size icon sheet, pattern previews and social
card before publication, then confirmed the live site. The chosen display name is
approved; **brand availability,
trademark rights and legal uniqueness have not been checked**.

## Current photo status

The four supplied kitchen inspiration images and original design PDF are saved.
A public download attempt for
[@homemadevegcakes](https://www.instagram.com/homemadevegcakes/) on 2026-10-04 was
stopped by Instagram's HTTP 429 rate limit. **No photos were downloaded from
Instagram by that request.** The owner subsequently supplied an extracted export,
which was imported offline: **167 eligible files, 160 unique originals and seven
byte-identical duplicates**. Eleven files were excluded by the import policy.
These counts describe the supplied export, not everything ever posted.

Five supplied screenshots have retained crop-only WebP/JPEG variants and untouched
originals under `.local\photos\prototype-20261004\`. The user's later choice
authorizes separate background-removed derivatives with white sticker contours:
20 transparent WebP/PNG variants, produced locally from recorded masks. Seven
additional, visually reviewed export photos now add 28 metadata-free full-photo
variants and 28 separate sticker variants. New selections avoid personal names,
photo toppers and unrelated media. The hero
and gallery show stickers; "View larger photo" opens the full prepared JPG, not
the cutout or private screenshot.

The local pipeline uses rembg/BiRefNet for candidate masks and recorded alpha-only
corrections. Normal preparation uses reviewed masks and Pillow without inference
or a network connection. No photographs are uploaded. Already-clipped cherries,
dress base and upper feather remain clipped; these are not reconstructed or
claimed to be perfect cutouts. See the asset guide above for commands and limits.

The export and all imported originals remain unchanged and private under the
source archive and `.local\instagram\imported\`. The seven-photo crop recipe and
lossless masters are in `.local\photos\notebook-20261004-v2\`; reviewed masks and
source hashes are recorded in the asset manifests. An earlier incorrectly
associated private candidate batch was rejected and was never promoted.

Raw account exports and imported originals stay local and Git-ignored. The
generated public directory is allowlisted for web-ready images and site assets.
The current generated build contains **160 files**, including original storefrontSVGs, six showcase JPGs and60sticker copies under
`site\assets\stickers\`. Masks, manifests, recipes and private review artifacts
are not public assets. [Workstream 12](../TODO/12_WHISK_AND_CRUMBS_BRAND.todo) records
the identity release; [workstream 13](../TODO/13_BAKERY_ENTRANCE_AND_COOKBOOK.todo)
records the deployed twelve-cake notebook. [Workstream 16](../TODO/16_CATEGORY_NOTEBOOKS.todo)
records the category interaction and selected cover extension; [workstream 15](../TODO/15_BOUNDED_IMAGE_REVIEW.todo)
owns the remaining archive classification.
[Workstream 11](../TODO/11_PALETTE_READABILITY_AND_PUBLISHING.todo)
retains the earlier 58-file public typography/layout release, and workstream 09
retains the sticker/source checks.
Native app/device/assistive-technology acceptance and feedback on the corrected
font remain open; these are separate from the explicitly requested public release.

## Current release evidence

Catalogue release `afb18cbf22ce250bec7f7f1912fcec28c7dc582f`,
Pages37949350437, version `e582762c863a`: all175live files and README/ABOUT match.
132Node/43campaign/10asset cases and72JPEG checks pass; local and public each pass
134notebook states/300photo views and full site/entrance reviews.
Receipt: `.local\catalog-right-tags-20261009\publication.json`.
See [the publishing guide](github-pages-publishing.md) for the frozen-source build
boundary that excludes the preserved, unpublished workstream64neon entrance rules.

### Historical release evidence

- Pastel-blue replacement: `a05964d`, Pages37260819501, version395f59e906ff.
  Honey was explicitly rejected. All149live files/README match;69Node and
  full local/public checks pass. Current contrast4.89:1text/1.71:1surface.
  Receipt: `.local\category-notebooks\pastel-blue-covers\publication.json`.
- Honey covers: `cf39360`, Pages37253171653, version9d0024f53bc6.
  All149live files/README match. Cover-only colour, cream interior/body,
 4.61:1minimum text contrast and1.81:1surface separation checked locally/publicly.
 69Node cases pass; no image files or interactions changed.
  Receipt: `.local\category-notebooks\honey-covers\publication.json`.
- Shared cake-weight line/photo-first notebooks: `d974f0e`, Pages37251302622,
  version574cbd67dd02. No notebook weight pages; one informational line before
  all covers.149live files/README match;68Node,152notebook/285photo local states
  and local/public browser checks pass. No covers/media changed.
  Receipt: `.local\category-notebooks\shared-weight-info\publication.json`.
- Chocolates exception: `5c08f99`, Pages37248095888, version0c48670fb432.
  Opens directly to photos, with no weight page or redundant single-page controls.
  Five cake weight lists remain; all149live files/README match.68Node,
 247notebook/285photo local states and local/public browser checks pass.
  Receipt: `.local\category-notebooks\chocolates-no-weights\publication.json`.
- Informational weights: `6b208e2`, Pages37246546238, versiond1809cdaaf48.
  Six noninteractive lists, no weight inputs/state and unchanged enquiry links.
  All149live files/README match;66Node,266notebook/285photo local fit states
  and full local/public browser checks pass. Receipt:
  `.local\category-notebooks\informational-weights\publication.json`.
- Horizontal/font-safe follow-up: `bb52b9a`, Pages37244829214, versiona44d4ef52290.
  All149live files and current README match. Enlarged photos and notebook controls
  fit both axes;266notebook/285photo states pass locally/publicly, including
  late-font success/failure and full browser checks. All120media variants are
  unchanged. See `.local\category-notebooks\horizontal-overflow\publication.json`.
- Cover/viewport-fit update: `9612799`, successful Pages37242217458, version32e45347bbe2.
  All149live files and README match;65Node, nine sticker/provenance cases and
 224measured page/viewport checks pass on local and public hosts.
  Evidence is in `.local\category-notebooks\publication-local-fit\`,
  publication-local-site/entrance and the separate publication-public-* folders.
  Extreme screen/text combinations explicitly show readable full-page content,
  not clipped notebooks. Deployment is recorded in the publishing guide.
- The following receipts are historical releases, not the current cover state.

- One-icon correction: `63f4437e4849802a9658770633753f68e1d288ae`;
  [Pages run 37230426976](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37230426976)
  succeeded. Only index.html changed from 49aa348; all 125 served files match
  committed blobs and the live Cream notebook works. Receipt:
  `.local\category-notebooks\mixing-bowl-publication.json`.
- Category release: `49aa3488b4a746e2866735571d4c7d6caef9d993`;
  [Pages run 37227774315](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37227774315)
  succeeded. Version `c4a9e6c342ee`, all 125 live files and public README match
  committed blobs. Both public browser checks pass; new cover candidates remain
  private and new-output visual inspection is still unperformed.
  Receipt: `.local\category-notebooks\publication.json`.
- Singular-brand notebook: `be221e660422dad8e74a67a46526ab81f3391306`;
  [Pages run 37212121826](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37212121826)
  succeeded. Live asset version `e268ea148bb4`; all 124 served files and the public
  README match committed blobs. Both live browser reviews pass.
- This release adds the explicitly requested public-safe root README. The complete
  former working README is retained in this local guide; private source material
  remains outside the public repository snapshot.

During push, GitHub reported that the repository had moved to
`https://github.com/Zanark/WhisksAndCrumbs.git`; the API confirmed that canonical
repository and its Pages address. The parent did not rename the repository or local
folder: it followed the verified destination, updated origin and corrected
`siteUrl`, canonical and Open Graph URLs in the final commit.

- First rebrand: `a1ff03b249ba5908d73e881cf32a92e0475c54f3`;
  [Pages run 37195641928](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37195641928) succeeded.
- Final canonical correction: `9723c286e465d2c6ebec59c1db4555f0f664dcd5`;
  [Pages run 37195797175](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37195797175) succeeded.
- Entrance/cookbook update: `f3761031b04fc1fe277988a3cb76ac642ccdb63f`;
  [Pages run 37200032861](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37200032861) succeeded.
  This release exposed a mixed-cache failure and was immediately rolled back.
- Cache-safe entrance/cookbook release:
  `9be430e0df63478dd08ff24735bcccc13a10ba98`;
  [Pages run 37200454931](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37200454931) succeeded.
  CSS and modules now share a generated content version. The committed and served
  CSS/JS bytes match, and both live browser reviews pass.
- Corrected spiral binding: `6325cad`;
  [Pages run 37203943996](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37203943996)
  succeeded. Dark wire loops now pass through rectangular punched slots, matching
  the supplied top-bound notebook construction instead of oval-and-dot symbols.
- Click-to-enter parallax doorway: `5c61fc3`;
  [Pages run 37204518507](https://github.com/Zanark/WhisksAndCrumbs/actions/runs/37204518507)
  succeeded. The live doorway fills the viewport within responsive padding, moves
  subtly with the pointer and opens/rings only after intentional entry.
- Public review passed against the exact canonical URL above; the parent verified
  12 served HTML/CSS/logo/icon/pattern/social files against the final commit's bytes.
- `.local\publication-whisks-and-crumbs.json` is the final CI receipt.
  `.local\website-review\` holds public evidence; `.local\branding\local-site-review\`
  preserves the local review. These directories and these docs remain private.

The earlier rebrand committed only public `site/` files. The singular-name notebook
release adds the explicitly requested public-safe root README. Authoring sources,
references, masks, model caches and this detailed local documentation remain local.

## Hosting and orders

Instagram enquiries work now. Adding a confirmed, digits-only international
`whatsappNumber` in `content/site.json` and rebuilding activates the WhatsApp
message path. The baker still confirms availability, price and fulfilment
personally; the site does not place or confirm orders.

The user explicitly requested GitHub Pages publication after the hosting warning.
GitHub Pages
[does not allow sites primarily facilitating commercial transactions](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
That restriction remains a hosting risk, not resolved by external messaging links.
The plan records a GitHub-connected alternative.

The first release is commit `ac905f6`, published by the Pages workflow. Only the
generated site, ignore rules and workflow were pushed; the authoring source and
private working materials remain local. `siteUrl` is configured to the live URL.
