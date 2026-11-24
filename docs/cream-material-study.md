# Isolated glossy cream-form study

**Isolated preview:** http://127.0.0.1:4174/

The owner's October10 20:00request authorizes adapting the current model/material
to the official bakery. Production integration is tracked separately in
[official-cream-effect.md](official-cream-effect.md); this independent preview is
not itself a deployment root and remains unchanged by that work.
The fabric awning is a separate effect. This study is a different approach to the
reference screenshot supplied after the earlier cream effects were removed.
It is not wired into the website runtime or Pages. A separate offline launch-art
exporter reuses the original material shader; that is not live-site integration.

## Current local review candidate

**October10 update complete (workstream74):** a missed-focus-return bug is
fixed: returning to or interacting with an active preview now clears stale blur
state without overriding manual pause or reduced motion. Inactive motion has an
explicit status message. Ambient movement is now1.5Xfaster. Each load has4-6
large/medium groups plus5-8additional small droplets, with randomized
together/apart behavior within the groups.

The owner explicitly scoped the strawberry-cream pointer replacement to this
local preview. A small, scissored shader pass is copied to a transparent,
click-through canvas above the text and controls; the native pointer is hidden
only while that replacement is rendered. Paused, reduced-motion, inactive,
outside-window, touch and unavailable-overlay states retain the native pointer.
The background cream remains ivory. The pointer stays above the center glass and
page controls without intercepting clicks. Its size and tail response are unchanged.
Completion: `.local\cream-strawberry-motion-20261010\completion.json`.

The later cursor refinement halves its pink tint by blending the strawberry base
50%toward white (`#ffc1d5` -> `#ffe0ea`) without changing opacity or shading.
Its displayed trail scale is now.66,1.5Xthe preceding.44path. Head radius and
follow/catch-up rates are unchanged. Actual GPU trailing extent grows1.485-1.496X
across six desktop/mobile cases; the centerline grows exactly1.5X.
Current receipt: `.local\strawberry-half-tint-20261010\completion.json`.

The next request increases **all autonomous movement another1.5X**. Current orbit
is.6328125, breathing.0871875, and the relative-lobe cycle is accelerated equally
(effective12-17.33seconds instead of18-26). Recipes, sizes and paths are unchanged:
15,120sampled values match the preceding model at1.5twithin3.41e-12. The softer
cursor and.66trail remain; pointer tracking itself is not sped up.
Receipt: `.local\cream-faster-all-20261010\completion.json`.

The October9feedback is implemented at4174 only. The owner will review this
candidate before deciding whether to integrate anything into the official website.
This work does not edit public site code, builds, README, images, commits or deployments.
The published148-photo catalogue and current launch artwork are unchanged.

Workstream63 introduced **four to six uneven clumps per refresh**.
Every recipe includes a massive envelope, a second large form and two to four
small clumps, with non-mirrored anchors and independent motion phases. The massive
envelope radius is28–31%of the shorter viewport; its actual rendered silhouette
now spans43.6-51.8%in90checked viewport/seed/time combinations. The second radius
is16–18.5%; small radii are5.4–7.2%. These are real geometry changes, not renamed
size labels. Each clump starts with two or three unequal lobes. Workstream74 adds
5-8small individual droplets with radii3.2-4%of the shorter viewport. The extra
quantity is packed into free space; a rare crowded recipe can omit its last optional
droplets, but never drops below five.

A32-bit seed is drawn once with `crypto.getRandomValues`, with browser
`Math.random` as the safe cosmetic fallback if that API is unavailable. A bounded
seeded generator chooses count, dimensions, profiles and anchors once per load.
The immutable recipe survives animation, resize, reset and graphics recovery.
**Refresh** chooses a new mix; **Reset shapes** clears placements and rewinds the
same mix. Random selection can legitimately repeat a count on consecutive loads.
Complete breathing, orbit and split/rejoin envelopes are packed before rendering.
Group clearance is at least3.5%of the shorter viewport; added droplets reserve2.4%.
The large groups do not collapse into one permanent smear.

