# Notebook titles below an unobscured spiral

Live layout: `43264edd0f39397aed81acbc1ab6848655b04548`, Pages37998387090.
Final artwork: `9eee4ec20059535256f0806fede90846f61f2ddc`, Pages38000529461.
Application version: `5253313789dd`.

The old toolbar's cream `::before` extended24pxbelow the title and painted above
the notebook atz8. It covered the upper20pxof the40pxbinding. Raising a z-index
alone would not put the heading in the right place.

The existing toolbar, including its title and Back button, now moves into the
active notebook heading. `display:contents` removes its separate painted box.
The book reserves the complete spiral strip, and the title begins4pxbelow it.
Focus rings remain below the coils too. Back stays an attached right-edge tag.

The whole toolbar moves together to preserve title-to-Back Tab order. Close,
failed dialogs and accessibility/static restoration return it to its original
position before the notebook mount. Page-turn completion excludes persistent
toolbar focus, so selecting Back during a turn no longer steals focus away.
The fitting guard observes the title and checks its clearance from the binding.

This reuses the previous header allowance: photo-stage positions are unchanged at
1440x1000,390x844and667x375. The short landscape heading removes8pxofinternal
padding rather than reducing photos or text. Titles remain34px, captions28px and
full pages keep four photographs.

## Delivery and evidence

The urgent five-file layout fix was published first; matching artwork followed.
All179live site files plus README/ABOUT match the final commit. The independent
148-photo/1241-file archive candidate remained unchanged and unpublished.

[Live notebooks](https://zanark.github.io/WhiskAndCrumbs/?v=5253313789dd#cakes)  
[Updated image gallery](../exports/website-launch-20261010-title-below-spiral/preview.html)

64Node cases,134notebook/300photo fitting states, full local site/entrance checks,
24live category/large-text states and two live motion directions pass. All six
titles, Tab order, focus return, reduced motion and failed-dialog restoration are
covered. The first full-site run caught the real Back-focus coupling; it was
fixed, not waived. Paper-pixel sampling excludes genuine control shadows and
focus rings while retaining its original opacity threshold.

The final kit preserves six landscapes/six portraits, colour variation, the
frosted cream treatment, raised phone glass and no diagonal background bands.
Only the open-notebook portrait changes. Landscapes02and05change; the entrance's
mobile capture has34pixels differing by more than3RGBlevels, without changes to
entrance assets/controllers. No visual interpretation or approval is claimed.

Receipt: `.local\notebook-title-binding-20261010\publication.json`.
No new image-tool views or Instagram posting occurred.
