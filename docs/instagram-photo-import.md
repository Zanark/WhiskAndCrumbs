# Get the cake photos without taking screenshots

## Current result

On 2026-10-04, a bounded, unauthenticated Instaloader attempt for
`@homemadevegcakes` stopped at Instagram's profile endpoint with
**HTTP 429 Too Many Requests**. It downloaded **zero cake photographs**.
The request used one connection attempt and aborted on 401, 403 or 429.
No password, browser cookies, session files or private account information were
accessed. Do not loop, rotate identities or use third-party download websites
to try to get around that response.

The saved kitchen references are not cake downloads.

The owner subsequently supplied an extracted export. The offline importer ran
successfully on 2026-10-04: **178 scanned files, 167 eligible entries, 160 unique
originals, seven byte-identical duplicates and 11 exclusions** (seven outside
scope, three videos disabled and one unsupported extension).
`.local\instagram\imported\manifest.json` records the source associations and
hashes. No authenticated download or photograph upload was performed.
Seven individually reviewed export photos now supplement the five screenshots
in the twelve-cake notebook; the rest of the archive remains private.

## Your handoff can be just a folder path

The folder-path handoff has now been exercised with the supplied export. Future
exports can use the same workflow without repacking.

For temporary screenshots/snippets, put them in a dedicated Downloads folder and
send its path. The five screenshots supplied in `Downloads\cakes-photos` on
2026-10-04 have now been preserved unchanged and prepared with conservative crops.
They remain explicitly labelled **screenshots**, separate from actual downloaded
photo files. See [the prototype asset notes](../assets/images/cakes/README.md).
Screenshots can include Instagram UI and have less detail; they do not establish
a complete archive.

Later, extract all downloaded export parts and send the **extracted folder
path**. You do not need to rename images, pick files individually, recreate the
ZIP or run commands yourself. The local import workflow accepts that folder,
finds supported uploaded-media subfolders recursively and reports what it found.
If parts were extracted into separate folders, give each folder path or a common
parent containing them.

Keep screenshots until their matching export/phone photos have been reviewed.
A screenshot and its source photo have different bytes, so automatic hash
deduplication cannot establish that they show the same cake.

## Recommended route: the account owner's Instagram export

Instagram can prepare a downloadable archive of the account's content. This
requires the account owner to request it while signed in normally; the agent
cannot request that authenticated export from the public profile URL.

Typical Accounts Center labels are below; Meta changes labels and grouping
between app versions. Use the official export/download feature, not a service
asking you to hand over your password.

1. Open Instagram while signed into **homemadevegcakes**.
2. Open the profile menu, then **Accounts Center**.
3. Find **Your information and permissions**, then **Export your information**
   or **Download your information**.
4. Create an export/download and select the **homemadevegcakes** account.
5. Choose **Export to device** or **Download to device**.
6. Customize the information to the owner's **posts/content/media**. Include
   reels or archived stories if those contain cakes you want to retain. Exclude
   messages, contacts, followers, login/security history and payment information.
7. Select **All time**, **JSON**, and the **highest media quality offered**.
8. Start the export. When Instagram notifies you that it is ready, download
   **every ZIP part** before the download expires.
9. Keep the ZIPs on this computer and provide their local paths. There is no need
   to upload a private account archive into the chat or send any credentials.

Official starting points:

