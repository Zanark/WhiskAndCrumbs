import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, mkdtemp, cp, rm, stat } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  root, renderSite, pictureMarkup, validateCoverStickers,
} from '../scripts/build-site.mjs';

const json = file => readFile(path.join(root, file), 'utf8').then(JSON.parse);
const [config, cakes, photos, stickers, notebooks, template] = await Promise.all([
  json('content/site.json'), json('content/cakes.json'), json('assets/images/cakes/manifest.json'),
  json('assets/images/cake-stickers/manifest.json'), json('content/notebooks.json'),
  readFile(path.join(root, 'web', 'index.template.html'), 'utf8'),
]);
const id = 'chocolates-five-selected-20261009';
const cake = cakes.find(item => item.id === 'assorted-moulded-chocolates');
const render = (media = stickers, books = notebooks) =>
  renderSite(template, config, cakes, photos, media, 'cover-test', books);
const coverPattern = /<a class="notebook-cover notebook-page"[^>]*data-category="chocolates"[^>]*>[\s\S]*?<\/a>/;

test('the fixed five-piece override changes only the decorative Chocolate cover', () => {
  const books = structuredClone(notebooks);
  delete books.find(book => book.id === 'chocolates').coverStickerId;
  const baseline = render(stickers, books);
  const changed = render();
  assert.equal(baseline.replace(coverPattern, ''), changed.replace(coverPattern, ''));
  const cover = changed.match(coverPattern)[0];
  assert.match(cover, new RegExp(`assets/stickers/${id}-1000.png`));
  assert.match(cover, /alt="" loading="lazy"/);
  assert.doesNotMatch(cover, /data-photo|href="assets\/images/);
  assert.doesNotMatch(changed.replace(coverPattern, ''), new RegExp(id));
  assert.match(changed, /href="assets\/images\/assorted-moulded-chocolates-1000.jpg"/);
  const assortment = stickers.photos.find(photo => photo.id === cake.id);
  const variant = assortment.variants.find(item => item.file === `${cake.id}-sticker-1000.png`);
  const query = assortment.revision ? `?v=${variant.sha256.slice(0, 12)}` : '';
  assert.ok(changed.includes(`src="assets/stickers/${variant.file}${query}"`));
  assert.deepEqual(stickers.covers[0].pieces.map(piece => piece.id), [
    'flower-detailed', 'flower-right', 'heart-left', 'heart-right', 'spiral-left',
  ]);
});

test('optional covers preserve the legacy no-override rendering', () => {
  const books = structuredClone(notebooks);
  delete books.find(book => book.id === 'chocolates').coverStickerId;
  const legacy = structuredClone(stickers);
  delete legacy.covers;
  assert.equal(render(legacy, books), render(stickers, books));
  assert.deepEqual(validateCoverStickers(legacy, cakes, photos), []);
});

test('a cover override cannot be used for a hero, gallery or enlarged photograph', () => {
  for (const options of [
    { coverStickerId: id }, { coverStickerId: id, hero: true },
    { coverStickerId: id, hero: true, decorative: true },
  ]) {
    assert.throws(() => pictureMarkup(cake, photos, stickers, options), /only for decorative notebook covers/);
  }
  assert.throws(() => pictureMarkup(cake, photos, stickers, {
    decorative: true, coverStickerId: 'unknown',
  }), /Unknown or mismatched/);
  assert.throws(() => pictureMarkup(cakes[0], photos, stickers, {
    decorative: true, coverStickerId: id,
  }), /Unknown or mismatched/);
});

test('unknown, empty and source-mismatched notebook overrides are rejected', () => {
  for (const value of ['unknown', '', null, 4]) {
    const books = structuredClone(notebooks);
    books.find(book => book.id === 'chocolates').coverStickerId = value;
    assert.throws(() => render(stickers, books), /Unknown or mismatched notebook cover/);
  }
  const books = structuredClone(notebooks);
  books[0].coverStickerId = id;
  assert.throws(() => render(stickers, books), /Unknown or mismatched notebook cover/);
});

const invalid = (change, pattern) => {
  const media = structuredClone(stickers);
  change(media.covers[0], media);
  assert.throws(() => render(media), pattern);
};

test('cover IDs are safe and unique, including original sticker IDs', () => {
  invalid((cover, media) => media.covers.push(structuredClone(cover)), /duplicate cover sticker ID/);
  for (const value of ['../private', '', null, cake.id]) {
    invalid(cover => { cover.id = value; }, /cover sticker ID/);
  }
  invalid((cover, media) => { media.covers = {}; }, /must be an array/);
});

test('all supplied cover records require a known matching source, including unreferenced ones', () => {
  invalid(cover => { cover.sourceCakeId = 'unknown'; }, /cover sticker source/);
  invalid(cover => { cover.source_photo_sha256 = '0'.repeat(64); }, /cover sticker source/);
  const media = structuredClone(stickers);
  media.covers[0].source_photo_sha256 = '0'.repeat(64);
  const books = structuredClone(notebooks);
  delete books.find(book => book.id === 'chocolates').coverStickerId;
  assert.throws(() => render(media, books), /cover sticker source/);
});

test('owner approval and recipe provenance are mandatory', () => {
  invalid(cover => { cover.owner_cutout_approval = false; }, /approval or provenance/);
  invalid(cover => { delete cover.approval_sha256; }, /approval or provenance/);
  invalid(cover => { cover.recipe_sha256 = 'not-a-hash'; }, /approval or provenance/);
});

test('approved pieces must be distinct, unchanged and bound to their hashes and count', () => {
  for (const change of [
    cover => { cover.pieces.pop(); },
    cover => { cover.pieces[1] = structuredClone(cover.pieces[0]); },
    cover => { cover.pieces[0].approved_piece_sha256 = 'not-a-hash'; },
    cover => { cover.pieces[0].source_cutout_changed = true; },
    cover => { cover.selected_items = 0; },
  ]) invalid(change, /approved cover sticker pieces/);
});

test('cover assets require precisely matching 480 and 1000 PNG/WebP variants', () => {
  for (const change of [
    cover => { cover.variants.pop(); },
    cover => { cover.variants[0].width = 1000; },
    cover => { cover.variants[0].file = '../private.png'; },
    cover => { cover.variants[0].height += 1; },
    cover => { cover.variants[0].bytes = 0; },
    cover => { cover.variants[0].sha256 = 'not-a-hash'; },
    cover => { cover.variants.push(structuredClone(cover.variants[0])); },
  ]) invalid(change, /variant/);
});

test('a cover filename cannot overwrite an original gallery sticker', () => {
  invalid(cover => {
    const old = cover.id;
    cover.id = `${cake.id}-sticker`;
    for (const variant of cover.variants) variant.file = variant.file.replace(old, cover.id);
  }, /colliding cover sticker variant/);
});

test('isolated builds copy only referenced cover assets and reject changed bytes before writing', async () => {
  const fixture = await mkdtemp(path.join(root, '.bakery-cover-test-'));
  try {
    const ids = new Set(['ribbon-and-pearl-cake', cake.id]);
    const data = structuredClone(stickers);
    data.photos = data.photos.filter(item => ids.has(item.id));
    const unused = structuredClone(data.covers[0]);
    unused.id += '-unused';
    for (const variant of unused.variants) variant.file = variant.file.replace(id, unused.id);
    data.covers.push(unused);
    const originals = structuredClone(photos);
    originals.photos = originals.photos.filter(item => ids.has(item.id));
    const books = structuredClone(notebooks);
    for (const book of books) {
      book.cakeIds = book.cakeIds.filter(item => ids.has(item));
      book.coverCakeId = book.cakeIds[0] || null;
    }
    const writeJSON = async (file, value) => {
      const destination = path.join(fixture, file);
      await mkdir(path.dirname(destination), { recursive: true });
      await writeFile(destination, JSON.stringify(value));
    };
    await cp(path.join(root, 'web'), path.join(fixture, 'web'), { recursive: true });
    await mkdir(path.join(fixture, 'scripts'));
    await cp(path.join(root, 'scripts', 'build-site.mjs'), path.join(fixture, 'scripts', 'build-site.mjs'));
    await writeJSON('content/site.json', config);
    await writeJSON('content/cakes.json', cakes.filter(item => ids.has(item.id)));
    await writeJSON('content/notebooks.json', books);
    for (const [folder, manifest, records] of [
      ['cakes', originals, originals.photos],
      ['cake-stickers', data, [...data.photos, data.covers[0]]],
    ]) {
      await writeJSON(`assets/images/${folder}/manifest.json`, manifest);
      for (const record of records) {
        for (const variant of record.variants) {
          await cp(path.join(root, 'assets', 'images', folder, variant.file),
            path.join(fixture, 'assets', 'images', folder, variant.file));
        }
      }
    }
    const builder = await import(pathToFileURL(path.join(fixture, 'scripts', 'build-site.mjs')).href);
    const output = path.join(fixture, 'referenced-output');
    const result = await builder.buildSite(output);
    assert.deepEqual(result.files.filter(file => file.includes(id)).sort(),
      data.covers[0].variants.map(variant => `assets/stickers/${variant.file}`).sort());
    assert.ok(result.files.every(file => !/unused|manifest|recipe|mask/.test(file)));
    for (const variant of data.covers[0].variants) {
      assert.deepEqual(await readFile(path.join(output, 'assets', 'stickers', variant.file)),
        await readFile(path.join(root, 'assets', 'images', 'cake-stickers', variant.file)));
    }
    delete books.at(-1).coverStickerId;
    await writeJSON('content/notebooks.json', books);
    const unreferenced = await builder.buildSite(path.join(fixture, 'unreferenced-output'));
    assert.ok(unreferenced.files.every(file => !file.includes(id)));
    assert.equal(unreferenced.files.length, result.files.length - 4);
    books.at(-1).coverStickerId = id;
    await writeJSON('content/notebooks.json', books);
    await writeFile(path.join(fixture, 'assets', 'images', 'cake-stickers', data.covers[0].variants[0].file), 'changed');
    const failedOutput = path.join(fixture, 'failed-output');
    await assert.rejects(builder.buildSite(failedOutput), /Prepared cover sticker changed/);
    await assert.rejects(stat(failedOutput), { code: 'ENOENT' });
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});
