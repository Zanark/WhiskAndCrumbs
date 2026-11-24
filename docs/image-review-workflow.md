# Bounded, local cake-image review

This workflow implements the user's 2026-10-04 request without changing originals
or publishing the archive. It reviews the supplied **posts directory**, not all
Instagram account history and not the site's repeated responsive derivatives.

The October9request expands the goal to **complete eligible-food categorization
and notebook import after review**. Its exact category rules and recursive queue
are saved in `.local\archive-import-20261009\request-and-preflight.json` and
`image-queue.json`, with workstream47tracking delivery. The original source
archive remains private and unchanged; only reviewed derivatives can become public.
The current session still cannot reserve a sheet: the real audit reports118image
attempts/117successful views against the16-slot stopping threshold.

Source:
`C:\Users\mishrad\Downloads\instagram-homemadevegcakes-2026-10-04-EUoajskJ\media\posts`

Private inventory, sheets and decisions:
`C:\devdesk\homedesk\B-Bakery\.local\image-review\posts-20261004-owner-v2`

Per-file and per-batch project record:
`C:\devdesk\homedesk\B-Bakery\docs\image-review-posts-20261004-owner-v2.md`

The owner subsequently identified six source files directly. Their hash-bound
receipt is `.local\image-review\owner-classifications-20261004.json`, documented
in [the source-selection guide](owner-selected-cakes.md). The v2 revision excludes
those files from re-viewing: 141 remaining representatives on eight 17-18-tile
sheets. The original nine-sheet revision remains unchanged as history.

## Non-negotiable limits

- Never open all originals individually, load images in parallel or delegate
  viewing to other agents. Programmatic decoding is not a visual inspection.
- Each labelled sheet contains **15-20 thumbnails**. Preserve full framing and
  aspect ratio, without upscaling or making crops on the original files.
- Review **one sheet at a time**, then save every tile's classification,
  selection/exclusion, reason and uncertainty before the next view.
- Stay **below 20 image views per session**. This workflow stops new reservations
  at 16 consumed slots, leaving a margin. Failed attempts and reservations whose
  view did not complete consume a slot. Compaction does not reset the counter.
- Use a current-session event log, not an empty replacement or a previous
  session's log. Other image tools, attachments or external previews must not be
  used to evade the budget. If their consumption is uncertain, stop conservatively.
- The auditor streams the event log and retains only image-view accounting.
  Large historical image payloads must not be loaded as one complete text buffer.
- Never reopen a reviewed sheet. Use its saved findings and full path. Make a
  separately labelled focused sheet of 15-20 uncertain/shortlisted items when
  closer comparison is necessary; that sheet also consumes one view.
- A shortlist is **not public selection approval**. Contact sheets are not
  full-resolution quality, privacy, copyright or photo-permission clearance.

## Inventory and preservation

`scripts\review_image_inventory.py` uses existing Pillow and repository helpers.
It enumerates full paths, filenames, SHA-256, byte counts, modification times,
stored/display dimensions, image format, mode and frame count. It records the
presence of EXIF without copying its contents into the report. Decode failures,
unsupported formats and animated files stay explicitly on hold.

Exact byte duplicates retain every path but need only one visual representative.
Previously selected website sources are recognized **only by source SHA-256**
against the prepared-photo manifest. Their existing provenance is reused, rather
than re-viewing or claiming a new review. Similar-looking but different-byte
images are not automatically called duplicates.

