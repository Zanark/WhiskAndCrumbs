# Bakery prototype: maintenance and release

The approved section order for the local prototype is **home -> story -> cakes ->
order**. The original "Our little story" copy and recipe-note illustration
are restored directly under the hero. This supersedes the previous three-section
restriction, not the decision to omit FAQs, forms and extra custom-cake content.
The verified renamed website is https://zanark.github.io/WhiskAndCrumbs/ following
the user's explicit request. See [the publishing guide](github-pages-publishing.md)
for the release commit, workflow and safe update process.
The reviewed category update supplies all six real cover stickers and fitted
four-photo notebook pages without vertical scrolling. It retains the mixing
bowl/whisk correction, cream hero, original story and entrance. There are fifteen
photo records and175generated files including six README showcase JPGs and
four original storefront SVGs; the
rejected cream-surface module is removed. See [the bounded review record](owner-cover-candidates.md)
and the publishing guide for the actual release receipt. P038/P145 source work
and the separate 141-image archive remainder are not completed by this update.
The root README has exactly six linked landscape showcase images and no visible
prose. The former public overview is preserved in [ABOUT.md](../ABOUT.md).
The detailed local maintenance history remains in [the authoring guide](authoring-guide.md).

Readability is a core product requirement, recorded in `AGENTS.md` and TODO
workstreams 08 and 09. Current reading copy is 18px, key labels/help text at least
16px, and principal controls at least 48px high. Keep the text brief and direct order
links obvious. Preserve the restored story without new biography; do not add FAQs
or a message form, or shrink type to fit more content. Navigation remains Home,
View cakes and How to order, without another story button.
The main Instagram contact is a large camera-logo button, with a visible action
label and associated handoff instructions. Its SVG uses the existing palette and
is omitted when WhatsApp is the configured channel.

The current visual direction is intentionally cute: locally hosted Courgette
for lightly handwritten display text; the original cream/deep-green palette;
scalloped section edges, small heart/bow doodles and rounded controls. DM Sans
remains on paragraphs, navigation and ordering actions. Do not make instructions
small or ornate. Keep wrapping/reflow at 200% text size, including narrow phones.
Weights are information, not a product configurator. A single **Cake weights**
line appears before the notebook covers. No category has a weight page or asks
visitors to choose a size; every populated notebook opens directly to photographs.

