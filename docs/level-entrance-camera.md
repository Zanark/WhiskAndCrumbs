# Level entrance camera and wider framing

Release: `3b8449318acbb3be212e2f67e3566b9f7e268186`  
Pages: [37887037434](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37887037434)  
Asset version: `0fe20a62bf44`

All175live site files and README/ABOUT match the commit. The eight changed public
paths are the camera module, cache HTML, three fallback posters, the entrance
showcase and the two root documents. No building or room geometry was stretched.

## Default view

The former camera eye was `[0,2.4,6.4]`, looking toward `[0,1.25,-2.5]`.
That produces a7.3626-degree downward pitch.

The new eye is `[0,1.65,8.4]`, looking toward `[0,1.65,-2.5]`.
Eye and target share their vertical coordinate, so the neutral optical axis is
horizontal: **zero default pitch**. The eye also moves back two scene units.
The display's projected width is approximately78.54%of its former size, giving
the interior more room within the existing shopfront glazing.

The facade, camera field-of-view policy, room meshes, baked illumination and
window-light direction are unchanged. This is a view correction, not an altered
building scale, raised counter or independent image-layer transform.

## Look-around and fallback behavior

Pulling back initially reduced short-screen look-around below its existing
responsiveness threshold. Rather than weakening that check, bounded eye-X travel
was adjusted to1.3, target-X to1.8 and target-Y travel to1.25. Mouse and optional
phone tilt still use the same normalized input and camera implementation.

All four cake landmarks remain in visible glazing, the counter contact remains
framed, and the actual uploaded camera matrix matches the shared projection
function. The default eye-level horizon stays centered across near/far depths.
The outer storefront does not move.

Wide, portrait and short fallback images were regenerated from the same renderer
using the new neutral camera. No light rebake was needed. Missing/stale bake,
resource failure, context loss/recovery and entry cleanup retain their existing
safe behavior.

## Artwork and preservation

The public entrance showcase is refreshed; the other five public showcase images
are unchanged. A new immutable local kit is available at
`exports\website-launch-20261009-level-camera\`, with current captures and the
same six-post design. Instagram phone layouts remain limited to posts01/06.
Nothing was posted to Instagram.

The separate4174cream experiment is byte-identical to its prior local receipt.
All120product variants, notebooks, wooden navigation, cloth interaction, facade
art, room mesh, paint atlas and baked lighting remain unchanged.

## Evidence

Evidence root: `.local\level-entrance-camera-20261009\`.

- `camera-comparison.json`: former/new pitch, framing and unchanged light.
- `posters-final\receipt.json`: matching fallback images and source hashes.
- `local-camera-final\review.json`: actual GPU eye/horizon/matrix and five viewport cases.
- Local site, entry, facade, phone-tilt and lifecycle reports.
- Separate public camera, entry, phone-tilt and facade reports.
- `release-local.json` and `publication.json`: scoped byte-preservation/live receipts.

The Node suite has131passing cases, including a new neutral-horizon regression;
nine asset cases cover the generated fallbacks. The phone-input reviewer uses
24synthetic cases, not physical phone hardware.

The exact plaque reflection fixture now waits for eight stable camera/render/
font-layout frames after text resizing. Its strict restoration threshold is
unchanged; the earlier incomplete local report remains as history.

No new image-tool inspection occurred. Source, geometry and browser evidence do
not establish subjective visual acceptance or a claim of perfect realism.
