import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { buildSite, renderSite, root, escapeHtml, validateNotebooks } from '../scripts/build-site.mjs';
import { buildMessage, getContactLink } from '../web/contact.mjs';

const template = await readFile(path.join(root, 'web', 'index.template.html'), 'utf8');
const config = JSON.parse(await readFile(path.join(root, 'content', 'site.json'), 'utf8'));
const cakes = JSON.parse(await readFile(path.join(root, 'content', 'cakes.json'), 'utf8'));
const photos = JSON.parse(await readFile(path.join(root, 'assets', 'images', 'cakes', 'manifest.json'), 'utf8'));
const stickers = JSON.parse(await readFile(path.join(root, 'assets', 'images', 'cake-stickers', 'manifest.json'), 'utf8'));
const notebooks = JSON.parse(await readFile(path.join(root, 'content', 'notebooks.json'), 'utf8'));
const render = (settings = config, gallery = cakes, assets = photos, cutouts = stickers, assetVersion = 'local', books = notebooks) =>
  renderSite(template, settings, gallery, assets, cutouts, assetVersion, books);

test('the restored story follows the landing, with cakes and ordering kept simple', () => {
  const html = render();
  assert.match(html, /class="hero-section" id="home"/);
  assert.match(html, /class="hero container"/);
  assert.match(html, /class="cake-section container section-space"/);
  assert.match(html, /class="category-notebooks" id="category-notebooks"/);
  assert.deepEqual([...html.matchAll(/<section\b[^>]*id="([^"]+)"/g)].map(match => match[1]), ['home', 'story', 'cakes', 'order']);
  assert.match(html, /OUR LITTLE STORY/);
  assert.match(html, /Behind these cakes is a mum who loves to bake\./);
  assert.match(html, /A little care<br>in every layer\./);
  assert.match(html, /That's the homemade bit\./);
  assert.equal((html.match(/class="cake-card"/g) || []).length, cakes.length);
  assert.equal((html.match(/data-photo data-photo-title=/g) || []).length, cakes.length + 1);
  assert.match(html, /Ribbon &amp; pearl cake/);
  assert.doesNotMatch(html, /cake-card-actions|cake-enquire|data-enlarge-photo/);
  assert.doesNotMatch(html, /\{\{[A-Z_]+\}\}/);
  assert.doesNotMatch(html, /<(form|textarea|select|details)\b|id="(custom|enquire|how-to-order|nav-toggle)"/);
  assert.doesNotMatch(html, /<(input|fieldset|legend)\b/);
  assert.match(html, /id="order-contact"/);
});

test('visual categories account for every supplied cake without guessing flavours', () => {
  const categories = Object.fromEntries(cakes.map(cake => [cake.id, cake.category]));
  const originalCategories = {
    'cherry-topped-cake': 'Classic cakes',
    'ribbon-and-pearl-cake': 'Decorated cakes',
    'butterfly-celebration-cake': 'Decorated cakes',
    'pink-doll-cake': 'Theme cakes',
    'peacock-feather-cake': 'Theme cakes',
    'rainbow-butterfly-cake': 'Decorated cakes',
    'purple-birthday-cake': 'Decorated cakes',
    'golden-drip-cake': 'Classic cakes',
    'cherry-curl-cake': 'Cream cakes',
    'pink-swirl-cake': 'Decorated cakes',
    'rose-topped-cake': 'Decorated cakes',
    'lavender-swirl-cake': 'Decorated cakes',
    'pastel-celebration-cake': 'Birthday Cakes',
    'round-and-heart-tea-cakes': 'Tea cakes',
    'assorted-moulded-chocolates': 'Chocolates',
  };
  assert.deepEqual(Object.fromEntries(Object.keys(originalCategories).map(id => [id, categories[id]])), originalCategories);
  const notebookNames = Object.fromEntries(notebooks.map(book => [book.id, book.name]));
  for (const cake of cakes.filter(item => item.id.startsWith('archive-'))) {
    const book = notebooks.find(item => item.cakeIds.includes(cake.id));
    assert.equal(cake.category, notebookNames[book.id]);
  }
  assert.equal((render().match(/data-category="(?:Classic cakes|Cream cakes|Decorated cakes|Theme cakes|Birthday Cakes|Tea cakes|Doll cakes|Chocolates)"/g) || []).length, cakes.length);
  assert.ok(cakes.every(cake => !('flavour' in cake)));
});

test('the approved brand is consistent in the header, footer and sharing metadata', () => {
  assert.equal(config.name, 'Whisk & Crumbs');
  assert.equal(config.wordmark, 'Whisk & Crumbs');
  assert.equal(config.descriptor, 'Home-baked vegetarian cakes');
  assert.ok(config.description.includes(config.name));
  assert.equal(config.siteUrl, 'https://zanark.github.io/WhiskAndCrumbs/');
  const html = render();
  const header = html.match(/<header\b[\s\S]*?<\/header>/)[0];
  const footer = html.match(/<footer\b[\s\S]*?<\/footer>/)[0];
  const title = 'Whisk &amp; Crumbs - Baked at home. Made with heart.';
  assert.ok(html.includes(`<title>${title}</title>`));
  assert.ok(html.includes(`<meta property="og:title" content="${title}">`));
  assert.ok(html.includes(`<meta property="og:site_name" content="Whisk &amp; Crumbs">`));
  assert.ok(html.includes(`<meta name="description" content="${escapeHtml(config.description)}">`));
  assert.ok(html.includes(`<meta property="og:description" content="${escapeHtml(config.description)}">`));
  assert.match(html, /property="og:image" content="https:\/\/zanark\.github\.io\/WhiskAndCrumbs\/assets\/whisk-and-crumbs-social-card\.jpg"/);
  assert.doesNotMatch(html, /WhisksAndCrumbs|WhiskAndCrubms/);
  assert.match(html, /property="og:image:alt" content="Whisk &amp; Crumbs: a home-baked cake with burgundy bows\."/);
  assert.match(header, /class="brand" href="#home" aria-label="Whisk &amp; Crumbs - home"/);
  assert.match(header, /<img src="assets\/whisk-and-crumbs-mark\.svg" width="128" height="128" alt="">/);
  assert.match(header, /class="wordmark">Whisk &amp; Crumbs<\/span>/);
  assert.match(header, /class="brand-descriptor">Home-baked vegetarian cakes<\/span>/);
  assert.match(footer, /&copy; <span id="year">\d{4}<\/span> Whisk &amp; Crumbs/);
  assert.doesNotMatch(html, /Homemade Veg Cakes|Whisk & Crumbs/);
  assert.doesNotMatch(html, /\bwhisks(?:\s|&|-|_)/i);
});

test('browser and touch icons use relative URLs with explicit formats and sizes', () => {
  const html = render();
  for (const [file, type, sizes] of [
    ['favicon.ico', 'image/x-icon', '16x16 32x32 48x48'],
    ['favicon-16.png', 'image/png', '16x16'],
    ['favicon-32.png', 'image/png', '32x32'],
    ['favicon.svg', 'image/svg+xml', 'any'],
  ]) {
    assert.ok(html.includes(`<link rel="icon" href="assets/${file}" type="${type}" sizes="${sizes}">`), file);
  }
  assert.ok(html.includes('<link rel="apple-touch-icon" href="assets/apple-touch-icon.png" sizes="180x180">'));
  assert.doesNotMatch(html, /assets\/(?:cake-mark\.svg|social-card\.jpg)/);
});

test('the click-to-enter doorway is decorative, skippable and has a native escape', () => {
  const html = render();
  assert.match(html, /id="bakery-entrance" class="bakery-entrance"/);
  assert.match(html, /class="entrance-art" aria-hidden="true"/);
  assert.match(html, /id="entrance-enter" class="entrance-enter" href="#home" aria-label="Open the bakery doors and enter"/);
  assert.match(html, /Click anywhere to enter/);
  assert.match(html, /id="entrance-skip" class="entrance-skip" href="#home">Skip entrance/);
  assert.match(html, /<noscript><style>\.bakery-entrance \{ display: none !important; \}<\/style><\/noscript>/);
  assert.match(html, /class="entrance-door entrance-door-left"/);
  assert.match(html, /class="entrance-door entrance-door-right"/);
  assert.match(html, /class="entrance-bell"/);
  assert.doesNotMatch(html, /<audio|autoplay|aria-modal="true"|<main[^>]+inert/);
});

test('the open sign hangs inside the door below its glass reflection', async () => {
  const html = render();
  const door = html.match(/class="entrance-door entrance-door-right"[\s\S]*?class="entrance-door-panel"/)[0];
  assert.equal((html.match(/class="entrance-open-sign"/g) || []).length, 1);
  assert.match(door, /class="entrance-glass"[\s\S]*class="entrance-open-sign"/);
  assert.match(door, /class="open-sign-greeting">We are<\/span>\s*<strong>OPEN<\/strong>/);
  assert.match(door, /class="open-sign-cord"[^>]*focusable="false"/);
  assert.doesNotMatch(door, /<(?:a|button)\b|tabindex=|onclick=/);
  const css = await readFile(path.join(root, 'web', 'entrance-shop.css'), 'utf8');
  assert.match(css, /\.entrance-open-sign \{[^}]*z-index: 1;[^}]*pointer-events: none/);
  assert.match(css, /\.entrance-glass::after \{[^}]*z-index: 2;[^}]*linear-gradient[^}]*pointer-events: none/);
  assert.match(css, /\.entrance-glass \{[^}]*isolation: isolate;[^}]*background-image: none/);
  assert.doesNotMatch(css.match(/\.entrance-open-sign \{[^}]*\}/)[0], /animation:|--look-/);
});