The category notebooks use light-pink covers and cream inner paper, dark wire loops
passing through rectangular punched slots along the top edge, light rules in open
space and the real transparent cake
stickers to read as a cookbook rather than an ecommerce grid. Fully opaque cream
or green local backgrounds remove rules and pattern outlines directly behind text.
The hero sits outside the notebook treatment in a full-width cream section,
retaining its original deep-green text, terracotta emphasis, headline, cake and
green/outline action links. The user rejected the unintended green background;
the story reference did not authorize a palette change.
It has no spiral, paper frame, fold or pointer tilt. Category notebooks
use nearly square light-pink cover faces, cream inner sheets, fine bottom paper layers and a thin
green backing board, without a broad left spine or a large folded cover corner.
Their paired top-wire loops are original SVG, not reference-image pixels.
The previous hero-only tilt initializer is removed; category notebooks retain
the explicit zoom/page interaction below.
Touch and reduced-motion layouts never get a hover-only dependency.
The cover-only colour is `--cover-paper: #f7dbe4`, a50%white blend of the previous
pink, following the user's2Xlighter request. Blue and honey remain rejected.
Title/count backplates are transparent with deep-green text. Text contrast is
7.59:1; cover/canvas separation is1.10:1 plus the existing deep-green backing board.
The earlier1.7surface target belonged to the darker colours, not a WCAG text rule.
Body/hero/inside paper stay
`#f5ebdd`; this request does not authorize recolouring those surfaces.
The latest colour/layout checks are programmatic, not additional image-tool viewing.
The original serif design remains in `.local\revisions\before-cursive-20261004\`.
The user rejected the later pink/sage palette and overly cursive Dancing Script.
That superseded revision remains in `.local\revisions\before-palette-correction-20261004\`.

## Source of truth

| Location | Purpose |
| --- | --- |
| `content/site.json` | Confirmed display name, real Instagram, optional WhatsApp/email/location and current public URL |
| `content/cakes.json` | Fifteen photograph records, including a two-cake group and chocolate assortment |
| `content/notebooks.json` | Six ordered category notebooks, explicit cake IDs and same-category cover choices |
| `web/index.template.html` | Semantic page layout and editorial copy |
| `web/styles.css` | Design tokens, typography, responsive layouts and motion preferences |
| `web/readability.css` | Readability baseline, explicit controls and simple mobile navigation; intentionally loaded last |
| `web/contact.mjs` | Pure enquiry formatting and contact-link validation |
| `web/main.mjs` | Category-scoped photo viewer, contextual contact and versioned optional modules |
| `web/notebooks.mjs` | Available weight data, four-photo grouping, modal opening, page turns, pointer lifecycle and safe fallbacks |
| `assets/images/cakes/` | Prepared photo variants and their provenance/crop manifest |
| `assets/images/cake-stickers/` | Transparent WebP/PNG variants, mask recipe, masks and source-side provenance |
| `scripts/prepare_cake_stickers.py` | Opt-in local mask inference, recorded alpha refinement and Pillow-only preparation |
| `web/assets/` | Whisk/crumb logo, favicon set, faint outline tiles, branded sharing image and licensed local fonts |
| `scripts/generate_brand_assets.py` | Reproduce the logo, icon variants and outline patterns using Pillow and existing Playwright/Edge |
| `scripts/build-site.mjs` | Static generation and public-file allowlist |
| `site/` | Generated public output; do not hand-edit |
| `TODO/00_INDEX.todo` | Current workstreams, blockers, acceptance criteria and development ledger |

The user selected **Whisk & Crumbs**, with **Home-baked vegetarian cakes** below it.
The Instagram handle remains `homemadevegcakes`; do not guess a replacement account.
Prices, dietary specifics, lead times, service area and payment/cancellation
terms still need confirmation. None is fabricated to make the site look
finished. Only the previously supplied story has been restored; new biography,
portraits and reviews have not been authorized.

The outline-only background tiles preserve the original colours. Their whole-layer
opacity is 0.075 on cream and 0.065 on green, covering about 1.62% of each tile.
Buttons, the header and the recipe note stay solid. See
[brand assets and quiet backgrounds](brand-and-backgrounds.md) for reproduction,
the private reference boundary and favicon formats.

## Static background; cream experiment parked

The owner rejected the pointer-reactive cream effect and requested its removal.
The original cream canvas and quiet outline pattern are static again. There is
no cream module, CSS gate or effect canvas in the active website.

Source, tests, browser-review script and integration snapshots are preserved
privately for a future revisit. See [the parked-effect record](parked-cream-effect.md).
Do not restore either rejected prototype without a new request.
`review_site.py` checks unchanged pixels under mouse movement, no cream resource
request/canvas and a404response at the former module URL.

## Bakery entrance and bell

`web/entrance-shop.css` provides a restrained sloping/scalloped fabric canopy
beneath the normal header and a matching one above the entrance doors. Both use
the original `bakery-awning.svg`; they do not cover the navigation or hero copy.
The doorway contains a single room behind both transparent glass windows:
original back-wall, middle shelving/pendant and foreground counter SVG layers.
Separate bounded parallax factors produce depth without moving text or controls.
The glass sheen is translucent, with surrounding opaque green door panels.
The foreground has a fixed raised position so the illustrated cakes remain
visible through the windows; touch/no-hover keeps that position without movement.

The scene is an imaginary decorative bakery, not the owner's actual premises or
new menu products. No stock-reference pixels, labels or characters were copied.
OriginalSVGsyntax/geometry and actual window pixel differences are checked;
`review_entrance_shop.py` covers responsive placement, touch, no-JS and missing art.

The first unfragmented visit may show an illustrated bakery doorway filling most
of the viewport inside generous responsive padding. It waits for the visitor to
click anywhere or activate the full-page entry link by keyboard. Restrained
pointer parallax shifts the backdrop and shop by only a few pixels while waiting.
On entry, paired doors open and the hanging bell swings. `web\bell.mjs` synthesizes
the short bell locally; there is no audio download. Playback is attempted only
from that entry gesture and only if the created context is already running. The
code never calls `resume()`, never replays blocked sound, and releases the context
after completion or skip.

The entrance has a visible `Skip entrance` link and its entry target is a native
`#home` link, so either action still reaches the site if enhancement modules fail.
It is absent for no JavaScript, reduced motion, forced colours, direct fragment
links, short screens and hidden/background tabs. Escape, focus, scroll or
navigation activity dismisses it safely. Use `python .\scripts\review_entrance.py`
with the local preview running to exercise click entry, parallax, timing,
fallbacks and generated muted waveform evidence.