- [Instagram help: review/export your information](https://help.instagram.com/181231772500920)
- [Meta Accounts Center](https://accountscenter.instagram.com/)

The Instagram Help Center returned only its shell in this environment, so the
exact current screen labels could not be independently read here. Follow the
equivalent export/download controls in the signed-in account.

**Quality:** these are actual media files returned by Instagram, not screen
captures. "High quality" does not recover detail Instagram previously removed.
For the strongest hero image, a phone/camera original may still be better.

## Local archive layout

Suggested private working folders:

```text
.local\
  instagram\
    incoming\    Downloaded ZIP parts, if you choose to move them here
    imported\    Importer output: original media and a local manifest
```

The repository ignores `.local/` and ZIP files. Keep extracted account exports
under `.local/` too, not in an arbitrary tracked folder. Git-ignore is not
encryption and does not protect files already tracked or force-added.

The future site must be deployed from its own public directory, never from the
repository root or this local archive.

## What the importer is for

`scripts/import_instagram.py` is an **offline** importer, not an Instagram
scraper. It does not need Instagram credentials or network access. It copies
eligible photo files without recompression and keeps byte-identical duplicates
once, with their source associations in a local manifest.

Its input can be ZIP files or an already extracted export. Provide all parts
together. It includes every eligible photo, rather than just a carousel's first
image. It cannot infer which photos show cakes; visual curation comes afterward.

Supported uploaded-media folders are `media/posts`, `media/reels`, `media/igtv`,
`media/stories` and `media/archived_posts`, including under an enclosing export
directory. Messages, profile pictures and unrelated account files are not part of
the import. Unknown folder layouts need inspection rather than blindly copying
every image from an account archive.

From the repository root, using Python 3.10 or newer:

```powershell
python .\scripts\import_instagram.py `
  'C:\path\to\instagram-export.zip' `
  --output '.\.local\instagram\imported'
```

For the future path-only handoff, this is the command the agent can run on your
behalf; you only need to provide the real folder path:

```powershell
python .\scripts\import_instagram.py `
  'C:\path\to\extracted-instagram-export' `
  --output '.\.local\instagram\imported'
```

For an export split into several downloads:

```powershell
python .\scripts\import_instagram.py `
  'C:\path\to\instagram-export-part-1.zip' `
  'C:\path\to\instagram-export-part-2.zip' `
  --output '.\.local\instagram\imported'
```

To preserve video files as well:

```powershell
python .\scripts\import_instagram.py `
  'C:\path\to\instagram-export.zip' `
  --output '.\.local\instagram\imported' `
  --include-videos
```

If a real export places relevant uploads in `media/other`, inspect that ambiguous
folder first. `--include-other-media` explicitly enables it; it does not enable
messages, profile pictures or arbitrary folders. Videos still require
`--include-videos`.

Use `--help` for the exact options and size limits. ZIP parts must be independent
complete archives, not binary split segments. The default limits are 512 MiB per
file and 20,480 MiB each for eligible input and the resulting collection. File
types are inferred from extensions, not decoded or classified as cakes.
Do not relabel a video thumbnail or an extracted frame as an original uploaded
still photograph.

## What "all photos" means

An import count establishes what was found in the supplied export, **not** that
every photo ever uploaded has been recovered. Post and image counts differ
because carousels contain multiple files, reels are videos and duplicates may
repeat the same bytes.

Review the import summary and local manifest, account for every ZIP part, and
compare with the account's post history. Deleted posts, expired stories,
unselected content, missing export parts or files Instagram does not include
cannot be reconstructed by the importer. Export folder layouts can also change;
zero eligible files must be treated as a problem to investigate, not success.

Compatibility is established for the supplied extracted export, including nested
dated media folders. This is not proof of full account-history recovery, and no
comparison with signed-in account history has been performed.

## Turn the archive into website photographs

The full supplied posts-folder review now has a bounded, resumable workflow:
[contact-sheet protocol](image-review-workflow.md) and
[per-file review ledger](image-review-posts-20261004-owner-v2.md). Its scope is 159 posts
files, not the complete 160-unique-original import across other media folders.
Eight labelled v2 sheets are generated but not yet viewed; 141 distinct images
await classification. Six owner-confirmed source files, six remaining prior
selections and six duplicate entries are accounted for without re-viewing.
The initial nine-sheet revision is retained as history. The owner's exact new
category examples are recorded in [the selection guide](owner-selected-cakes.md). Workstream 15 owns the sequential review and
its strict fewer-than-20-image-views-per-session limit.

Keep the source archive and imported originals unchanged. Review copies for
customer names, faces, addresses, order slips, publication permission and
sensitive embedded metadata before promoting anything to public assets.

Select the strongest photographs, identify products with the baker and choose
intentional crops. Preserve colour and cake detail; do not upscale or replace
the bakes with generated imagery. Create optimized web derivatives only after
selection. The full account archive should not become a public website gallery.