`CLUMP_PROFILES` describes normalized offsets, radii and peak strengths inside
each original moving envelope. `expandScoops` derives the joined geometry from
that parent transform. Seeded group modes now choose coherent movement or relative
motion. One randomly chosen large group lets a lobe narrow, peel away and rejoin
over an18-26second cycle; the smaller divergent groups flex without shedding tiny
pieces. Other groups retain fixed relative offsets. This intentionally supersedes
the earlier always-attached requirement without introducing random frame-to-frame jitter.
The generated `static-clumps.css` uses the same profiles for the simple static
fallback, using the deterministic seed2baseline of six groups and seven droplets. No-JavaScript is
honestly static, not refresh-randomized. Regenerate it with
`node .\experiments\cream-metaballs\generate_static_clumps.mjs`
after changing the profiles or recipe.

The current speed request multiplies the preceding ambient rates by **1.5**:
orbit.421875 -> .6328125 and breathing.058125 -> .0871875. The30fpsceiling remains.
The same retained path reaches the old1.5tpose at new timet; this is measured
separately from the new relative lobe motion. Pointer and trail responsiveness
retain their previous timing.

Frost and etched icons now cover **only the center reading column**, up to760px
wide with the existing responsive gutters. Both layers remain full-height while
scrolling, but the side areas are outside the glass. The texture remains10%tinted,
8pxblurred and1.025saturated, with the existing0.8pxcanvas blur. Foreground text
and controls remain sharp; no opaque reading-card or footer wash was restored.

The bakery outlines now appear as etched linework above that glass: an original
fine recessed edge, a pale offset light-catching edge and a faint frosted centre.
`generate_etching.py` reuses the experiment's exact original bakery-pattern geometry.
No reference pixels, traced geometry or background photography were used.
The original pattern file remains unchanged.

The later side-background request adds that exact normal outline tile beneath
the cream in both outer columns. The background has a plain center whose width
matches the glass, so the center retains only its separate etched treatment.
The original640x480scale and baked-in subtle opacity are preserved.

The WebGL canvas now emits associated-alpha cream and contact shadows instead
of an opaque cream-coloured ground. This lets the patterned background show
through empty space and darken naturally under shadows, while solid cream hides
it. The existing blur still applies to the material only, not the background
pattern or foreground text. Workstream63 preserves this material/shadow shader,
the glass and both pattern assets without changes.

Controls remain visible and comfortably sized. Reduced-transparency uses a94%
cream backing without blur; unsupported backdrop filtering keeps the78%fallback.
No JavaScript shows the complete static glass/side forms with explicitly disabled
interactive controls. Missing WebGL, forced colours and print remain safe.

## Interaction

The forms roam and breathe continuously without needing pointer movement.
Their rate is1.5Xthe previous slow revision. Some anchors shift to reserve the
new split/rejoin envelopes, but the motion multiplier is checked on identical
anchors rather than inferred from unrelated random layouts.
The mouse becomes a strawberry-cream shape with a trailing tail. Click or tap an
open area to add a scoop; records remain until **Reset shapes** while their visible
forms move. **Pause motion** holds the complete composition still, not just the
pointer follower; the normal pointer returns while paused. **Material only** hides
editorial text for comparison.

The cursor head is now25%smaller than the preceding revision:2.4%of the shorter
viewport. An eight-link tapered tail stretches behind it and catches up into the
head when movement stops. It does not fade by opacity, accumulate permanent paint,
or consume stored-scoop slots. Pause freezes its stored path and hides the overlay
so a usable native pointer remains.
The current displayed path scale is **.66 instead of.44**, a50%increase. The stored
segment bound is3.2head radii instead of2.4, exactly compensating for the smaller
head:76.8pxin both versions at1440x1000. This prevents the smaller head from
accidentally shortening the trail. Eight links, taper and catch-up rates remain.
The earlier workstream63measurements were29.0-30.9%more trailing extent with a
smaller head; current76adds another48.5-49.6%visible extent with no head-size change.

There are always **twelve user-placement slots**, in addition to9-14ambient
records. The maximum is26logical records and36GPUslots, including the reserved
cursor slot. Derived lobes do not consume placements. Main logical records are
packed first and satellites afterward. The visible pointer uses its own scissored
pass and transparent overlay; the main canvas is restored to ambient-only state.