## Build and view

```powershell
npm run build
python .\scripts\serve_site.py --port 4173
```

Visit `http://127.0.0.1:4173/`. It is local to this computer, not a shareable public
website address.

## Six top-bound category notebooks

The visible category grid `#category-notebooks` remains under **Cakes we've made**.
Its six covers are ordinary links into complete baseline notebooks in
`#cake-gallery`: Birthday Cakes, Tea cakes, Cream cakes, Decorated cakes,
Doll cakes and Chocolates. Birthday Cakes replaces Ice cream and is first.
The shared cake-weight line and every photograph are present in baseline HTML.

Each cover's two small ornaments match that notebook's name: balloons/gift, teacup/loaf,
mixing bowl with whisk/layered slice, piping bag/candles, dress/tiara, chocolate bar/wrapped
truffle. The shared renderer in `scripts\build-site.mjs` applies
white contours to twelve distinct SVG drawings; positioning classes are
`notebook-doodle-primary` and `notebook-doodle-secondary`, not heart/bow classes.
Missing category motifs fail the build instead of silently reusing another pair.

Cover and open-notebook construction overrides are deliberately scoped to
`.notebook-cover.notebook-page` and `.category-notebook.notebook-page`, so mobile
shared paper rules cannot restore the rejected left inset stripe. Cover ruling is
removed while inner sheets stay lightly ruled. Paired-wire tiles use a 30x40 box,
`space no-repeat`, and top slots centred 8px above the binding's bottom. That keeps
the existing measured page-turn hinge aligned with the new slots.

Enhancement requires the current stylesheet's `--notebooks-ready: 1` marker and a
native dialog API. The module is loaded separately with the same generated
cache version as the styles/main/entrance/bell. Reduced motion, forced colours,
print, missing modules/styles and direct notebook/page fragments keep the complete
baseline visible instead of hiding content behind an unavailable interaction.

Click, tap, Enter or Space opens a cover by moving its real notebook into
`#notebook-dialog`, with a brief 380ms zoom from the cover's position. No duplicate
cake controls or IDs are created. Every populated notebook starts with its first
photo page. A one-page notebook hides unused page controls, while Back to categories
and photo enlargement still work. Empty categories keep an honest photo-pending page.

The one `#cake-weight-info` bakery note sits above `#category-notebooks`, outside
all books. A Courgette heading, small decorative whisk mark, pink edge and crumb
dots frame the six sizes. A labelled noninteractive list presents 1/2 KG,1 KG,
1.5 KG,2 KG,2.5 KG,3 KG from `CAKE_WEIGHTS` through `CAKE_WEIGHT_ITEMS`.
The sizes use18px sans-serif text and wrap as complete labels on narrow screens;
the solid cream backing keeps patterns away from the text. These are list
items, not buttons, radio controls, selectable options or an extra page.
There are no weight pages, radio controls, selected/preferred state or
weight-dependent enquiry links. Instagram and configured WhatsApp enquiries
retain their original URLs. No automatic order or message is sent.

`cakePages()` groups explicit category membership into four cake records per
subsequent page. The last page may contain fewer; never add filler or repeated
photos to reach four. The owner's later request keeps FOUR photos while forbidding
vertical scrolling inside open notebooks. A fixed-viewport dialog and flexible
contained media use two-by-two grids in portrait and four across on short landscape
screens. Reading text is not transformed/scaled down; controls remain at least 48px.
Static/no-JavaScript/reduced-motion fallbacks still expose the complete document.

Use left/right arrow tags, with full Previous page / Next page accessible names,
both attached on the RIGHT of the book, or left/right/up/down arrow keys.
The page count is outside the buttons; single-page books hide pagination.
Weight information is not focusable or selectable. The next-page arrow tag
also supports an optional upward pointer/touch drag; a deliberate threshold
bounded between 72px and 180px commits the turn. Short/downward/cancelled drags
leave the current page in place. A tap on the tag acts as Next page.
The shared next/drag element has only one advancing click listener.

Catalogue images are direct full-photo links with no per-photo buttons, contact
links or pseudo-labels. Enhancement adds dialog semantics and Space support;
plain click/Enter/Space opens the viewer and closing restores the image's focus.
Modified/middle clicks stay native. Main ordering/contact links are unchanged.
Navigation uses opaque blue/pink arrow tags and a lilac category-return Back tag,
with16pxattachments and96pxright-edge exposure at default text size.
Near-square corners,28pxarrow glyphs and48pxtargets remain; no left/bottom action gutters.
The fit reviewer measures actual button corners, caption separation and both
scroll axes, including enlarged text and the direct image targets.

