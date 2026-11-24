# Optional phone tilt and the supported rose canopy

Original release: `a7325203eaffef402caf5fe3b594b555098a69f4`  
Pages: [37853015851](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37853015851)  
Asset version: `ff6086d91be6`

All 175 live files and root README/ABOUT match the commit. The 16-path release
preserves the wooden header/navigation, facade artwork, room/bake/camera,
notebook code/colours, original customer copy and all 120 product variants.

## Phone tilt

On the entrance, **Phone tilt** appears only when the browser exposes device
orientation in a secure context with a coarse pointer. The owner's later
default-on request is published in`d5426bec9208834d8e9bd779ebca7d2b1d6095be`,
Pages`38134100596`, version`79f160338f1a`.
Eligible phones start listening once automatically when no permission gesture
is required. Browsers exposing`requestPermission` retain the explicit **Phone tilt**
action; no permission request is made merely by loading the page.
Explicitly switching tilt off or reaching the no-data timeout does not start
an automatic retry loop on subsequent layout changes.

The first finite beta/gamma sample establishes the visitor's comfortable neutral
position. A 0.75-degree dead zone ignores small noise; 15 degrees reaches the
existing normalized look limit. Screen rotation remaps the axes and recalibrates.
Updates are limited to roughly 30Hz, smoothed, and deduplicated before writing
the existing `--look-x`/`--look-y` values. The room renderer and camera are unchanged.
The outer building remains fixed.

The button becomes **Tilt on** after usable data arrives. Tapping it again stops
and recentres the view. Entry, Skip, background/pagehide, direct links, short screens,
reduced motion, forced colours and print remove listeners. A late permission result
cannot restart motion after dismissal. The optional static room poster also
supports consented tilt when WebGL is unavailable.

Denied/rejected permission, missing support, null samples or a 2.5-second startup no-data
timeout produce an inactive state and keep ordinary entry/Skip usable. The website
does not save or upload sensor readings or persist an opt-in preference.

The top controls wrap and reserve actual space above the building. At
320x568 with 200% text, the complete site is shown directly instead of clipping
the controls or shrinking their text. At 390x844 with 200% text the entrance
remains available; its plaque is 6px narrower, with unchanged 16px/24px lettering,
to preserve all four cake sightlines.

This uses browser device orientation, not positional tracking or raw gyroscope
capture. Actual API availability and permission policy vary, including embedded
browsers. References:

- [MDN requestPermission](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent/requestPermission_static)
- [W3C Device Orientation and Motion](https://www.w3.org/TR/orientation-event/)

`tests\entrance-tilt.test.mjs` covers seven mapping cases and the automatic-start policy.
`review_phone_tilt.py` covers28synthetic permission/sensor/lifecycle/layout cases,
including grant, legacy no-prompt API, denial, rejection, missing/null samples,
late grant, rotation and poster fallback. Those local/live browser results are
**not physical iPhone/Android or native Safari sensor validation**.
Current local/LIVE results and full site/entrance checks pass in
`.local\default-phone-tilt-20261011\publication.json`. Existing launch images are
unchanged and continue to illustrate the retained permission-gated path.
The following canopy and original release evidence is historical.

## Longer cloth, narrower stripes and fixed hardware

The original canopy now uses a 1200x300 artboard with forty alternating
`#ce7183` reddish-pink and cream stripes, replacing the former 24 wide stripes.
That release retained twenty-four deep scallops. The later
[alignment correction](aligned-awning-scallops.md) replaces them with forty
matching30pxscallops, one per stripe, without changing depth or motion.
The sloping section spans source Y13-184;
the front bar spans Y182-190 and the hem ends at Y294.

The main canopy is 150-337.5px high, 25% taller overall. Its physical sloping
portion is approximately 54% longer, while the former hem depth is retained.
The entrance keeps its building rectangle and clear sign/door sightlines; its
relative sloped portion is approximately 23% longer.

Two visible bolted wall plates and angled tension rods connect to clamps on the
projecting front bar. They are original decorative construction, not a structural
engineering certification. `bakery-awning-supports.svg` is a separate static
layer over the cloth, so metal hardware never bends with the spring mesh.
Six sampled opaque hardware points remain pixel-identical during motion.

`generate_awning_art.py` reads `AWNING_GEOMETRY` from the existing cloth module
and regenerates both vector assets. The 97x17 mesh retains its fixed rails/end
vertices and bounded physics, with rows aligned to the new art coordinates.
Normal builds only copy the generated assets.

## Renderer diagnosis and safeguards

The stronger stripe colours exposed two separate issues:

1. Native SVG and the budget-limited GPU texture use different sampling grids.
   Their edge reconstruction difference was being counted as distant motion.
2. Straight-alpha texture interpolation darkened partly transparent fabric edges.

The renderer now uses matching premultiplied texture/context alpha and clamps
shaded associated colour to alpha. The checker captures a zero-deformation,
unit-shade frame through the **same actual GPU pipeline**, without changing model
state, texture, viewport, density or CSS, then restores the held frame exactly.
Motion is compared with that control; native/GPU sampling differences are
reported separately rather than relabelled as movement.

The original locality threshold is unchanged. Current far-field and fixed-rail
motion fractions are zero. A separate colour-footprint guard detects colours
outside the native one-CSS-pixel reconstruction neighbourhood. Deliberately
injected straight-alpha and nonlocal-deformation defects are rejected.
Exact native rest restoration, idle stopping and the existing approximately
two-million-pixel budget remain.

## Delivery and maintenance

Original release [launch gallery](../exports/website-launch-20261009-rose-tilt/preview.html)
and [Instagram ZIP](../exports/website-launch-20261009-rose-tilt/Whisk-and-Crumbs-Instagram-3x4.zip)
use current real captures. All six README visuals were refreshed. Portraits remain
1080x1440, with phones only in posts 01/06. No social posting occurred.

ZIP SHA256: `d5cc885ca55495b705aa0a682e98c6666735eecbdf454f93b27880a3f085983c`.

Primary receipts:

- `.local\red-supported-awning-20261009\publication.json`
- `.local\red-supported-awning-20261009\renderer-handoff.json`
- `.local\red-supported-awning-20261009\local-fabric-final\review.json`
- `.local\red-supported-awning-20261009\local-supports-final\review.json`
- `.local\phone-tilt-20261009\local-final\review.json`
- `.local\phone-tilt-20261009\parent-delivery-review.json`

The combined suites contain 128 Node cases, 25 campaign cases and 9 asset cases.
Full site/entry and facade reports are separate from the targeted sensor/material
reports. The 12-case facade matrix explicitly records eleven displayed layouts
and the one tiny/enlarged-control complete-site fallback.
Final local and public site, entry, facade, sensor, support and fabric reviews pass.

No new image-tool inspection was performed; the session allowance remains
exhausted. Source, numerical and simulated browser evidence does not establish
aesthetic approval or physical-device acceptance.