The layout now uses the same centered container as the bakery:1200pxmaximum,
40pxside gutters on smaller desktops,24pxat widths up to900px and20pxup to600px.
Header, main and footer share it; the narrower reading surface is centered inside.
This is a central content area with side gutters, not three fixed content columns.
The original bakery-pattern-cream.svg is copied byte-for-byte from this repository.
Its local bakery-glass-etching.svg derivative tiles640x480above the center-only glass,
below text and controls. Neither glass nor etching paints into the side columns.
The side tile is a separate noninteractive layer below the canvas and static
fallback forms. Forced colours and print hide it with the other decoration.

The cream canvas has a slight0.8pxblur, not the text or controls. Three of the six
baseline starting groups have tapered soft peaks; random recipes have two or three.
Other forms stay rounded. The old clamped
surface-height plateau is replaced by continuous curved domes and rounded,
slightly offset peaks. Added scoops alternate rounded/peaked shapes.

The material uses original WebGL2 signed-distance blending, computed surface
normals, soft shadows and specular highlights. No reference-site code, textures,
photographs or trademark artwork were copied. It is a stylized material study,
not a physical whipped-cream simulation or a pixel-identical clone.

## Current numerical evidence

Workstream74passes28model tests,57campaign tests and the complete local browser
review, including pause/focus/visibility recovery and90actualGPUcoverage cases.
An8,191-seed bounded survey covers245,730viewport/time states. Identical-anchor
speed comparisons match old1.5twithin1.82e-12. Maximum-load samples stay near30fps;
pointer scissoring uses at most4.24%of the canvas in the measured samples.

The12Gaussian artwork layers remain byte-identical. The historical non-Gaussian
exporter now uses its own fixed six-form recipe rather than indexing the expanded
ambient scene; its12layers also reproduce the historical bytes. Existing artwork
kits are not regenerated or changed. No image-tool viewing or visual approval is claimed.

## Run locally

From the repository root:

```powershell
python .\experiments\cream-metaballs\serve.py --port 4174
```

The dedicated server binds only to loopback and serves only the experiment folder,
with correct JavaScript module MIME types. A detached preview is running under
shellId `cream-versioned-preview`; the old server was replaced for workstream75.
Refresh after source changes; this is not a hot-reloading production preview.

The server hashes `index.html`, `preview.css`, `static-clumps.css`, `preview.mjs`
and `model.mjs` into one12-character revision. Served HTML attaches that revision
to both stylesheet URLs and the entry module; the entry passes it to its dynamic
model import. The source HTML remains usable as the static fallback.
Responses use `Cache-Control:no-store,max-age=0`, and old conditional validators
cannot produce a stale304. The HTML and canvas expose matching
`data-preview-revision` values for diagnosis.

This fixes a real delivery gap: the owner's screenshot had new page copy but
cached old JavaScript, including the old clump count and ivory follower.
Fresh browser contexts alone did not establish what an existing browser loaded.
The regression now warms a real HTTP cache with old modules, proves their reuse,
then uses ordinary navigation to load the versioned update and strawberry pointer.
Evidence: `.local\cream-cache-20261010\warm-cache-review.json`.

```powershell
node --test .\experiments\cream-metaballs\model.test.mjs
python -B .\experiments\cream-metaballs\review.py --output .\.local\cream-massive-random-20261009\next-review --baseline-model .\.local\cream-massive-random-20261009\before\cream-metaballs\model.mjs
```

Regenerate etchings only when intentionally editing the original pattern geometry.
The existing asset is unchanged for the side-layer request.

Generating a review sheet is not permission to view it. The current allowance is
recorded in `.local\cream-metaballs-20261008\review-budget.json`.

## Boundaries and evidence