Pages rotate on the X axis about the measured spiral-slot line, not a left spine
or the lower edge of the fixed category heading. Both
transitioning pages are temporarily inert; completion, cancellation or the bounded
1000ms watchdog restores a single usable page. Resize, lost pointer capture,
blur, visibility changes, preference changes, print and dialog close release all
inert/hidden transition state. Focus moves to the new page title only if it was
still inside the notebook, never stealing focus from Back to categories.

Back closes the dialog, restores the notebook to its baseline location
and returns focus to the original cover. Reopening begins at the first photo
page for every populated category.
Full-photo enlargement stays in the category being browsed; photo-viewer arrow
keys do not also turn notebook pages.

### No sideways scrolling

The horizontal-scroll follow-up exposed two additional sizing problems: native
photo-dialog max-width narrowed a320px screen to242px at200%text, and flex
controls/viewport-height photographs exceeded the remaining space. The old live
viewer could scroll19px sideways and131px vertically in that case.

The enlarged viewer now has explicit bounded width/height, shrinkable grid
columns and header/image/control rows. The image uses the remaining row with
`object-fit: contain`; long titles wrap and Back/Next retain48px targets.
Notebook controls use balanced, shrinkable columns, including at200%text.
Neither correction depends on smaller reading text or a cropped photograph.
Loading and failed-image states keep the same bounded controls.
The earlier horizontal-fit revision checked266notebook states and285enlarged-photo
states across19viewport/text cases, plus both loading outcomes. Its evidence is in
`.local\category-notebooks\horizontal-overflow\`.

The first public follow-up exposed a separate late-font race during extreme
resize: the fitter skipped while fonts loaded, and its one-time initial
`document.fonts.ready` callback did not cover a later loading cycle. A held
FontFace fixture reproduced the clipped open notebook after that font resolved.
The module now rechecks on `loadingdone` and `loadingerror`. Both outcomes are
covered without requiring a geometry change or arbitrary retry timer.

### Current data boundary

The owner explicitly identified source `17855219376447920.jpg` as a Cream cake
and more precisely Black Forest. Its existing `cherry-curl-cake` ID and image
bytes remain unchanged; its new display label is Black Forest cake and it supplies
the Cream cover. Ten existing designs remain in Decorated cakes, and one in Doll cakes.

Three additional photograph records now populate Birthday, Tea and Chocolates,
including their actual cover IDs. Tea contains two cakes in one photograph;
cover counts therefore say photos, not bakes. The real anniversary topper stays
unchanged. Chocolate's reflective face required an alpha-only native-coordinate
repair. Exact mappings and remaining New Year/Doraemon work are in
[the selection guide](owner-selected-cakes.md).

The remaining 141 unique archive candidates await sequential contact-sheet
classification in a fresh session using the eight-sheet `posts-20261004-owner-v2`
revision, not the old nine sheets. Consult
[the bounded protocol](image-review-workflow.md) and its saved ledger; never open
extra images to evade the existing session limit.

No npm install is required. The builder uses Node's standard library; Node 22+
is supported. The local server uses Python's standard library and binds only to
127.0.0.1. Use this server rather than opening the HTML as `file://` or relying on
Windows file associations: it serves ES modules with the correct JavaScript MIME
type without weakening browser protections.

The generated site uses plain HTML, CSS and small JavaScript modules. It needs
no production server-side application, database, account system or feed widget.
There are no automatic external font, analytics or Instagram-feed requests.

## Change the contact details

`content/site.json` deliberately has an empty `whatsappNumber`. This selects the
known Instagram profile instead of displaying a fake or broken WhatsApp button.

Once a public number is confirmed, enter the actual country code and number as
8-15 digits, without a plus sign, spaces or punctuation. Rebuild. The same
configuration supplies the main ordering/contact links, not per-photo controls.
Invalid values fail explicitly rather than silently falling back to another
number/channel.

Instagram links open the profile; customers tap Message and may need to log in.
Instagram cannot receive a prefilled DM or selected cake from this site, so
customers name the cake in their message. There is no form or copy-message step.
When WhatsApp is configured, the main contact link carries a general enquiry for
the customer to review and send. Cake images always link to photos, independently
of contact-channel configuration. A link click never confirms an order.

