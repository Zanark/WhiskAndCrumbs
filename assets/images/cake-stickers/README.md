# Cake stickers: provenance and reproduction

The user chose separate cake cutouts with transparent backgrounds and white sticker
contours. These derivatives do not replace or retouch the original screenshots
or the ten subsequently selected export photographs.
Local site/image validation and parent visual review are complete; see
[`TODO\09_STORY_AND_CAKE_STICKERS.todo`](../../../TODO/09_STORY_AND_CAKE_STICKERS.todo)
for actual outcomes. These checks and recorded mask corrections are not user
visual approval or a claim of perfect cutouts.

## What is retained

| Location, relative to the repository root | Role and publication boundary |
| --- | --- |
| `.local\photos\prototype-20261004\` | Untouched screenshot originals and preserved crop masters; private |
| `assets\images\cakes\` | Existing prepared WebP/JPG variants and crop provenance; retained |
| `assets\images\cake-stickers\*-sticker-*.webp` / `*.png` | Sixty catalogue records, including 45 contact-sheet-reviewed archive imports; small native cutouts are never upscaled |
| `assets\images\cake-stickers\manifest.json` | Source/crop/mask hashes, bounds, padding, contour, source limitations and variant hashes/dimensions; source-side only |
| `assets\images\cake-stickers\mask-recipe.json` | Recorded alpha-only correction recipe; source-side only |
| `assets\images\cake-stickers\masks\*.png` and `masks\review.json` | Saved masks, candidate/final hashes, model names and correction reasons; source-side only |
| `.local\stickers\final-review.jpg` | Source/cream/dark comparison sheet; private review artifact |
| `.local\revisions\before-stickers-20261004\site\` and `review\` | Previous site and browser-review snapshot; private history |

The source directory is **not a public deployment root**. The builder copies only
the manifest-listed sticker variants to `site\assets\stickers\`, while retaining
prepared photos in `site\assets\images\`. The hero/gallery show the stickers;
"View larger photo" opens the full prepared JPG, not the cutout or raw screenshot.
The current generated public build is 533 files. Masks, JSON provenance, this README,
model caches and private reviews are never part of that allowlist.
Implementation: `scripts\build-site.mjs`, `pictureMarkup` and `buildSite`
(lines 89-104, 181-228).

## Mask decisions and source limitations

Inference uses rembg 2.0.85 with BiRefNet locally:

| Cake | Candidate model | Recorded alpha correction |
| --- | --- | --- |
| Ribbon and pearl | `birefnet-general-lite` | None |
| Cherry-topped | `birefnet-general-lite` | Clear detached placemat fragments below the board |
| Pink doll | `birefnet-general-lite` | Threshold the translucent lower-left board remnant |
| Butterfly | `birefnet-general-lite` | None |
| Peacock feather | `birefnet-general` | Keep the real feather eye and surrounding central vane incorrectly excluded by the model |

These operations change transparency, not source RGB. They do not reconstruct the
cherries, dress base or upper feather already clipped in the supplied screenshots.
Fine edges still need visual judgement. The manifest's `source_limitation` is
inherited from the source/crop record, not a claim about a newly generated scene.
Evidence: `mask-recipe.json:1-34`, `masks\review.json:1-40`, and
`scripts\prepare_prototype_photos.py`, `RECIPES` (lines 13-58).

Historical five-cake local evidence, supplied by the parent on 2026-10-04:

- `npm test`: 20 passing Node cases; `npm run build`: 53 public files.
- `python -m unittest discover -s .\tests -p test_cake_stickers.py -v`: five passing
  cases, including unchanged archived screenshot/crop hashes and source RGB
  equality for all opaque mask pixels before resizing/compression.
- `python .\scripts\review_site.py`: passed, including transparent corner alpha
  for all six on-page image instances and unchanged full-JPG viewer links.
- The parent visually inspected `.local\stickers\final-review.jpg` on cream/dark,
  desktop/mobile full pages and the 200% order screenshot. User visual acceptance,
  native app/device/assistive-technology acceptance and public launch remain open.

`scripts\prepare_cake_stickers.py` separates three operations:

- `infer` generates unapproved candidate masks on CPU; model downloads are opt-in.
  Photographs stay in the local process (lines 34-53).
- `refine` applies the recorded keep/clear/threshold regions and saves hashes plus
  correction reasons (lines 56-86).
- `prepare` uses saved masks and Pillow only, applies alpha, fits the cutout bounds,
  adds transparent padding and a white contour, then writes WebP/PNG sizes without
  upscaling (lines 89-177). The current recipe uses 28px padding and a 13px contour
  before resizing; this does not paint new cake detail.

## Normal reproduction: no inference or network

Run from the repository root. Python needs the Pillow version recorded in
`scripts\requirements-images.txt:1`; rembg is unnecessary for `prepare`.

```powershell
python .\scripts\prepare_cake_stickers.py prepare --masks .\assets\images\cake-stickers\masks --output .\.local\notebook-release\reproduction --review .\.local\notebook-release\reproduction.jpg
npm run build
```

The default source is `.local\photos\prototype-20261004\crops\`, and the default
output is `assets\images\cake-stickers\`. Use `--output` and `--review` to save an
experiment in a new project-local revision. Export entries also carry their own
private crop directory, leaving the five original screenshot crops unchanged.
Identical existing files are reused;
differing files fail rather than being overwritten. Do not delete old outputs to
force a changed recipe through. Implementation: `prepare_cake_stickers.py`,
`main` (lines 181-203), and `prepare_prototype_photos.py`,
`save_preserving_existing` (lines 62-69).

## Optional mask inference and refinement

Only if re-running inference is deliberately required, use the isolated local
environment. If it is absent, create it and install the pinned requirements:

```powershell
python -m venv .\.local\sticker-env
.\.local\sticker-env\Scripts\python.exe -m pip install -r .\scripts\requirements-stickers.txt
```

`scripts\requirements-stickers.txt:1-2` pins rembg 2.0.85 and includes the Pillow
requirements. Model weights may download into the project-local cache; no
photographs are uploaded. With that environment available:

```powershell
$env:U2NET_HOME = Join-Path (Get-Location) '.local\models\rembg'
.\.local\sticker-env\Scripts\python.exe .\scripts\prepare_cake_stickers.py infer --model birefnet-general-lite --ids ribbon-and-pearl-cake cherry-topped-cake pink-doll-cake butterfly-celebration-cake --output .\.local\stickers\birefnet-lite-masks
.\.local\sticker-env\Scripts\python.exe .\scripts\prepare_cake_stickers.py infer --model birefnet-general --ids peacock-feather-cake --output .\.local\stickers\birefnet-general-masks
python .\scripts\prepare_cake_stickers.py refine --masks .\.local\stickers\birefnet-lite-masks --detailed .\.local\stickers\birefnet-general-masks --output .\.local\stickers\reviewed-masks
```

`refine` defaults to `assets\images\cake-stickers\mask-recipe.json`. Inspect the
resulting masks before passing their folder to `prepare --masks`; an
`inference.json` or `review.json` file is not user approval. Choose fresh output
directories for different models/recipes instead of overwriting the recorded
candidate and reviewed-mask history. Keep full visible cake/toppers in CSS and
check the cream/dark review sheet plus actual browser views before accepting a
new derivative revision.

## Seven-photo notebook extension

The reviewed selection/crops are in `.local\photos\notebook-20261004-v2\`.
The first private `notebook-20261004` batch had incorrect filename associations
and was rejected before promotion. Filename-labelled review sheets and a source
association test prevent those rejected labels from becoming public assets.

The new designs are rainbow butterfly, purple birthday, golden drip, cherry and
curl, pink swirl, rose-topped and lavender swirl. Names describe visible designs,
The owner subsequently identified the cherry-and-curl source
`17855219376447920.jpg` as **Black Forest cake**, in **Cream cakes**. Its stable
`cherry-curl-cake` asset ID, masks and variant bytes are retained; this one name
is now owner-confirmed rather than inferred. See
[the source-selection guide](../../../docs/owner-selected-cakes.md). Names describe visible designs,
not ingredients or flavours. The purple/rose bases and some lavender swirls were
already clipped by their sources; no missing pixels were generated.

`notebook-mask-recipe.json` and `masks\notebook-review.json` record the selection:
detailed BiRefNet masks for rainbow, purple and pink; lite masks for golden,
cherry, rose and lavender. An alpha-only polygon clears the lavender cake's
right-side placemat remnant. The detailed pink mask removes the placemat leaves,
and the detailed rainbow mask avoids the partial board wing in the lite candidate.
Every source RGB pixel is unchanged before compositing/resizing.

The new batch can be processed separately with `--manifest`:

```powershell
python .\scripts\prepare_cake_stickers.py refine --masks .\.local\stickers\notebook-20261004-v2\candidate-masks --detailed .\.local\stickers\notebook-20261004-v2\detailed-masks --recipe .\assets\images\cake-stickers\notebook-mask-recipe.json --output .\.local\stickers\notebook-20261004-v2\reviewed-masks
python .\scripts\prepare_cake_stickers.py prepare --manifest .\.local\photos\notebook-20261004-v2\prepared\manifest.json --masks .\.local\stickers\notebook-20261004-v2\reviewed-masks --output .\.local\stickers\notebook-20261004-v2\prepared --review .\.local\stickers\notebook-20261004-v2\final-sheet.jpg
```

Inspect only `final-review-1-3.jpg`, `final-review-4-6.jpg` and
`final-review-7-7.jpg`, one small batch at a time, rather than opening a large
archive contact sheet. Current validation: seven sticker/provenance cases, 51 Node
cases and local notebook/entrance browser reviews. Export provenance uses
`source_photo_sha256`; the original `source_screenshot_sha256` records remain
intact. Both are checked against the corresponding full-photo source hash.

## Three owner-selected category covers

The full-frame photo recipe is `.local\photos\owner-covers-20261005\selection.json`.
Tea keeps both round/heart cakes in one photograph; Birthday keeps the real
anniversary topper; Chocolates keeps the pictured assortment and original
edge clipping. The old twelve records and all96earlier variants are unchanged.

Tea and Birthday use detailed BiRefNet masks unchanged. Chocolate required local
edge segmentation, source-connected neutral regions and a native-coordinate
keep polygon for a reflective face. The final guard retains the prior alpha of
79 newly covered saturated-blue tray-edge pixels; it never erases prior foreground
or changes source RGB. Earlier colour-only, global and polygon trials were rejected.

Selected mask hashes and review scope are in `masks\owner-cover-review.json`.
The eight-sheet decisions are in `docs\owner-cover-candidates.md`; the complete
recipe/source snapshot is `.local\stickers\owner-covers-20261005\final-masks-v7\`.
Contact-sheet/native-region review does not imply full-resolution review of every
photo, perfect pixel edges or owner acceptance.

Normal reproduction of all15stickers still uses saved masks and Pillow only.
The optional chocolate refinement tool uses the existing isolated environment;
`requirements-stickers.txt` now pins OpenCV for its local edge segmentation.
No photograph is uploaded for processing.

```powershell
.\.local\sticker-env\Scripts\python.exe .\scripts\refine_owner_cover_masks.py --reflection-only --output .\.local\stickers\owner-covers-20261005\reflection-reproduction
python .\scripts\prepare_cake_stickers.py prepare --masks .\assets\images\cake-stickers\masks --output .\.local\stickers\all-fifteen-reproduction --review .\.local\stickers\all-fifteen-unopened.jpg
```

The second command generates a preparation sheet, not permission to view a large
sheet or reset an exhausted image budget. Use the saved bounded review evidence.
