# Local website fonts

The current display face is **Courgette**, weight 400: lightly handwritten,
with simpler letterforms than the rejected Dancing Script. It is hosted locally;
normal browsing makes no Google Fonts request.

- Upstream: https://github.com/google/fonts/tree/main/ofl/courgette
- Download: https://raw.githubusercontent.com/google/fonts/main/ofl/courgette/Courgette-Regular.ttf
- Local file: `courgette-regular.ttf`, downloaded 2026-10-04.
- License: `Courgette-OFL.txt`, SIL Open Font License 1.1.

The earlier Dancing Script face is preserved but no longer used:

- Upstream: https://github.com/google/fonts/tree/main/ofl/dancingscript
- Download: https://raw.githubusercontent.com/google/fonts/main/ofl/dancingscript/DancingScript%5Bwght%5D.ttf
- Local file: `dancing-script-variable.ttf`, downloaded 2026-10-04.
- License: `Dancing-Script-OFL.txt`, SIL Open Font License 1.1. The font's internal
  name and bytes are unmodified; only its local filename is normalized.

**DM Sans** remains the reading/control face. Earlier Dancing Script and DM Serif
Display files/licenses remain preserved, but the current CSS and sharing-image
generator do not use them. Every shipped font keeps its license in public output;
this source-side README is not copied to the website.
