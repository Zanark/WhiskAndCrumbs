import test from 'node:test';
import assert from 'node:assert/strict';
import { canAutoStartPhoneTilt, phoneTiltLook } from '../web/entrance.mjs';

const neutral = { beta: 45, gamma: 0 };

test('phone tilt starts automatically only once when no permission gesture is required', () => {
  const ready = { available: true, waiting: true, attempted: false, requiresPermission: false };
  assert.equal(canAutoStartPhoneTilt(ready), true);
  for (const change of [{ available: false }, { waiting: false }, { attempted: true }, { requiresPermission: true }]) {
    assert.equal(canAutoStartPhoneTilt({ ...ready, ...change }), false);
  }
});

test('phone tilt calibrates to a comfortable non-flat neutral pose', () => {
  assert.deepEqual(phoneTiltLook(45, 0, neutral), { x: 0, y: 0 });
  assert.deepEqual(phoneTiltLook(-35, 19, { beta: -35, gamma: 19 }), { x: 0, y: 0 });
});

test('small orientation noise remains inside the neutral dead zone', () => {
  assert.deepEqual(phoneTiltLook(45.7, -.7, neutral), { x: 0, y: 0 });
});

test('fifteen-degree tilt reaches the same bounded look range as the pointer', () => {
  assert.deepEqual(phoneTiltLook(60, 15, neutral), { x: 1, y: 1 });
  assert.deepEqual(phoneTiltLook(30, -15, neutral), { x: -1, y: -1 });
  assert.deepEqual(phoneTiltLook(120, 70, neutral), { x: 1, y: 1 });
});

test('partial tilt is continuous and symmetric outside the dead zone', () => {
  const positive = phoneTiltLook(45, 7.875, neutral);
  const negative = phoneTiltLook(45, -7.875, neutral);
  assert.ok(Math.abs(positive.x - .5) < 1e-10);
  assert.equal(negative.x, -positive.x);
});

test('screen rotation maps device axes into landscape screen axes', () => {
  assert.deepEqual(phoneTiltLook(60, 0, neutral, 90), { x: 1, y: 0 });
  assert.deepEqual(phoneTiltLook(45, 15, neutral, 90), { x: 0, y: -1 });
  assert.deepEqual(phoneTiltLook(60, 0, neutral, 270), { x: -1, y: 0 });
  const inverted = phoneTiltLook(60, 15, neutral, 180);
  assert.ok(Math.abs(inverted.x + 1) < 1e-12 && Math.abs(inverted.y + 1) < 1e-12);
});

test('crossing the beta wrap boundary does not jump to a maximum turn', () => {
  const look = phoneTiltLook(-179, 0, { beta: 179, gamma: 0 });
  assert.ok(look.y > 0 && look.y < .1);
});

test('missing or invalid sensor numbers are not coerced into fake movement', () => {
  for (const value of [undefined, null, NaN, Infinity, '45']) {
    assert.throws(() => phoneTiltLook(value, 0, neutral), TypeError);
    assert.throws(() => phoneTiltLook(45, value, neutral), TypeError);
  }
  assert.throws(() => phoneTiltLook(45, 0, undefined), TypeError);
  assert.throws(() => phoneTiltLook(45, 0, neutral, NaN), TypeError);
});
