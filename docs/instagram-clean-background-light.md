# Clean Instagram background lighting

[Review the updated images](../exports/website-launch-20261009-instagram-no-diagonal/preview.html).

The repeated slant was an artificial diagonal light beam plus a narrow shadow
rail in the editorial background, generated from `x + y * .20`. Both are now
disabled for all six Instagram portraits. Smooth colour washes, grain, cream
sculptures, frosted glass and the raised phone-edge lighting remain.

Use `--no-portrait-light-bands` with the existing `--frosted-cream`,
`--portrait-colour-variance` and `--raised-phone-glass` options.
Default/README rendering is unchanged; all six landscape JPEGs match the prior
kit exactly. The new kit reuses the published catalogue/neon source captures,
not the separate unpublished archive-import candidate.

51campaign tests and72actual-JPEG typography checks pass. Unoccluded source-ground
measurements at three rail positions per image reduce the old8.71-8.94RGB-level
depression to within0.10ofzero. The initial final-JPEG scan had insufficient clear
background rows in01; it was not counted as successful evidence. Final JPEG hashes,
unchanged foreground geometry and typography are checked separately.

Four gallery widths and the six-image ZIP pass. Evidence:
`.local\instagram-no-diagonal-20261009\validation.json`, `gallery.json` and
`completion.json`. No new image-tool viewing, public build or Instagram posting.
