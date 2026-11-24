# Stronger, broader and lingering cloth response

Release: `712238543f2db707604f581b54fdf1758aec6b80`  
Pages: [37858472274](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37858472274)  
Asset version: `26dede947f25`

All 175 live site files and README/ABOUT match the commit. Only four public paths
changed: the two cloth modules, cache-version references in HTML, and the ABOUT
description. Every static image, SVG, stylesheet, phone-tilt module, notebook,
product variant and other runtime module is unchanged. No unnecessary screenshot
or Instagram-kit regeneration was performed.

## Requested behavior

The owner asked for much greater mouse sensitivity, a reaction that travels
farther and waves that linger briefly after the cursor leaves.

The model now uses:

| Parameter | Previous | Current |
| --- | --- | --- |
| Near-pointer margin | 72px | 112px |
| Model displacement bound | min(14px,7.5% height) | min(26px,14% height) |
| Horizontal influence radius | clamp(10% width,80,130) | clamp(18% width,120,240) |
| Vertical influence radius | clamp(42% height,60,85) | clamp(55% height,80,120) |
| Pointer kick multiplier | 3 | 6 |
| Pointer target multiplier | .78 | .94 |
| Horizontal spring rate | 150 / cell-width, squared | 220 / cell-width, squared |
| Vertical coupling | 65 | 95 |
| Slope/hem rest spring | 64 / 32 | 46 / 22 |
| Slope/hem damping | 9 / 6.5 | 4.4 / 2.6 |

Horizontal stiffness remains bounded. The runtime pointer-speed ceiling now
matches the model's existing 2400px/s input limit. Broader forcing and neighbour
coupling spread the response; lower damping produces the longer settling tail.

## Measured differences

The preserved old and new models received identical input at 1440x324.

| Measurement | Previous | Current |
| --- | --- | --- |
| Stationary-pointer peak in first0.5s | 8.27 | 24.76 |
| Affected model width at0.5s | 420px | 870px |
| Fast-pointer peak in first0.5s | 8.81 | 26 |
| Fast-pointer affected width at0.5s | 420px | 930px |
| Release to exact idle | 2.067s | 4.725s |
| Last projected motion of at least0.25px | 0.883s | 2.675s |

This is approximately three times the initial response, twice the affected width
and a longer visible tail. The final stages naturally become subtle before exact
rest; the table does not claim equally strong motion for the entire settling time.

The actual local/live uploaded browser mesh reaches a19.5px projected peak over
a900px affected width in the first650ms. After release, the live probe records
a1.25px peak in the1.6-2.4second window, then exact idle at4.7105seconds with no
further uploads. Measurements use a standard viewport and controlled input, not
a guarantee of identical wall-clock timing on every device.

## Preserved safeguards

The97x17topology, fixed rail/end vertices, separate rigid hardware, original SVG
and premultiplied-alpha renderer remain. The maximum projected vertical motion is
19.5px, inside the existing20pxgutter. The approximately2Mpixel GPU budget is unchanged.

The cloth still returns to byte-identical native static artwork, stops rendering
at idle, and respects reduced motion, forced colours, print, background/offscreen
states, dialogs and the entrance. Resource failures retain static artwork.
Scrolling still creates signed waves; phone orientation remains confined to its
separate opt-in entrance feature.

The unchanged matched-GPU locality gate passes. The stronger wave has a small
legitimate distant response, while the fixed top/front rails and six sampled
opaque hardware points have zero movement. Sampling-footprint colour checks pass.

## Reproduction and evidence

- `tests\awning-cloth.test.mjs`:16targeted model cases, including strength,
  spread, two-second persistence and finite exact idle.
- `scripts\review_cloth_response.py`: actual uploaded vertex offsets and timed
  release, not guessed CSS values.
- `scripts\review_awning_fabric.py`: motion, locality, pixel colour, rails, idle,
  resource/preference/resize safeguards and exact static return.
- `scripts\review_supported_awning.py`: unchanged artwork and rigid hardware.

Evidence root: `.local\responsive-lingering-awning-20261009\`.
`model-comparison.json` records the controlled baseline comparison;
`local-response-settled` and `public-response` record the real browser trajectory;
`publication.json` records all live bytes.

The combined Node suite has130passing cases. Full local site/entrance and local/live
cloth/response/support reviews pass. Initial reviewer startup waits were aligned
with the existing10second settling limit because page-fragment scrolling can
excite the newly longer-lived wave; response thresholds were not relaxed.

The static launch kit remains `exports\website-launch-20261009-rose-tilt\`.
No image-tool views, new artwork, social posting or aesthetic-approval claim occurred.