test('versioned styles, modules and storefront artwork prevent mixed cached releases', () => {
  const html = render(config, cakes, photos, stickers, 'release123');
  for (const file of ['styles.css', 'entrance-shop.css', 'cozy-bakery.css', 'readability.css', 'entrance.mjs', 'bell.mjs', 'notebooks.mjs', 'main.mjs']) {
    assert.ok(html.includes(`${file}?v=release123`), file);
  }
  for (const file of ['bakery-awning.svg', 'bakery-interior-wide.webp', 'bakery-interior-portrait.webp', 'bakery-interior-short.webp', 'bakery-shelf.svg']) {
    assert.ok(html.includes(`assets/${file}?v=release123`), file);
    assert.ok(!html.includes(`src="assets/${file}"`), file);
  }
});

test('the larger illuminated wooden sign keeps the original wordmark and navigation below it', async () => {
  const html = render();
  const header = html.match(/<header\b[\s\S]*?<\/header>/)[0];
  assert.match(header, /class="shop-sign"[\s\S]*class="brand"/);
  assert.ok(header.indexOf('id="site-nav"') > header.indexOf('class="brand-descriptor"'));
  assert.match(header, /<nav id="site-nav" class="container" aria-label="Main navigation">/);
  const css = await readFile(path.join(root, 'web', 'cozy-bakery.css'), 'utf8');
  assert.match(css, /\.shop-sign \{[^}]*background-color: #62432f/);
  assert.match(css, /\.shop-sign \.wordmark \{[^}]*font-size: 5\.5rem/);
  assert.match(css, /\.shop-sign \.wordmark \{[^}]*text-shadow:/);
  assert.match(header, /--sign-wood:url\('assets\/bakery-sign-wood\.webp\?v=local'\)/);
  assert.match(css, /\.shop-sign::before \{[^}]*background: var\(--sign-wood\) center \/ cover no-repeat/);
  assert.doesNotMatch(css.match(/\.shop-sign::before \{[^}]*\}/)[0], /mask-image|opacity:|linear-gradient/);
  assert.match(css, /7px 10px 5px rgb\(14 8 3 \/ 82%\)/);
  assert.match(css, /10px 15px 10px rgb\(15 9 4 \/ 72%\)/);
  assert.match(css, /\.shop-sign \.header-inner \{[^}]*justify-content: center/);
  assert.match(css, /\.shop-sign \.brand > img \{[^}]*width: 128px/);
  assert.doesNotMatch(css.match(/\.shop-sign \.wordmark \{[^}]*\}/)[0], /font-family:/);
  assert.doesNotMatch(css, /@keyframes|animation:|transition:.*shadow/);
});

