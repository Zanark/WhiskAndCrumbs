import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createBakeryScene } from '../web/bakery-scene.mjs';
import { bakeryLight } from '../web/bakery-view.mjs';
import { bakeryGeometryKey, decodeBakeryLighting } from '../web/bakery-interior.mjs';
import { createTracer, sampleLighting, windowRay } from '../scripts/generate_bakery_lighting.mjs';

const scene = createBakeryScene();
const tracer = createTracer(scene);
const light = bakeryLight();
const file = readFileSync(new URL('../web/assets/bakery-light-bake.bin', import.meta.url));
const buffer = file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength);

test('baked illumination is geometry-bound, finite and visibly nonuniform', () => {
  const decoded = decodeBakeryLighting(scene, buffer);
  assert.equal(decoded.length, scene.opaque.materials.length * 4);
  assert.ok(decoded.every(value => Number.isFinite(value) && value >= 0 && value <= 1));
  for (let channel = 0; channel < 4; channel++) {
    const values = decoded.filter((_, i) => i % 4 === channel);
    assert.ok(Math.max(...values) - Math.min(...values) > 0.4);
  }
  assert.equal(new DataView(buffer).getUint32(8, true), bakeryGeometryKey(scene));
});

test('stale, truncated or changed-light bakes fail rather than silently light a different room', () => {
  assert.throws(() => decodeBakeryLighting(scene, buffer.slice(0, 30)));
  for (const byte of [0, 4, 8, 12, 24, 28]) {
    const changed = buffer.slice(0);
    new DataView(changed).setUint32(byte, 0, true);
    assert.throws(() => decodeBakeryLighting(scene, changed));
  }
  const changedScene = createBakeryScene();
  changedScene.opaque.positions[0] += 0.1;
  assert.throws(() => decodeBakeryLighting(changedScene, buffer));
});

test('daylight enters only the actual aperture and does not illuminate through the cabinet', () => {
  const open = sampleLighting(tracer, [0, 0, -2.4], [0, 1, 0], 32);
  const under = sampleLighting(tracer, [0, 0, -1.1], [0, 1, 0], 32);
  const outside = sampleLighting(tracer, [0, 0, 2.5], [0, 1, 0], 32);
  assert.equal(open[2], 1);
  assert.equal(under[2], 0);
  assert.equal(outside[2], 0);
  assert.ok(open[0] - under[0] > 0.45);
  assert.ok(open[1] > under[1] + 0.1);
  assert.ok(open[3] > 0);
});

test('actual mullion geometry blocks sunlight within the otherwise open window aperture', () => {
  function pointForWindow(y, z) {
    const length = y / light.direction[1];
    return [-4.24 - length * light.direction[0], 0, z - length * light.direction[2]];
  }
  const mullion = pointForWindow(2.55, -1.75), pane = pointForWindow(3.08, -1.75);
  assert.ok(windowRay(mullion));
  assert.ok(windowRay(pane));
  assert.equal(sampleLighting(tracer, mullion, [0, 1, 0], 8)[2], 0);
  assert.equal(sampleLighting(tracer, pane, [0, 1, 0], 8)[2], 1);
});

test('the offline bake has no random/camera input and preserves its fixed world-space results', () => {
  const random = Math.random;
  let a, b;
  try {
    Math.random = () => { throw new Error('Lighting cannot depend on noise'); };
    a = sampleLighting(tracer, [0, 0, -2.4], [0, 1, 0]);
    b = sampleLighting(tracer, [0, 0, -2.4], [0, 1, 0]);
  } finally {
    Math.random = random;
  }
  assert.deepEqual(a, b);
  assert.ok(a.every(value => value >= 0 && value <= 1));
});

test('published room modules contain no runtime ray tracer or bake generator dependency', () => {
  for (const name of ['bakery-scene.mjs', 'bakery-interior.mjs', 'bakery-view.mjs']) {
    const source = readFileSync(new URL(`../web/${name}`, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /createTracer|sampleLighting|generate_bakery_lighting|\/scripts\//, name);
  }
});
