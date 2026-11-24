import { createHash } from 'node:crypto';
import { copyFile, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { buildMessage, getContactLink } from '../web/contact.mjs';
import { cakePages, CAKE_WEIGHTS } from '../web/notebooks.mjs';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = path.join(root, 'web');
const photoRoot = path.join(root, 'assets', 'images', 'cakes');
const stickerRoot = path.join(root, 'assets', 'images', 'cake-stickers');
const versionedPublicSources = ['styles.css', 'entrance-shop.css', 'cozy-bakery.css', 'cream.css', 'readability.css', 'main.mjs', 'notebooks.mjs', 'entrance.mjs', 'bell.mjs', 'awning.mjs', 'awning-cloth.mjs', 'bakery-interior.mjs', 'bakery-view.mjs', 'bakery-scene.mjs', 'cream.mjs', 'cream-model.mjs', 'cream-material.mjs'];
const storefrontFiles = ['bakery-awning.svg', 'bakery-shelf.svg', 'bakery-paint-atlas.png', 'bakery-interior-wide.webp', 'bakery-interior-portrait.webp', 'bakery-interior-short.webp', 'bakery-sign-wood.webp', 'bakery-light-bake.bin', 'bakery-facade-upper.svg', 'bakery-facade-upper-mobile.svg', 'bakery-facade-ground.svg', 'bakery-facade-plaster.webp', 'bakery-awning-supports.svg', 'bakery-glass-etching.svg'];
const showcaseFiles = [
  '01-welcome.jpg', '02-bakery-entrance.jpg', '03-our-story.jpg',
  '04-cake-notebooks.jpg', '05-open-notebook.jpg', '06-simple-ordering.jpg',
];
const fontFiles = [
  'dm-sans-regular.ttf', 'dm-sans-semibold.ttf',
  'dm-serif-display-regular.ttf', 'dm-serif-display-italic.ttf',
  'DM-Sans-OFL.txt', 'DM-Serif-Display-OFL.txt',
  'dancing-script-variable.ttf', 'Dancing-Script-OFL.txt',
  'courgette-regular.ttf', 'Courgette-OFL.txt',
];

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

function validateVariants(photo, extensions, pattern, label) {
  if (!Array.isArray(photo?.variants)) throw new Error(`Missing ${label} variants.`);
  for (const extension of extensions) {
    const variants = photo.variants.filter(item => item.file?.endsWith(`.${extension}`));
    if (variants.length < 1 || new Set(variants.map(item => item.width)).size !== variants.length) {
      throw new Error(`Missing or duplicate responsive ${extension} variants: ${label}`);
    }
  }
  if (new Set(photo.variants.map(item => item.file)).size !== photo.variants.length) {
    throw new Error(`Duplicate prepared photo variant: ${label}`);
  }
  for (const variant of photo.variants) {
    if (!pattern.test(variant.file)
      || !Number.isInteger(variant.width) || variant.width <= 0
      || !Number.isInteger(variant.height) || variant.height <= 0
      || !/^[a-f0-9]{64}$/.test(variant.sha256)) {
      throw new Error(`Invalid prepared photo variant: ${label}`);
    }
  }
}

function validateStickerRevision(sticker) {
  if (sticker.revision !== undefined &&
      (typeof sticker.revision !== 'string' || !/^[a-z0-9][a-z0-9-]{0,79}$/.test(sticker.revision))) {
    throw new Error(`Invalid sticker revision: ${sticker.id}`);
  }
}

function validate(config, cakes, manifest, stickers) {
  for (const key of ['name', 'wordmark', 'descriptor', 'description', 'instagramHandle']) {
    if (typeof config[key] !== 'string' || !config[key].trim()) {
      throw new Error(`Missing business configuration: ${key}`);
    }
  }
  getContactLink(config);
  if (config.creamEffects !== undefined && typeof config.creamEffects !== 'boolean') {
    throw new Error('creamEffects must be a boolean.');
  }
  if (config.siteUrl) {
    const url = new URL(config.siteUrl);
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
      throw new Error('siteUrl must be an HTTPS base URL, without credentials, query or fragment.');
    }
  }
  if (config.publicEmail && !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(config.publicEmail)) {
    throw new Error('publicEmail must be an email address, not a link or placeholder.');
  }
  if (!Array.isArray(cakes) || cakes.length === 0 || !Array.isArray(manifest.photos)) {
    throw new Error('A nonempty cake gallery and photo manifest are required.');
  }
  if (!Array.isArray(stickers?.photos)) throw new Error('A reviewed sticker manifest is required.');
  const ids = new Set();
  for (const cake of cakes) {
    if (!/^[a-z0-9-]+$/.test(cake.id) || ids.has(cake.id)) {
      throw new Error(`Invalid or duplicate cake ID: ${cake.id}`);
    }
    ids.add(cake.id);
    for (const key of ['name', 'category']) {
      if (typeof cake[key] !== 'string' || !cake[key].trim()) {
        throw new Error(`Missing ${key} for cake ${cake.id}`);
      }
    }
    if (cake.name.length > 160 || cake.category.length > 40) throw new Error(`Cake label is too long: ${cake.id}`);
    const photo = manifest.photos.find(item => item.id === cake.id);
    if (!photo?.alt || !Array.isArray(photo.variants)) throw new Error(`Missing photo: ${cake.id}`);
    validateVariants(photo, ['webp', 'jpg'], /^[a-z0-9-]+\.(webp|jpg)$/, cake.id);
    const matches = stickers.photos.filter(item => item.id === cake.id);
    if (matches.length !== 1 ||
      (matches[0].source_photo_sha256 ?? matches[0].source_screenshot_sha256) !== photo.source_sha256) {
      throw new Error(`Missing, duplicate or mismatched sticker: ${cake.id}`);
    }
    validateVariants(matches[0], ['webp', 'png'], new RegExp(`^${cake.id}-sticker-\\d+\\.(webp|png)$`), cake.id);
    validateStickerRevision(matches[0]);
  }
  if (!ids.has('ribbon-and-pearl-cake')) throw new Error('The current hero recipe requires ribbon-and-pearl-cake.');
}

