# Slower physical top-spiral paper turn

Status: deployed with the neon entrance as `68d2aece95ffd26ed15f89be74d1baa16607b409`,
Pages `37958797053`, version `1016478169f5`. All175live files and README/ABOUT
match; public catalogue/motion, neon and entrance reviews pass. Final receipt:
`.local\entrance-neon-20261009\publication.json`.

Historical handoff: `.local\physical-page-turn-20261009\parent-final-handoff.json`.
The parent completed final source-bound artwork and a four-width gallery review
after opening collapsed sections and scrolling lazy images before decoding.
Current kit: `exports\website-launch-20261009-final-catalogue-neon\`.

This is the owner's follow-up to the published catalogue/no-separate-Turn release
`afb18cbf22ce250bec7f7f1912fcec28c7dc582f`. It must be completed before local63.

## Implemented motion

- A full forward or reverse turn lasts1800ms, replacing650ms. Nine angular stops
  keep the readable front face lifting for most of the turn; symmetric eased
  acceleration/deceleration avoids a quick snap. Partial drag settlement takes
  at least360ms, proportional to remaining angular travel.
- The actual sheet rotates on the X axis around the real top spiral-slot line.
  The camera origin shares that hinge. Perspective is bounded from the available
  viewport so the projected face remains on screen without clipping photographs,
  shrinking text or covering the right-side controls.
- A receiving-paper shadow changes reach, rightward skew, blur and opacity with
  the same angle. A sharper contact shadow remains near the hinge, while a moving
  highlight/shade layer and thin paper edge emphasize the lifting face.
  Only decorative cast-shadow paint is clipped to its receiving sheet.
- All four Web Animations share a start time, duration, easing and angular stops.
  Direct dragging uses the same lighting pose as animated settlement.
- This is **planar perspective rotation with shading**, not a geometrically curled,
  bent or deforming paper mesh. No visual/owner approval is inferred.

Both previous/next arrow tags remain on the right. Next alone also supports the
optional upward drag; no Turn button, label or extra handle exists. Four photos,
layout, typography, static/noJS links and all contact behavior are unchanged.

## Interruption and accessibility

The duration-relative watchdog is now duration+350ms; it no longer cuts a slower
turn short at the old1000ms deadline. Completion/cancellation removes every
lighting animation and decorative node, restores both pages' inert/ARIA state,
clears perspective overrides and retains existing focus behavior.

Resize, blur, visibility, close, print and preference changes preserve the same
safe settlement/static paths. Missing animation APIs and a separately simulated
lighting-animation failure leave usable pages. Reduced motion, forced colours,
print and noJS keep complete static notebooks, without animated lighting.

## Numerical evidence

Evidence root: `.local\physical-page-turn-20261009\`.

-134Node cases, including pacing/partial/reverse poses and lighting geometry.
-`local-motion-v1`: six forward/reverse cases,48sampled poses, and six real
  elapsed-time checks across1440x1000,390x844and667x375.
- The motion review checks shared1800ms timelines, monotonic X-only rotation,
  spiral alignment, actual bottom-edge depth, opaque faces, visible-face bounds,
  changing shadow geometry, actual painted shadow pixels and complete cleanup.
-`local-fit-v1`:134notebook states/300photo views; fitting expectations unchanged.
-`local-site-v2` and `local-entry-v1`: full sequential UI/entrance safety coverage.
  The first site run hit a retired reviewer variable; its failed log is preserved.
-43campaign and10asset regressions,72actual-JPEG typography checks.

Fresh12viewport/fourcomponent captures use the same approved Gaussian layers.
Motion-only pre-neon kit: `exports\website-launch-20261009-physical-page-turn\`.
It retains six1600x1000landscapes and six1080x1440portraits, phones only01/06.
Only landscape04differs from the catalogue kit. Its mobile source geometry is
identical; raster differences have maximum15RGBlevels and only161pixels above
three levels. No visual interpretation is claimed. All other11JPEGs are identical.

## Build boundary

The pre-neon motion checks excluded64. After the coordinated source handoff,
the exact parent-owned neon stylesheet was copied into the snapshot under
`.local\physical-page-turn-20261009\release-source\` and built for parent review.
That intermediate snapshot is historical; the final root build includes the
reviewed smaller neon spill and thicker heart tube. Original pre-neon CSS is
preserved as `pre-neon-reviewed-entrance-shop.css` in the evidence directory.
Motion source bytes match the reviewed snapshot exactly. All17local4174files are
unchanged. Final release evidence: `.local\entrance-neon-20261009\`.
No image-tool views, archive import, Instagram posting, production cream animation
or `.agent-context` edits occurred.
