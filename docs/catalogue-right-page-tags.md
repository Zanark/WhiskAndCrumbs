# Catalogue-only photos and right-side page arrows

Status: published and verified locally and publicly.

Commit `afb18cbf22ce250bec7f7f1912fcec28c7dc582f`,
[Pages37949350437](https://github.com/Zanark/WhiskAndCrumbs/actions/runs/37949350437),
version `e582762c863a`. All175live files and root README/ABOUT match committed Git
blobs at https://zanark.github.io/WhiskAndCrumbs/. Exactly eight generated files
and the two approved root documents changed; tracked files are clean.

## Behavior

The later slower-motion follow-up is recorded in
[Physical top-spiral turning](physical-notebook-turn.md). It preserves this
catalogue and arrow-only control contract; its publication is tracked separately.

All fifteen cake images remain native links to their original full prepared JPGs.
The per-photo Enlarge/Ask/Order controls and catalogue pseudo-labels are removed.
Plain click, Enter and Space open the existing category-scoped viewer; closing
restores focus to the exact image anchor. Ctrl/Shift/middle clicks open the native
image destination. Alt/Ctrl/Meta/Shift events are not intercepted. Without
JavaScript, or if the viewer cannot open, the same full-photo link still works.
The hero retains its View larger photo label. Main ordering/contact is unchanged.

Both previous/next arrows are stacked tags on the RIGHT edge of the open book.
They attach16px to the cream paper and expose96px beyond it at default text size.
Faces and attachments stay opaque pastel. The separate counter remains outside
buttons; single-page books hide pagination. The next arrow doubles as the
optional upward-drag handle, without a duplicate advancing click listener.
Short, downward and cancelled gestures do not turn pages.

The owner's later **"remove the page turn button"** clarification is already
satisfied by this release: there is no separate Turn/page-turn button, text label,
corner or drag handle. Both requested right-side previous/next arrows remain.
Only the Next arrow carries the optional upward-drag behavior.

Names remain centered28px, open titles34px, cover titles36px and the catalogue
description24px. Arrows use28pxglyphs; text buttons20px and targets at least48px.
Four-photo pages stay2x2, or four across on short landscape screens, with an honest
shorter final page. No left action gutter or bottom action footer remains.

## Measured fitting

The pre-cleanup measurement covers230states across all six categories and the
combined fit/reflow cases. Twelve category/viewport/text combinations retain
complete static fallback, with explicit measured overflow/overlap reasons:

- Decorated:320x480,360x540,320x568at100%;320x900and390x844at200%;
  390x844at150%;600x800at200%.
- Birthday:320x900and390x844at200%.
- Tea, Cream and Chocolates:320x900at200%.

Decorated360x640at100%now fits. In the900px-height reflow sweep only320/390/600at200%
fall back;320at100%and768at200%now fit. No threshold, text size or photo count was
lowered to obtain these improvements. Extreme/resize/late-font safety paths remain.

## Checks and artwork

132Node cases,10asset cases,134enhanced notebook states and300photo views pass.
Both local and public hosts pass the same full fit/site/entrance reviews. The fit review
checks both scroll axes, descendant bounds, centered captions, exact image sources,
full hit areas, opaque faces, loading/error views and late-font completion/failure.
The full site and entrance reviews pass sequentially, including native touch and
mouse drags, interrupted turns, keyboard/focus, native modified clicks, noJS,
missing styles/modules, forced colours, reduced motion and print.

The initial site run had a transient image decode failure. A separate all-visible
image decode probe and a fresh full site run passed; the failed log is preserved.

Fresh12viewport/fourfeature captures supply a new frosted Gaussian-cream kit:
`exports\website-launch-20261009-catalogue-right-tags\`.
It contains six1600x1000landscapes, six1080x1440portraits and a six-JPEG ZIP.
Phones occur only on portrait01/06. Reused layers:
`.local\frosted-cream-launch-20261009\layers-v2`.
Hash comparison changes landscapes03/04/05and portrait05only; other images are
byte-identical. The story viewport includes the revised catalogue introduction.
43campaign regressions and72actual-JPEG typography checks pass.

Evidence: `.local\catalog-right-tags-20261009\`, including baseline snapshots,
`fallback-measurement-before-cleanup.json`, `local-fit-v1`, `local-site-v2`,
`local-entry-v1`, campaign logs, `public-fit-v1`, `public-site-v1`, `public-entry-v1`
and `publication.json`. The publication receipt includes all175live file hashes,
root-document hashes, exact workflow SHA and the public review JSON hashes.

### Later no-separate-Turn confirmation

`no-separate-turn-control.json` binds the clarification to the same commit/run.
Six no-JavaScript cases and48enhanced page cases pass across both hosts at
1440x1000,390x844and667x375. Every notebook has exactly the two arrow buttons,
with one drag target identical to Next; no standalone handle or Turn text exists
in DOM content, accessible names, titles or pseudo-elements. Single-page controls
remain hidden. The targeted catalogue Node regression also passes.

All25capture-source hashes,16capture files and12kit JPEGs are unchanged; all six
public README images match those exact kit/deployed bytes. This verifies capture
provenance, not visual approval. No new build, artwork replacement, commit or
deployment was needed. The original publication receipt remains immutable.
The initial probe's localCRLF-versus-GitLF fixture failure is preserved separately.

## Concurrent-source boundary

While this release was being prepared, workstream64added unreviewed neon rules
to `web\entrance-shop.css`. Those authoring bytes are preserved unchanged and are
NOT part of the catalogue release. The final output is built with the existing
builder from a frozen reviewed source copy under
`.local\catalog-right-tags-20261009\release-source\`; its entrance stylesheet
matches the capture/source receipt exactly, including source line endings.
The normal root build will include the pending64rules, so do not rerun it for
this release. `concurrent-source-boundary.json` records both hashes and the saved
pending stylesheet. All25capture-source hashes match the final catalogue output.

No image was opened for visual inspection. No aesthetic/native-device approval
is inferred from numerical checks. No archive import, Instagram posting, live
cream integration or changes to the isolated local4174source were made.