export function validateCoverStickers(stickers, cakes, manifest) {
  const covers = stickers.covers === undefined ? [] : stickers.covers;
  if (!Array.isArray(covers)) throw new Error('Reviewed cover stickers must be an array.');
  const ids = new Set(stickers.photos.map(photo => photo.id));
  const files = new Set(stickers.photos.flatMap(photo => photo.variants.map(variant => variant.file)));
  const hash = /^[a-f0-9]{64}$/;
  for (const cover of covers) {
    if (typeof cover?.id !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(cover.id) || ids.has(cover.id)) {
      throw new Error('Invalid or duplicate cover sticker ID.');
    }
    ids.add(cover.id);
    const photo = manifest.photos.find(item => item.id === cover.sourceCakeId);
    if (!cakes.some(cake => cake.id === cover.sourceCakeId) || !photo ||
        !hash.test(cover.source_photo_sha256) || cover.source_photo_sha256 !== photo.source_sha256) {
      throw new Error(`Unknown or mismatched cover sticker source: ${cover.id}`);
    }
    if (cover.owner_cutout_approval !== true || !hash.test(cover.recipe_sha256) || !hash.test(cover.approval_sha256)) {
      throw new Error(`Missing cover sticker approval or provenance: ${cover.id}`);
    }
    if (!Number.isInteger(cover.selected_items) || cover.selected_items < 1 ||
        !Array.isArray(cover.pieces) || cover.pieces.length !== cover.selected_items ||
        new Set(cover.pieces.map(piece => piece?.id)).size !== cover.pieces.length ||
        cover.pieces.some(piece => typeof piece?.id !== 'string' || !/^[a-z0-9-]+$/.test(piece.id) ||
          !hash.test(piece.approved_piece_sha256) || piece.source_cutout_changed !== false)) {
      throw new Error(`Invalid approved cover sticker pieces: ${cover.id}`);
    }
    validateVariants(cover, ['webp', 'png'], new RegExp(`^${cover.id}-(480|1000)\\.(webp|png)$`), cover.id);
    validateStickerRevision(cover);
    if (cover.variants.length !== 4) throw new Error(`A cover requires four responsive variants: ${cover.id}`);
    for (const variant of cover.variants) {
      const extension = path.extname(variant.file);
      const pair = cover.variants.find(item => item.width === variant.width && path.extname(item.file) !== extension);
      if (![480, 1000].includes(variant.width) || variant.file !== `${cover.id}-${variant.width}${extension}` ||
          !Number.isInteger(variant.bytes) || variant.bytes <= 0 || !pair || pair.height !== variant.height ||
          files.has(variant.file)) {
        throw new Error(`Invalid or colliding cover sticker variant: ${variant.file}`);
      }
      files.add(variant.file);
    }
  }
  return covers;
}