Optional `publicEmail` and `location` are rendered only when configured. Put
only intentionally public information in this file. Never add passwords, API
keys, payment credentials or a private pickup address.

## Update cakes and photos

The current gallery is explicitly **past bakes**, not a priced product catalogue.
Names such as "Ribbon & pearl cake" and categories such as "Theme cakes" describe
appearance, not flavours or ingredients. Flavour, size and price questions remain
a direct conversation.

Edit the `id`, `name` and visual `category` records in `content/cakes.json`.
Edit `content/notebooks.json` for notebook membership and cover selection. Every
reviewed cake must appear in exactly one notebook, and a populated notebook's
cover must reference one of its own cake IDs. Empty lists require a null cover.
IDs must match both prepared-photo and sticker manifests and remain unique.
The current hero uses `ribbon-and-pearl-cake`; changing it also requires updating the
builder's deliberate selection and the sharing-image recipe.

The hero and gallery now use transparent, white-outlined cake stickers. Preserve
the full sticker, including visible toppers and transparent padding, with no
stretching or second cover crop. Remove photo-card rectangles; use only a subtle
alpha-following shadow, and keep "View larger photo" readable and unrotated.
The viewer still opens the complete prepared JPG, not the sticker or raw screenshot.

Background removal is authorized on separate derivatives only. Originals and old
photo variants are retained. Recorded alpha-only corrections preserve the peacock
eye and remove cherry/doll background fragments without painting source RGB.
Cherries, dress base and upper feather already clipped in the sources remain
clipped; no missing detail is reconstructed.

The supplied Instagram export has now been imported offline: 167 eligible media
files became 160 unique private originals, with seven duplicate entries and 11
policy exclusions. Seven reviewed photos supplement, rather than replace, the
original five screenshots. The selected crop recipe is
`.local\photos\notebook-20261004-v2\selection.json`; the generated batch manifest
records each original hash and private crop directory. The first private candidate
batch was rejected after a filename-association check; use only the v2 records.

Future source archives can be handed over by their extracted-folder path. Use
the [offline import workflow](instagram-photo-import.md), then curate and prepare
web copies separately. The entire export must never become a public gallery.

`scripts/prepare_prototype_photos.py` retains its original five-file default recipe
and accepts `--recipe` for a separately reviewed export batch. Reproduce to a new
output revision rather than overwriting the combined twelve-photo manifest:

```powershell
python .\scripts\prepare_prototype_photos.py .\.local\instagram\imported\images --recipe .\.local\photos\notebook-20261004-v2\selection.json --output .\.local\photos\notebook-20261004-v2\prepared --private .\.local\photos\notebook-20261004-v2
```

`scripts/generate_social_card.py` reproduces the 1200x630 sharing image.
Those image utilities use the Pillow dependency recorded in
`scripts/requirements-images.txt`; the ordinary site build does not run them.

### Reproduce the stickers

From the repository root, use the saved masks without downloading or running a model:

```powershell
python .\scripts\prepare_cake_stickers.py prepare --masks .\assets\images\cake-stickers\masks --output .\.local\notebook-release\reproduction --review .\.local\notebook-release\reproduction.jpg
npm run build
```

