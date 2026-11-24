# Three-times-lighter Instagram backgrounds

[Review the softer images](../exports/website-launch-20261010-instagram-three-times-lighter/preview.html).

The Instagram editorial ground now retains one third of its prior tint:
`new RGB = white - (white - old RGB) / 3`, rounded to8-bit channels.
This blends the ground two thirds toward white before the original cream,
lightly frosted pane and sharp foreground are added. It does not fade the text,
website screenshots, phone details or cream sculptures.

The six palette references are now `#fbf5e7`, `#fbedf3`, `#f0f4ef`, `#faece5`,
`#f7f1ec` and `#fbf9f4`. The pane remains8%tint/9pxblur. Original distinct cream
arrangements, raised phone edges and the removal of diagonal light bands remain.

Use `--portrait-tint-strength "0.3333333333333333"` with the four existing
frosted-cream, portrait-colour-variance, raised-phone-glass and no-portrait-light-bands
options. Strength1remains available only to reproduce earlier editions; future
current-art refreshes should carry the one-third setting.

The complete148-photo catalogue captures are reused. All six README landscapes
are byte-identical to the previous complete-catalogue kit; the website was not
rebuilt, committed or changed. Both kits remain intact and nothing was posted.

57campaign tests and72actual-JPEG typography checks pass. Background tint ratios
are.333236-.333374after8-bit rounding, with unchanged foreground specifications
and at least7.60:1body-copy contrast. Four gallery widths decode all12images.
Evidence: `.local\instagram-third-strength-20261010\completion.json`.
No new image-tool views or owner visual approval are claimed.