- Current massive/random candidate:
  `.local\cream-massive-random-20261009\completion.json`,
  `review-v1\review.json` and `export-identity.json`.
 26model/layer/fallback cases and43existing campaign cases pass. All54actual
  coverage cases preserve the requested4/5/6separate connected clumps, with the
  largest visible diameter44.3–49.4%of the shorter viewport and minimum sampled
  envelope gap34.45px. Six GPU cursor comparisons measure29.0–30.9%longer visible
  trails and a25%smaller radius; this is raster evidence, not merely constants.
  Eight real refreshes produced distinct seeds/geometries and counts4/5/6.
  Seeded4/5/6lifecycle cases each retain12placements, stable logical indices,
  identical resize/reset pixels and the same recipe. The full prior review still
  covers pause, inactive/hidden windows, graphics recovery, reduced motion,
  reduced transparency, DPR2, touch, noJS, forced colours and print.
  `geometry-preservation.json` additionally checks8,191distinct seeds over
  286,685viewport/time states: all remain contained and separated (minimum sampled
  gap6.83%of the shorter viewport). Twenty-eight existing placed-orbit comparisons
  are exact; the literal shader text and material/motion profiles are unchanged.
  All12offline Gaussian material layers are byte-identical to
  `.local\frosted-cream-launch-20261009\layers-v2`; no exporter edit was needed.
  The original shader text, quarter-rate motion constants, glass and pattern
  assets are preserved.610sampled covered pattern pixels show zero through-cream
  changes. Screenshots and a contact sheet were generated but **not viewed**;
  no aesthetic approval is claimed. Public files and the concurrent catalogue
  changes were not edited, built, reset, staged, committed or published.
- Previous joined-clump candidate:
  `.local\cream-clumps-20261009\completion.json` and `local-review\review.json`.
 25model/layer/fallback cases,43campaign cases and the full browser review pass.
  Eighteen actual coverage cases retain six separate visible clumps after canvas
  and glass filtering. Native SDF silhouettes are1.296-1.746times their main-lobe
  area, proving the satellites visibly extend the shape while remaining joined
  and inside the original envelope. Native geometry and filtered visibility are
  measured separately; the smallest isolated main-lobe control can disappear
  under8pxfrost even though its complete clump stays visible.
  Twenty-eight old/new envelope-motion comparisons are exact. Side patterns
  remain behind opaque cream;207covered ink pixels show zero through-surface
  difference in the final held pose. Context recovery, pause, resize, placement
  limit, noJS and preference cases pass. All twelve offline Gaussian material
  layers remain byte-identical. The official release and existing launch kit
  are unchanged; no build, commit or publication occurred.
- Previous side-background/center-etching candidate:
  `.local\cream-side-patterns-20261009\completion.json` and
  `local-review\review.json`.21localmodel/layer cases and the full browser review
  pass, including18separation coverage cases and eight responsive column widths.
  The final held pose shows the normal pattern in both side columns;459pattern
  pixels beneath opaque cream are completely hidden. No pattern-induced pixels
  change in the center interior, excluding the blur's edge-sampling footprint.
  Existing center glass/etching checks still show zero changes outside its bounds.
  Same-pose plain-ground comparisons at desktop/DPR1 and mobile/DPR2 differ by
  at most2RGBlevels (mean below.028) from the former opaque renderer.
  The model and both SVG assets are byte-identical.
  The offline exporter was adapted to the associated-alpha output; all12Gaussian
  material layers still export byte-identically to the prior edition.43campaign
  cases pass. No existing launch images, website files, README, commit or deployment
  changed. The official release remains9f51bc3.
- Previous separated/center-glass/quarter-speed candidate:
  `.local\cream-center-glass-20261009\completion.json` and
  `quarter-speed-review\review.json`.
  Twenty model cases pass, including unequal sizes, non-mirrored anchors and
  visible pairwise gaps over six viewport shapes and long runs. Eighteen actual
  material-coverage renders through the canvas/glass filters each retain six
  separate components; minimum sampled boundary gap35.21px.
  Twenty-eight same-path timing comparisons prove current(4t)=previous(t), maximum
  difference0. The glass matches the center reading bounds at eight widths;
  toggling it changes zero pixels outside those bounds. Existing lifecycle,
  cursor/trail, contrast, placement and accessibility checks pass.
  The cursor and user-placed scoops are excluded from the ambient separation fixture:
  deliberate pointer/placement blending remains available.