Preparation stages files in a private temporary directory, verifies source hashes
and modification times, then promotes the complete directory. Existing review
revisions are never overwritten. Original bytes, names and modification times
must match again at every stopping point. Neither the source images nor `site\`
are written by this workflow.

## Resume in a fresh session

Read `AGENTS.md`, the numbered TODOs, this guide, the per-file report and the
current `.agent-context` store. Check Git status and the complete diff. Do not
open any image while hydrating.

The examples below run from `C:\devdesk\homedesk\B-Bakery`. Set `$events` to the
**new session's actual `events.jsonl`**, obtained from its supplied session path.
Do not reuse the old session ID to claim a reset.

```powershell
$review = 'C:\devdesk\homedesk\B-Bakery\.local\image-review\posts-20261004-owner-v2'
$report = 'C:\devdesk\homedesk\B-Bakery\docs\image-review-posts-20261004-owner-v2.md'
python .\scripts\review_image_inventory.py --output $review verify
python .\scripts\review_image_inventory.py --output $review report --events $events --report $report
python .\scripts\review_image_inventory.py --output $review reserve batch-01 --events $events
```

Only if reservation succeeds, open its returned **contact-sheet path once**.
The script does not open the image itself. The reservation is persisted first
so interruption cannot silently reset the budget.

Edit `drafts\batch-01.json` with actual observations. Each tile must have its
labelled ID, a classification, selection, specific reason, risk list and
`needs_focus` boolean. Valid classifications: `cake`, `other-bake`, `process`,
`non-product`, `uncertain`. Valid selections: `shortlist`, `reserve`, `exclude`,
`hold`. Uncertain items must use `hold` and `needs_focus: true`.

Record design/colour/shape only. Do not infer flavour, price, ingredients, dietary
guarantees, identities or publication permission. Flag visible personal text,
faces/photo toppers, brand/character art, clipping, blur, distracting surroundings,
collages and possible alternate shots without transcribing personal details.

Set the batch status to `reviewed` and write a concise observation summary, then:

```powershell
python .\scripts\review_image_inventory.py --output $review record batch-01 `
  --decisions "$review\drafts\batch-01.json" --events $events --report $report
```

The recorder requires a successful matching view, exactly one reasoned decision
per tile, and regenerates the project documentation immediately. Do not move to
the next sheet if recording or documentation fails. Repeat sequentially with
the next unviewed batch from the report, never all sheets together.

For focused comparisons, select 15-20 unique IDs from uncertain or shortlisted
items. The `focus` subcommand requires a new `focus-NN` name, `--ids` and a
specific `--reason`; it generates another labelled sheet, not individual views.
Reserve, view and record that focused sheet through the same gates. First-level
decisions remain immutable; the later focused decision is shown in the ledger.

## Failure and stopping protocol

Owner-provided source classifications are separate evidence. Supply their
hash-bound JSON through `prepare --owner-classifications` when generating a
new named revision; never invent successful contact-sheet views to record them.
The report labels them `owner-confirmed-*`, not cutout or publication approval.
Keep earlier inventory/sheet revisions and use only the latest designated set.

If a view fails, record a separate decision document with `status: "view-failed"`,
an explanatory `summary` and `items: []`. If a prior session was interrupted with
no reliable notes, use `status: "interrupted-unclassified"` instead. Never invent
classifications to clear a stuck reservation. Both retain the original consumed
slot and leave the affected images pending; an explicitly justified focused
sheet can recover them later without repeatedly reopening the failed artifact.

If source hashes, directory membership, sheet hashes or labels disagree, stop
and investigate the exact mismatch. Do not repair by deleting or replacing source
files. A changed input needs a separately named inventory revision.

Before the budget margin is reached, or on any blocking failure:

1. Save the batch decisions and regenerated project report.
2. Run source/sheet verification.
3. Update workstream 15, the development ledger and this base's STATE/JOURNAL.
4. Record the exact next unreviewed sheet and pending focused comparisons.
5. Refresh Context Mesh and stop for a fresh session.

## Honest initial stop

The existing session `7fb2037d-b09c-4d86-87ae-64889392ea4c` already contained
**100 successful image-tool views, plus one failed attempt**, before this bounded
review was requested. No new image views are permitted in it. Inventory and sheet
generation do not count as looking at the images; the first visual batch must
start in a fresh session. Historical notebook selections are not re-labelled as
new visual findings.
