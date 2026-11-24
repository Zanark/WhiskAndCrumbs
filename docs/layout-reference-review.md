# Layout references and readability direction

Reviewed 2026-10-04. These are layout studies, not authorization to reproduce
another bakery's brand, photographs, testimonials, offers or commercial claims.

## Live websites

Both homepages were opened in isolated desktop (1440px) and mobile (390px)
browser views. The hero and early browsing/product sections were visually
inspected, alongside page structure and publicly returned content. This was not
a checkout, accessibility-compliance or performance audit of either business.

| Reference | Observed layout | Useful for this bakery |
| --- | --- | --- |
| [Bakingo](https://www.bakingo.com/) | Prominent red utility/search header on desktop; category navigation; large promotional hero; menu/category tiles; photo-led product rows with names/prices/ratings. The observed mobile page uses a compact utility header and a three-column category grid. | Make cake browsing easy to find; group items visually; keep a direct route from a cake to an enquiry. |
| [Creme Castle](https://cremecastle.in/) | Search/support/navigation on desktop; circular category shortcuts before the hero; large image-led hero; bestsellers, dessert categories and occasion-based browsing; a visible chat action. Mobile preserves a search row and visual categories, then stacks/swipes sections. | Clear type hierarchy, visible navigation, large cake images, recognizable categories and easy access to a person. |

Do not borrow the dense mega-menus, login/cart/wishlist controls, autoplay
promotions, broad catalogue or delivery promises. Five real cake examples do not
need a complicated search/filter system, and a home bakery does not need to
pretend to be a nationwide delivery service.

The sites' offers, ratings, delivery times and scale are their own statements,
not verified facts about this bakery.

## Supplied visual references

The first two attachments show the same pink/arched bakery concept at different
scales: a split hero, a large arched image, pastel product cards, and a longer
catalogue/customisation page.

The peach reference uses a soft organic hero shape, isolated cake imagery,
spacious sections and a restrained cream/peach palette. The cupcake reference
uses a bold pink hero, an icing-like divider, large product imagery and clear
section headings.

Useful ideas are soft framing, a little pink, playful section edges and a strong
visual distinction between browsing and contacting. Avoid tiny product text,
icon-only favourites/cart controls, illegible decorative copy, manufactured
discounts and copied ingredient/trust claims.

The supplied reference cakes are not our product photos. The user's later explicit
choice authorizes background removal and white sticker contours on separate
derivatives of the five actual cakes. It does not authorize generative background
replacement, new cake detail or clipping tall toppers into an arch. Original
screenshots and prepared full-photo variants remain unchanged.

## Accessibility requirement from the user

The intended audience includes many people over 35 and some over 50, with varied
familiarity with websites. The design response is to support limited digital
confidence and different reading needs, not to assume that age determines ability.

Readability and clarity take priority over decorative detail. The current
baseline is 18px reading copy, at least 16px important labels/help text, principal
controls at least 48px high, high-contrast text, visible keyboard focus and
layouts that tolerate enlarged text.

Use literal labels. "View cakes" is clearer than "Find your something sweet";
"Ask about this cake" is clearer than "Something like this?".

## Applied to the current prototype

- The user first requested a three-section reduction, then explicitly asked for
  the original "Our little story" immediately below the first section. The current
  order is home -> story -> cakes -> order; the original copy and recipe-note
  illustration are restored without adding biography.
- FAQs, duplicate marketing, a separate custom-cake section and message forms
  remain out. The story restoration does not revive the longer page.
- Main mobile links are always visible: Home, View cakes and How to order.
- Large text remains; the reduction is in words, not font size.
- All five cake stickers have plain design names, visual categories and direct
  "Ask about this cake" links. No catalogue filters or extra sections are needed.
- Ordering is one short instruction and a prominent messaging button, with a
  brief login/handoff note and manual-confirmation reminder. Instagram opens the
  profile without prefilling a DM or passing the cake name.
- Photo links explicitly say "View larger photo", below rather than over the
  cake, without rotating the label. The viewer opens the full prepared JPG and
  uses visible Close/Previous/Next labels.
- The hero and gallery have transparent white-contour cake images on cream,
  without polaroid rectangles or a hero backing rectangle. Alpha-following
  shadows replace box shadows; the overlapping hero badge has been removed.
  Full sticker bounds and visible toppers fit rather than receiving a cover crop.
- The user kept the cute details but rejected the pink/sage palette and overly
  cursive Dancing Script. The current version restores the original cream/deep
  green, with clearer Courgette display text. Scallops, rounded controls and
  heart/bow doodles remain; body/actions use DM Sans.
- The selected Whisk & Crumbs identity adds an original whisk/crumb logo and a
  complete favicon set. New supplied pattern references informed sparse, original
  outline drawings, not copied image pixels. Cream/green tiles use 7.5%/6.5% layer
  opacity and about 1.62% line coverage; primary controls and the note stay solid.
  The reference images are inspiration, not replacement product assets.

WhatsApp is likely to reduce the handoff burden for customers who already use it,
but the real public number has not been supplied. The prototype does not invent
one. Instagram is the available destination, with an explicit login warning.

The cursive design explicitly responds to the user's newer request for an
extremely cute appearance. Background removal uses locally inferred and
recorded alpha masks; no photograph upload or cake reconstruction is involved.
Source-clipped cherries, dress base and upper feather remain clipped. The private
`.local\stickers\final-review.jpg` sheet compares source and cutout on cream/dark;
its existence is not proof of perfect masking or user visual approval.

## Evidence and preservation

- Four supplied images: `assets/references/layouts/`, copied without changing bytes.
- The earlier public prototype and review were retained under
  `.local/revisions/before-readability-20261004/`.
- The longer readability revision remains under
  `.local/revisions/before-three-sections-20261004/`.
- The three-section site/review immediately before stickers remains under
  `.local\revisions\before-stickers-20261004\site\` and `review\`.
- Current local browser evidence: `.local/website-review/`.
- The preceding serif/sticker design is preserved in
  `.local\revisions\before-cursive-20261004\`.
- Live-reference screenshots and observations: this session's
  `files/layout-reference-review/` artifacts.
- Durable requirements: `AGENTS.md`, `TODO/08_READABILITY_AND_SIMPLE_ORDERING.todo`
  `TODO/09_STORY_AND_CAKE_STICKERS.todo` and `TODO/12_WHISK_AND_CRUMBS_BRAND.todo`.
- Local model/correction and public-boundary documentation:
  `assets\images\cake-stickers\README.md`.

Current local review passed for the four-section order, restored story, six
transparent on-page image instances, full prepared JPG viewer links,
320/390/600/768/1024/1440px widths, 16px+ key labels, 48px principal controls,
200% text resizing, keyboard/photo interaction, no-JavaScript contact and slower
network loading. The report measures 188 main DOM words: 113 focus and 75 story.

The final cream/dark contact sheet, desktop/mobile pages, enlarged-text views and
matching sharing image have been inspected. Workstream 12 records the current
25 passing Node cases, four branding cases, 66-file build and public release;
workstream 09 retains the five passing
sticker/source cases. Neither automated checks nor visual inspection imply
perfect cutouts, complete source details, user visual approval or native
app/device/assistive-technology acceptance.
