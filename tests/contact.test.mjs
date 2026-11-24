import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { buildMessage, getContactLink } from '../web/contact.mjs';

const config = Object.freeze({
  whatsappNumber: '',
  instagramUrl: 'https://www.instagram.com/homemadevegcakes/',
  instagramHandle: '@homemadevegcakes',
});

test('blank details produce a warm generic enquiry with no placeholders', () => {
  const message = buildMessage();
  assert.match(message, /^Hello!/);
  assert.match(message, /custom cake/);
  assert.match(message, /availability and price/);
  assert.doesNotMatch(message, /Preferred|Servings|\[|\]|undefined|null/);
  assert.equal(buildMessage({ cakeName: '  ', date: '\t', servings: ' ', notes: '\n' }), message);
});

test('optional fields are trimmed, readable and individually optional', () => {
  const message = buildMessage({
    cakeName: '  Chocolate garden  ', date: '2028-02-29',
    servings: ' 12 ', notes: '  Less sweet, please.\nNo nuts.  ',
  });
  assert.match(message, /Preferred cake or design: Chocolate garden/);
  assert.match(message, /Preferred date: 29 February 2028/);
  assert.match(message, /Servings: 12/);
  assert.match(message, /A little more about my idea: Less sweet, please.\nNo nuts\./);
  assert.match(buildMessage({ cakeName: 'Vanilla' }), /design: Vanilla/);
  assert.match(buildMessage({ notes: 'A surprise!' }), /idea: A surprise!/);
  assert.match(buildMessage({ servings: 1 }), /Servings: 1/);
  assert.doesNotMatch(buildMessage({ date: '2026-12-01' }), /Servings|design:/);
});

test('calendar formatting preserves the supplied local date in different time zones', () => {
  const moduleUrl = new URL('../web/contact.mjs', import.meta.url).href;
  for (const zone of ['UTC', 'America/Los_Angeles', 'Pacific/Kiritimati', 'Asia/Kolkata']) {
    const script = `import { buildMessage } from ${JSON.stringify(moduleUrl)}; process.stdout.write(buildMessage({ date: '2028-02-29' }));`;
    const message = execFileSync(process.execPath, ['--input-type=module', '-e', script], {
      encoding: 'utf8', env: { ...process.env, TZ: zone },
    });
    assert.match(message, /Preferred date: 29 February 2028/, zone);
  }
});

test('date validation handles leap centuries, year boundaries and historical dates', () => {
  for (const [date, expected] of [
    ['2000-02-29', '29 February 2000'], ['2024-12-31', '31 December 2024'],
    ['2025-01-01', '1 January 2025'], ['0001-01-01', '1 January 0001'],
    ['9999-12-31', '31 December 9999'],
  ]) {
    assert.ok(buildMessage({ date }).includes(`Preferred date: ${expected}`), date);
  }
  for (const date of [
    '1900-02-29', '2100-02-29', '2026-02-29', '2028-02-30', '2026-04-31',
    '2026-00-01', '2026-13-01', '2026-01-00', '0000-01-01',
    '2026-1-01', '26-01-01', '01/01/2026', 'tomorrow',
    '2026-01-01T00:00:00Z', '2026-01-01<script>',
  ]) {
    assert.throws(() => buildMessage({ date }), /date/i, date);
  }
});

test('cake, notes and servings bounds are enforced without silently truncating', () => {
  assert.ok(buildMessage({ cakeName: 'x'.repeat(160), notes: 'x'.repeat(1500), servings: 1000 }));
  assert.match(buildMessage({ servings: '0001' }), /Servings: 1/);
  assert.throws(() => buildMessage({ cakeName: 'x'.repeat(161) }), /160/);
  assert.throws(() => buildMessage({ notes: 'x'.repeat(1501) }), /1500/);
  for (const servings of [0, -1, 1001, 1.5, NaN, Infinity, null, true, {}, '1.5', '-2', '1e2', '12 guests', '10000']) {
    assert.throws(() => buildMessage({ servings }), /whole number from 1 to 1000/);
  }
  for (const field of ['cakeName', 'date', 'notes']) {
    for (const value of [null, 42, false, [], {}]) {
      assert.throws(() => buildMessage({ [field]: value }), /must be text/);
    }
  }
  assert.throws(() => buildMessage({ notes: 'Hello\u0000' }), /readable text/);
  assert.throws(() => buildMessage({ cakeName: '\uD800' }), /readable text/);
  for (const value of [null, [], 'details', 42, true]) {
    assert.throws(() => buildMessage(value), /details must be an object/);
  }
});