`prepare` needs only the Pillow dependency above and defaults to
`assets\images\cake-stickers\`. It preserves existing identical files and rejects
differing output; use a new `--output` and `--review` revision instead of overwriting
an earlier result. The final review sheet is private, not a public cake asset.

Re-running inference is separate and opt-in: rembg 2.0.85 in
`.local\sticker-env\`, BiRefNet general-lite for four cakes and general for peacock,
with model files cached under `.local\models\rembg\`. `infer` supports `--model`,
`--ids` and `--output`; `refine` combines the lite/detailed folders with the recorded
alpha recipe. Models may download; photographs are processed locally, never
uploaded. Full commands, provenance and correction details are in
[the sticker asset guide](../assets/images/cake-stickers/README.md).
For a new subset, `infer` and `prepare` accept `--manifest`. Export stickers record
`source_photo_sha256`; screenshot stickers retain `source_screenshot_sha256`.
The builder verifies either against the corresponding photo's `source_sha256`.

## Focused developer commands

```powershell
npm test
python .\scripts\review_site.py
python .\scripts\review_entrance.py
```

The first command runs the Node built-in tests. The second expects the preview
server to be running and uses an installed Python Playwright plus Microsoft Edge.
It writes private screenshots and a result record to `.local\website-review\`.
Install browser tooling only if it is missing; it is not a site runtime dependency.

For this local revision, verify `home -> story -> cakes -> order`, exact restored
story, six category covers, one shared cake-weight line before them, all-category
photo-first opening, four-photo paging, full-JPG
enlargement and no message forms or weight inputs. The static
all-pages fallback has **371 main DOM words**, and the original story remains
unchanged. The overview
budget stays below 224 and the shared weight line below 30 words.
Latest cream-hero evidence is `.local\category-notebooks\cream-hero-site\`
and `cream-hero-entrance\`. The green standalone-hero revision is rejected history.
Earlier category-sticker and
`local-site-final\` / `local-entrance-final\` reviews remain historical. Preserve earlier
`.local\notebook-release\` publication evidence rather than overwriting it.

Current test totals and public-file counts are recorded in the publishing guide
and its named release receipt.
The hero spans the viewport with zero border/radius/shadow/transform; its tested
text/button contrast ratios are at least 4.67:1. The original story markup is
byte-identical to the earlier published version. Eight authorized contact sheets
include actual covers/UI and native-scale reflective regions. Nine
sticker/provenance cases preserve the original twelve records and all 96 earlier
variants. Those checks include padding, dimensions/hashes,
source-file associations, metadata removal, the peacock eye, the new placemat
correction, unchanged archived originals and source RGB equality at all opaque
mask pixels before output resizing/compression.

`python .\scripts\review_site.py` passed. It confirms the cursive font actually
loads while body copy and buttons retain DM Sans. All sixteen linked image instances
have transparent corners and full prepared JPG viewer links.
`python .\scripts\review_notebook_fit.py --output <private directory>` checks
every current notebook page and enlarged photo across the configured viewports,
including320x480, static weight information, 100%/200% text,
zero scroll offsets, no action/caption overlap, contained photographs and48px
controls. Separate extreme320x360/200%tests confirm the explicit readable static
fallback on initial open and resize. Final evidence is under
`publication-local-site`, `publication-local-entrance`, `publication-local-fit`
and the matching separate public folders in `.local\category-notebooks\`.
Contact-sheet/native-region evidence is not complete full-resolution archive
inspection, owner visual acceptance or native-device acceptance.

Retain coverage for 320/390/600/768/1024/1440px layouts, actual image loading,
visible navigation, keyboard focus, photo controls, minimum text/control sizes,
200% text resizing at 320/390/600/1280px,
no-JavaScript links and a simulated slower connection.
External Instagram handoffs are intercepted for the check; real messages are not
sent. Native apps, assistive technology and real-device/user acceptance remain
release work.

## Public release boundary

Deploy **only `site/`**. The builder copies an explicit allowlist and refuses
unexpected existing files in its output instead of deleting them or potentially
publishing a private archive. Fonts retain their SIL Open Font License files.
The current generated build contains160files, including60sticker variants, six refreshed showcase JPGs, original room/canopySVGs, locally
hosted fonts with their licenses and the original doodle SVG.
Stickers are copied to `site\assets\stickers\`. Prepared full photographs
remain under `site\assets\images\` for enlargement.
Original screenshots, kitchen references, PDF, import/sticker manifests,
`mask-recipe.json`, `masks\`, source README files, model caches and test/review
artifacts are outside the output. Do not deploy `assets\images\cake-stickers\`
directly just because it contains the prepared variants.

The immediately preceding site and browser review are retained in
`.local\revisions\before-palette-correction-20261004\site\` and `review\`. The earlier
long-page source of the restored story remains under
`.local\revisions\before-three-sections-20261004\`. Historical evidence is not a
pass for the new image treatment.

The publishing guide records the deployed cover/viewport-fit snapshot and its
live-byte checks. The earlier `63f4437`/125-file, `49aa348` and `be221e6` receipts
remain historical; their missing-cover status is not the current source state.

`siteUrl` is set to https://zanark.github.io/WhiskAndCrumbs/, including the project
subpath. Canonical and Open Graph URLs use that public base. If changing hosts,
update the field and rebuild. The deployed sharing image is reachable; actual
WhatsApp/social-app preview rendering has not been tested.

GitHub Pages' commercial-use restriction still applies. The user explicitly
requested this release after the warning; publication does not establish provider
compliance. No external form service or new hosting account was created.
