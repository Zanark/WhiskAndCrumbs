import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { AWNING_GEOMETRY, CLOTH_ROWS, createAwningCloth } from '../web/awning-cloth.mjs';

function makeCloth(options = {}) {
  return createAwningCloth({ width: 1200, height: 180, ...options });
}

function indexAt(cloth, row, column) {
  return row * (cloth.columns + 1) + column;
}

function peak(values) {
  return values.reduce((maximum, value) => Math.max(maximum, Math.abs(value)), 0);
}

function assertBounded(cloth) {
  for (let index = 0; index < cloth.displacement.length; index++) {
    assert.ok(Number.isFinite(cloth.displacement[index]));
    assert.ok(Number.isFinite(cloth.velocity[index]));
    assert.ok(Math.abs(cloth.displacement[index]) <= cloth.maxDisplacement);
  }
}

function assertAnchors(cloth) {
  for (let row = 0; row < cloth.rows.length; row++) {
    for (let column = 0; column <= cloth.columns; column++) {
      if (![0, 1, 8, 9].includes(row) && column !== 0 && column !== cloth.columns) continue;
      const index = indexAt(cloth, row, column);
      assert.equal(cloth.displacement[index], 0);
      assert.equal(cloth.velocity[index], 0);
    }
  }
}

function settle(cloth, seconds = 8) {
  for (let frame = 0; frame < seconds * 60; frame++) {
    if (!cloth.step(1 / 60)) return frame + 1;
  }
  assert.fail(`Cloth must become idle within ${seconds} seconds.`);
}

test('row-major mesh starts at exact rest with frozen rail-aligned rows', () => {
  const cloth = makeCloth();
  assert.deepEqual(CLOTH_ROWS, [0, 16, 34, 58, 84, 112, 138, 164, 182, 190, 206, 224, 244, 266, 286, 296, 300]
    .map((value) => value / 300));
  assert.ok(Object.isFrozen(CLOTH_ROWS));
  assert.equal(cloth.rows, CLOTH_ROWS);
  assert.equal(cloth.geometry, AWNING_GEOMETRY);
  assert.equal(cloth.columns, 96);
  assert.ok(cloth.displacement instanceof Float32Array);
  assert.ok(cloth.velocity instanceof Float32Array);
  assert.equal(cloth.displacement.length, 97 * 17);
  assert.equal(cloth.velocity.length, cloth.displacement.length);
  assert.equal(cloth.maxDisplacement, Math.fround(25.2));
  assert.equal(cloth.hasPointer, false);
  for (const dt of [0, 1 / 120, 1 / 60, 1, Number.MAX_VALUE]) assert.equal(cloth.step(dt), false);
  assert.equal(peak(cloth.displacement), 0);
  assert.equal(peak(cloth.velocity), 0);
  cloth.impulseScroll(0);
  cloth.clearPointer();
  assert.equal(cloth.step(1), false);
});

test('the longer narrow-striped slope and fixed rails agree with the actual SVG artwork', () => {
  const svg = readFileSync(new URL('../web/assets/bakery-awning.svg', import.meta.url), 'utf8');
  assert.ok(Object.isFrozen(AWNING_GEOMETRY));
  assert.equal(AWNING_GEOMETRY.height, 300);
  assert.match(svg, /viewBox="0 0 1200 300"/);
  assert.match(svg, /id="awning-hanging-panels" width="30" height="300"/);
  assert.match(svg, /V279A15 15 0 0 1 0 279Z/);
  assert.match(svg, /data-curve-depth="15" data-straight-depth="91"/);
  assert.match(svg, /M4 279A11 11 0 0 0 26 279/);
  assert.match(svg, /data-stripe-count="40"/);
  assert.match(svg, /data-scallop-count="40"/);
  assert.match(svg, /id="awning-slope-clip"><rect y="13" width="1200" height="171"/);
  assert.match(svg, /M1158\.6 13H1200L1200 112\.84Q1200 160 1200 184/);
  assert.match(svg, /fill="#ce7183"/);
  assert.match(svg, /id="awning-valance-mask"[^>]*height="108"/);
  assert.equal(CLOTH_ROWS[1] * AWNING_GEOMETRY.height, AWNING_GEOMETRY.topRailBottom);
  assert.equal(CLOTH_ROWS[8] * AWNING_GEOMETRY.height, AWNING_GEOMETRY.frontBarTop);
  assert.equal(CLOTH_ROWS[9] * AWNING_GEOMETRY.height, AWNING_GEOMETRY.frontBarBottom);
  assert.ok(CLOTH_ROWS.filter(row => row > AWNING_GEOMETRY.frontBarBottom / AWNING_GEOMETRY.height).length >= 7);
});