export function pictureMarkup(cake, manifest, stickers, {
  hero = false, decorative = false, sizes = '', coverStickerId,
} = {}) {
  const photo = manifest.photos.find(item => item.id === cake.id);
  let cutout = stickers.photos.find(item => item.id === cake.id);
  if (coverStickerId !== undefined) {
    if (!decorative || hero) throw new Error('Cover stickers are only for decorative notebook covers.');
    cutout = stickers.covers?.find(item => item.id === coverStickerId);
    if (!cutout || cutout.sourceCakeId !== cake.id) throw new Error('Unknown or mismatched notebook cover sticker.');
  }
  const variants = extension => cutout.variants
    .filter(item => item.file.endsWith(`.${extension}`)).sort((a, b) => a.width - b.width);
  const full = photo.variants.filter(item => item.file.endsWith('.jpg')).sort((a, b) => a.width - b.width).at(-1);
  const fallback = variants('png').at(-1);
  const stickerUrl = item => `assets/stickers/${item.file}${cutout.revision ? `?v=${item.sha256.slice(0, 12)}` : ''}`;
  const srcset = extension => variants(extension)
    .map(item => `${stickerUrl(item)} ${item.width}w`).join(', ');
  const sizeHint = sizes || '(max-width: 600px) calc(100vw - 90px), (max-width: 1100px) 42vw, 260px';
  const picture = `<picture>
      <source type="image/webp" srcset="${srcset('webp')}" sizes="${sizeHint}">
      <img src="${stickerUrl(fallback)}" srcset="${srcset('png')}" sizes="${sizeHint}" width="${fallback.width}" height="${fallback.height}" alt="${decorative ? '' : escapeHtml(photo.alt)}" ${hero ? 'fetchpriority="high" loading="eager"' : 'loading="lazy"'} decoding="async">
    </picture>`;
  if (decorative) return picture;
  return `<a class="photo-link" href="assets/images/${full.file}" data-photo data-photo-title="${escapeHtml(cake.name)}" data-photo-alt="${escapeHtml(photo.alt)}" aria-label="View a larger photo of ${escapeHtml(cake.name)}">
    ${picture}
  </a>`;
}

export function validateNotebooks(notebooks, cakes, covers = []) {
  const expected = ['birthday-cakes', 'tea-cakes', 'cream-cakes', 'decorated-cakes', 'doll-cakes', 'chocolates'];
  if (!Array.isArray(notebooks) || notebooks.length !== expected.length ||
      notebooks.some((book, index) => book.id !== expected[index])) {
    throw new Error('Configure all six category notebooks in their approved order.');
  }
  const assigned = new Set();
  for (const book of notebooks) {
    if (typeof book.name !== 'string' || !book.name.trim() || book.name.length > 40 || !Array.isArray(book.cakeIds)) {
      throw new Error(`Invalid notebook name or cake list: ${book.id}`);
    }
    for (const id of book.cakeIds) {
      if (assigned.has(id) || !cakes.some(cake => cake.id === id)) {
        throw new Error(`Unknown or duplicate notebook cake: ${id}`);
      }
      assigned.add(id);
    }
    if (book.cakeIds.length ? !book.cakeIds.includes(book.coverCakeId) : book.coverCakeId !== null) {
      throw new Error(`A notebook cover must use one of its verified cakes: ${book.id}`);
    }
    if (book.coverStickerId !== undefined &&
        (typeof book.coverStickerId !== 'string' || !book.cakeIds.length ||
         !covers.some(cover => cover.id === book.coverStickerId && cover.sourceCakeId === book.coverCakeId))) {
      throw new Error(`Unknown or mismatched notebook cover sticker: ${book.id}`);
    }
  }
  if (assigned.size !== cakes.length) throw new Error('Every reviewed cake must appear in exactly one notebook.');
}

