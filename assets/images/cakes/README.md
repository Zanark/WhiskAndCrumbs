# Prepared cake photographs

The current gallery contains **60 real cake-photo records**: the original reviewed
set plus 45 contact-sheet-reviewed archive imports. The archive imports retain
their full framing and have WebP/JPEG variants; rejected sticker candidates are
not included in the catalogue.
Public copies are metadata-free; source originals remain private and unchanged.

The new visual design labels are rainbow butterfly, purple birthday, golden drip,
cherry and curl, pink swirl, rose-topped and lavender swirl. They do not establish
flavours or ingredients. The exact filename associations, hashes, crops and
limitations are recorded in `manifest.json` and in the private
`.local\photos\notebook-20261004-v2\selection.json` recipe.

## Original five-photo batch (retained)

Five user-supplied screenshots, prepared with **cropping, downscaling and web
compression only**. No background replacement, retouching, colour filters,
sharpening, upscaling or generated cake detail.

These are descriptive image labels, not confirmed product names or flavours.

| Photo | Larger WebP | Suggested prototype use |
| --- | --- | --- |
| Ribbon and pearl decorations | [1000px](ribbon-and-pearl-cake-1000.webp) | Strongest feature-image/menu-card candidate |
| Cherries and white piping | [1000px](cherry-topped-cake-1000.webp) | Close-up menu card; black screenshot margin removed |
| Butterfly celebration | [1000px](butterfly-celebration-cake-1000.webp) | Celebration/menu card; most seating cropped away |
| Pink doll cake | [885px](pink-doll-cake-885.webp) | Portrait custom-design example |
| Peacock-feather decoration | [710px](peacock-feather-cake-710.webp) | Tall portrait gallery; keep the feather visible |

Each image has a 480px variant and a larger variant, in both WebP and JPEG.
`manifest.json` records actual widths/heights, hashes, crop coordinates,
source screenshot identity, suggested alt text and image-specific limitations.
Use those dimensions rather than assuming a common square aspect ratio.

The larger WebP set totals 752,098 bytes; the five source PNGs total 11,990,798
bytes. The sources are screenshot captures, not original Instagram downloads.

## Important framing limits

Do not apply a second `object-fit: cover` crop that cuts off the decorations.
Use the prepared aspect ratio or a contained frame. The feather and doll images
are not suitable for a wide full-bleed hero.

Some backgrounds remain because removing them would require a more intrusive
edit. The doll's lower skirt, some cherries and the upper feather were already
clipped in the source screenshots; no missing detail has been invented. The
bakery's actual colours, frosting texture, lettering and handmade finish remain.

## Preserved originals and before/after preview

Original files, lossless crop masters and the side-by-side preview are kept
under ignored `.local\photos\prototype-20261004\`.

[Open the local before/after preview](../../../.local/photos/prototype-20261004/review.jpg).
This link is local-only; private originals and the preview are not published.
The user has not yet approved these crops as final photography.

The exact current batch is reproducible from the repository root:

```powershell
python .\scripts\prepare_prototype_photos.py 'C:\path\to\cakes-photos'
```

The script uses the reviewed five-file recipe, not automatic background removal.
New photographs need a new crop review. Existing differing originals/outputs are
not overwritten. The reviewed archive batch is reproducibly promoted with
`python .\scripts\import_archive_notebook_assets.py`. Pillow is recorded in
`scripts\requirements-images.txt`;
install that dependency only if it is missing.

For future Instagram exports, use the separate
[offline import workflow](../../../docs/instagram-photo-import.md), which accepts
an extracted export folder path without repacking.