test('metal supports are separate from flexible cloth and attach to both fixed rails', () => {
  const support = readFileSync(new URL('../web/assets/bakery-awning-supports.svg', import.meta.url), 'utf8');
  assert.match(support, /viewBox="0 0 1200 300"/);
  assert.match(support, /id="awning-support-left"/);
  assert.match(support, /id="awning-support-right"/);
  assert.match(support, /M160 16 90 186/);
  assert.match(support, /rect x="77" y="179" width="27" height="14"/);
  assert.doesNotMatch(support, /<animate|<script|<image/);
});

test('the awning front fold is lit above its cast shadow without changing cloth geometry', () => {
  const svg = readFileSync(new URL('../web/assets/bakery-awning.svg', import.meta.url), 'utf8');
  assert.match(svg, /id="awning-rear-contact-shadow" y="16" width="1200" height="24"/);
  assert.match(svg, /id="awning-rounded-fold-light" y="168" width="1200" height="16"/);
  assert.match(svg, /id="awning-front-lip-shadow" y="190" width="1200" height="27"/);
  assert.match(svg, /fill="url\(#awning-front-roll\)"/);
  assert.match(svg, /data-curve-depth="15" data-straight-depth="91"/);
  assert.equal(AWNING_GEOMETRY.frontBarTop, 182);
  assert.equal(AWNING_GEOMETRY.frontBarBottom, 190);
});

test('invalid dimensions, cell counts and nonfinite events fail without mutating state', () => {
  for (const field of ['width', 'height', 'columns']) {
    for (const value of [NaN, Infinity, -Infinity]) {
      assert.throws(() => makeCloth({ [field]: value }), RangeError);
    }
    for (const value of ['120', null, true]) {
      assert.throws(() => makeCloth({ [field]: value }), TypeError);
    }
  }
  for (const field of ['width', 'height']) {
    for (const value of [0, -1]) assert.throws(() => makeCloth({ [field]: value }), RangeError);
  }
  for (const columns of [0, 1, 257, 2.5]) assert.throws(() => makeCloth({ columns }), RangeError);
  assert.equal(makeCloth({ columns: 2 }).columns, 2);
  assert.equal(makeCloth({ columns: 256 }).columns, 256);
  assert.throws(() => createAwningCloth(), TypeError);
  assert.throws(() => createAwningCloth(null), TypeError);

  const cloth = makeCloth();
  for (const value of [NaN, Infinity, -Infinity, undefined, '1']) {
    const error = typeof value === 'number' ? RangeError : TypeError;
    assert.throws(() => cloth.setPointer(value, 100), error);
    assert.throws(() => cloth.setPointer(600, value), error);
    if (value !== undefined) assert.throws(() => cloth.setPointer(600, 100, value), error);
    assert.throws(() => cloth.impulseScroll(value), error);
    assert.throws(() => cloth.step(value), error);
  }
  assert.equal(cloth.hasPointer, false);
  assert.equal(peak(cloth.displacement), 0);
  assert.equal(peak(cloth.velocity), 0);
});

test('upper rail, front bar and all row ends stay exactly anchored during motion', () => {
  const cloth = makeCloth();
  for (const [x, y] of [[0, 0], [600, 16], [600, 122], [600, 130], [1200, 180]]) {
    cloth.setPointer(x, y, 2400);
    cloth.impulseScroll(240);
    for (let frame = 0; frame < 20; frame++) {
      cloth.step(1 / 60);
      assertAnchors(cloth);
      assertBounded(cloth);
    }
  }
  assert.ok(peak(cloth.displacement) > 0.1);
});