function notebookDoodles(category) {
  const motifs = {
    'birthday-cakes': [
      ['birthday-balloons', 'M28 11c-18 0-18 29 0 29s18-29 0-29Zm23 8c-16 0-16 27 0 27s16-27 0-27Z',
        'M22 18c-4 3-5 8-4 12M46 26c-4 3-4 8-3 11M28 40l-3 5h6Zm23 6-3 5h6ZM28 45c-9 11 16 16 8 26m15-20c7 9-3 14-8 20'],
      ['birthday-gift', 'M14 31h52v37H14ZM10 23h60v10H10Zm30 0C13 22 19 5 30 12Zm0 0C67 22 61 5 50 12Z',
        'M35 23v45m10-45v45M14 44h21m10 0h21'],
    ],
    'tea-cakes': [
      ['teacup', 'M14 31h40v14c0 13-8 20-20 20S14 58 14 45V31Zm40 5h8c12 0 12 17 0 17H54',
        'M22 14c-6 5 6 7 0 12m13-14c-6 5 6 7 0 12m13-10c-5 4 5 6 0 10M10 69h53M21 38v8'],
      ['loaf-cake', 'M13 36c-3-17 11-26 24-20 11-8 29 1 29 17v26c0 5-4 8-9 8H21c-5 0-8-3-8-8Z',
        'M14 35c16-6 34-6 52-2M26 23c-1 4 1 7 5 9m12-10c-1 4 1 7 5 9M22 46v12m13-14v15m13-15v15m10-14v13'],
    ],
    'cream-cakes': [
      ['mixing-bowl', 'M12 35h49c-2 21-10 31-25 31S14 56 12 35ZM52 26l11-16c3-4 9 0 6 4L58 30Z',
        'M14 35c13-4 32-4 45 0M19 45c2 9 7 15 14 17M52 26c-12-4-25 14-15 20s24-9 21-16ZM38 44l16-17m-10 18 12-16M21 70h31'],
      ['cream-cake-slice', 'M14 31 57 17 68 33v30L14 68Z',
        'M14 31l35 10 19-8M49 41v25M15 47l34 10 18-8M15 56l34 10M31 28c-5-6 4-12 7-5 8-4 12 6 5 8'],
    ],
    'decorated-cakes': [
      ['piping-bag', 'M19 14 62 27 47 52 33 44Zm14 30 14 8-15 14-9-5Z',
        'M19 14l5 16 27 8M31 24l23 7M32 66l-6 6M20 66l-8 4'],
      ['birthday-candles', 'M15 37h10v29H15Zm20-10h10v39H35Zm20 12h10v27H55Z',
        'M20 17c-12 14 12 14 0 0Zm20-8c-12 14 12 14 0 0Zm20 11c-12 14 12 14 0 0ZM16 49l8-5m12-4 8-5m-8 19 8-5m12 5 8-5M12 70h56'],
    ],
    'doll-cakes': [
      ['doll-dress', 'M29 15l-12 8 7 14 7-4-12 31c12 7 30 7 42 0L49 33l7 4 7-14-12-8c-3 11-19 11-22 0Z',
        'M31 34h18M30 49l-3 12m14-19v22m9-15 4 13M37 35l4 6 4-6'],
      ['tiara', 'M15 57l-5-30 18 14 12-25 13 25 18-14-6 30Z',
        'M15 63h50M19 49h43M40 37l4 5-4 5-4-5Zm-15 5 2 2m28-2-2 2'],
    ],
    'chocolates': [
      ['chocolate-bar', 'M20 10h41v58H20Z',
        'M20 47l12-7 10 7 10-7 9 7M29 18h10v11H29Zm15 0h9v11h-9ZM29 33h10v8H29Zm15 0h9v7h-9ZM22 57l14 8'],
      ['wrapped-truffle', 'M24 26c10-6 22-4 27 5 3 6 1 14-4 18-7 6-19 5-23-2-4-6-5-15 0-21Zm-2 3-12-8 2 13-3 13 13-6Zm31 3 15-8-2 13 3 14-16-6Z',
        'M28 31c6-4 15-2 17 3m-18 8c5 5 13 5 17 0M13 33l8 2m36 3 8-1'],
    ],
  };
  if (!Object.hasOwn(motifs, category)) throw new Error(`Missing notebook cover motifs: ${category}`);
  return motifs[category].map(([name, outline, detail], index) => `<span class="notebook-doodle notebook-doodle-${index === 0 ? 'primary' : 'secondary'}" data-doodle="${name}" aria-hidden="true">
    <svg viewBox="0 0 80 80" width="80" height="80" fill="none" stroke-linecap="round" stroke-linejoin="round" focusable="false">
      <path d="${outline}" fill="#e8decd" stroke="#fffaf1" stroke-width="9"/>
      <path d="${detail}" stroke="#fffaf1" stroke-width="7"/>
      <path d="${outline}" stroke="currentColor" stroke-width="2.5"/>
      <path d="${detail}" stroke="currentColor" stroke-width="2.5"/>
    </svg>
  </span>`).join('\n');
}