test('Unicode, emoji, literal markup and URL punctuation remain plain text', () => {
  const notes = 'Crème brûlée 🎂 & tea? / 50% + café #1\n<script>alert("cake")</script>';
  const message = buildMessage({ cakeName: 'Fête 🌷', notes });
  assert.ok(message.includes('Fête 🌷'));
  assert.ok(message.includes(notes));
  const result = getContactLink({ ...config, whatsappNumber: '12345678901' }, message);
  assert.equal(result.label, 'Message on WhatsApp');
  assert.equal(result.channel, 'whatsapp');
  assert.equal(result.href, `https://wa.me/12345678901?text=${encodeURIComponent(message)}`);
  const parsed = new URL(result.href);
  assert.equal(parsed.searchParams.get('text'), message);
  assert.equal([...parsed.searchParams.keys()].length, 1);
  assert.equal(parsed.hash, '');
  assert.doesNotMatch(result.href, /<script>/);
});

test('an unconfigured WhatsApp number uses the Instagram profile without a prefilled message', () => {
  const expected = {
    href: config.instagramUrl, label: 'Message on Instagram', channel: 'instagram',
  };
  assert.deepEqual(getContactLink(config, 'Private notes & cake?'), expected);
  assert.deepEqual(getContactLink({ instagramUrl: config.instagramUrl }), expected);
  assert.equal(getContactLink({ ...config, instagramUrl: 'https://instagram.com/cake.studio_1' }).href,
    'https://instagram.com/cake.studio_1');
});

test('WhatsApp number format is strict and invalid values never silently fall back', () => {
  for (const whatsappNumber of ['12345678', '123456789012345']) {
    assert.equal(getContactLink({ ...config, whatsappNumber }).href, `https://wa.me/${whatsappNumber}?text=`);
  }
  for (const whatsappNumber of [
    '1234567', '1234567890123456', '012345678', '+12345678901', '123 45678901',
    '123-45678901', ' 12345678901', '12345678901 ', ' ', '1234567\n8',
    '12345678\n', '12345678\r', 'fake-number',
    null, 12345678901, false,
  ]) {
    assert.throws(() => getContactLink({ ...config, whatsappNumber }), /WhatsApp number/);
  }
});

test('only clean HTTPS Instagram profile URLs are accepted', () => {
  for (const instagramUrl of [
    '', 'javascript:alert(1)', 'http://www.instagram.com/homemadevegcakes/',
    'https://evil.example/homemadevegcakes/', 'https://instagram.com.evil.example/cake/',
    'https://evil.example@instagram.com/cake/', 'https://user:pass@instagram.com/cake/',
    'https://instagram.com@evil.example/cake/', 'https://instagram.com:444/cake/',
    'https://m.instagram.com/cake/', 'https://instagram.com/',
    'https://instagram.com/p/', 'https://instagram.com/p/photo/',
    'https://instagram.com/direct/', 'https://instagram.com/explore/',
    'https://instagram.com/cake/?text=notes', 'https://instagram.com/cake/#notes',
    'https://instagram.com/cake/../other/', 'https://instagram.com/cake\\',
    'https://instagram.com/%63ake/', 'https://instagram.com/.cake/',
    'https://instagram.com/cake../', 'https://instagram.com/ca..ke/',
    'https://instagram.com/ca\nke/', 'https://instagram.com/cake/\n',
    ' https://instagram.com/cake/', `https://instagram.com/${'a'.repeat(31)}/`,
    null, 123,
  ]) {
    assert.throws(() => getContactLink({ ...config, instagramUrl }), /Instagram profile URL/);
  }
});

test('malformed configuration and message types fail explicitly', () => {
  for (const value of [undefined, null, [], 'config', 42, true]) {
    assert.throws(() => getContactLink(value), /configuration must be an object/);
  }
  assert.throws(() => getContactLink({ ...config, instagramHandle: 42 }), /handle must be text/);
  assert.throws(() => getContactLink({ ...config, whatsappNumber: '12345678', instagramUrl: 'https://evil.example/' }),
    /Instagram profile URL/);
  for (const message of [null, 123, {}, '\uD800']) {
    assert.throws(() => getContactLink(config, message), /valid Unicode text/);
  }
  const message = '  Hello & goodbye?  ';
  assert.equal(new URL(getContactLink({ ...config, whatsappNumber: '12345678' }, message).href).searchParams.get('text'),
    message);
  assert.deepEqual(config, {
    whatsappNumber: '', instagramUrl: 'https://www.instagram.com/homemadevegcakes/',
    instagramHandle: '@homemadevegcakes',
  });
});