test('pointer creates a local dent and affects nearby exterior points but not far pointers', () => {
  const cloth = makeCloth();
  cloth.setPointer(600, 154);
  for (let frame = 0; frame < 20; frame++) cloth.step(1 / 60);
  const center = cloth.displacement[indexAt(cloth, 12, 48)];
  assert.ok(center > 1);
  assert.ok(Math.abs(cloth.displacement[indexAt(cloth, 12, 8)]) < center * 0.01);
  assert.equal(cloth.hasPointer, true);

  for (const [x, y] of [[-36, 154], [1236, 154], [600, -36], [600, 216], [600, 292]]) {
    cloth.reset();
    cloth.setPointer(x, y);
    assert.equal(cloth.hasPointer, true);
    for (let frame = 0; frame < 20; frame++) cloth.step(1 / 60);
    assert.ok(peak(cloth.displacement) > 0.01, `near pointer ${x},${y} must affect fabric`);
  }
  for (const [x, y] of [[-113, 90], [1313, 90], [600, -113], [600, 293], [Number.MAX_VALUE, 0]]) {
    cloth.reset();
    cloth.setPointer(x, y, 2400);
    assert.equal(cloth.hasPointer, false);
    assert.equal(cloth.step(1 / 60), false);
    assert.equal(peak(cloth.velocity), 0);
    assert.equal(peak(cloth.displacement), 0);
  }
});

test('neighbor springs carry a disturbance beyond the directly forced pointer patch', () => {
  const cloth = makeCloth();
  const outsidePatch = indexAt(cloth, 12, 84);
  cloth.setPointer(600, 154);
  cloth.step(1 / 120);
  assert.equal(cloth.displacement[outsidePatch], 0);
  for (let frame = 0; frame < 40; frame++) cloth.step(1 / 120);
  assert.ok(cloth.displacement[outsidePatch] > 0.0001);
  assert.ok(cloth.displacement[indexAt(cloth, 12, 48)] >
    cloth.displacement[outsidePatch] * 10);
});

test('a stationary mouse produces a strong broad response within half a second', () => {
  const cloth = makeCloth({ width: 1440, height: 324 });
  cloth.setPointer(720, 324 * .86);
  let strongest = 0;
  for (let frame = 0; frame < 60; frame++) {
    cloth.step(1 / 120);
    strongest = Math.max(strongest, peak(cloth.displacement));
    assertAnchors(cloth);
    assertBounded(cloth);
  }
  const movedColumns = [...cloth.displacement].flatMap((value, index) =>
    Math.abs(value) >= .5 ? [index % (cloth.columns + 1)] : []);
  const span = (Math.max(...movedColumns) - Math.min(...movedColumns)) / cloth.columns * 1440;
  assert.ok(strongest >= 22, `Weak response: ${strongest}`);
  assert.ok(span >= 800, `Narrow response: ${span}`);
  assert.ok(cloth.maxDisplacement * .75 < 20, 'Projected motion must remain inside the existing canvas gutter.');
});

test('released waves remain meaningful for two seconds but return to exact idle within eight', () => {
  const cloth = makeCloth({ width: 1440, height: 324 });
  cloth.setPointer(720, 324 * .86, 1800);
  settle(cloth);
  cloth.clearPointer();
  for (let frame = 0; frame < 240; frame++) cloth.step(1 / 120);
  assert.ok(peak(cloth.displacement) >= .75, 'Waves faded too quickly after the pointer left.');
  const remainingFrames = settle(cloth);
  assert.ok(2 + remainingFrames / 60 >= 4, 'The requested lingering tail disappeared early.');
  assert.ok(2 + remainingFrames / 60 <= 8);
  assert.equal(peak(cloth.displacement), 0);
  assert.equal(peak(cloth.velocity), 0);
  assert.equal(cloth.step(1 / 60), false);
});

test('up and down scrolling produce opposite nonuniform cloth waves, not a translation', () => {
  const down = makeCloth();
  const up = makeCloth();
  down.impulseScroll(100);
  up.impulseScroll(-100);
  for (let frame = 0; frame < 30; frame++) {
    down.step(1 / 60);
    up.step(1 / 60);
    for (let index = 0; index < down.displacement.length; index++) {
      assert.equal(down.displacement[index] + up.displacement[index], 0);
    }
    assertAnchors(down);
    assertAnchors(up);
  }
  assert.ok(peak(down.displacement) > 0.1);
  assert.ok(Math.abs(down.displacement[indexAt(down, 14, 48)] -
    down.displacement[indexAt(down, 14, 12)]) > 0.1);
  settle(down, 24);
  settle(up, 24);
  assert.equal(peak(down.displacement), 0);
  assert.equal(peak(up.velocity), 0);
});