export function renderSite(template, config, cakes, manifest, stickers, assetVersion = 'local', notebooks) {
  validate(config, cakes, manifest, stickers);
  const coverStickers = validateCoverStickers(stickers, cakes, manifest);
  validateNotebooks(notebooks, cakes, coverStickers);
  const contact = getContactLink(config, buildMessage());
  const hero = cakes.find(cake => cake.id === 'ribbon-and-pearl-cake');
  const cards = new Map(cakes.map(cake => {
    const photo = manifest.photos.find(item => item.id === cake.id);
    const full = photo.variants.filter(item => item.file.endsWith('.jpg')).sort((a, b) => b.width - a.width)[0];
    const orientation = full.height > full.width ? 'portrait' : 'landscape';
    return [cake.id, `<article class="cake-card" data-cake-id="${cake.id}" data-category="${escapeHtml(cake.category)}" data-orientation="${orientation}">
      <figure>${pictureMarkup(cake, manifest, stickers)}</figure>
      <div class="cake-card-info">
        <h4>${escapeHtml(cake.name)}</h4>
      </div>
    </article>`];
  }));
  const coverTabLayouts = {
    'birthday-cakes': [['blue', 20, 24, 44], ['butter', 38, 20, 40], ['lilac', 58, 26, 46], ['mint', 76, 22, 42]],
    'tea-cakes': [['pink', 24, 22, 42], ['mint', 46, 26, 48], ['butter', 70, 20, 40]],
    'cream-cakes': [['lilac', 18, 26, 46], ['blue', 34, 20, 40], ['pink', 50, 24, 44], ['butter', 66, 18, 38], ['mint', 82, 22, 42]],
    'decorated-cakes': [['mint', 22, 20, 40], ['pink', 42, 26, 48], ['blue', 62, 22, 42], ['lilac', 80, 24, 44]],
    'doll-cakes': [['butter', 20, 26, 44], ['lilac', 44, 22, 42], ['pink', 72, 24, 46]],
    chocolates: [['pink', 18, 20, 40], ['butter', 35, 24, 44], ['mint', 52, 18, 38], ['lilac', 68, 26, 48], ['blue', 83, 22, 42]],
  };
  const covers = notebooks.map(book => {
    const featured = cakes.find(cake => cake.id === book.coverCakeId);
    const artwork = featured
      ? pictureMarkup(featured, manifest, stickers, {
        decorative: true, sizes: '(max-width: 600px) 65vw, 280px', coverStickerId: book.coverStickerId,
      })
      : '<span class="notebook-cover-placeholder"><img src="assets/whisk-and-crumbs-mark.svg" width="110" height="110" alt=""></span>';
    return `<a class="notebook-cover notebook-page" href="#notebook-${book.id}" data-open-notebook="notebook-${book.id}" data-category="${book.id}">
      <span class="spiral-binding" aria-hidden="true"></span>
      <span class="notebook-cover-tabs" aria-hidden="true">${coverTabLayouts[book.id].map(([color, top, out, height]) =>
        `<span class="notebook-cover-tab" data-tab-color="${color}" style="--flag-top:${top}%;--flag-out:${out}px;--flag-height:${height}px"></span>`).join('')}</span>
      <h3>${escapeHtml(book.name)}</h3>
      <span class="notebook-cover-art" aria-hidden="true">${artwork}${notebookDoodles(book.id)}</span>
      <span class="notebook-cover-note">${featured ? `${book.cakeIds.length} ${book.cakeIds.length === 1 ? 'photo' : 'photos'}` : 'Photo preparation pending'}</span>
      <span class="notebook-cover-action">Open notebook <span aria-hidden="true">&#8599;</span></span>
    </a>`;
  }).join('\n');
  const notebookPages = notebooks.map(book => {
    const pages = cakePages(book.cakeIds);
    const pageCount = Math.max(1, pages.length);
    const photographs = pages.map((ids, index) => `<div class="notebook-sheet" data-notebook-page data-page-kind="photos">
      <div class="notebook-sheet-copy"><h4 id="${book.id}-photos-${index + 1}" data-page-title tabindex="-1">${escapeHtml(book.name)} &middot; ${index + 1}</h4></div>
      <div class="cake-grid">${ids.map(id => cards.get(id)).join('\n')}</div>
    </div>`).join('\n');
    const emptyPage = pages.length ? '' : `<div class="notebook-sheet" data-notebook-page data-page-kind="empty">
          <div class="notebook-sheet-copy">
            <h4 id="${book.id}-empty" data-page-title tabindex="-1">${escapeHtml(book.name)}</h4>
            <p class="notebook-empty-note">Selected photos are being prepared for this notebook.</p>
          </div>
        </div>`;
    return `<div class="category-notebook notebook-page" id="notebook-${book.id}" data-category="${book.id}" data-photo-count="${book.cakeIds.length}" aria-labelledby="notebook-title-${book.id}">
      <span class="spiral-binding" aria-hidden="true"></span>
      <div class="notebook-heading">
        <h3 id="notebook-title-${book.id}" tabindex="-1">${escapeHtml(book.name)}</h3>
        <a class="notebook-static-back" href="#cakes" aria-label="Back to cake categories">Back <span aria-hidden="true">&#8593;</span></a>
      </div>
      <div class="notebook-stage">
        ${[emptyPage, photographs].filter(Boolean).join('\n')}
        <div class="notebook-controls" hidden>
          <button data-page-previous type="button" aria-label="Previous page" title="Previous page"><span aria-hidden="true">&#8592;</span></button>
          <button data-page-next data-page-drag type="button" aria-label="Next page" title="Next page, or drag this tag upwards" hidden><span aria-hidden="true">&#8594;</span></button>
          <p class="notebook-page-status" data-page-counter aria-label="Page 1 of ${pageCount}">1 / ${pageCount}</p>
          <span class="visually-hidden" data-page-announcement role="status" aria-live="polite">Page 1 of ${pageCount}</span>
        </div>
      </div>
    </div>`;
  }).join('\n');
  const baseUrl = config.siteUrl ? `${config.siteUrl.replace(/\/+$/, '')}/` : '';
  const sharingMeta = baseUrl
    ? `<link rel="canonical" href="${escapeHtml(baseUrl)}">
       <meta property="og:url" content="${escapeHtml(baseUrl)}">
       <meta property="og:image" content="${escapeHtml(new URL('assets/whisk-and-crumbs-social-card.jpg', baseUrl).href)}">
       <meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
       <meta property="og:image:alt" content="${escapeHtml(`${config.name}: a home-baked cake with burgundy bows.`)}">`
    : '<meta name="robots" content="noindex, nofollow">';
  const replacements = {
    PAGE_TITLE: escapeHtml(`${config.name} - Baked at home. Made with heart.`),
    DESCRIPTION: escapeHtml(config.description),
    NAME: escapeHtml(config.name),
    WORDMARK: escapeHtml(config.wordmark),
    DESCRIPTOR: escapeHtml(config.descriptor),
    INSTAGRAM_HANDLE: escapeHtml(config.instagramHandle),
    INSTAGRAM_URL: escapeHtml(config.instagramUrl),
    CONTACT_URL: escapeHtml(contact.href),
    CONTACT_LABEL: escapeHtml(contact.label),
    CONTACT_BUTTON_CLASS: contact.channel === 'instagram' ? 'instagram-contact' : '',
    CONTACT_LOGO: contact.channel === 'instagram'
      ? `<svg class="instagram-logo" viewBox="0 0 24 24" width="128" height="128" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true" focusable="false">
          <rect x="2.5" y="2.5" width="19" height="19" rx="5.5"/>
          <circle cx="12" cy="12" r="4.5"/>
          <circle cx="17.8" cy="6.2" r="1.1" fill="currentColor" stroke="none"/>
        </svg>`
      : '',
    DIRECT_CONTACT_HELP: contact.channel === 'whatsapp'
      ? 'Opens WhatsApp. Review your message, then send.'
      : 'Tap Message on Instagram. Login may be required.',
    SHARING_META: sharingMeta,
    ASSET_VERSION: escapeHtml(assetVersion),
    CREAM_ATTRIBUTE: config.creamEffects ? ' data-cream-effects="enabled"' : '',
    CREAM_STYLES: config.creamEffects ? `<link rel="stylesheet" href="cream.css?v=${escapeHtml(assetVersion)}">` : '',
    CREAM_PANE: config.creamEffects ? `<span class="cream-glass" aria-hidden="true" style="--cream-etching-image:url('assets/bakery-glass-etching.svg?v=${escapeHtml(assetVersion)}')"><span class="cream-etching"></span></span>` : '',
    CREAM_EFFECTS: config.creamEffects ? `<div id="cream-effects" aria-hidden="true" hidden>
    <canvas id="cream-material"></canvas>
  </div>
  <canvas id="cream-cursor" aria-hidden="true" hidden></canvas>` : '',
    CREAM_CONTROL: config.creamEffects ? '<div id="cream-motion-control" hidden><button id="cream-motion-toggle" type="button" aria-pressed="false">Pause cream motion</button><span id="cream-motion-help" class="visually-hidden">Alt+Shift+P pauses or resumes background cream motion when available.</span></div>' : '',
    CREAM_SHORTCUT_HELP: config.creamEffects ? ' Alt+Shift+P pauses or resumes background cream motion when available.' : '',
    CREAM_PHOTO_DESCRIPTION: config.creamEffects ? ' aria-describedby="cream-motion-help"' : '',
    YEAR: new Date().getFullYear(),
    HERO_IMAGE: pictureMarkup(hero, manifest, stickers, {
      hero: true, sizes: '(max-width: 600px) calc(100vw - 78px), (max-width: 900px) 43vw, 460px',
    }),
    CAKE_WEIGHT_ITEMS: CAKE_WEIGHTS.map(weight => `<li>${escapeHtml(weight.label)}</li>`).join('\n'),
    CATEGORY_COVERS: covers,
    CATEGORY_NOTEBOOKS: notebookPages,
    BUSINESS_DETAILS: [
      config.location ? `<p>${escapeHtml(config.location)}</p>` : '',
      config.publicEmail ? `<a class="text-link" href="mailto:${escapeHtml(config.publicEmail)}">${escapeHtml(config.publicEmail)}</a>` : '',
    ].join('\n'),
  };
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (_, token) => {
    if (!(token in replacements)) throw new Error(`Unknown template token: ${token}`);
    return replacements[token];
  });
}

