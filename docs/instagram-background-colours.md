# Instagram-only background colour variation

[Review the six Instagram images](../exports/website-launch-20261009-instagram-colour-variance/preview.html)
or [download the six-JPEG ZIP](../exports/website-launch-20261009-instagram-colour-variance/Whisk-and-Crumbs-Instagram-3x4.zip).

The six portrait grounds now alternate buttercream, blush, soft green, peach,
oat and vanilla. These are static editorial backgrounds only, not a new website
palette. README landscapes remain byte-identical to the final catalogue/neon kit.

Colour is applied to the shaded editorial ground before the unchanged ivory
cream-material layer and lightly frosted pane. The pane still uses8%tint,
92%background transmission and9pxblur. No per-text masks or opaque backplates
were added. Each image retains its distinct original Gaussian cream structure.

The exact final catalogue/neon browser captures are reused, not recaptured from
the concurrent catalogue-import candidate. Foreground text specifications,
device/feature positions and brand ornaments are unchanged. Phones still occur
only on Instagram portraits01and06; no new photos or product details were invented.

## Reproduction

Use `scripts\compose_launch_campaign.py` with the existing `--frosted-cream`
option plus `--portrait-colour-variance`. The additional option is rejected for
other styles. Supply a fresh output directory; old kits are immutable.

Current source captures:
`.local\launch-campaign-20261008\captures\final-catalogue-neon-20261009\`.
Material layers: `.local\frosted-cream-launch-20261009\layers-v2\`.
Composition: `.local\launch-campaign-20261008\composed\instagram-colour-variance-20261009\`.
Package using `scripts\package_launch_campaign.py`.

The package validates exactly six assigned portrait colours and rejects applying
this palette to landscapes. Its gallery and alt text name each colour.

## Evidence and boundary

46existing-runner campaign tests and72actual-JPEG typography checks pass.
Minimum body-copy contrast is6.05:1; measured unoccluded ground colours have
minimum pairwise RGB distance21.22. Six README images are byte-identical and
all six portraits differ. Four gallery widths decode all12images without
overflow or external requests.

Receipts: `.local\instagram-color-variance-20261009\composition-validation.json`,
`gallery.json` and `completion.json`. Numerical evidence is not visual approval.
No public build, staging, commit, push, image viewing or Instagram posting.