test('scroll gusts fill the width, stay strong for fourteen seconds and then stop exactly', () => {
  for (const [width, height] of [[390, 150], [1440, 324], [2560, 337.5]]) {
    const cloth = makeCloth({ width, height });
    cloth.impulseScroll(60);
    let firstPeak = 0;
    const latePeaks = { 5: 0, 10: 0, 14: 0 };
    let widest = 0;
    for (let frame = 0; frame < 18 * 120; frame++) {
      cloth.step(1 / 120);
      assertAnchors(cloth);
      assertBounded(cloth);
      const time = (frame + 1) / 120;
      const maximum = peak(cloth.displacement);
      if (time <= .6) {
        firstPeak = Math.max(firstPeak, maximum);
        const columns = new Set([...cloth.displacement].flatMap((value, index) =>
          Math.abs(value) >= 1 ? [index % (cloth.columns + 1)] : []));
        widest = Math.max(widest, columns.size / cloth.columns);
      }
      for (const second of [5, 10, 14]) {
        if (Math.abs(time - second) <= .2) latePeaks[second] = Math.max(latePeaks[second], maximum);
      }
    }
    assert.ok(firstPeak >= cloth.maxDisplacement * .9, `Weak initial gust at ${width}: ${firstPeak}`);
    assert.ok(widest >= .7, `The gust should cross most of the cloth: ${widest}`);
    assert.ok(latePeaks[5] >= cloth.maxDisplacement * .5, JSON.stringify(latePeaks));
    assert.ok(latePeaks[10] >= 2 && latePeaks[14] >= 1.5, JSON.stringify(latePeaks));
    const tail = settle(cloth);
    assert.ok(tail / 60 <= 6);
    assert.equal(cloth.hasWind, false);
    assert.equal(peak(cloth.displacement), 0);
    assert.equal(peak(cloth.velocity), 0);
    assert.equal(cloth.step(1), false);
  }
});

test('renewed and reversing scrolls sustain the gust instead of cancelling its tail', () => {
  const cloth = makeCloth();
  cloth.impulseScroll(60);
  for (let frame = 0; frame < 10 * 60; frame++) cloth.step(1 / 60);
  cloth.impulseScroll(-60);
  assert.equal(cloth.hasWind, true);
  for (let frame = 0; frame < 12 * 60; frame++) cloth.step(1 / 60);
  assert.equal(cloth.hasWind, true);
  assert.ok(peak(cloth.displacement) >= 1.5);
  cloth.reset();
  assert.equal(cloth.hasWind, false);
  assert.equal(cloth.step(1), false);
});

test('clearing or leaving the near zone releases the dent and rebounds to exact rest', () => {
  for (const leave of [(cloth) => cloth.clearPointer(), (cloth) => cloth.setPointer(600, 500)]) {
    const cloth = makeCloth();
    cloth.setPointer(600, 170);
    settle(cloth);
    assert.ok(peak(cloth.displacement) > 1);
    leave(cloth);
    assert.equal(cloth.hasPointer, false);
    assert.equal(cloth.step(1 / 60), true);
    let reversed = false;
    for (let frame = 0; frame < 480; frame++) {
      const active = cloth.step(1 / 60);
      if (cloth.displacement.some((value) => value < -0.01)) reversed = true;
      if (!active) break;
    }
    assert.ok(reversed, 'released fabric has a damped rebound');
    assert.equal(cloth.step(1 / 60), false);
    assert.equal(peak(cloth.displacement), 0);
    assert.equal(peak(cloth.velocity), 0);
  }
});

test('a stationary pointer settles into a held dent without an idle simulation loop', () => {
  const cloth = makeCloth();
  cloth.setPointer(600, 154, 1000);
  settle(cloth);
  const held = cloth.displacement.slice();
  assert.equal(cloth.hasPointer, true);
  assert.ok(peak(held) > 1);
  assert.equal(peak(cloth.velocity), 0);
  for (let frame = 0; frame < 120; frame++) {
    cloth.setPointer(600, 154);
    assert.equal(cloth.step(1 / 60), false);
    assert.deepEqual(cloth.displacement, held);
  }
  cloth.setPointer(750, 154);
  assert.equal(cloth.step(1 / 60), true);
  settle(cloth);
  assert.ok(cloth.displacement[indexAt(cloth, 12, 60)] >
    cloth.displacement[indexAt(cloth, 12, 48)]);
});