test('navigation shares the wooden board and the ordering action is a raised wooden button', async () => {
  const header = render().match(/<header\b[\s\S]*?<\/header>/)[0];
  assert.match(header, /<nav id="site-nav"[\s\S]*?<\/nav>\s*<\/div>\s*<\/header>/);
  const css = await readFile(path.join(root, 'web', 'cozy-bakery.css'), 'utf8');
  assert.match(css, /\.site-header #site-nav > a \{[^}]*color: var\(--cream\);[^}]*font-size: 1\.125rem;[^}]*text-shadow:/);
  assert.match(css, /\.site-header #site-nav \.nav-cta \{[^}]*background: #62432f var\(--sign-wood\)[^}]*box-shadow:/);
  assert.match(css, /\.site-header #site-nav > a:focus-visible \{[^}]*outline-color: var\(--paper\)/);
  assert.match(css, /\.site-header #site-nav \.nav-cta \{[^}]*background: ButtonFace/);
});

test('the architectural entrance joins its roof, fascia, glazing and grounded threshold', () => {
  const html = render();
  for (const name of ['entrance-masonry', 'entrance-upper-storey', 'entrance-cornice',
    'entrance-threshold', 'entrance-step', 'entrance-pavement']) {
    assert.ok(html.includes(`class="${name}"`), name);
  }
  assert.equal((html.match(/class="entrance-room"/g) || []).length, 1);
  assert.equal((html.match(/class="entrance-fixed-bay /g) || []).length, 2);
  assert.match(html, /class="entrance-wordmark">Whisk &amp; Crumbs<\/span>/);
  assert.match(html, /class="entrance-descriptor">Home-baked vegetarian cakes<\/span>/);
  for (const name of ['bakery-facade-upper.svg', 'bakery-facade-upper-mobile.svg',
    'bakery-facade-ground.svg', 'bakery-facade-plaster.webp']) {
    assert.ok(html.includes(`assets/${name}?v=local`), name);
  }
});

test('fabric motion enhances only the decorative page awning and the scallop edge has no inset seam', async () => {
  const main = await readFile(path.join(root, 'web', 'main.mjs'), 'utf8');
  const runtime = await readFile(path.join(root, 'web', 'awning.mjs'), 'utf8');
  const css = await readFile(path.join(root, 'web', 'entrance-shop.css'), 'utf8');
  const cozy = await readFile(path.join(root, 'web', 'cozy-bakery.css'), 'utf8');
  assert.match(main, /import\(versionedModule\('\.\/awning\.mjs'\)\)/);
  assert.match(main, /import\(versionedModule\('\.\/awning-cloth\.mjs'\)\)/);
  assert.match(runtime, /querySelector\('\.site-awning'\)/);
  assert.match(runtime, /precision highp float/);
  assert.match(runtime, /UNPACK_PREMULTIPLY_ALPHA_WEBGL, true/);
  assert.match(runtime, /min\(fabric\.rgb \* v_shade, vec3\(fabric\.a\)\)/);
  assert.match(runtime, /canvas\.setAttribute\('aria-hidden', 'true'\)/);
  assert.match(runtime, /prefers-reduced-motion: reduce/);
  assert.match(runtime, /forced-colors: active/);
  assert.match(runtime, /webglcontextlost/);
  assert.match(runtime, /cancelAnimationFrame/);
  assert.match(runtime, /passive: true/);
  assert.doesNotMatch(runtime, /setInterval|AudioContext|cream\.mjs/);
  assert.match(css, /\.awning-fabric \{[^}]*pointer-events: none/);
  assert.equal((render().match(/class="awning-supports"/g) || []).length, 2);
  assert.match(css, /\.awning-supports \{[^}]*position: absolute;[^}]*pointer-events: none/);
  assert.match(render(), /bakery-awning-supports\.svg\?v=local/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\), \(forced-colors: active\)/);
  assert.match(cozy, /\.story-section \{ box-shadow: none; \}/);
  assert.doesNotMatch(cozy, /\.story-section \{[^}]*inset/);
});

test('cozy bakery decoration is progressive, static and separate from reading and notebook surfaces', async () => {
  const html = render();
  assert.ok(html.indexOf('href="cozy-bakery.css') < html.indexOf('href="readability.css'));
  assert.doesNotMatch(html, /hero-window|bakery-window\.svg/);
  assert.match(html, /class="bakery-shelf" aria-hidden="true"/);
  assert.ok(html.indexOf('class="bakery-shelf"') > html.indexOf('id="order-contact-help"'));
  assert.ok(html.indexOf('class="bakery-shelf"') < html.indexOf('<footer'));
  const base = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(base, /\.bakery-shelf \{ display: none; \}/);
  const cozy = await readFile(path.join(root, 'web', 'cozy-bakery.css'), 'utf8');
  assert.doesNotMatch(cozy, /hero-window|bakery-window|\.hero-photo\s*\{[^}]*padding/);
  assert.match(cozy, /\.bakery-shelf img \{[^}]*object-fit: contain/);
  assert.match(cozy, /@media \(forced-colors: active\)/);
  assert.match(cozy, /@media print/);
  assert.doesNotMatch(cozy, /@keyframes|animation:|backdrop-filter:|overflow:\s*hidden/);
  assert.doesNotMatch(cozy, /--cream:|--green:|--cover-paper:|\.notebook-sheet\s*\{|\.is-open-notebook/);
});

test('category cookbook surfaces bind at the top and reading text stays pattern-free', async () => {
  const html = render();
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.equal((html.match(/class="spiral-binding" aria-hidden="true"/g) || []).length, 12);
  assert.match(css, /\.notebook-page \{[\s\S]*repeating-linear-gradient/);
  assert.match(css, /\.notebook-page \{[\s\S]*background-color: var\(--cream\)/);
  assert.match(css, /\.spiral-binding \{[\s\S]*repeat-x/);
  assert.match(css, /%3Crect x='9' y='28' width='16' height='8'/);
  assert.match(css, /M11\.5 31V14\.5C11\.5 5\.5 22\.5 5\.5 22\.5 14\.5V31/);
  assert.match(css, /\.hero-copy::before, \.section-heading::before, \.cake-card-info::before \{[\s\S]*background: var\(--cream\)/);
  assert.match(css, /\.story-copy::before, \.order-layout > div::before, \.order-action::before \{[\s\S]*background: var\(--green\)/);
  assert.match(css, /body \{[^}]*bakery-pattern-cream\.svg/);
  assert.match(css, /\.story-section, \.order-section \{[^}]*bakery-pattern-green\.svg/);
});

test('the unframed hero retains the original cream, green and terracotta colours', async () => {
  const html = render();
  const hero = html.match(/<section class="hero-section" id="home"[\s\S]*?<\/section>/)[0];
  assert.doesNotMatch(hero, /notebook-page|spiral-binding|page-corner/);
  assert.match(hero, /Baked at home\.<br>Made with <em>heart\.<\/em>/);
  assert.match(hero, /class="hero-photo"/);
  assert.match(hero, /href="#cakes">View cakes/);
  assert.match(hero, /href="#order">How to order/);
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(css, /\.hero-section \{[^}]*background-color: var\(--cream\); color: var\(--green\)/);
  assert.match(css, /\.hero-section \{[^}]*bakery-pattern-cream\.svg/);
  assert.match(css, /\.hero-description \{[^}]*color: var\(--muted\)/);
  assert.match(css, /em \{ color: var\(--accent\)/);
  assert.doesNotMatch(css, /\.hero-actions \.button(?:-outline)?(?::hover)? \{[^}]*\b(?:background|color|border-color):|\.hero-copy em,|\.hero-photo \.photo-link::after \{|\.hero-section :focus-visible/);
  const main = await readFile(path.join(root, 'web', 'main.mjs'), 'utf8');
  assert.doesNotMatch(main, /initNotebookPages|page-tilt|hero\.notebook-page/);
});

test('category notepads use thin paper stacks and paired top wires rather than a left spine', async () => {
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const paper = css.match(/\.notebook-cover\.notebook-page, \.category-notebook\.notebook-page \{([^}]+)\}/)[1];
  assert.match(paper, /border-radius: 2px/);
  assert.doesNotMatch(paper, /inset/);
  assert.match(paper, /0 11px 0 2px var\(--green\)/);
  assert.match(css, /\.notebook-cover\.notebook-page \{[^}]*background-image: none; \}/);
  assert.match(css, /\.notebook-cover\.notebook-page::after, \.category-notebook\.notebook-page::after \{ content: none; \}/);
  const binding = css.match(/\.notebook-cover > \.spiral-binding, \.category-notebook > \.spiral-binding \{([^}]+)\}/)[1];
  assert.match(binding, /background-repeat: space no-repeat/);
  assert.match(binding, /background-size: 30px 40px/);
  assert.match(binding, /%3Crect x='7' y='27' width='17' height='10'/);
  assert.match(binding, /M12 32C5 32 5 3 12 3s7 29 0 29Z/);
  assert.match(binding, /M17 32C10 32 10 3 17 3s7 29 0 29Z/);
  assert.doesNotMatch(binding, /%3Cimage|dreamstime|copilot-image/i);
});

test('paler pink covers change without recolouring cream interiors or the weight-note accents', async () => {
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const halfWhitePink = [247, 219, 228].map(channel => Math.round((channel + 255) / 2));
  assert.deepEqual(halfWhitePink, [251, 237, 242]);
  assert.match(css, /--cover-paper: #fbedf2;/);
  assert.match(css, /--weight-note-accent: #f7dbe4;/);
  assert.match(css, /--cream: #f5ebdd;/);
  assert.match(css, /\.notebook-cover\.notebook-page \{[^}]*background-color: var\(--cover-paper\)/);
  const pinkRules = [...css.matchAll(/([^{}]+)\{[^{}]*var\(--cover-paper\)[^{}]*\}/g)]
    .map(match => match[1].trim());
  assert.deepEqual(pinkRules.sort(), [
    '.notebook-cover.notebook-page',
  ].sort());
  assert.match(css, /\.notebook-cover h3 \{[^}]*background: transparent/);
  assert.match(css, /\.notebook-cover-note \{[^}]*background: transparent[^}]*color: var\(--green\)/);
  assert.match(css, /\.notebook-page \{[^}]*background-color: var\(--cream\)/);
  assert.match(css, /\.notebook-sheet \{[^}]*var\(--cream\)/);
  assert.match(css, /\.cake-weight-values li::before \{[^}]*background: var\(--weight-note-accent\)/);
});

test('catalogue photos open directly and page arrows remain opaque right-edge book tags', async () => {
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const tabs = css.slice(css.indexOf('/* Index flags overlap'), css.indexOf('.photo-dialog[open]'));
  for (const color of ['--tab-pink: 238 180 198', '--tab-butter: 237 215 148',
    '--tab-blue: 182 210 229', '--tab-lilac: 211 197 227', '--tab-mint: 196 216 188']) {
    assert.ok(tabs.includes(color), color);
  }
  assert.match(tabs, /min-height: 48px/);
  assert.match(tabs, /border-radius: 2px/);
  assert.match(tabs, /background: rgb\(var\(--tab-color\)\)/);
  assert.doesNotMatch(tabs, /linear-gradient|rgb\(var\(--tab-color\) \//);
  assert.match(tabs, /box-sizing: border-box/);
  assert.match(tabs, /pointer-events: none/);
  assert.match(tabs, /\.is-open-notebook \.notebook-controls button \{[^}]*width: 100%; max-width: 100%; min-width: 0/);
  assert.match(tabs, /inset: 0/);
  assert.match(tabs, /--tab-direction: 90deg; --tab-attachment: 16px/);
  assert.match(css, /--book-edge-gutter: 6rem/);
  assert.match(css, /--book-left-gutter: 0px/);
  assert.match(css, /--book-tab-height: 56px/);
  assert.match(css, /\.notebook-dialog\[open\] \{[^}]*border: 0;[^}]*border-radius: 0;[^}]*background: transparent;[^}]*box-shadow: none;[^}]*overflow: visible/);
  assert.match(css, /\.notebook-dialog \.notebook-dialog-toolbar button \{[^}]*position: absolute;[^}]*right: 0;[^}]*width: calc\(var\(--book-edge-gutter\) \+ 16px\)[^}]*margin: 0;/);
  assert.match(css, /\.category-notebook\.is-open-notebook \{[^}]*background: transparent[^}]*box-shadow: none/);
  assert.match(css, /\.is-open-notebook \.notebook-stage::before \{[^}]*inset: 0 var\(--book-edge-gutter\) var\(--photo-tab-footer\) var\(--book-left-gutter\)[^}]*background: var\(--cream\)/);
  assert.match(css, /\.is-open-notebook \.notebook-controls \{[^}]*position: absolute;[^}]*right: 0;[^}]*width: calc\(var\(--book-edge-gutter\) \+ 16px\);[^}]*grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /\.notebook-page-status \{ grid-column: 1; grid-row: 3;/);
  assert.doesNotMatch(css, /\.is-open-notebook \.notebook-controls \{[^}]*grid-template-columns: (?:repeat\(3|minmax\(0, 1fr\) minmax)/);
  assert.match(tabs, /:focus-visible \{ outline-offset: 2px/);
  assert.match(tabs, /@media \(forced-colors: active\)/);
  assert.doesNotMatch(tabs, /rotate\(|overflow:\s*hidden|clip-path|opacity:/);
  assert.match(css, /\.photo-link::after \{ content: "View larger photo"/);
  assert.match(css, /\.category-notebook \.photo-link::after \{ content: none; \}/);
  assert.match(css, /\.is-open-notebook \.photo-link \{[^}]*grid-template-columns: minmax\(0, 1fr\)[^}]*min-width: 0/);
  const html = render();
  assert.doesNotMatch(html, /cake-card-actions|cake-enquire|data-enlarge-photo|enquiry-full-label|enquiry-compact-label/);
  assert.equal((html.match(/data-photo data-photo-title=/g) || []).length, cakes.length + 1);
  assert.equal((html.match(/aria-label="Previous page" title="Previous page"><span aria-hidden="true">&#8592;<\/span>/g) || []).length, 6);
  assert.equal((html.match(/data-page-next data-page-drag type="button" aria-label="Next page"/g) || []).length, 6);
  assert.equal((html.match(/\bdata-page-drag\b/g) || []).length, 6);
  assert.doesNotMatch(html, /notebook-drag-edge|notebook-turn-label|class="page-corner"/);
  assert.doesNotMatch(html, /(?:aria-label|title)="[^"]*\bturn\b|>\s*(?:page[- ]turn|turn(?: the)?(?: page)?)\s*</i);
  assert.equal((html.match(/<p class="notebook-page-status" data-page-counter/g) || []).length, 6);
  const reading = await readFile(path.join(root, 'web', 'readability.css'), 'utf8');
  assert.match(reading, /\.photo-dialog button \{ font-size: 1\.25rem; line-height: 1\.25; \}/);
  assert.match(reading, /\.notebook-dialog #notebook-dialog-title \{ font-size: 2\.125rem/);
  assert.match(reading, /\.category-notebook \.cake-card-info h4,\s*\.category-notebook \.notebook-sheet-copy h4, #photo-title \{ font-size: 1\.75rem/);
  assert.match(reading, /\.category-notebook \.cake-card-info h4 \{ width: 100%; text-align: center; \}/);
  assert.match(reading, /#cakes \.section-heading > p \{ font-size: 1\.5rem; line-height: 1\.5/);
  assert.match(reading, /\.notebook-cover h3, \.category-notebook \.notebook-heading h3 \{ font-size: 2\.25rem/);
  assert.match(css, /\.notebook-cover-tab \{[^}]*background: rgb\(var\(--tab-color\)\)/);
  assert.match(reading, /\.notebook-controls :is\(\[data-page-previous\], \[data-page-next\]\) \{ font-size: 1\.75rem; line-height: 1;/);
  assert.match(reading, /#notebook-fit-note, #photo-counter \{ font-size: 1\.125rem/);
  const gallery = await readFile(path.join(root, 'web', 'main.mjs'), 'utf8');
  assert.match(gallery, /if \(plainClick\(event\)\) openPhoto\(link, event\)/);
  assert.match(gallery, /opener = link/);
  assert.match(gallery, /opener\?\.focus\(\{ preventScroll: true \}\)/);
  assert.match(gallery, /link\.setAttribute\('aria-haspopup', 'dialog'\)/);
  assert.match(gallery, /if \(!openPhoto\(link, event\)\) location\.assign\(link\.href\)/);
  assert.doesNotMatch(gallery, /data-enlarge-photo|has-photo-enlarge/);
  assert.match(html, /id="notebook-dialog-title" tabindex="-1"/);
  assert.match(html, /id="notebook-close" type="button" aria-label="Back to cake categories">Back<\/button>/);
  assert.equal((html.match(/class="notebook-static-back" href="#cakes" aria-label="Back to cake categories">Back /g) || []).length, 6);
  assert.match(html, /data-page-previous type="button" aria-label="Previous page"/);
  assert.doesNotMatch(html, />All categories(?:<| )/);
  const notebook = await readFile(path.join(root, 'web', 'notebooks.mjs'), 'utf8');
  assert.match(notebook, /title\.getClientRects\(\)\.length \? title : dialogTitle/);
  assert.match(notebook, /if \(book\.next !== handle\) book\.next\.addEventListener/);
});

test('closed covers have deterministic text-free pastel index flags outside their right paper edges', async () => {
  const html = render();
  const covers = [...html.matchAll(/<a class="notebook-cover notebook-page"[^>]*data-category="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)];
  assert.equal(covers.length, 6);
  const layouts = [];
  for (const [index, [, category, markup]] of covers.entries()) {
    const decoration = markup.match(/<span class="notebook-cover-tabs" aria-hidden="true">((?:<span class="notebook-cover-tab"[^>]*><\/span>)+)<\/span>/);
    assert.ok(decoration, category);
    const flags = [...decoration[1].matchAll(/data-tab-color="([^"]+)" style="--flag-top:(\d+)%;--flag-out:(\d+)px;--flag-height:(\d+)px"/g)];
    assert.equal(flags.length, [4, 3, 5, 4, 3, 5][index], category);
    assert.equal(new Set(flags.map(flag => flag[1])).size, flags.length);
    for (const [, color, top, out, height] of flags) {
      assert.ok(['pink', 'butter', 'blue', 'lilac', 'mint'].includes(color));
      assert.ok(Number(top) >= 18 && Number(top) <= 83);
      assert.ok(Number(out) >= 18 && Number(out) <= 26);
      assert.ok(Number(height) >= 36 && Number(height) <= 50);
    }
    assert.doesNotMatch(decoration[1], /tabindex|role=|href=|<img|<svg/);
    assert.equal(decoration[1].replace(/<[^>]*>/g, ''), '');
    layouts.push(decoration[1]);
  }
  assert.equal(new Set(layouts).size, 6);
  assert.equal(render(), html, 'Category tab colours and positions must not flicker between renders.');
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(css, /\.notebook-cover \{[^}]*width: calc\(100% - 32px\); margin-right: 32px/);
  assert.match(css, /\.notebook-cover-tabs \{[^}]*pointer-events: none/);
  assert.match(css, /\.notebook-cover-tab \{[^}]*left: 100%[^}]*width: var\(--flag-out\)[^}]*pointer-events: none/);
  assert.match(css, /\.notebook-cover-action \{[^}]*max-width: 100%[^}]*overflow-wrap: anywhere/);
});

test('all six notebooks begin with photos and share weight information before the covers', async () => {
  const html = render();
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.equal((html.match(/class="notebook-cover notebook-page"/g) || []).length, 6);
  assert.match(html, /id="cake-gallery">/);
  assert.doesNotMatch(html, /id="cake-gallery"[^>]*(hidden|inert)/);
  assert.deepEqual(notebooks.map(book => book.name),
    ['Birthday Cakes', 'Tea cakes', 'Cream cakes', 'Decorated cakes', 'Doll cakes', 'Chocolates']);
  assert.doesNotMatch(html, /data-page-kind="weights"|weight-page|weight-list|weight-size/);
  assert.equal((html.match(/id="cake-weight-info"/g) || []).length, 1);
  assert.ok(html.indexOf('id="cake-weight-info"') < html.indexOf('id="category-notebooks"'));
  const weights = html.match(/<ul class="cake-weight-values"[^>]*>([\s\S]*?)<\/ul>/)[1];
  assert.deepEqual([...weights.matchAll(/<li>([^<]+)<\/li>/g)].map(match => match[1]),
    ['1/2 KG', '1 KG', '1.5 KG', '2 KG', '2.5 KG', '3 KG']);
  assert.match(css, /\.cake-weight-info \{[^}]*background: var\(--cream\)/);
  for (const book of notebooks) {
    const markup = html.split(`id="notebook-${book.id}"`)[1];
    assert.equal(markup.match(/data-page-kind="([^"]+)"/)[1], 'photos');
  }
  assert.equal((html.match(/class="cake-grid"/g) || []).length,
    notebooks.reduce((total, book) => total + Math.ceil(book.cakeIds.length / 4), 0));
  assert.match(html, /data-page-previous type="button"/);
  assert.match(html, /data-page-next data-page-drag type="button"/);
  assert.doesNotMatch(html, /notebook-drag-edge|notebook-turn-label|class="page-corner"/);
  assert.match(css, /\.notebook-sheet \{[^}]*transform-origin: center top/);
  assert.match(css, /\.cake-grid \{[^}]*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /@media print \{/);
});

test('available weights are information only and never become enquiry selections', async () => {
  for (const settings of [config, { ...config, whatsappNumber: '441234567890' }]) {
    const html = render(settings);
    assert.equal((html.match(/id="cake-weight-info"/g) || []).length, 1);
    assert.doesNotMatch(html, /weight-page|weight-list|weight-size|data-page-kind="weights"/);
    assert.doesNotMatch(html, /type="radio"|data-weight|Preferred weight|Choose a preferred|aria-checked|aria-selected/);
  }
  const notebook = await readFile(path.join(root, 'web', 'notebooks.mjs'), 'utf8');
  assert.doesNotMatch(notebook, /weightedEnquiry|data-weight|weight-summary|Preferred weight|originalEnquiries/);
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const weightStyle = css.match(/\.cake-weight-info\s*\{([^}]+)\}/)[1];
  assert.doesNotMatch(weightStyle, /cursor:\s*pointer/);
});

test('the bakery weight note is decorative readable information, not size buttons', async () => {
  const html = render();
  const info = html.slice(html.indexOf('<div class="cake-weight-info"'), html.indexOf('<div class="category-notebooks"'));
  assert.match(info, /class="cake-weight-heading" id="cake-weight-heading"/);
  assert.match(info, /width="32" height="32" alt="" aria-hidden="true"/);
  assert.match(info, /<ul class="cake-weight-values" aria-labelledby="cake-weight-heading" role="list">/);
  assert.doesNotMatch(info, /<(button|input|a|select)\b|tabindex|data-weight/);
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(css, /\.cake-weight-heading \{[^}]*var\(--script\)/);
  assert.match(css, /\.cake-weight-values \{[^}]*flex-wrap: wrap/);
  assert.match(css, /\.cake-weight-values li \{[^}]*font-size: 1\.125rem/);
  assert.match(css, /\.cake-weight-info \{[^}]*border-left: 6px solid var\(--weight-note-accent\)/);
});
test('Chocolates starts with photographs and never shows cake weights', () => {
  const chocolate = render().split('id="notebook-chocolates"')[1].split('<section')[0];
  assert.deepEqual([...chocolate.matchAll(/data-page-kind="([^"]+)"/g)].map(match => match[1]), ['photos']);
  assert.doesNotMatch(chocolate, /weight-page|weight-list|weight-size|Available weights|We make cakes in these weights/);
  assert.match(chocolate, /data-cake-id="assorted-moulded-chocolates"/);
  assert.match(chocolate, /aria-label="Page 1 of 1">1 \/ 1/);
});

test('an empty Chocolates notebook keeps an honest page instead of inventing weights', () => {
  const books = structuredClone(notebooks);
  const chocolate = books.find(book => book.id === 'chocolates');
  chocolate.cakeIds = [];
  chocolate.coverCakeId = null;
  delete chocolate.coverStickerId;
  const media = structuredClone(stickers);
  media.covers = [];
  const html = render(config, cakes.filter(cake => cake.id !== 'assorted-moulded-chocolates'), photos, media, 'local', books);
  const markup = html.split('id="notebook-chocolates"')[1].split('<section')[0];
  assert.deepEqual([...markup.matchAll(/data-page-kind="([^"]+)"/g)].map(match => match[1]), ['empty']);
  assert.match(markup, /Selected photos are being prepared for this notebook/);
  assert.match(markup, /aria-label="Page 1 of 1">1 \/ 1/);
  assert.doesNotMatch(markup, /weight-list|weight-size|data-page-kind="weights"/);
});

test('notebook membership is explicit, complete and never fills unknown categories with invented photos', () => {
  validateNotebooks(notebooks, cakes, stickers.covers);
  assert.ok(notebooks.every(book => book.cakeIds.length));
  assert.doesNotMatch(render(), /Photo preparation pending|Selected photos are being prepared/);
  assert.deepEqual(notebooks.find(book => book.id === 'doll-cakes').cakeIds, [
    'pink-doll-cake',
    'archive-p022-89de28a9',
    'archive-p136-176693df',
  ]);
  const assigned = notebooks.flatMap(book => book.cakeIds);
  assert.equal(new Set(assigned).size, cakes.length);
  assert.deepEqual([...assigned].sort(), cakes.map(cake => cake.id).sort());
  for (const book of notebooks.filter(book => book.cakeIds.length)) {
    assert.ok(book.cakeIds.includes(book.coverCakeId));
  }
});

test('the three owner-selected sources supply actual stickers on their category covers', () => {
  const expected = {
    'birthday-cakes': ['pastel-celebration-cake', '18077297165641061.jpg'],
    'tea-cakes': ['round-and-heart-tea-cakes', '18069978263206386.jpg'],
    chocolates: ['assorted-moulded-chocolates', '17952408272859389.jpg'],
  };
  const html = render();
  for (const [category, [id, filename]] of Object.entries(expected)) {
    const book = notebooks.find(item => item.id === category);
    assert.equal(book.cakeIds[0], id);
    assert.ok(book.cakeIds.includes(id));
    assert.equal(book.coverCakeId, id);
    assert.equal(path.basename(photos.photos.find(photo => photo.id === id).export_file), filename);
    const cover = html.match(new RegExp(`<a class="notebook-cover notebook-page"[^>]*data-category="${category}"[^>]*>([\\s\\S]*?)<\\/a>`))[1];
    assert.ok(cover.includes(`assets/stickers/${book.coverStickerId || `${id}-sticker`}-`));
    assert.ok(cover.includes(`${book.cakeIds.length} ${book.cakeIds.length === 1 ? 'photo' : 'photos'}`));
    assert.doesNotMatch(cover, /placeholder|1 past bake/);
  }
  assert.match(html, /Two owner-identified tea cakes, one round and one heart-shaped/);
  assert.match(html, /original Happy Anniversary topper/);
  assert.doesNotMatch(html, /Order these chocolates|cake-enquire/);
});

test('a genuinely empty category still stays honest without a substitute product image', () => {
  const books = structuredClone(notebooks);
  const removed = new Set(books[0].cakeIds);
  books[0].cakeIds = [];
  books[0].coverCakeId = null;
  const html = render(config, cakes.filter(cake => !removed.has(cake.id)), photos, stickers, 'local', books);
  assert.equal((html.match(/Photo preparation pending/g) || []).length, 1);
  assert.equal((html.match(/Selected photos are being prepared for this notebook/g) || []).length, 1);
});

test('enhanced notebooks fit the viewport without changing the four-photo page limit', async () => {
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(css, /\.notebook-dialog\[open\] \{[^}]*height: calc\(100dvh - 24px\)/);
  assert.match(css, /\.is-open-notebook \{[^}]*grid-template-rows: auto minmax\(0, 1fr\);/);
  assert.match(css, /\.is-open-notebook \.cake-grid:has\(\.cake-card:nth-child\(3\)\) \{[^}]*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /@media \(min-width: 600px\) and \(max-height: 540px\)/);
  assert.match(css, /\.is-open-notebook \.cake-card img,[^}]*object-fit: contain/);
  const html = render();
  assert.match(html, /data-page-previous type="button" aria-label="Previous page"/);
  assert.match(html, /data-page-next data-page-drag type="button" aria-label="Next page"/);
  assert.match(html, /title="Next page, or drag this tag upwards"/);
  assert.match(html, /aria-describedby="notebook-keyboard-help"/);
  assert.equal((html.match(/<span class="visually-hidden" data-page-announcement role="status" aria-live="polite">/g) || []).length, 6);
});

test('notebook controls and enlarged photos shrink to their available width', async () => {
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const photoDialog = css.match(/\.photo-dialog\[open\] \{([^}]+)\}/)[1];
  assert.match(photoDialog, /grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(photoDialog, /grid-template-rows: auto minmax\(0, 1fr\) auto/);
  assert.match(photoDialog, /max-width: none/);
  assert.match(css, /\.is-open-notebook \.notebook-controls \{[^}]*grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /\.is-open-notebook \.notebook-controls button \{[^}]*min-width: 0[^}]*overflow-wrap: anywhere/);
  assert.match(css, /#photo-image \{[^}]*grid-row: 2[^}]*min-height: 0[^}]*height: 100%[^}]*object-fit: contain/);
  assert.match(css, /#photo-title \{[^}]*overflow-wrap: anywhere/);
  assert.match(render(), /id="photo-prev" type="button" aria-label="Back to previous photo">Back/);
  assert.match(render(), /id="photo-next" type="button" aria-label="Next photo">Next/);
  const notebook = await readFile(path.join(root, 'web', 'notebooks.mjs'), 'utf8');
  assert.ok(notebook.includes("document.fonts?.addEventListener('loadingdone', scheduleFitCheck)"));
  assert.ok(notebook.includes("document.fonts?.addEventListener('loadingerror', scheduleFitCheck)"));
});

test('Birthday Cakes is first and the owner-confirmed Black Forest source belongs to Cream cakes', () => {
  assert.equal(notebooks[0].id, 'birthday-cakes');
  assert.equal(notebooks[1].id, 'tea-cakes');
  assert.ok(notebooks.every(book => book.id !== 'ice-cream'));
  const cream = notebooks.find(book => book.id === 'cream-cakes');
  assert.equal(cream.cakeIds[0], 'cherry-curl-cake');
  assert.ok(cream.cakeIds.includes('cherry-curl-cake'));
  assert.equal(cream.coverCakeId, 'cherry-curl-cake');
  assert.equal(cakes.find(cake => cake.id === 'cherry-curl-cake').name, 'Black Forest cake');
  const source = photos.photos.find(photo => photo.id === 'cherry-curl-cake');
  assert.equal(path.basename(source.export_file), '17855219376447920.jpg');
  assert.equal(source.source_sha256, 'bb623251e01cc6c7c7bbb230471b7b2f70963e78fc349e44899ac7bb9e636f60');
  assert.doesNotMatch(render(), /Ice cream|ice-cream-cone|ice-pop/);
});

test('each notebook has its own name-matched decorative sticker pair', () => {
  const expected = {
    'birthday-cakes': ['birthday-balloons', 'birthday-gift'],
    'tea-cakes': ['teacup', 'loaf-cake'],
    'cream-cakes': ['mixing-bowl', 'cream-cake-slice'],
    'decorated-cakes': ['piping-bag', 'birthday-candles'],
    'doll-cakes': ['doll-dress', 'tiara'],
    chocolates: ['chocolate-bar', 'wrapped-truffle'],
  };
  const html = render();
  const outlines = new Set();
  const covers = [...html.matchAll(/<a class="notebook-cover notebook-page"[^>]*data-category="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)];
  assert.equal(covers.length, 6);
  for (const [, category, markup] of covers) {
    assert.deepEqual([...markup.matchAll(/data-doodle="([^"]+)"/g)].map(match => match[1]), expected[category]);
    const motifs = [...markup.matchAll(/<span class="notebook-doodle [^"]+" data-doodle="[^"]+" aria-hidden="true">([\s\S]*?)<\/span>/g)];
    assert.equal(motifs.length, 2);
    for (const [, motif] of motifs) {
      assert.match(motif, /viewBox="0 0 80 80"/);
      assert.match(motif, /focusable="false"/);
      assert.match(motif, /stroke="#fffaf1" stroke-width="9"/);
      assert.match(motif, /stroke="currentColor" stroke-width="2.5"/);
      assert.doesNotMatch(motif, /<image|<text|<script|<foreignObject|href=|onload=/);
      outlines.add([...motif.matchAll(/<path d="([^"]+)"/g)].map(match => match[1]).join('|'));
    }
  }
  assert.equal(outlines.size, 12, 'Different motif names must not disguise reused artwork.');
  assert.doesNotMatch(html, /notebook-heart|notebook-bow|data-doodle="cream-swirl"/);
});

test('invalid notebook membership and cover provenance fail instead of dropping cakes', () => {
  assert.throws(() => validateNotebooks(notebooks.slice(1), cakes, stickers.covers), /six category notebooks/);
  const missing = structuredClone(notebooks);
  missing.find(book => book.id === 'decorated-cakes').cakeIds.pop();
  assert.throws(() => validateNotebooks(missing, cakes, stickers.covers), /exactly one/);
  const duplicate = structuredClone(notebooks);
  duplicate[0].cakeIds.push(cakes[0].id);
  duplicate[0].coverCakeId = cakes[0].id;
  assert.throws(() => validateNotebooks(duplicate, cakes, stickers.covers), /duplicate/);
  const wrongCover = structuredClone(notebooks);
  wrongCover.find(book => book.id === 'decorated-cakes').coverCakeId = 'pink-doll-cake';
  assert.throws(() => validateNotebooks(wrongCover, cakes, stickers.covers), /verified cakes/);
  const unknown = structuredClone(notebooks);
  unknown.find(book => book.id === 'decorated-cakes').cakeIds.push('imaginary-product');
  assert.throws(() => validateNotebooks(unknown, cakes, stickers.covers), /Unknown/);
});

test('the cursive font remains local and preloaded with the new business name', async () => {
  const html = render();
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(html, /rel="preload" href="assets\/fonts\/courgette-regular\.ttf"/);
  assert.match(css, /font-family: "Courgette"/);
  assert.match(css, /h1, h2, h3, h4 \{ font-family: var\(--script\)/);
  assert.doesNotMatch(css, /DM Serif Display|Dancing Script|--blush|--rose|--sage|--lilac/);
  assert.match(css, /--cream: #f5ebdd/);
  assert.match(css, /--green: #34483a/);
  assert.match(html, /Whisk &amp; Crumbs/);
});

test('unknown business details are not invented and current enquiries use Instagram', () => {
  const html = render({ ...config, siteUrl: '' });
  assert.match(html, /noindex, nofollow/);
  assert.match(html, /Message on Instagram/);
  assert.doesNotMatch(html, /https:\/\/wa\.me\/|rel="canonical"|property="og:url"/);
  assert.doesNotMatch(html, /Rs\.|₹|Vishakhapatnam|Visakhapatnam|100% eggless|same-day|five-star/i);
  assert.match(html, /before your order is final/);
});

test('Instagram contact has a large decorative logo and a visible action label', () => {
  const html = render();
  assert.equal(config.instagramHandle, 'homemadevegcakes');
  assert.equal(config.instagramUrl, 'https://www.instagram.com/homemadevegcakes/');
  assert.match(html, /id="order-contact" class="button instagram-contact"/);
  assert.match(html, /id="order-contact"[^>]+href="https:\/\/www\.instagram\.com\/homemadevegcakes\/"/);
  assert.match(html, /class="instagram-logo"[^>]+width="128" height="128"[^>]+aria-hidden="true" focusable="false"/);
  assert.match(html, /class="contact-button-label">Message on Instagram/);
  assert.match(html, /aria-describedby="order-contact-help"/);
  assert.match(html, /id="order-contact-help" class="small-note">Tap Message on Instagram/);
  assert.match(html, /Login may be required/);
  assert.doesNotMatch(html, /cake-enquire|cake-card-actions/);
});

test('one phone configuration changes the contact without keeping Instagram branding', () => {
  const html = render({ ...config, whatsappNumber: '441234567890' });
  assert.match(html, /Message on WhatsApp/);
  assert.match(html, /https:\/\/wa\.me\/441234567890/);
  assert.match(html, /Opens WhatsApp\. Review your message, then send\./);
  assert.doesNotMatch(html, /instagram-contact|instagram-logo/);
  const mainContact = getContactLink({ ...config, whatsappNumber: '441234567890' }, buildMessage());
  assert.ok(html.includes(`href="${escapeHtml(mainContact.href)}"`));
  for (const cake of cakes) {
    const link = getContactLink({ ...config, whatsappNumber: '441234567890' }, buildMessage({ cakeName: cake.name }));
    assert.ok(!html.includes(`href="${escapeHtml(link.href)}"`), `Catalogue must not add an order link for ${cake.name}`);
  }
  assert.throws(() => render({ ...config, whatsappNumber: '+44 wrong number' }));
});

test('configured base URL supports project subpaths and absolute social preview metadata', () => {
  const html = render({ ...config, siteUrl: 'https://example.test/bakery' });
  assert.match(html, /rel="canonical" href="https:\/\/example\.test\/bakery\/"/);
  assert.match(html, /content="https:\/\/example\.test\/bakery\/assets\/whisk-and-crumbs-social-card\.jpg"/);
  assert.doesNotMatch(html, /noindex/);
  assert.throws(() => render({ ...config, siteUrl: 'javascript:alert(1)' }));
});

test('text content is escaped and template-like product content is not reevaluated', () => {
  const updated = structuredClone(cakes);
  updated[0].name = '<script>alert("cake")</script> & {{NAME}}';
  const html = render(config, updated);
  assert.match(html, /&lt;script&gt;alert\(&quot;cake&quot;\)&lt;\/script&gt; &amp; \{\{NAME\}\}/);
  assert.doesNotMatch(html, /<script>alert\("cake"\)/);
});

test('branding follows configuration and escapes names in accessible and social text', () => {
  const name = 'Bakes & "Crumbs" <Kitchen>';
  const html = render({ ...config, name, wordmark: name });
  const escaped = escapeHtml(name);
  assert.ok(html.includes(`<title>${escaped} - Baked at home. Made with heart.</title>`));
  assert.ok(html.includes(`aria-label="${escaped} - home"`));
  assert.ok(html.includes(`<span class="wordmark">${escaped}</span>`));
  assert.ok(html.includes(`<meta property="og:site_name" content="${escaped}">`));
  assert.ok(html.includes(`<meta property="og:image:alt" content="${escaped}: a home-baked cake with burgundy bows.">`));
  assert.ok(html.match(/<footer\b[\s\S]*?<\/footer>/)[0].includes(escaped));
  assert.doesNotMatch(html, /Bakes & "Crumbs" <Kitchen>/);
});

test('responsive transparent stickers link to the full photographs, hero is eager', () => {
  const html = render();
  assert.equal((html.match(/<source type="image\/webp"/g) || []).length, cakes.length + notebooks.length + 1);
  assert.equal((html.match(/fetchpriority="high" loading="eager"/g) || []).length, 1);
  assert.equal((html.match(/<img\b[^>]*src="assets\/stickers\/[^"]+"[^>]*loading="lazy"/g) || []).length,
    cakes.length + notebooks.length);
  for (const cutout of stickers.photos) {
    const full = cutout.variants.filter(item => item.file.endsWith('.png')).at(-1);
    assert.ok(html.includes(`width="${full.width}" height="${full.height}"`));
    const revision = cutout.revision ? `?v=${full.sha256.slice(0, 12)}` : '';
    assert.ok(html.includes(`src="assets/stickers/${full.file}${revision}"`));
    const original = photos.photos.find(photo => photo.id === cutout.id).variants
      .filter(item => item.file.endsWith('.jpg')).at(-1);
    assert.ok(html.includes(`href="assets/images/${original.file}"`));
  }
});

test('open titles reserve the entire spiral strip and restore the toolbar on close', async () => {
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const controller = await readFile(path.join(root, 'web', 'notebooks.mjs'), 'utf8');
  assert.match(css, /\.notebook-dialog-toolbar::before \{ content: none; \}/);
  assert.match(css, /\.notebook-dialog \.notebook-dialog-toolbar \{[^}]*display: contents;/);
  assert.match(css, /\.is-open-notebook \.notebook-heading \{[^}]*padding: 24px 8px 4px;/);
  assert.doesNotMatch(css, /--binding-gap/);
  assert.match(controller, /book\.heading\.prepend\(toolbar\)/);
  assert.match(controller, /dialog\.insertBefore\(toolbar, mount\)/);
  assert.match(controller, /fitObserver\.observe\(dialogTitle\)/);
  assert.match(controller, /!toolbar\.contains\(document\.activeElement\)/);
  assert.match(controller, /notebook title overlaps the spiral binding/);
});

test('revised sticker PNG and WebP URLs track their exact bytes without changing photo links', () => {
  const revised = structuredClone(stickers);
  const cutout = revised.photos.find(photo => photo.id === 'ribbon-and-pearl-cake');
  cutout.revision = 'rounded-source-edges-test';
  const html = render(config, cakes, photos, revised);
  for (const variant of cutout.variants) {
    assert.ok(html.includes(`assets/stickers/${variant.file}?v=${variant.sha256.slice(0, 12)}`));
  }
  const original = photos.photos.find(photo => photo.id === cutout.id).variants
    .filter(item => item.file.endsWith('.jpg')).at(-1);
  assert.ok(html.includes(`href="assets/images/${original.file}"`));
  const before = cutout.variants[0].sha256.slice(0, 12);
  cutout.variants[0].sha256 = 'a'.repeat(64);
  const changed = render(config, cakes, photos, revised);
  assert.ok(changed.includes(`assets/stickers/${cutout.variants[0].file}?v=aaaaaaaaaaaa`));
  assert.ok(!changed.includes(`assets/stickers/${cutout.variants[0].file}?v=${before}`));
  for (const revision of ['', '../masks', true, null]) {
    cutout.revision = revision;
    assert.throws(() => render(config, cakes, photos, revised), /Invalid sticker revision/);
  }
});

test('gallery validation rejects ambiguous IDs and missing media', () => {
  assert.throws(() => render(config, [...cakes, cakes[0]]), /duplicate cake ID/);
  assert.throws(() => render(config, cakes, { photos: [] }), /Missing photo/);
  const bad = structuredClone(photos);
  bad.photos[0].variants[0].file = '../private.webp';
  assert.throws(() => render(config, cakes, bad), /Invalid prepared photo/);
});

test('sticker validation rejects missing, mismatched and unsafe cutouts', () => {
  assert.throws(() => render(config, cakes, photos, { photos: [] }), /sticker/);
  const mismatch = structuredClone(stickers);
  mismatch.photos[0].source_screenshot_sha256 = '0'.repeat(64);
  assert.throws(() => render(config, cakes, photos, mismatch), /mismatched sticker/);
  const exportMismatch = structuredClone(stickers);
  exportMismatch.photos.find(photo => photo.id === 'rainbow-butterfly-cake').source_photo_sha256 = '0'.repeat(64);
  assert.throws(() => render(config, cakes, photos, exportMismatch), /mismatched sticker/);
  const unsafe = structuredClone(stickers);
  unsafe.photos[0].variants[0].file = '../masks/private.webp';
  assert.throws(() => render(config, cakes, photos, unsafe), /Invalid prepared photo/);
  const duplicate = structuredClone(stickers);
  duplicate.photos.push(duplicate.photos[0]);
  assert.throws(() => render(config, cakes, photos, duplicate), /duplicate/);
});

test('public build contains only the allowlisted site, branding, photos and licensed fonts', async () => {
  const temporary = await mkdtemp(path.join(root, '.bakery-site-test-'));
  try {
    const output = path.join(temporary, 'public');
    const result = await buildSite(output);
    const versionHash = createHash('sha256');
    for (const file of [
      'styles.css', 'entrance-shop.css', 'cozy-bakery.css', 'cream.css', 'readability.css', 'main.mjs', 'notebooks.mjs', 'entrance.mjs', 'bell.mjs',
      'awning.mjs', 'awning-cloth.mjs',
      'bakery-interior.mjs', 'bakery-view.mjs', 'bakery-scene.mjs',
      'cream.mjs', 'cream-model.mjs', 'cream-material.mjs',
      'assets/bakery-awning.svg', 'assets/bakery-shelf.svg', 'assets/bakery-paint-atlas.png',
      'assets/bakery-interior-wide.webp', 'assets/bakery-interior-portrait.webp', 'assets/bakery-interior-short.webp',
      'assets/bakery-sign-wood.webp',
      'assets/bakery-light-bake.bin',
      'assets/bakery-facade-upper.svg', 'assets/bakery-facade-upper-mobile.svg',
      'assets/bakery-facade-ground.svg', 'assets/bakery-facade-plaster.webp',
      'assets/bakery-awning-supports.svg',
      'assets/bakery-glass-etching.svg',
    ]) {
      versionHash.update(await readFile(path.join(root, 'web', file)));
    }
    assert.equal(result.assetVersion, versionHash.digest('hex').slice(0, 12));
    const referencedCovers = new Set(notebooks.map(book => book.coverStickerId).filter(Boolean));
    const coverFiles = (stickers.covers || []).filter(cover => referencedCovers.has(cover.id))
      .reduce((total, cover) => total + cover.variants.length, 0);
    const expectedMediaFiles = photos.photos.reduce((total, photo) => total + photo.variants.length, 0)
      + stickers.photos.reduce((total, photo) => total + photo.variants.length, 0) + coverFiles;
    assert.equal(result.files.length, 60 + expectedMediaFiles);
    assert.ok(result.files.includes('assets/bakery-light-bake.bin'));
    assert.ok(result.files.includes('awning.mjs'));
    assert.ok(result.files.includes('awning-cloth.mjs'));
    for (const file of ['bakery-interior.mjs', 'bakery-view.mjs', 'bakery-scene.mjs']) assert.ok(result.files.includes(file));
    assert.ok(result.files.includes('entrance-shop.css'));
    assert.ok(result.files.includes('cozy-bakery.css'));
    for (const name of ['cream.mjs', 'cream-model.mjs', 'cream-material.mjs', 'cream.css', 'assets/bakery-glass-etching.svg']) {
      assert.ok(result.files.includes(name));
    }
    assert.ok(result.files.includes('entrance.mjs'));
    assert.ok(result.files.includes('bell.mjs'));
    assert.ok(result.files.includes('notebooks.mjs'));
    assert.equal(result.files.filter(file => file.startsWith('assets/stickers/')).length,
      stickers.photos.reduce((total, photo) => total + photo.variants.length, 0) + coverFiles);
    assert.equal(result.files.filter(file => file.startsWith('assets/images/')).length,
      photos.photos.reduce((total, photo) => total + photo.variants.length, 0));
    const showcase = [
      '01-welcome.jpg', '02-bakery-entrance.jpg', '03-our-story.jpg',
      '04-cake-notebooks.jpg', '05-open-notebook.jpg', '06-simple-ordering.jpg',
    ];
    assert.deepEqual(result.files.filter(file => file.startsWith('assets/showcase/')),
      showcase.map(file => `assets/showcase/${file}`));
    for (const file of showcase) {
      assert.deepEqual(await readFile(path.join(output, 'assets', 'showcase', file)),
        await readFile(path.join(root, 'web', 'assets', 'showcase', file)));
    }
    assert.ok(result.files.includes('readability.css'));
    assert.ok(result.files.includes('assets/fonts/DM-Sans-OFL.txt'));
    assert.ok(result.files.includes('assets/fonts/Dancing-Script-OFL.txt'));
    assert.ok(result.files.includes('assets/fonts/dancing-script-variable.ttf'));
    assert.ok(result.files.includes('assets/fonts/Courgette-OFL.txt'));
    assert.ok(result.files.includes('assets/fonts/courgette-regular.ttf'));
    assert.ok(result.files.includes('assets/bakery-doodles.svg'));
    for (const file of [
      'whisk-and-crumbs-mark.svg', 'whisk-and-crumbs-logo.png',
      'favicon.svg', 'favicon-16.png', 'favicon-32.png', 'favicon.ico',
      'apple-touch-icon.png', 'bakery-pattern-cream.svg', 'bakery-pattern-green.svg',
      'whisk-and-crumbs-social-card.jpg',
      'bakery-awning.svg', 'bakery-shelf.svg', 'bakery-paint-atlas.png',
      'bakery-interior-wide.webp', 'bakery-interior-portrait.webp', 'bakery-interior-short.webp',
      'bakery-sign-wood.webp',
      'bakery-light-bake.bin', 'bakery-facade-upper.svg', 'bakery-facade-upper-mobile.svg',
      'bakery-facade-ground.svg', 'bakery-facade-plaster.webp',
      'bakery-awning-supports.svg',
    ]) {
      assert.ok(result.files.includes(`assets/${file}`), file);
      assert.deepEqual(await readFile(path.join(output, 'assets', file)),
        await readFile(path.join(root, 'web', 'assets', file)), file);
    }
    assert.ok(!result.files.includes('assets/cake-mark.svg'));
    assert.ok(!result.files.includes('assets/social-card.jpg'));
    assert.ok(!result.files.includes('assets/bakery-window.svg'));
    assert.ok(result.files.every(name => !/\.local|references|manifest|masks|recipe|\.onnx|Screenshot|\.pdf|\.zip|TODO/.test(name)));
    assert.equal(await readFile(path.join(output, 'index.html'), 'utf8'),
      render(config, cakes, photos, stickers, result.assetVersion));
    for (const file of ['assets/cake-mark.svg', 'assets/social-card.jpg', 'assets/bakery-window.svg', 'assets/bakery-room-counter.svg', 'cream-surface.mjs']) {
      const retired = path.join(output, file);
      await writeFile(retired, 'obsolete branding');
      await assert.rejects(buildSite(output), /Unexpected file in public output/);
      assert.equal(await readFile(retired, 'utf8'), 'obsolete branding');
      await rm(retired);
    }
    await mkdir(path.join(output, 'private'), { recursive: true });
    await writeFile(path.join(output, 'private', 'account-export.json'), '{}');
    await assert.rejects(buildSite(output), /Unexpected file in public output/);
    assert.equal(await readFile(path.join(output, 'private', 'account-export.json'), 'utf8'), '{}');
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test('the shop canopy and coherent painted room retain transparent windows and static fallbacks', async () => {
  const html = render();
  assert.equal((html.match(/src="assets\/bakery-awning\.svg\?v=local"/g) || []).length, 2);
  assert.ok(html.indexOf('class="site-awning"') > html.indexOf('</header>'));
  assert.ok(html.indexOf('class="site-awning"') < html.indexOf('<main'));
  assert.match(html, /class="site-awning" aria-hidden="true"/);
  for (const variant of ['wide', 'portrait', 'short']) {
    assert.ok(html.includes(`assets/bakery-interior-${variant}.webp?v=local`));
  }
  assert.doesNotMatch(html, /bakery-room-(back|middle|counter)\.svg|entrance-room-layer/);
  assert.ok(html.indexOf('class="entrance-room"') < html.indexOf('class="entrance-door entrance-door-left"'));
  const css = await readFile(path.join(root, 'web', 'entrance-shop.css'), 'utf8');
  assert.match(css, /\.entrance-door \{[^}]*background: transparent/);
  assert.match(css, /\.entrance-glass \{[^}]*background-color: transparent/);
  assert.match(css, /\.entrance-doorframe::before \{ content: none/);
  assert.match(css, /\.bakery-interior \{[^}]*pointer-events: none/);
  assert.doesNotMatch(css, /translateY\(-14%\)|entrance-room-counter/);
  const entrance = await readFile(path.join(root, 'web', 'entrance.mjs'), 'utf8');
  assert.match(entrance, /--look-x/);
  assert.match(entrance, /\* 3\.2/);
  assert.doesNotMatch(entrance, /setProperty\('--parallax/);
  assert.match(entrance, /enteredFromControl && focused === document\.body/);
  const renderer = await readFile(path.join(root, 'web', 'bakery-interior.mjs'), 'utf8');
  assert.match(renderer, /viewModule\.search = new URL\(import\.meta\.url\)\.search/);
  assert.match(renderer, /webglcontextlost/);
  assert.match(renderer, /retaining the painted bakery illustration/);
  assert.match(css, /prefers-reduced-motion: reduce/);
});

test('the approved cream enhancement is gated and the rejected old implementation stays absent', async () => {
  const main = await readFile(path.join(root, 'web', 'main.mjs'), 'utf8');
  const css = await readFile(path.join(root, 'web', 'styles.css'), 'utf8');
  const packageJson = await readFile(path.join(root, 'package.json'), 'utf8');
  assert.doesNotMatch(main, /initCreamSurface|cream-surface/);
  assert.match(main, /document\.body\.dataset\.creamEffects === 'enabled'/);
  assert.match(main, /versionedModule\('\.\/cream\.mjs'\)/);
  assert.match(main, /versionedModule\('\.\/cream-model\.mjs'\)/);
  assert.doesNotMatch(css, /cream-surface|cream-ready/);
  assert.doesNotMatch(render(), /cream-surface/);
  assert.match(render(), /data-cream-effects="enabled"/);
  assert.match(render(), /id="cream-effects" aria-hidden="true"[^>]*hidden/);
  assert.match(render(), /id="cream-cursor" aria-hidden="true" hidden/);
  assert.match(render(), /Pause cream motion/);
  assert.match(render(), /bakery-glass-etching\.svg\?v=local/);
  assert.match(packageJson, /cream\.test\.mjs/);
  assert.match(css, /body \{[^}]*background: var\(--cream\) url\("assets\/bakery-pattern-cream\.svg"\) repeat/);
  assert.match(css, /--cover-paper: #fbedf2/);
  const disabled = render({ ...config, creamEffects: false });
  assert.doesNotMatch(disabled, /id="cream-effects"|id="cream-cursor"|id="cream-motion-control"|href="cream\.css/);
  const absent = { ...config };
  delete absent.creamEffects;
  assert.doesNotMatch(render(absent), /data-cream-effects="enabled"/);
  assert.throws(() => render({ ...config, creamEffects: 'yes' }), /must be a boolean/);
  const enhancement = await readFile(path.join(root, 'web', 'cream.css'), 'utf8');
  assert.match(enhancement, /prefers-reduced-motion: reduce/);
  assert.match(enhancement, /prefers-reduced-transparency: reduce/);
  assert.match(enhancement, /#cream-cursor \{[^}]*pointer-events: none/);
  assert.ok(template.indexOf('CREAM_STYLES') < template.indexOf('readability.css'));
});

test('themed glass covers each complete content section without individual text plates', async () => {
  const html = render();
  const cream = await readFile(path.join(root, 'web', 'cream.css'), 'utf8');
  assert.equal((html.match(/class="cream-glass" aria-hidden="true"/g) || []).length, 5);
  assert.match(cream, /width: min\(1344px, calc\(100vw - 32px\)\)/);
  assert.doesNotMatch(cream, /760px/);
  assert.match(cream, /--cream-glass-color: var\(--green\)/);
  assert.match(cream, /--cream-glass-opacity: 84%/);
  assert.match(cream, /blur\(clamp\(2px, \.55vw, 8px\)\)/);
  assert.match(cream, /color-mix\(in srgb, var\(--cream-glass-color, var\(--cream\)\)/);
  assert.match(cream, /var\(--cream-glass-opacity, 30%\)/);
  assert.doesNotMatch(cream, /\.cream-etching \{[^}]*opacity:\s*\.08/);
  assert.match(cream, /:is\(#story, #order\) \.cream-etching \{ filter: brightness\(\.4\); \}/);
  assert.match(cream, /\.hero-copy, \.section-heading, \.story-copy, \.order-layout > div, \.order-action\)::before \{ content: none; \}/);
  assert.match(cream, /#cream-motion-control \{[\s\S]*?position: relative;/);
  assert.match(html, /<footer\b[\s\S]*id="cream-motion-control"[\s\S]*<\/footer>/);
  assert.match(html, /<footer\b[\s\S]*class="mobile-enquire"[\s\S]*<\/footer>/);
  assert.match(cream, /\.mobile-enquire \{ position: relative; inset: auto;/);
  assert.match(html, /aria-describedby="cream-motion-help"/);
  assert.doesNotMatch(html.match(/<div id="cream-effects"[\s\S]*?<\/div>/)[0], /cream-glass/);
});

test('README contains exactly six linked images and the prose is preserved in ABOUT', async () => {
  const readme = await readFile(path.join(root, 'README.md'), 'utf8');
  const pattern = /\[!\[([^\]]+)\]\((site\/assets\/showcase\/[^)]+)\)\]\((https:\/\/zanark\.github\.io\/WhiskAndCrumbs\/(?:#[a-z]+)?)\)/g;
  const images = [...readme.matchAll(pattern)];
  assert.equal(images.length, 6);
  assert.equal(new Set(images.map(match => match[2])).size, 6);
  assert.ok(images.every(match => match[1].length >= 30));
  assert.equal(readme.replace(pattern, '').trim(), '', 'The README must have no visible prose or headings.');
  const about = await readFile(path.join(root, 'ABOUT.md'), 'utf8');
  for (const section of ['Step inside', 'Category notebooks', 'Enquiries', 'Repository and publication']) {
    assert.ok(about.includes(`## ${section}`), section);
  }
  assert.match(about, /Following a link does not place or confirm an order/);
  assert.match(about, /legal uniqueness have not been established/);
  assert.match(about, /https:\/\/github\.com\/Zanark\/WhiskAndCrumbs/);
  assert.doesNotMatch(about, /WhisksAndCrumbs|WhiskAndCrubms|\.local[\\/]|C:\\|cookies|token=/);
  for (const [, source] of about.matchAll(/<img src="([^"]+)"/g)) {
    assert.ok(source.startsWith('site/assets/'));
    await readFile(path.join(root, source));
  }
});
