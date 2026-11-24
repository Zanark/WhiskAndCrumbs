import test from 'node:test';
import assert from 'node:assert/strict';
import { cakePages, pageTarget, dragCompletesTurn, CAKE_WEIGHTS, PAGE_TURN_MS, pageTurnFrames, paperTurnPose } from '../web/notebooks.mjs';

test('requested weights run from half a kilo to three kilos in half-kilo steps', () => {
  assert.deepEqual(CAKE_WEIGHTS.map(weight => weight.grams), [500, 1000, 1500, 2000, 2500, 3000]);
  assert.deepEqual(CAKE_WEIGHTS.map(weight => weight.label), ['1/2 KG', '1 KG', '1.5 KG', '2 KG', '2.5 KG', '3 KG']);
});

test('cake pagination preserves order without adding images to partial or empty pages', () => {
  const ids = Array.from({ length: 11 }, (_, index) => `cake-${index}`);
  const pages = cakePages(ids);
  assert.deepEqual(pages.map(page => page.length), [4, 4, 3]);
  assert.deepEqual(pages.flat(), ids);
  assert.deepEqual(cakePages([]), []);
  assert.deepEqual(cakePages(['doll']), [['doll']]);
  assert.equal(ids.length, 11);
  assert.throws(() => cakePages(null), /array/);
});

test('page arrows stop at both ends rather than wrap or skip a photo page', () => {
  assert.equal(pageTarget(0, -1, 4), 0);
  assert.equal(pageTarget(0, 1, 4), 1);
  assert.equal(pageTarget(3, 1, 4), 3);
  assert.equal(pageTarget(3, -1, 4), 2);
  assert.equal(pageTarget(0, 1, 1), 0);
  for (const args of [[-1, 1, 4], [4, 1, 4], [0, 2, 4], [0, 1, 0], [0.5, 1, 4]]) {
    assert.throws(() => pageTarget(...args), /valid page/);
  }
});

test('bottom-to-top dragging needs deliberate travel with a bounded mobile threshold', () => {
  assert.equal(dragCompletesTurn(179, 1200), false);
  assert.equal(dragCompletesTurn(180, 1200), true);
  assert.equal(dragCompletesTurn(71, 200), false);
  assert.equal(dragCompletesTurn(72, 200), true);
  assert.equal(dragCompletesTurn(-300, 700), false);
  assert.throws(() => dragCompletesTurn(100, 0), /positive page height/);
  assert.throws(() => dragCompletesTurn(NaN, 300), /finite distance/);
});

test('physical page turns spend longer lifting the readable face around the top hinge', () => {
  assert.equal(PAGE_TURN_MS, 1800);
  const frames = pageTurnFrames(0, 180);
  assert.deepEqual(frames[0], { angle: 0, offset: 0 });
  assert.deepEqual(frames.at(-1), { angle: 180, offset: 1 });
  assert.ok(frames.find(frame => frame.angle === 87).offset >= .8);
  const reverse = pageTurnFrames(180, 0);
  assert.deepEqual(reverse.map(frame => frame.angle), frames.map(frame => frame.angle).reverse());
  for (const pair of [[0, 180], [180, 0], [37, 180], [37, 0]]) {
    const sequence = pageTurnFrames(...pair);
    assert.equal(sequence[0].angle, pair[0]);
    assert.equal(sequence.at(-1).angle, pair[1]);
    assert.ok(sequence.every((frame, index) => index === 0 || frame.offset > sequence[index - 1].offset));
  }
  for (const pair of [[NaN, 180], [0, 181], [-1, 30], [30, 30]]) {
    assert.throws(() => pageTurnFrames(...pair), /distinct angles/);
  }
});

test('paper lighting follows the same angle as the sheet and disappears at rest', () => {
  const rest = paperTurnPose(0, 700), lifted = paperTurnPose(52, 700), over = paperTurnPose(180, 700);
  assert.equal(rest.transform, 'rotateX(0deg)');
  assert.equal(lifted.transform, 'rotateX(52deg)');
  assert.equal(rest.cast.opacity, 0);
  assert.ok(lifted.cast.opacity > .2 && lifted.contact.opacity > .2 && lifted.sheen.opacity > .4);
  assert.notEqual(lifted.cast.transform, rest.cast.transform);
  assert.notEqual(lifted.cast.filter, rest.cast.filter);
  assert.notEqual(lifted.sheen.backgroundPosition, rest.sheen.backgroundPosition);
  assert.equal(over.cast.opacity, 0);
  assert.equal(over.contact.opacity, 0);
  for (const args of [[-1, 400], [181, 400], [30, 0], [NaN, 400]]) {
    assert.throws(() => paperTurnPose(...args), /positive height/);
  }
});
