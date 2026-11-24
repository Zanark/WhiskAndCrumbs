# A window into the kitchen

Historical design baseline. The current catalogue has direct clickable cake images,
no per-photo order buttons, and both page-arrow tags on the right edge. See the
[catalogue implementation record](catalogue-right-page-tags.md) and
[publishing guide](github-pages-publishing.md) for current behavior and release.

Status: design baseline for the implemented local prototype. The supplied
[design specification](references/home-bakery-design-specification.pdf) is the
design baseline; this document turns it into a small first release and records
decisions still needed. Current implementation and maintenance instructions are
in [the prototype guide](prototype-guide.md); public release remains pending.

The later [layout-reference and readability review](layout-reference-review.md)
adds a core constraint: prioritize clear, comfortably sized content and simple
contact for customers with varied digital confidence. The user first narrowed the
The later category-notebook request supersedes this plan's single-gallery layout:
six category covers, weight-first pages and four-cake photo pages are implemented
locally under [workstream 16](../TODO/16_CATEGORY_NOTEBOOKS.todo). It is not yet
published; four photo categories and visual review remain pending. See the
[current implementation guide](prototype-guide.md#six-top-bound-category-notebooks). The user first narrowed the
page to landing, past cakes and ordering, then explicitly restored the original
story immediately below the hero and chose white-outlined cake cutouts. Current
order: **home -> story -> cakes -> order**. The old three-section-only rule is
superseded; the original long page and optional helper remain out of scope.

## The idea

Make visitors hungry first, comfortable second, and certain how to enquire third.
A real cake and a real person matter more than decorative polish.

The user describes vegetarian cakes made by a home baker. Do not invent a menu,
prices, business name, kitchen history, reviews or delivery promises. Instagram's
public profile is useful background, not final approval for website claims.

**Working headline:** "Baked at home. Made with heart."

The visual promise is a sunlit Indian home kitchen, not a luxury patisserie, a
delivery app or a pretend storefront. The four supplied kitchen images establish
the mood; they are not evidence that this is the baker's own kitchen.

## Translate the references, do not imitate a room

| Reference detail | Website treatment |
| --- | --- |
| Peach walls and warm daylight | Warm cream canvas, generous breathing space and natural photographs |
| Green marble worktops | Deep green type/buttons, occasional quieter green panels |
| Steel tins and open shelves | Fine separators, orderly headings and simple category navigation |
| Floral curtains | One restrained floral detail or section divider, not patterned text backgrounds |
| Wooden utensils and handwritten labels | Warm brown captions and a small recipe-note motif |
| Plants by the window | An occasional botanical accent, never competing with the cake |

Palette from the specification: cream `#F5EBDD`, deep green `#34483A`, marble green
`#536457`, terracotta `#B9684A`, soft pink `#D99A91`, wood brown `#76543D`, neutral
`#E7DED0`. Treat the spec's 55/20/10/7/5/3 ratio as a visual guide, not a requirement
to colour every component. Green-on-cream is the default readable pairing; test
all actual text combinations. Do not assume terracotta or pink works for small
text.

The user's later cursive/cute request supersedes the original serif direction.
The user then rejected the overly cursive Dancing Script and the unrequested
palette change. Use clearer Courgette display text and DM Sans reading/actions.
Retain cream #F5EBDD, deep green #34483A, terracotta #A45137 and the original
brown/paper accents. Do not change this palette without approval.
Scalloped edges, rounded buttons and small original heart/bow doodles add warmth
without extra copy, motion or decorations over the actual cakes.

## First-release composition

Keep **one homepage with exactly four sections** in the order below. Navigation
remains Home, View cakes and How to order; the story does not need another button.
Do not restore other sections from the original specification merely because more
content becomes available.

| Section | Experience and content |
| --- | --- |
| Home | One real cake sticker, large headline, one short description, View cakes and How to order |
| Our little story | Exact original grounded copy and recipe-note illustration, immediately below the hero; no new biography |
| Cakes we've made | All five real cake stickers, plain design names, visual categories, full-photo enlargement and direct enquiry links |
| How to order | Message the cake, date and number of people; one messaging button, brief handoff note and manual-confirmation reminder |

The header and footer stay minimal. Reviews, FAQs, separate custom-cake
marketing and forms are outside this scope. Never invent customer counters,
five-star badges, "bestseller" labels or a baking schedule.

On desktop, keep the asymmetric hero and one photo-led gallery. On mobile, put
the image before the heading, keep the main actions visible and use generous tap
targets. The contextual How to order link must respect safe areas and never
obscure content or focus.

Use the user's chosen transparent cutouts with baked-in white sticker contours
on the cream canvas, rather than rectangular/polaroid cards or a hero backing
rectangle. A subtle drop shadow follows the image alpha. Preserve all visible
toppers and padding without `object-fit: cover`; enlargement labels remain
readable and unrotated, and no badge covers the cake. The recipe-note paper
illustration belongs to the restored story, not to the gallery photo treatment.

## Ways to take orders without a server

**Recommended final MVP: WhatsApp first, Instagram as a fallback.** The working
prototype currently uses Instagram because no WhatsApp number has been supplied.
Ordinary links work
from a static site. There is no need for accounts, a shopping cart or a database.

| Channel | How it works | Fit and limitations |
| --- | --- | --- |
| WhatsApp | A `wa.me` link opens a conversation with a URL-encoded suggested message | Best default: customer can send a date, cake size and reference picture. Requires WhatsApp; opening a chat does not send or confirm an order. |
| Instagram DM | Link to the known profile with "Message us on Instagram"; optional direct-DM link only after device testing | Familiar to existing followers; login may be required. Keep a dependable profile-link fallback. |
| Phone call | A `tel:` link using a confirmed public number | Useful for questions and customers who prefer speaking. Publish contact hours; calls do not create a written order record. |
| Email | A `mailto:` link with a suggested subject/body | Useful fallback, but depends on an email app and may receive slower replies. Never the only contact path. |
| Google Forms or Microsoft Forms | Link to an owner-managed enquiry form | Useful if requests become hard to track. Another service holds customer data; verify sharing settings, notifications and upload/sign-in restrictions. |
| Hosted form backend, e.g. Formspree | Static form submits to a third-party endpoint | More integrated, but introduces quotas, spam controls and privacy work. Browser code cannot safely contain email/API secrets. Defer until needed. |

Use one primary channel, not six competing buttons. Phone/email can be quiet
fallbacks if explicitly approved. The alternatives above are options, not a
backlog to add forms. No WhatsApp API or paid integration is needed for click-to-chat.

Example link shape, **not a configured business number**:

```text
https://wa.me/COUNTRYCODE_AND_NUMBER?text=URL_ENCODED_MESSAGE
```

Store the verified international-format, digits-only number in one configuration
location. Encode message text with `encodeURIComponent`; never concatenate raw
customer text into a URL. Do not invent a phone number now.

Suggested product message:

```text
Hi! I'd like to enquire about [CAKE NAME].
Preferred size: [SIZE]
Needed for: [DATE]
Pickup/delivery area: [AREA]
Could you confirm availability and the price?
```

Suggested custom-cake message:

```text
Hi! I'd like to discuss a custom cake for [DATE].
Theme/design: [IDEA]
Approximate servings: [NUMBER]
May I send a reference photo?
```

The current WhatsApp implementation prepares a short enquiry, including the cake
name on cake-specific links; it does not show blank placeholders or a form.
Instagram opens the profile only. Customers supply date/servings and reference
images in their conversation. Request precise home addresses only when needed,
privately.

The site must say **"Your order is confirmed only after we reply and agree the
details."** No fake checkout or "Order placed!" on link click. Final design,
availability, price, fulfilment and payment are confirmed directly with the baker.
Do not collect card details on the site.

## Hosting: change needed before launch

The specification names GitHub Pages, but its official usage limits say it is
not intended or allowed for running an online business or a site primarily
facilitating commercial transactions. A bakery order-enquiry site should not
assume that external WhatsApp links remove that restriction.

**Proposal, awaiting approval:** keep the source in this GitHub repository and
deploy static HTML/CSS/JS to an appropriate host such as Cloudflare Pages.
Its documented GitHub integration supports deployment from a connected
repository. Confirm current terms, plan limits and account settings before
choosing the host; no hosting account or deployment is being created now.

GitHub source control and GitHub Pages hosting are separate decisions.

References, checked 2026-10-04:

- [GitHub Pages usage limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Cloudflare Pages Git integration](https://developers.cloudflare.com/pages/get-started/git-integration/)

## Assets and implementation boundaries

Keep unedited uploads and export manifests under ignored `.local/instagram/`.
Keep the supplied mood references separate in `assets/references/kitchen/`.
Only reviewed, optimized derivatives belong in the future public site. The five
prototype screenshots/crop masters remain under `.local\photos\prototype-20261004\`;
existing prepared WebP/JPG variants are retained.

The sticker source directory contains 20 transparent WebP/PNG variants plus
manifest, mask and correction provenance. Local rembg 2.0.85 generates candidate
alpha masks (BiRefNet general-lite for four cakes, general for peacock); recorded
alpha corrections preserve the feather eye and remove cherry/doll background
fragments. Ordinary preparation uses saved masks and Pillow without a model or
network. No photographs are uploaded or missing details generated. Source-clipped
cherries, dress base and upper feather remain clipped. See
[sticker reproduction and limits](../assets/images/cake-stickers/README.md).

Implemented publishing boundary: a dedicated `site/` directory containing only
the public HTML, CSS, JavaScript, approved product data and web assets. Do not
deploy the repository root: it contains the design PDF and planning references,
which are not customer-facing assets.
The published build contains 66 allowlisted files, including 20 copies in
`site\assets\stickers\`. Full prepared JPGs remain available for "View larger photo".
Do not publish source-side `manifest.json`, `mask-recipe.json`, `masks\`, README
files, model caches or private review sheets. The previous site/review is retained
under `.local\revisions\before-stickers-20261004\`.

Keep business configuration separate from product data. Products should carry
stable IDs, genuine names/descriptions, approved images/alt text, confirmed
sizes/prices and a manually maintained enquiry/availability state. Repeated cake
photographs are a gallery, not automatically different products.

Use plain HTML/CSS and small progressive-enhancement scripts. Core content,
menu and contact links should remain usable without JavaScript. Do not fetch
the product catalogue solely client-side if that makes it disappear otherwise.
The implementation uses a Node-standard-library build step to render the gallery
from structured data into actual HTML; no framework or runtime fetch is needed.

Future image processing must preserve originals, remove sensitive EXIF/GPS from
web copies, create responsive widths without upscaling, and keep subjects/names
from being clipped in hero crops. Use explicit dimensions, suitable alt text,
WebP/AVIF with a fallback, and lazy loading below the fold. Avoid hotlinking
Instagram CDN URLs: they are not a durable image library.

Respect `prefers-reduced-motion`, visible keyboard focus, sufficient contrast
and readable type. No autoplay, loaders, aggressive parallax or essential content
hidden behind an animation. Social sharing gets a real approved cake image,
accurate bakery name and short description, never a placeholder business claim.

## Decisions needed, not assumptions

The user selected Whisk & Crumbs as the display name. Brand availability/legal
registration has not been checked. Public contact details, service area, products/prices,
lead times, dietary/allergen wording, delivery/pickup rules, payment/cancellation
policy, photo permissions, any further biography/portraits/reviews and final
hosting choice remain open. Restoring the original story and choosing sticker
background removal are approved scope changes, not approval of the finished
cutouts or website. Current local checks and parent visual review are complete;
[workstream 12](../TODO/12_WHISK_AND_CRUMBS_BRAND.todo) records the current rebrand,
25 passing Node cases, four branding cases, 66-file build and successful publication
at https://zanark.github.io/WhisksAndCrumbs/.
Workstream 09
retains the five passing sticker/source-fidelity cases.
Actual user visual acceptance, native app/device/assistive-technology acceptance
remain separate and open. The user explicitly requested publication after the
GitHub commercial-use warning; the hosting risk remains documented.
The [TODO catalogue](../TODO/00_INDEX.todo) tracks dependencies and release gates.