- Earlier separation-only evidence:
  `.local\cream-separated-blobs-20261009\completion.json`.
  This precedes the center-only glass and quarter-speed follow-ups; retain it as history.
- Earlier shorter-trail revision:
  `.local\cream-short-trail-20261009\completion.json` and `local-review\review.json`.
  Twenty model tests and the full local browser suite pass. The sampled GPU
  trail is170.993px versus512.978px when expanded back to its former length,
  while head radius stays32pxat1440x1000. Actual shorter/longer/no-trail pixels
  differ and the paused frame restores exactly. Glass, etching and ambient
  motion files/behavior remain unchanged. This is still local-only.
- Earlier full-page etched-glass candidate:
  `.local\cream-etched-glass-20261009\completion.json` and
  `candidate-04-final\review.json`.
  Nineteen model cases pass.24same-path comparisons prove current(t*2)=prior(t)
  exactly; the new default side lanes are separately tested for connectivity and
  containment over five viewport shapes and long runs.
  Actual visible cream changes21.36%of the sampled left region and20.48%of the
  right when each group is removed; etched linework affects2.05%of pixels.
  The full-glass fixture changes29.22%of the reading area while ordinary sampled
  text contrast stays at least6.887:1and the large accent at3.93:1.
  Eight viewport widths, scrolling coverage, Pause, trail/peaks,18-record limit,
  resize with retained placed scoops, context recovery, DPR2, touch, no-JS and
  preference fallbacks pass. The final15-tile sheet was generated but NOTviewed.
- Previous faster-motion/frosted-pane revision is preserved:
  `.local\cream-frosted-motion-20261008\completion.json`.
  Eighteen model/profile/trail cases and browser/GPU checks pass. Real autonomous motion,
  peak contribution, blur, sharp controls, Pause,18-record cap, resize/context
  retention, DPR2and touch behavior are covered. A15tile sheet was generated but
  NOTviewed; no new image-review allowance was consumed.
- New evidence also covers200pxblob displacement over an approximately0.8swindow,
  actual cream transmission through the pane, sampled reading contrast and the
  reduced-transparency fallback, plus the earlier trail/layout/pattern checks.
  A centered rendered cream fixture changes26.85%ofpane pixels while ordinary
  reading contrast remains at least7.09:1in that fixture.
  The prior cursor/layout revision is retained in
  `.local\cream-trails-layout-20261008\`; current before\ preserves its source.
  The previous moving/peaked revision is retained in
  `.local\moving-cream-study-20261008\`; the new before\ snapshot preserves its source.
- Four to six separated ambient clumps, up to18stored scoops plus one pointer follower. The limit
  retains existing shapes and asks for Reset rather than silently evicting them.
- Continuous visible animation is now explicitly requested, capped at30fps.
  Pause, reduced motion, inactive/hidden windows, print and forced colours stop it.
  The simulation clock freezes while inactive, without catch-up jumps on resume.
  No opacity decay, localStorage, telemetry or external runtime calls; assets are served locally.
- Native pixel ratio up to2 with an8.4million-pixel budget, no coarse-grid upscale.
- Reduced-motion mode stops both drift and pointer following. Touch supports
  automatic drift and direct placement.
  Missing WebGL2 shows a labelled static fallback; context loss/recovery retains forms.
- Existing licensed DM Sans/Courgette fonts are copied with their license files.
- Historical original-study evidence: candidate-01\review.json and extended-checks.json under
  `.local\cream-metaballs-20261008\`.
- Parent inspected one labelled15-tile contact sheet covering initial/joined/
  separated/retained forms, material-only mode and DPR1/DPR2details. Selected as
  an isolated concept, not as approval to put it on the live bakery.

At05:57IST onOct9the owner again liked the prior4174study and requested half-speed
side groups and full-page etched glass. They explicitly want to review it before
deciding about the official site. **Production integration is not authorized.**
Their later correction rejects merged/symmetrical groups, narrows frost to the
center column and slows ambient motion to a quarter of its preceding rate.
The earlier ripple and piped-relief implementations remain parked; previous
positive feedback is not acceptance of this new candidate.