async function existingFiles(directory, prefix = '') {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
  const result = [];
  for (const entry of entries) {
    if (entry.isSymbolicLink()) throw new Error(`Output contains a symbolic link: ${entry.name}`);
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) result.push(...await existingFiles(path.join(directory, entry.name), relative));
    else result.push(relative);
  }
  return result;
}

export async function buildSite(output = path.join(root, 'site')) {
  output = path.resolve(output);
  const [template, config, cakes, manifest, stickers, notebooks] = await Promise.all([
    readFile(path.join(web, 'index.template.html'), 'utf8'),
    readFile(path.join(root, 'content', 'site.json'), 'utf8').then(JSON.parse),
    readFile(path.join(root, 'content', 'cakes.json'), 'utf8').then(JSON.parse),
    readFile(path.join(photoRoot, 'manifest.json'), 'utf8').then(JSON.parse),
    readFile(path.join(stickerRoot, 'manifest.json'), 'utf8').then(JSON.parse),
    readFile(path.join(root, 'content', 'notebooks.json'), 'utf8').then(JSON.parse),
  ]);
  const assetVersionHash = createHash('sha256');
  for (const file of versionedPublicSources) {
    assetVersionHash.update(await readFile(path.join(web, file)));
  }
  for (const file of storefrontFiles) {
    assetVersionHash.update(await readFile(path.join(web, 'assets', file)));
  }
  const assetVersion = assetVersionHash.digest('hex').slice(0, 12);
  const html = renderSite(template, config, cakes, manifest, stickers, assetVersion, notebooks);
  const copies = [
    ['styles.css', path.join(web, 'styles.css')],
    ['entrance-shop.css', path.join(web, 'entrance-shop.css')],
    ['cozy-bakery.css', path.join(web, 'cozy-bakery.css')],
    ['cream.css', path.join(web, 'cream.css')],
    ['cream.mjs', path.join(web, 'cream.mjs')],
    ['cream-model.mjs', path.join(web, 'cream-model.mjs')],
    ['cream-material.mjs', path.join(web, 'cream-material.mjs')],
    ['readability.css', path.join(web, 'readability.css')],
    ['main.mjs', path.join(web, 'main.mjs')],
    ['notebooks.mjs', path.join(web, 'notebooks.mjs')],
    ['entrance.mjs', path.join(web, 'entrance.mjs')],
    ['bell.mjs', path.join(web, 'bell.mjs')],
    ['awning.mjs', path.join(web, 'awning.mjs')],
    ['awning-cloth.mjs', path.join(web, 'awning-cloth.mjs')],
    ['bakery-interior.mjs', path.join(web, 'bakery-interior.mjs')],
    ['bakery-view.mjs', path.join(web, 'bakery-view.mjs')],
    ['bakery-scene.mjs', path.join(web, 'bakery-scene.mjs')],
    ['contact.mjs', path.join(web, 'contact.mjs')],
    ['assets/whisk-and-crumbs-mark.svg', path.join(web, 'assets', 'whisk-and-crumbs-mark.svg')],
    ['assets/whisk-and-crumbs-logo.png', path.join(web, 'assets', 'whisk-and-crumbs-logo.png')],
    ['assets/favicon.svg', path.join(web, 'assets', 'favicon.svg')],
    ['assets/favicon-16.png', path.join(web, 'assets', 'favicon-16.png')],
    ['assets/favicon-32.png', path.join(web, 'assets', 'favicon-32.png')],
    ['assets/favicon.ico', path.join(web, 'assets', 'favicon.ico')],
    ['assets/apple-touch-icon.png', path.join(web, 'assets', 'apple-touch-icon.png')],
    ['assets/bakery-pattern-cream.svg', path.join(web, 'assets', 'bakery-pattern-cream.svg')],
    ['assets/bakery-pattern-green.svg', path.join(web, 'assets', 'bakery-pattern-green.svg')],
    ['assets/bakery-doodles.svg', path.join(web, 'assets', 'bakery-doodles.svg')],
    ['assets/whisk-and-crumbs-social-card.jpg', path.join(web, 'assets', 'whisk-and-crumbs-social-card.jpg')],
    ...storefrontFiles.map(file => [`assets/${file}`, path.join(web, 'assets', file)]),
    ...fontFiles.map(file => [`assets/fonts/${file}`, path.join(web, 'assets', 'fonts', file)]),
    ...showcaseFiles.map(file => [`assets/showcase/${file}`, path.join(web, 'assets', 'showcase', file)]),
  ];
  for (const cake of cakes) {
    for (const [collection, folder, prefix] of [
      [manifest, photoRoot, 'assets/images'],
      [stickers, stickerRoot, 'assets/stickers'],
    ]) {
      for (const variant of collection.photos.find(photo => photo.id === cake.id).variants) {
        const source = path.join(folder, variant.file);
        const digest = createHash('sha256').update(await readFile(source)).digest('hex');
        if (digest !== variant.sha256) throw new Error(`Prepared photo changed: ${variant.file}`);
        copies.push([`${prefix}/${variant.file}`, source]);
      }
    }
  }
  for (const id of new Set(notebooks.map(book => book.coverStickerId).filter(id => id !== undefined))) {
    for (const variant of stickers.covers.find(cover => cover.id === id).variants) {
      const source = path.join(stickerRoot, variant.file);
      const data = await readFile(source);
      if (data.length !== variant.bytes || createHash('sha256').update(data).digest('hex') !== variant.sha256) {
        throw new Error(`Prepared cover sticker changed: ${variant.file}`);
      }
      copies.push([`assets/stickers/${variant.file}`, source]);
    }
  }
  const publicFiles = new Set(['index.html', ...copies.map(([name]) => name)]);
  for (const file of await existingFiles(output)) {
    if (!publicFiles.has(file)) {
      throw new Error(`Unexpected file in public output: ${file}. Use a clean output folder; it was not deleted.`);
    }
  }
  // Read every source before writing, so missing assets cannot publish a partial build.
  for (const [, source] of copies) await readFile(source);
  await mkdir(output, { recursive: true });
  await writeFile(path.join(output, 'index.html'), html, 'utf8');
  for (const [relative, source] of copies) {
    const destination = path.join(output, relative);
    await mkdir(path.dirname(destination), { recursive: true });
    await copyFile(source, destination);
  }
  return { output, files: [...publicFiles].sort(), assetVersion };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const { values } = parseArgs({ options: { out: { type: 'string' } } });
  const result = await buildSite(values.out);
  console.log(`Built ${result.files.length} public files in ${result.output}`);
}