test('zero time does not advance, negative time rejects, and slow frames have bounded substeps', () => {
  const cloth = makeCloth();
  cloth.impulseScroll(240);
  const initialVelocity = cloth.velocity.slice();
  assert.equal(cloth.step(0), true);
  assert.equal(peak(cloth.displacement), 0);
  assert.deepEqual(cloth.velocity, initialVelocity);
  assert.throws(() => cloth.step(-0.01), RangeError);
  assert.deepEqual(cloth.velocity, initialVelocity);
  const capped = makeCloth();
  capped.impulseScroll(240);
  cloth.step(1);
  capped.step(8 / 120);
  assert.deepEqual(cloth.displacement, capped.displacement);
  assert.deepEqual(cloth.velocity, capped.velocity);
  const fractional = makeCloth();
  fractional.impulseScroll(240);
  assert.equal(fractional.step(1 / 240), true);
  assert.equal(peak(fractional.displacement), 0);
  fractional.step(1 / 240);
  assert.ok(peak(fractional.displacement) > 0);
  cloth.step(Number.MAX_VALUE);
  assertBounded(cloth);
});

test('finite extreme inputs are capped and signed scroll and speed caps are deterministic', () => {
  for (const sign of [-1, 1]) {
    const extreme = makeCloth();
    const capped = makeCloth();
    extreme.impulseScroll(sign * Number.MAX_VALUE);
    capped.impulseScroll(sign * 240);
    extreme.setPointer(600, 154, Number.MAX_VALUE);
    capped.setPointer(600, 154, 2400);
    assert.deepEqual(extreme.velocity, capped.velocity);
    for (let frame = 0; frame < 90; frame++) {
      extreme.step(1 / 60);
      capped.step(1 / 60);
      assert.deepEqual(extreme.displacement, capped.displacement);
      assertBounded(extreme);
    }
  }
  const negativeSpeed = makeCloth();
  negativeSpeed.setPointer(600, 154, -100);
  assert.equal(peak(negativeSpeed.velocity), 0);
  for (const dimensions of [
    { width: Number.MIN_VALUE, height: Number.MIN_VALUE },
    { width: Number.MAX_VALUE, height: Number.MAX_VALUE },
    { width: 320, height: 80.3333 },
  ]) {
    const cloth = makeCloth(dimensions);
    cloth.setPointer(dimensions.width / 2, dimensions.height * 0.85, Number.MAX_VALUE);
    cloth.impulseScroll(Number.MAX_VALUE);
    for (let frame = 0; frame < 40; frame++) {
      cloth.step(1);
      assertBounded(cloth);
      assertAnchors(cloth);
    }
  }
});

test('thousands of capped events cannot escape displacement limits or fixed anchors', () => {
  const cloth = makeCloth({ width: 390, height: 80.3333, columns: 32 });
  for (let event = 0; event < 2048; event++) {
    cloth.setPointer((event * 37) % 480 - 45, (event * 13) % 160 - 40, 1e50);
    cloth.impulseScroll(event % 3 === 0 ? -1e100 : 1e100);
    cloth.step([0, 1 / 1000, 1 / 60, 1][event % 4]);
    assertBounded(cloth);
    assertAnchors(cloth);
  }
  cloth.clearPointer();
  settle(cloth, 24);
  assert.equal(peak(cloth.displacement), 0);
  assert.equal(peak(cloth.velocity), 0);
});

test('reset clears pointers, held deformation, velocity and fractional time without replacing arrays', () => {
  const cloth = makeCloth();
  const positions = cloth.displacement;
  const velocities = cloth.velocity;
  cloth.setPointer(600, 154, 2400);
  cloth.impulseScroll(240);
  cloth.step(1 / 60);
  cloth.step(1 / 240);
  cloth.reset();
  assert.equal(cloth.displacement, positions);
  assert.equal(cloth.velocity, velocities);
  assert.equal(cloth.hasPointer, false);
  assert.equal(cloth.hasWind, false);
  assert.equal(cloth.step(1 / 60), false);
  assert.equal(peak(positions), 0);
  assert.equal(peak(velocities), 0);
  cloth.impulseScroll(100);
  cloth.step(1 / 240);
  assert.equal(peak(positions), 0);
  cloth.reset();
  assert.equal(cloth.step(1), false);
});
