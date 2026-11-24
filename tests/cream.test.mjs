import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { setMaxListeners } from 'node:events';
import * as model from '../web/cream-model.mjs';
import { createCreamShaders } from '../web/cream-material.mjs';
import { CREAM_FRAME_INTERVAL, CREAM_PIXEL_BUDGET, creamOutputSize, creamLifecycle,
  CREAM_MOTION_MULTIPLIER, creamSampleTime, creamPauseShortcut, creamElapsed, creamModuleUrl, initCreamEffect } from '../web/cream.mjs';
import { CURSOR_SHAPE_PROFILE, createCursorShape, updateCursorShape, resizeCursorShape, cursorShapePoint } from '../web/cream.mjs';
import { CREAM_GEOMETRY_MULTIPLIER, CREAM_MAX_GROUPS, CREAM_MAX_DROPLETS, CREAM_MAX_SPAWNS,
  CREAM_MAX_PRIMITIVES, CREAM_TRAIL_LENGTH, CREAM_SPAWN_BASE_RADIUS, createProductionRecipe,
  sampleProductionScene, sampleProductionTrail, appendCreamSpawn, creamClickAllowed } from '../web/cream.mjs';
import { CREAM_EDGE_PROFILE, productionEdgeLayout } from '../web/cream.mjs';
import { creamFieldDistances, creamContactState } from '../web/cream.mjs';
import { GROUP_GEOMETRY_MULTIPLIER, LARGE_GROUP_GEOMETRY_MULTIPLIER, GROUP_MOTION_PROFILE, sampleGroupMotion } from '../web/cream.mjs';
import { SPAWN_GEOMETRY_MULTIPLIER, SPAWN_SHAPE_PROFILE, createSpawnShape, spawnShapePoint, creamPrimitiveDistance } from '../web/cream.mjs';
import { BACKGROUND_POPULATION_SCALE, COHORT_MOTION_PROFILE, sampleCohortMotion,
  sampleProductionScoops, productionBackgroundLayout } from '../web/cream.mjs';

const text = path => readFile(new URL(path, import.meta.url), 'utf8');

test('production model is the byte-identical current owner-selected local model', async () => {
  const [production, reference] = await Promise.all([
    readFile(new URL('../web/cream-model.mjs', import.meta.url)),
    readFile(new URL('../experiments/cream-metaballs/model.mjs', import.meta.url)),
  ]);
  assert.deepEqual(production, reference);
  assert.equal(model.MAX_SCOOPS, 26);
  assert.equal(model.MAX_PRIMITIVES, 36);
  assert.equal(model.MOTION_PROFILE.speedMultiplier, .6328125);
  assert.equal(model.MOTION_PROFILE.breathRate, .0871875);
  assert.equal(model.MOTION_PROFILE.lobeRate, 1.5);
  assert.equal(model.TRAIL_PROFILE.lengthScale, .66);
  assert.equal(model.TRAIL_PROFILE.headFraction, .024);
});

test('material retains original ivory arithmetic and supports isolated strawberry regions', async () => {
  const preview = (await text('../experiments/cream-metaballs/preview.mjs')).replaceAll('\r\n', '\n');
  const material = (await text('../web/cream-material.mjs')).replaceAll('\r\n', '\n');
  for (const [start, end] of [['const vertex = `', 'const fragment = `'],
    ['float merge(', 'float surface('], ['    float q2=dot(q,q);', 'void main(){'],
    ['  cream+=vec3(', '\n`;']]) {
    assert.ok(material.includes(preview.slice(preview.indexOf(start), preview.indexOf(end))),
      `Original non-cursor material block must remain exact: ${start}`);
  }
  assert.match(material, /else d=merge\(d,length\(p-s\.xy\)-s\.z,blend\)/);
  assert.match(material, /if\(cursorTint>\.5&&i==scoopCount-1\)q=cursorWarp\(p-s\.xy,s\.z\)\/s\.z/);
  assert.match(material, /float d=surface\(p\)/);
  assert.match(material, /vec3 cream=ivory\*\(\.86\+\.14\*diffuse\)/);
  assert.match(material, /if\(cursorTint>\.5\)\{\s*float follower=d;/);
  assert.match(material, /if\(dot\(q,q\)<\.000001\)return q;\s*float theta=atan/);
  const shaders = createCreamShaders(model);
  assert.ok(shaders.vertex.startsWith('#version 300 es'));
  assert.match(shaders.fragment, /vec3\(255\.,224\.,234\.\)\/255\./);
  assert.match(shaders.fragment, /vec3 ivory=vec3\(255\.,250\.,238\.\)\/255\./);
  assert.match(shaders.fragment, /uniform vec4 scoops\[36\]/);
  assert.match(shaders.fragment, /uniform vec4 trail\[8\]/);
  assert.match(shaders.fragment, /color=vec4\(clamp\(cream,0\.,1\.\)\*coverage,alpha\)/);
  assert.doesNotMatch(shaders.fragment, /\$\{|255\.,193\.,213/);
  assert.doesNotMatch(shaders.fragment, /strawberryStart|strawberryWeight/);
  assert.match(shaders.strawberryFragment, /uniform int strawberryStart/);
  assert.match(shaders.strawberryFragment, /if\(strawberryStart>=0\)/);
  assert.match(shaders.strawberryFragment, /max\(1\.-smoothstep\(-aa,aa,pinkDistance\),smoothstep/);
  assert.match(createCreamShaders({ ...model, MAX_PRIMITIVES: CREAM_MAX_PRIMITIVES }).fragment, /uniform vec4 scoops\[48\]/);
});

test('classic material stays exact and shared contact retains its own field', async () => {
  const before = await text('../.local/interactive-cream-20261011/before-contact/cream-material.mjs');
  const specification = { ...model, MAX_PRIMITIVES: CREAM_MAX_PRIMITIVES };
  const previous = Function('model', before.replace('export function createCreamShaders', 'function createCreamShaders') +
    ';return createCreamShaders(model);')(specification);
  const current = createCreamShaders(specification);
  assert.equal(current.fragment, previous.fragment);
  assert.equal(current.strawberryFragment, previous.strawberryFragment);
  assert.match(current.contactFragment, /vec4 contactSurfaces/);
  assert.match(current.contactFragment, /coverage=max\(added,baseCoverage\*max\(softCursor,neck\)\)/);
  assert.match(current.contactFragment, /coverage=baseCoverage;\s*shadow=baseShadow/);
  assert.match(current.contactFragment, /contactActive>0\?contactTrailCount:trailCount/);
  assert.match(current.contactFragment, /if\(dot\(q,q\)<\.000001\)return q/);
});

test('no-spawn classic and shared-contact shaders remain byte-identical before shaped spawns', async () => {
  const before = await text('../.local/group-motion-20261011/before-spawn-shapes/cream-material.mjs');
  const specification = { ...model, MAX_PRIMITIVES: CREAM_MAX_PRIMITIVES };
  const previous = Function('model', before.replace('export function createCreamShaders', 'function createCreamShaders') +
    ';return createCreamShaders(model);')(specification);
  const current = createCreamShaders(specification);
  assert.equal(current.fragment, previous.fragment);
  assert.equal(current.contactFragment, previous.contactFragment);
  for (const shader of [current.spawnFragment, current.spawnContactFragment]) {
    assert.match(shader, /uniform vec4 spawnShapes\[8\]/);
    assert.match(shader, /i<strawberryStart\+spawnShapeCount/);
    assert.match(shader, /if\(spawnIndex\(i\)\)q=spawnLocal/);
    assert.match(shader, /float distance=spawnDistance/);
    assert.match(shader, /if\(dot\(q,q\)<\.0000000001\)return q/);
  }
});

test('per-click shapes are reproducible, different, noncircular and fully inscribed around the opaque click centre', () => {
  assert.equal(SPAWN_GEOMETRY_MULTIPLIER, 1);
  for (const seed of [0, 4, 17, 0xffffffff]) {
    const shapes = Array.from({ length: 24 }, (_, i) => createSpawnShape(seed, i + 1));
    assert.equal(new Set(shapes.map(shape => JSON.stringify(shape))).size, shapes.length);
    shapes.forEach((shape, i) => {
      assert.deepEqual(shape, createSpawnShape(seed, i + 1));
      assert.ok(Object.isFrozen(shape));
      assert.equal(Math.hypot(...Object.values(spawnShapePoint(0, 0, shape))), 0);
      const radii = [];
      for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 90) {
        let low = 0, high = 1;
        for (let j = 0; j < 20; j++) {
          const r = (low + high) / 2, p = spawnShapePoint(Math.cos(angle) * r, Math.sin(angle) * r, shape);
          if (Math.hypot(p.x, p.y) <= 1) low = r;
          else high = r;
        }
        radii.push((low + high) / 2);
      }
      assert.ok(Math.max(...radii) <= SPAWN_SHAPE_PROFILE.extent + 1e-6);
      assert.ok(Math.max(...radii) / Math.min(...radii) > 1.05);
      assert.ok(Math.min(...radii) > .3);
      assert.ok(Math.max(...radii.map((r, j) => Math.abs(r - radii[(j + 1) % radii.length]))) < .05);
    });
  }
  assert.throws(() => createSpawnShape(-1, 1), RangeError);
  assert.throws(() => createSpawnShape(4, 0), RangeError);
  assert.throws(() => spawnShapePoint(0, 0, { ...createSpawnShape(4, 1), aspect: 0 }), RangeError);
});

test('scalar fields and contact gates follow the inscribed shape rather than a stale bounding circle', () => {
  const p = { x: 400, y: 300, radius: 60, peak: 0, spawnShape: createSpawnShape(4, 1) };
  const circle = { ...p, spawnShape: undefined }, cursorShape = createCursorShape();
  let removedCircleContacts = 0;
  for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 12) for (let radius = 65; radius < 150; radius += 5) {
    const cursor = { x: p.x + Math.cos(angle) * radius, y: p.y + Math.sin(angle) * radius }, path = model.resetTrail(cursor);
    if (creamContactState(model, [circle], cursor, cursorShape, path, 1000, 800).active &&
        !creamContactState(model, [p], cursor, cursorShape, path, 1000, 800).active) removedCircleContacts++;
    const fields = creamFieldDistances(model, [p], cursor, cursorShape, path, 1000, 800, cursor);
    assert.equal(fields.background, creamPrimitiveDistance(p, cursor));
  }
  assert.ok(removedCircleContacts > 10);
});
test('shared scalar field makes a near-gap bridge horizontally and vertically without pushing background geometry', () => {
  const shape = createCursorShape(), width = 1000, height = 800, radius = model.cursorRadius(width, height);
  for (const vertical of [false, true]) {
    const background = [{ x: 400, y: 300, radius: 80, peak: 0 }], saved = structuredClone(background);
    const direction = vertical ? { x: 0, y: -1 } : { x: -1, y: 0 };
    const q = cursorShapePoint(direction.x, direction.y, shape), reach = radius/Math.hypot(q.x, q.y);
    const near = { x: 400+(vertical ? 0 : 80+reach+8), y: 300+(vertical ? 80+reach+8 : 0) };
    const point = { x: 400+(vertical ? 0 : 84), y: 300+(vertical ? 84 : 0) };
    const fields = creamFieldDistances(model, background, near, shape, model.resetTrail(near), width, height, point);
    assert.ok(fields.background > 0 && fields.cursor > 0 && fields.shared < 0, 'A real bridge must exist outside the ordinary union.');
    assert.ok(creamContactState(model, background, near, shape, model.resetTrail(near), width, height).head);
    const far = { x: near.x+(vertical ? 0 : 160), y: near.y+(vertical ? 160 : 0) };
    assert.equal(creamContactState(model, background, far, shape, model.resetTrail(far), width, height).active, false);
    assert.deepEqual(background, saved);
  }
});

test('the rendered trail can contact a background surface independently of a distant head', () => {
  const cursor = { x: 800, y: 400 }, shape = createCursorShape();
  const path = Array.from({ length: 8 }, (_, i) => ({ x: 800-(i+1)*50, y: 400 }));
  const state = creamContactState(model, [{ x: 500, y: 426, radius: 20, peak: 0 }], cursor, shape, path, 1000, 800);
  assert.equal(state.head, false);
  assert.equal(state.tail, true);
  assert.equal(state.active, true);
});

test('cursor continuously morphs at rest with bounded phase, area axes and unchanged click centre', () => {
  let shape = createCursorShape();
  const snapshots = [];
  for (let i = 0; i < 1800; i++) {
    shape = updateCursorShape(shape, { x: 0, y: 0 }, 1000 / 30, 24);
    assert.ok(shape.stretch >= CURSOR_SHAPE_PROFILE.minStretch && shape.stretch <= CURSOR_SHAPE_PROFILE.maxStretch);
    assert.ok(shape.phase >= 0 && shape.phase < Math.PI * 2 && shape.energy === 0);
    if (i % 150 === 0) snapshots.push(shape);
  }
  assert.ok(Math.max(...snapshots.map(s => s.stretch)) - Math.min(...snapshots.map(s => s.stretch)) > .06);
  assert.ok(new Set(snapshots.map(s => s.phase)).size > 10);
  for (const sample of snapshots) {
    const centre = cursorShapePoint(0, 0, sample);
    assert.equal(Math.hypot(centre.x, centre.y), 0);
    const radii = [];
    for (let i = 0; i < 180; i++) {
      const angle = i / 180 * Math.PI * 2;
      let low = 0, high = 1.6;
      for (let j = 0; j < 16; j++) {
        const radius = (low + high) / 2;
        const p = cursorShapePoint(Math.cos(angle) * radius, Math.sin(angle) * radius, sample);
        if (Math.hypot(p.x, p.y) <= 1) low = radius;
        else high = radius;
      }
      radii.push((low + high) / 2);
    }
    const areaRatio = radii.reduce((sum, radius) => sum + radius * radius, 0) / radii.length;
    assert.ok(areaRatio > .97 && areaRatio < 1.03);
    assert.ok(Math.max(...radii) < CURSOR_SHAPE_PROFILE.maxExtent);
    assert.ok(Math.max(...radii) / Math.min(...radii) > 1.08);
    assert.ok(Math.max(...radii.map((r, i) => Math.abs(r - radii[(i + 1) % radii.length]))) < .03, 'Organic outline must remain smooth.');
  }
});

test('cursor stretch follows smoothed head speed, direction and reversals without snapping', () => {
  let shape = createCursorShape();
  for (let i = 0; i < 60; i++) shape = updateCursorShape(shape, { x: 24, y: 0 }, 1000 / 30, 24);
  assert.ok(shape.energy > .95 && shape.stretch > 1.27);
  assert.ok(Math.abs(Math.sin(shape.angle)) < .01);
  for (const direction of [{ x: -24, y: 0 }, { x: 0, y: 24 }]) {
    for (let i = 0; i < 60; i++) {
      const next = updateCursorShape(shape, direction, 1000 / 30, 24);
      const turn = Math.atan2(Math.sin(next.angle - shape.angle), Math.cos(next.angle - shape.angle));
      assert.ok(Math.abs(turn) < .5);
      assert.ok(Math.abs(next.stretch - shape.stretch) < .05);
      assert.ok(next.energy >= 0 && next.energy <= 1 && next.stretch <= 1.38);
      shape = next;
    }
  }
  assert.ok(Math.abs(Math.cos(shape.angle)) < .01);
  for (let i = 0; i < 180; i++) shape = updateCursorShape(shape, { x: 0, y: 0 }, 1000 / 30, 24);
  assert.ok(shape.energy < .001 && shape.stretch < 1.18);
});

test('cursor update scales with head radius, preserves resize phase, and validates inputs', () => {
  const initial = createCursorShape();
  const first = updateCursorShape(initial, { x: 12, y: 6 }, 30, 24);
  const double = updateCursorShape(initial, { x: 24, y: 12 }, 30, 48);
  for (const key of ['angle', 'stretch', 'phase', 'energy']) assert.equal(first[key], double[key]);
  assert.equal(double.velocityX, first.velocityX * 2);
  const resized = resizeCursorShape(first, 2, .5);
  assert.equal(resized.phase, first.phase);
  assert.equal(resized.energy, first.energy);
  assert.equal(resized.stretch, first.stretch);
  assert.equal(resized.velocityX, first.velocityX * 2);
  assert.equal(resized.velocityY, first.velocityY * .5);
  assert.deepEqual(updateCursorShape(first, { x: 0, y: 0 }, 0, 24), first);
  assert.deepEqual(initial, createCursorShape());
  for (const args of [[initial, { x: NaN, y: 0 }, 30, 24], [initial, { x: 0, y: 0 }, -1, 24],
    [initial, { x: 0, y: 0 }, 30, 0], [{ ...initial, stretch: 8 }, { x: 0, y: 0 }, 30, 24]]) {
    assert.throws(() => updateCursorShape(...args), RangeError);
  }
  assert.throws(() => resizeCursorShape(first, 0, 1), RangeError);
});

test('cursor harmonic contour remains continuous when phase wraps at two pi', () => {
  const shape = { ...createCursorShape(), angle: 1.1, stretch: 1.32, energy: .8 };
  for (let index = 0; index < 72; index++) {
    const angle = index / 72 * Math.PI * 2, x = Math.cos(angle), y = Math.sin(angle);
    const before = cursorShapePoint(x, y, { ...shape, phase: Math.PI * 2 - 1e-7 });
    const after = cursorShapePoint(x, y, { ...shape, phase: 1e-7 });
    assert.ok(Math.hypot(before.x - after.x, before.y - after.y) < 1e-6);
  }
});

test('seed validation, stable recipes, 4-6 groups and 5-8 droplets are retained', () => {
  const totals = new Set();
  for (const seed of [...Array(64).keys(), 0xffffffff, 0x7fffffff, 0x80000000]) {
    const recipe = model.createSceneRecipe(seed);
    assert.deepEqual(recipe, model.createSceneRecipe(seed));
    assert.ok(Object.isFrozen(recipe) && Object.isFrozen(recipe.clumps));
    assert.ok(recipe.groupCount >= 4 && recipe.groupCount <= 6);
    assert.ok(recipe.dropletCount >= 5 && recipe.dropletCount <= 8);
    assert.equal(recipe.clumps.length, recipe.groupCount + recipe.dropletCount);
    totals.add(recipe.clumps.length);
    assert.equal(recipe.clumps.slice(0, 2).filter(group => group.lobeMotion.canDetach).length, 1);
  }
  assert.ok(totals.has(9) && totals.has(14), 'Both minimum and maximum supported ambient populations are exercised.');
  for (const seed of [-1, .5, NaN, Infinity, 0x100000000, '2', null]) {
    assert.throws(() => model.createSceneRecipe(seed), RangeError);
  }
});

test('ambient primitives remain finite and inside the viewport throughout peel/rejoin and resize', () => {
  for (const seed of [0, 2, 14, 25, 51, 0xffffffff]) {
    const recipe = model.createSceneRecipe(seed);
    for (const [width, height] of [[320, 568], [390, 844], [667, 375], [1440, 1000], [3840, 2160]]) {
      const scoops = model.seedScoops(width, height, recipe);
      for (const seconds of [0, .5, 4, 8, 12, 16, 29, 90, 3600]) {
        const expanded = model.expandScoops(model.sampleScoops(scoops, seconds, width, height));
        assert.ok(expanded.length <= model.MAX_PRIMITIVES);
        for (const p of expanded) {
          assert.ok([p.x, p.y, p.radius, p.peak].every(Number.isFinite));
          assert.ok(p.x - p.radius >= 0 && p.x + p.radius <= width);
          assert.ok(p.y - p.radius >= 0 && p.y + p.radius <= height);
        }
      }
      assert.deepEqual(scoops, model.seedScoops(width, height, recipe), 'Sampling must not mutate seed geometry.');
    }
  }
});

test('large divergent lobe peels and rejoins without changing parent identity', () => {
  const seeds = model.seedScoops(1440, 1000);
  const index = seeds.findIndex(scoop => scoop.lobeMotion?.canDetach);
  const movement = seeds[index].lobeMotion;
  const period = movement.period / 1.5;
  const initial = model.CLUMP_PROFILES[seeds[index].clump][movement.lobe];
  const half = model.sampleScoops(seeds, period / 2, 1440, 1000)[index].lobeState[movement.lobe];
  const end = model.sampleScoops(seeds, period, 1440, 1000)[index].lobeState[movement.lobe];
  assert.ok(Math.hypot(half[0] - initial[0], half[1] - initial[1]) > .1);
  assert.deepEqual(end, initial.slice(0, 3));
});

test('official autonomous motion samples the unchanged model at exactly twice its former time', () => {
  assert.equal(CREAM_MOTION_MULTIPLIER, 2);
  for (const seed of [2, 4, 7, 51]) {
    const recipe = model.createSceneRecipe(seed), scoops = model.seedScoops(1440, 1000, recipe);
    const modes = new Set(scoops.filter(s => s.lobeMotion).map(s => s.lobeMotion.mode));
    assert.ok(modes.has('together') && modes.has('divergent'));
    for (const time of [0, .034, .5, 3, 6, 10, 15, 30, 60]) {
      const official = model.expandScoops(model.sampleScoops(scoops, creamSampleTime(time), 1440, 1000));
      const previousAtDoubleTime = model.expandScoops(model.sampleScoops(scoops, time * 2, 1440, 1000));
      assert.deepEqual(official, previousAtDoubleTime);
    }
  }
  for (const invalid of [-1, NaN, Infinity, '2']) assert.throws(() => creamSampleTime(invalid), RangeError);
});

test('pointer head, lag, bounded trail and 0.66 rendering length remain unchanged', () => {
  const head = { x: 500, y: 300 }, target = { x: 900, y: 200 };
  const next = model.followPointer(head, target, 30);
  assert.equal(next.x, 500 + 400 * (1 - Math.exp(-30 / 82)));
  assert.equal(model.cursorRadius(1000, 800), 19.2);
  let trail = model.resetTrail(head);
  const stored = model.followTrail(trail, target, 30, 19.2);
  const rendered = model.sampleTrail(stored, target);
  rendered.forEach((point, index) => {
    assert.ok(Math.abs((point.x - target.x) - (stored[index].x - target.x) * .66) < 1e-10);
    assert.ok(Math.abs((point.y - target.y) - (stored[index].y - target.y) * .66) < 1e-10);
  });
  let lead = target;
  for (const point of stored) {
    assert.ok(Math.hypot(point.x - lead.x, point.y - lead.y) <= 19.2 * 3.2 + 1e-9);
    lead = point;
  }
  assert.deepEqual(trail, model.resetTrail(head));
});

test('automatic populations are exactly ceil(previous pieces/2), with whole groups and stable source motion phases', async () => {
  const before = await import('../.local/smooth-grouping-20261011/before/cream.mjs');
  assert.equal(BACKGROUND_POPULATION_SCALE, .5);
  assert.equal(CREAM_GEOMETRY_MULTIPLIER, 2);
  assert.equal(GROUP_GEOMETRY_MULTIPLIER, 4 / 3);
  assert.equal(LARGE_GROUP_GEOMETRY_MULTIPLIER, 2 / 3);
  const populations = new Set();
  for (const seed of [...Array(32).keys(), 0xffffffff]) {
    const previous = before.createProductionRecipe(model, seed), recipe = createProductionRecipe(model, seed);
    populations.add(recipe.groupCount);
    assert.deepEqual(recipe, createProductionRecipe(model, seed));
    assert.deepEqual(recipe.sourceClumps, previous.clumps);
    assert.equal(recipe.groupCount + recipe.dropletCount, recipe.clumps.length);
    assert.ok(recipe.groupCount >= 3 && recipe.dropletCount >= 2);
    assert.equal(recipe.sourceParents.length, new Set(recipe.sourceParents).size);
    assert.equal(recipe.clumps.filter(p => p.lobeMotion?.canDetach).length, 1);
    for (const [width, height] of [[390, 844], [1440, 1000]]) for (const seconds of [0, 8, 20, 3600]) {
      const old = before.sampleProductionScene(model, previous, width, height, seconds);
      const scene = sampleProductionScene(model, recipe, width, height, seconds);
      const raw = sampleProductionScoops(model, recipe, width, height, seconds);
      assert.equal(scene.strawberryStart, -1);
      assert.equal(scene.ambientCount, scene.primitives.length);
      assert.equal(scene.ambientCount, Math.ceil(old.ambientCount / 2));
      assert.equal(recipe.sourceAutomaticPrimitiveCount, old.ambientCount);
      assert.equal(scene.ambientCount, recipe.automaticPrimitiveCount);
      for (const actual of scene.primitives) {
        const previousPart = old.primitives.find(p => p.parent === actual.sourceParent && p.lobe === actual.lobe);
        assert.equal(actual.radius, previousPart.radius);
        assert.equal(actual.peak, 0);
        assert.equal(actual.pieceId, `${actual.sourceParent}:${actual.lobe}`);
        assert.equal(raw[actual.parent].sourceParent, actual.sourceParent);
        const parent = recipe.clumps[actual.parent];
        assert.equal(scene.primitives.filter(p => p.parent === actual.parent).length,
          parent.kind === 'group' ? model.CLUMP_PROFILES[parent.clump].length : 1);
      }
      assert.ok(scene.primitives.every(p => [p.x, p.y, p.radius, p.peak].every(Number.isFinite)));
    }
  }
  assert.ok(populations.has(3) && populations.has(5));
});

test('every production group has reproducible asynchronous multi-cycle all-member separation with unchanged piece radii and centre', () => {
  const periods = new Set(), stages = new Set();
  for (let seed = 0; seed < 32; seed++) {
    const recipe = createProductionRecipe(model, seed);
    recipe.groupMotions.forEach((motion, parent) => {
      if (!motion) return;
      assert.equal(motion.cycles.length, GROUP_MOTION_PROFILE.cycles);
      assert.equal(sampleGroupMotion(motion, 0).stage, 'joined');
      assert.deepEqual(sampleGroupMotion(motion, 0).lobeState, motion.lobes);
      assert.ok(new Set(motion.cycles.map(cycle => JSON.stringify(cycle.offsets))).size > 1);
      const mass = motion.lobes.reduce((sum, lobe) => sum + lobe[2] ** 2, 0);
      const minRadius = recipe.clumps[parent].radius * motion.geometryMultiplier *
        (1 - .025 * (1 + Math.sin(recipe.sourceParents[parent] * 2.399963)));
      motion.cycles.forEach(cycle => {
        periods.add(cycle.period);
        const ramp = (1 - cycle.joined - cycle.held) / 2;
        for (const phase of [cycle.joined / 2, cycle.joined + ramp / 2, cycle.joined + ramp + cycle.held / 2, 1 - ramp / 2]) {
          const time = motion.duration + cycle.start + phase * cycle.period - motion.offset;
          const state = sampleGroupMotion(motion, time), repeated = sampleGroupMotion(motion, time + motion.duration * 3);
          stages.add(state.stage);
          assert.equal(repeated.cycle, state.cycle);
          assert.ok(Math.abs(repeated.amount - state.amount) < 1e-12);
          for (const axis of [0, 1]) {
            const centre = state.lobeState.reduce((sum, lobe) => sum + lobe[axis] * lobe[2] ** 2, 0) / mass;
            assert.ok(Math.abs(centre - motion.centre[axis]) < 1e-12);
          }
          state.lobeState.forEach((lobe, i) => {
            assert.equal(lobe[2], motion.lobes[i][2]);
            if (state.stage === 'separated') {
              const [dx, dy] = cycle.offsets[i], original = motion.lobes[i];
              assert.ok(Math.hypot(dx, dy) > .01, 'Every member moves; none is a stationary peel anchor.');
              assert.ok(dx * (original[0] - motion.centre[0]) + dy * (original[1] - motion.centre[1]) > 0);
              for (let j = i + 1; j < state.lobeState.length; j++) {
                const other = state.lobeState[j];
                const gap = (Math.hypot(lobe[0] - other[0], lobe[1] - other[1]) - lobe[2] - other[2]) * minRadius;
                assert.ok(gap >= GROUP_MOTION_PROFILE.gapFraction - 1e-12, 'The open gap exceeds the full .04 smooth-union width.');
                const dx = motion.lobes[i][0] - motion.lobes[j][0], dy = motion.lobes[i][1] - motion.lobes[j][1];
                assert.ok(dx * (lobe[0] - other[0] - dx) + dy * (lobe[1] - other[1] - dy) >= -1e-10,
                  'No pair initially moves closer while repelling.');
              }
            }
          });
        }
      });
    });
  }
  assert.ok(periods.size > 100);
  assert.deepEqual(stages, new Set(['joined', 'repelling', 'separated', 'attracting']));
});

test('all free parents participate in seeded changing cross-parent cohorts, excluding every large edge group', () => {
  const periods = new Set();
  for (let seed = 0; seed < 32; seed++) {
    const recipe = createProductionRecipe(model, seed), motion = recipe.cohortMotion;
    assert.equal(motion.cycles.length, COHORT_MOTION_PROFILE.cycles);
    assert.deepEqual(motion.eligible, recipe.clumps.flatMap((_, parent) =>
      recipe.edgeGroups.some(e => e.parent === parent) ? [] : [parent]));
    const participants = new Set(), pairings = new Set();
    let mixed = 0, asynchronous = false;
    for (const cycle of motion.cycles) {
      periods.add(cycle.period);
      const seen = new Set();
      for (const cohort of cycle.cohorts) {
        assert.ok(cohort.parents.length >= 2 && cohort.parents.length <= 3);
        cohort.parents.forEach(parent => {
          assert.ok(motion.eligible.includes(parent) && !seen.has(parent));
          seen.add(parent); participants.add(parent);
        });
        pairings.add([...cohort.parents].sort().join(':'));
        if (new Set(cohort.parents.map(p => recipe.clumps[p].kind)).size > 1) mixed++;
      }
      const states = sampleCohortMotion(motion, cycle.start + cycle.period * .25).cohorts;
      asynchronous ||= new Set(states.map(s => s.amount)).size > 1;
    }
    assert.deepEqual([...participants].sort((a, b) => a - b), motion.eligible);
    assert.ok(pairings.size > 1 && mixed > 0);
    if (motion.eligible.length > 3) assert.ok(asynchronous);
  }
  assert.ok(periods.size > 100);
});

test('cohort ramps are quintic, replayable and join changing parents without resizing pieces', () => {
  for (const seed of [0, 4, 17, 31]) {
    const recipe = createProductionRecipe(model, seed), motion = recipe.cohortMotion, epsilon = 1e-4;
    for (const cycle of motion.cycles) for (const cohort of cycle.cohorts) {
      const ramp = (cohort.end - cohort.start - cohort.hold) / 2;
      for (const phase of [0, cohort.start, cohort.start + ramp, cohort.end - ramp, cohort.end, 1]) {
        const time = motion.duration + cycle.start + phase * cycle.period;
        const index = cycle.cohorts.indexOf(cohort);
        if (phase > 0 && phase < 1) {
          const a = sampleCohortMotion(motion, time - epsilon).cohorts[index];
          const b = sampleCohortMotion(motion, time + epsilon).cohorts[index];
          assert.ok(Math.abs(b.amount - a.amount) / (2 * epsilon) < 1e-6);
        }
        const a = sampleProductionScene(model, recipe, 1440, 1000, time - epsilon).primitives;
        const b = sampleProductionScene(model, recipe, 1440, 1000, time + epsilon).primitives;
        a.forEach((p, i) => {
          assert.equal(p.pieceId, b[i].pieceId);
          assert.ok(Math.hypot(p.x - b[i].x, p.y - b[i].y) < .1, 'No partner-switch positional jump.');
        });
      }
      const time = cycle.start + (cohort.start + ramp + cohort.hold / 2) * cycle.period;
      const state = sampleCohortMotion(motion, time);
      assert.equal(state.cohorts[cycle.cohorts.indexOf(cohort)].stage, 'joined');
      const repeated = sampleCohortMotion(motion, time + motion.duration * 3);
      assert.equal(repeated.cycle, state.cycle);
      const scene = sampleProductionScene(model, recipe, 1440, 1000, time);
      const parts = cohort.parents.map(parent => scene.primitives.find(p => p.parent === parent && p.lobe === 0));
      for (let i = 0; i < parts.length; i++) for (let j = i + 1; j < parts.length; j++) {
        const gap = Math.hypot(parts[i].x - parts[j].x, parts[i].y - parts[j].y) - parts[i].radius - parts[j].radius;
        assert.ok(Math.abs(gap - 1000 * COHORT_MOTION_PROFILE.gapFraction) < 1e-8);
      }
    }
  }
  assert.throws(() => sampleCohortMotion(null, 0), RangeError);
});

test('free full-motion envelopes fit seven viewport shapes with stable identities and no radius scaling on resize', () => {
  for (let seed = 0; seed < 32; seed++) {
    const recipe = createProductionRecipe(model, seed);
    for (const [width, height] of [[320, 568], [390, 844], [667, 375], [768, 1024], [1024, 768], [1440, 1000], [1920, 1080]]) {
      const unit = Math.min(width, height), layout = productionBackgroundLayout(recipe, width, height);
      for (let i = 0; i < layout.length; i++) for (let j = i + 1; j < layout.length; j++)
        assert.ok(Math.hypot(layout[i].x - layout[j].x, layout[i].y - layout[j].y) > layout[i].radius + layout[j].radius + unit * .04);
      for (const fraction of [0, .25, .5, .75, 1]) {
        const scene = sampleProductionScene(model, recipe, width, height, recipe.cohortMotion.duration * fraction);
        assert.equal(scene.ambientCount, recipe.automaticPrimitiveCount);
        assert.equal(new Set(scene.primitives.map(p => p.pieceId)).size, scene.ambientCount);
        for (const p of scene.primitives.filter(p => recipe.cohortMotion.eligible.includes(p.parent))) {
          assert.ok(p.x - p.radius >= 0 && p.x + p.radius <= width);
          assert.ok(p.y - p.radius >= 0 && p.y + p.radius <= height);
        }
      }
    }
  }
});

test('separated spans stay restrained independently of the category-specific canonical geometry', () => {
  const bounds = parts => [
    Math.max(...parts.map(p => p[0] + p[2])) - Math.min(...parts.map(p => p[0] - p[2])),
    Math.max(...parts.map(p => p[1] + p[2])) - Math.min(...parts.map(p => p[1] - p[2])),
  ];
  for (const seed of [...Array(32).keys(), 0xffffffff]) {
    const recipe = createProductionRecipe(model, seed);
    recipe.groupMotions.forEach((motion, parent) => {
      if (!motion) return;
      const compact = bounds(motion.lobes), radius = recipe.clumps[parent].radius;
      const maximumPreviousSpan = radius >= .14 ? .65 : 1.2;
      for (const cycle of motion.cycles) {
        const target = motion.lobes.map(([x, y, r], i) => [x + cycle.offsets[i][0], y + cycle.offsets[i][1], r]);
        bounds(target).forEach((span, axis) => assert.ok(span / compact[axis] * motion.geometryMultiplier / 2 <= maximumPreviousSpan));
      }
    });
  }
});

test('group motion has zero-velocity joined/separated endpoints and smooth cycle/table boundaries', () => {
  const recipe = createProductionRecipe(model, 17), epsilon = 1e-4;
  for (const motion of recipe.groupMotions.filter(Boolean)) for (const cycle of motion.cycles) {
    const ramp = (1 - cycle.joined - cycle.held) / 2;
    for (const phase of [0, cycle.joined, cycle.joined + ramp, cycle.joined + ramp + cycle.held, 1]) {
      const time = motion.duration + cycle.start + phase * cycle.period - motion.offset;
      const states = [-epsilon, 0, epsilon].map(delta => sampleGroupMotion(motion, time + delta));
      for (let lobe = 0; lobe < motion.lobes.length; lobe++) for (const axis of [0, 1]) {
        assert.ok(Math.abs(states[2].lobeState[lobe][axis] - states[0].lobeState[lobe][axis]) / (2 * epsilon) < 1e-6);
      }
    }
  }
  assert.throws(() => sampleGroupMotion(null, 0), RangeError);
  assert.throws(() => sampleGroupMotion(recipe.groupMotions[0], -1), RangeError);
});

test('kept edge geometry and all click-spawn bytes remain exact while automatic peaks become zero', async () => {
  const before = await import('../.local/smooth-grouping-20261011/before/cream.mjs');
  const packed = parts => new Float32Array(parts.flatMap(p => [p.x, p.y, p.radius, p.peak]));
  for (let seed = 0; seed < 32; seed++) {
    const recipe = createProductionRecipe(model, seed), oldRecipe = before.createProductionRecipe(model, seed);
    const spawns = Array.from({ length: 8 }, (_, i) => ({ id: i + 1, x: .1 + i * .1, y: .6, born: 0 }));
    for (const [width, height] of [[390, 844], [844, 390], [1440, 1000]]) for (const seconds of [0, 5, 30, 1234]) {
      const current = sampleProductionScene(model, recipe, width, height, seconds, spawns);
      const previous = before.sampleProductionScene(model, oldRecipe, width, height, seconds, spawns);
      const spawnsOnly = p => p.spawnId;
      assert.deepEqual(current.primitives.filter(spawnsOnly), previous.primitives.filter(spawnsOnly));
      assert.deepEqual(packed(current.primitives.filter(spawnsOnly)), packed(previous.primitives.filter(spawnsOnly)));
      for (const entry of recipe.edgeGroups) {
        const parts = current.primitives.filter(p => p.parent === entry.parent);
        const oldParts = previous.primitives.filter(p => p.parent === recipe.sourceParents[entry.parent]);
        assert.deepEqual(packed(parts), packed(oldParts.map(p => ({ ...p, peak: 0 }))));
      }
    }
  }
});

test('canonical geometry and large classification use source radii, not the reindexed or scaled population', async () => {
  const before = await import('../.local/smooth-grouping-20261011/before/cream.mjs');
  for (let seed = 0; seed < 32; seed++) {
    const recipe = createProductionRecipe(model, seed), oldRecipe = before.createProductionRecipe(model, seed);
    assert.deepEqual(recipe.edgeGroups.map(e => ({ ...e, parent: recipe.sourceParents[e.parent] })), oldRecipe.edgeGroups);
    const spawns = [{ id: 1, x: .5, y: .4, born: 0 }];
    for (const [width, height] of [[390, 844], [1440, 1000]]) for (const seconds of [0, 4, 17, 80]) {
      const actual = sampleProductionScene(model, recipe, width, height, seconds, spawns);
      const previous = before.sampleProductionScene(model, oldRecipe, width, height, seconds, spawns);
      for (const p of actual.primitives.filter(p => !p.spawnId)) {
        const old = previous.primitives.find(q => q.parent === p.sourceParent && q.lobe === p.lobe);
        assert.equal(p.radius, old.radius);
        const parent = recipe.clumps[p.parent], motion = recipe.groupMotions[p.parent];
        if (motion) assert.equal(motion.geometryMultiplier, parent.radius >= .14 ? 2 / 3 : 4 / 3);
      }
    }
  }
  for (const radius of [.139999, .14]) {
    const modified = { ...model, createSceneRecipe(seed) {
      const base = model.createSceneRecipe(seed);
      return { ...base, clumps: base.clumps.map((group, i) => i === 2 ? { ...group, radius } : group) };
    } };
    const recipe = createProductionRecipe(modified, 4);
    assert.equal(recipe.edgeGroups.some(group => recipe.sourceParents[group.parent] === 2), radius >= .14);
    const parent = recipe.sourceParents.indexOf(2);
    if (parent >= 0) assert.equal(recipe.groupMotions[parent].geometryMultiplier, radius >= .14 ? 2 / 3 : 4 / 3);
  }
});

test('valid spawn endpoints survive Float32 uniform round trips without changing their field', () => {
  const original = { angle: Math.PI * 2 - 1e-9, aspect: .70, phase: Math.PI * 2 - 1e-9, kind: 2 };
  const values = new Float32Array(Object.values(original));
  const uploaded = { angle: values[0], aspect: values[1], phase: values[2], kind: values[3] };
  assert.doesNotThrow(() => appendCreamSpawn([], { id: 1, x: .5, y: .5, born: 0, shape: uploaded }));
  for (const [x, y] of [[0, 0], [.7, .3], [-.5, .4]]) {
    const a = spawnShapePoint(x, y, original), b = spawnShapePoint(x, y, uploaded);
    assert.ok(Math.hypot(a.x - b.x, a.y - b.y) < 1e-6);
  }
});

test('background-only changes preserve material, cursor, renderer, spawn and lifecycle source', async () => {
  const [source, previous] = await Promise.all([
    text('../web/cream.mjs'), text('../.local/smooth-grouping-20261011/before/cream.mjs'),
  ]);
  const current = source.replaceAll('\r\n', '\n'), before = previous.replaceAll('\r\n', '\n');
  for (const [start, end] of [['function compactGroupOffsets(', 'export function sampleGroupMotion('],
    ['export function createSpawnShape(', 'export function sampleProductionTrail('],
    ['function excludedCreamTarget(', 'export function creamModuleUrl('],
    ['class CreamContextLostError', 'async function initialize('],
    ['  const schedule =', '  const on =']]) {
    assert.equal(current.slice(current.indexOf(start), current.indexOf(end)), before.slice(before.indexOf(start), before.indexOf(end)));
  }
  assert.equal(current.slice(current.indexOf('    const updatePointer ='), current.indexOf("    on(canvas, 'webglcontextlost'")),
    before.slice(before.indexOf('    const updatePointer ='), before.indexOf("    on(canvas, 'webglcontextlost'")));
  assert.deepEqual(await readFile(new URL('../web/cream-material.mjs', import.meta.url)),
    await readFile(new URL('../.local/smooth-grouping-20261011/before/cream-material.mjs', import.meta.url)));
});

test('shaped spawns halve radius only, retain complete groups and keep shape/FIFO identity through time and resize', async () => {
  const before = await import('../.local/group-motion-20261011/before-spawn-shapes/cream.mjs');
  for (const seed of [0, 4, 17, 52, 0xffffffff]) {
    const recipe = createProductionRecipe(model, seed), oldRecipe = before.createProductionRecipe(model, seed);
    let records = [];
    for (let id = 1; id <= 12; id++) records = appendCreamSpawn(records, { id, x: .4, y: .5, born: 0 }, seed);
    assert.deepEqual(records.map(p => p.id), [5, 6, 7, 8, 9, 10, 11, 12]);
    assert.equal(new Set(records.map(p => JSON.stringify(p.shape))).size, 8);
    for (const record of records) assert.deepEqual(record.shape, createSpawnShape(seed, record.id));
    for (const [width, height] of [[390, 844], [844, 390], [1440, 1000]]) for (const seconds of [0, 7, 60]) {
      const scene = sampleProductionScene(model, recipe, width, height, seconds, records);
      const old = before.sampleProductionScene(model, oldRecipe, width, height, seconds, records);
      assert.equal(scene.ambientCount, Math.ceil(old.ambientCount / 2));
      scene.primitives.slice(scene.ambientCount).forEach((p, i) => {
        const previous = old.primitives[old.ambientCount + i];
        assert.equal(p.radius, previous.radius / 2);
        assert.equal(p.x, previous.x); assert.equal(p.y, previous.y);
        assert.deepEqual(p.spawnShape, records[i].shape);
      });
    }
  }
});
test('complete large-group motion envelopes stay at balanced edges without shrinking or recentering', () => {
  assert.equal(CREAM_EDGE_PROFILE.largeFraction, .14);
  let offscreenCenters = 0;
  for (const seed of [...Array(32).keys(), 52, 0xffffffff]) {
    const recipe = createProductionRecipe(model, seed);
    assert.deepEqual(recipe.edgeGroups.map(g => g.side), ['left', 'right']);
    for (const [width, height] of [[320, 568], [390, 844], [667, 375], [768, 1024], [1024, 768], [1440, 1000], [1920, 1080]]) {
      const layout = productionEdgeLayout(model, recipe, width, height);
      assert.equal(layout.intrusion, width >= 1200 ? 32 : 16);
      assert.equal(layout.glassRight - layout.glassLeft, Math.min(1344, width - 32));
      const cyclePeaks = recipe.edgeGroups.flatMap(({ parent }) => {
        const motion = recipe.groupMotions[parent];
        return motion.cycles.map(cycle => cycle.start + cycle.period * (1 + cycle.joined) / 2 - motion.offset);
      });
      for (const seconds of [0, .1, 1, 2, 4, 6, 8, 12, 18, 30, 60, 120, 1000, 3600, ...cyclePeaks]) {
        const scene = sampleProductionScene(model, recipe, width, height, seconds);
        for (const group of layout.groups) {
          const primitives = scene.primitives.filter(p => p.parent === group.parent);
          const blend = Math.min(width, height) * .04;
          const left = primitives.map(p => p.x-p.radius).reduce((a,b) => model.smoothUnion(a,b,blend)) - group.otherUnionMargin - group.shadowLeft;
          const right = primitives.map(p => p.x+p.radius).reduce((a,b) => -model.smoothUnion(-a,-b,blend)) + group.otherUnionMargin + group.shadowRight;
          assert.ok(left >= group.envelopeMinX - 1e-7 && right <= group.envelopeMaxX + 1e-7);
          if (group.side === 'left') assert.ok(right <= layout.leftLimit + 1e-7);
          else assert.ok(left >= layout.rightLimit - 1e-7);
          offscreenCenters += primitives.filter(p => p.x < 0 || p.x > width).length;
        }
      }
      const first = sampleProductionScene(model, recipe, width, height, 0).primitives;
      const later = sampleProductionScene(model, recipe, width, height, 8).primitives;
      const originalFirst = model.sampleScoops(model.seedScoops(width, height, recipe), 0, width, height);
      const originalLater = model.sampleScoops(model.seedScoops(width, height, recipe), 8, width, height);
      for (const group of layout.groups) {
        const anchor = (items, original) => {
          const parts = items.filter(p => p.parent === group.parent), mass = parts.reduce((sum, p) => sum + p.radius ** 2, 0);
          return parts.reduce((sum, p) => sum + p.x * p.radius ** 2, 0) / mass -
            recipe.groupMotions[group.parent].centre[0] * original[group.parent].radius * recipe.groupMotions[group.parent].geometryMultiplier;
        };
        assert.ok(Math.abs((anchor(later, originalLater) - anchor(first, originalFirst)) -
          (originalLater[group.parent].x - originalFirst[group.parent].x)) < 1e-9);
      }
    }
  }
  assert.ok(offscreenCenters > 100, 'Offscreen decoration is intentional, never clamped back into the column.');
});

test('large extra groups receive balanced edge envelopes too', () => {
  const enlarged = { ...model, createSceneRecipe(seed) {
    const base = model.createSceneRecipe(seed);
    return { ...base, clumps: base.clumps.map((group, i) => i === 2 ? { ...group, radius: .17 } : group) };
  } };
  const recipe = createProductionRecipe(enlarged, 4);
  assert.equal(recipe.edgeGroups.length, 4);
  assert.deepEqual(recipe.edgeGroups.map(g => g.side), ['left', 'right', 'left', 'right']);
  for (const seconds of [0, 4, 10, 40]) {
    const layout = productionEdgeLayout(model, recipe, 390, 844);
    const scene = sampleProductionScene(model, recipe, 390, 844, seconds);
    for (const group of layout.groups) {
      const parts = scene.primitives.filter(p => p.parent === group.parent);
      if (group.side === 'left') assert.ok(parts.map(p => p.x+p.radius).reduce((a,b) => -model.smoothUnion(-a,-b,390*.04)) + group.otherUnionMargin + group.shadowRight <= layout.leftLimit+1e-7);
      else assert.ok(parts.map(p => p.x-p.radius).reduce((a,b) => model.smoothUnion(a,b,390*.04)) - group.otherUnionMargin - group.shadowLeft >= layout.rightLimit-1e-7);
    }
  }
});

test('edge placement does not move smaller groups, droplets or click spawns', () => {
  const recipe = createProductionRecipe(model, 4), withoutEdges = { ...recipe, edgeGroups: [] };
  const spawns = [{ id: 1, x: .5, y: .4, born: 0 }, { id: 2, x: .2, y: .8, born: 0 }];
  for (const [width, height] of [[390, 844], [1440, 1000]]) for (const seconds of [0, 8, 120]) {
    const actual = sampleProductionScene(model, recipe, width, height, seconds, spawns);
    const prior = sampleProductionScene(model, withoutEdges, width, height, seconds, spawns);
    actual.primitives.forEach((p, i) => {
      if (!recipe.edgeGroups.some(group => group.parent === p.parent)) assert.deepEqual(p, prior.primitives[i]);
      assert.equal(p.radius, prior.primitives[i].radius);
      assert.equal(p.y, prior.primitives[i].y);
    });
  }
});

test('48 slots retain spare capacity for the reduced background, eight FIFO spawns and a separate cursor', () => {
  assert.equal(CREAM_MAX_GROUPS * Math.max(...model.CLUMP_PROFILES.map(p => p.length)) +
    CREAM_MAX_DROPLETS + CREAM_MAX_SPAWNS + 1, 44);
  assert.ok(CREAM_MAX_PRIMITIVES >= 44);
  let spawns = [];
  for (let id = 1; id <= 500; id++) {
    const before = [...spawns];
    spawns = appendCreamSpawn(spawns, { id, x: .2, y: .3, born: 0 });
    assert.deepEqual(before.slice(-7), spawns.slice(0, -1));
    assert.ok(spawns.length <= 8 && Object.isFrozen(spawns));
  }
  assert.deepEqual(spawns.map(p => p.id), [493, 494, 495, 496, 497, 498, 499, 500]);
  for (const seed of [4, 7, 17, 51, 52]) {
    const recipe = createProductionRecipe(model, seed);
    for (const [width, height] of [[390, 844], [1440, 1000]]) {
      const scene = sampleProductionScene(model, recipe, width, height, 0, spawns);
      assert.ok(scene.primitives.length + 1 <= CREAM_MAX_PRIMITIVES);
      assert.equal(scene.primitives.length, Math.ceil(recipe.sourceAutomaticPrimitiveCount / 2) + 8);
      if (seed === 17) assert.equal(scene.primitives.length, 24);
      if (seed === 52) assert.equal(scene.primitives.length, 17);
      assert.equal(scene.primitives.length - scene.strawberryStart, 8);
      for (const p of scene.primitives.slice(scene.strawberryStart)) {
        assert.equal(p.x, width * .2); assert.equal(p.y, height * .3);
        assert.equal(p.radius, Math.min(width, height) * .075 * SPAWN_GEOMETRY_MULTIPLIER);
      }
      const moved = sampleProductionScene(model, recipe, width, height, 50, spawns);
      assert.notDeepEqual(moved.primitives, scene.primitives);
      assert.equal(CREAM_SPAWN_BASE_RADIUS, .075, 'The protected local placement uses .075 of the short axis.');
    }
  }
  assert.throws(() => appendCreamSpawn(spawns, { id: 1, x: -1, y: .2, born: 0 }), RangeError);
  assert.throws(() => sampleProductionScene(model, createProductionRecipe(model, 4), 1000, 800, 0, [...spawns, spawns[0]]), RangeError);
});

test('production trail is exactly 1.5x longer without changing stored lag, links or head', () => {
  const head = { x: 700, y: 400 };
  const stored = model.followTrail(model.resetTrail({ x: 100, y: 100 }), head, 30, 24);
  const previous = model.sampleTrail(stored, head), longer = sampleProductionTrail(model, stored, head);
  assert.equal(CREAM_TRAIL_LENGTH, .99);
  assert.equal(longer.length, 8);
  longer.forEach((point, i) => {
    assert.ok(Math.abs(point.x - head.x - (previous[i].x - head.x) * 1.5) < 1e-10);
    assert.ok(Math.abs(point.y - head.y - (previous[i].y - head.y) * 1.5) < 1e-10);
  });
});

test('only a trusted completed primary gesture can spawn; keyboard, modifiers, edits and drags cannot', () => {
  const gesture = { valid: true, released: true, ended: 100, x: 50, y: 70, type: 'mouse' };
  const click = { isTrusted: true, button: 0, detail: 1, clientX: 50, clientY: 70, pointerType: 'mouse' };
  assert.ok(creamClickAllowed(click, gesture, 101));
  assert.ok(creamClickAllowed({ ...click, defaultPrevented: true }, gesture, 101), 'Scripted same-page anchor navigation remains eligible.');
  for (const extra of [{ isTrusted: false }, { button: 2 }, { detail: 0 }, { ctrlKey: true },
    { altKey: true }, { shiftKey: true }, { metaKey: true }, { clientX: 200 },
    { pointerType: 'touch' }, { target: { isContentEditable: true } }, { target: { closest: () => ({}) } }]) {
    assert.equal(creamClickAllowed({ ...click, ...extra }, gesture, 101), false);
  }
  for (const candidate of [undefined, { ...gesture, valid: false }, { ...gesture, released: false }]) {
    assert.equal(creamClickAllowed(click, candidate, 101), false);
  }
  assert.equal(creamClickAllowed(click, gesture, 1000), false);
});

test('production backing store stays within 2.02M pixels, DPR 1.5, and half-resolution minimum', () => {
  assert.equal(CREAM_PIXEL_BUDGET, 2_000_000);
  for (const [width, height] of [[320, 568], [390, 844], [667, 375], [1440, 1000],
    [1920, 1080], [2560, 1440], [3000, 2000], [3840, 2160]]) {
    for (const ratio of [.5, .75, 1, 1.25, 1.5, 2, 3]) {
      const result = creamOutputSize(width, height, ratio);
      if (!result) {
        assert.ok(Math.min(ratio, Math.sqrt(2_000_000 / (width * height))) < .5);
        continue;
      }
      assert.ok(result.ratio >= .5 && result.ratio <= 1.5);
      assert.ok(result.width * result.height <= 2_020_000);
      assert.equal(result.width, Math.ceil(width * result.ratio));
      assert.equal(result.height, Math.ceil(height * result.ratio));
    }
  }
  assert.equal(creamOutputSize(3840, 2160, 2), null);
  assert.equal(creamOutputSize(1000, 800, .49), null);
  assert.equal(creamOutputSize(2000, 1000, 1.5, 512), null);
  assert.deepEqual(creamOutputSize(2000, 1000, 2, 1024), { width: 1024, height: 512, ratio: .512 });
  assert.deepEqual(creamOutputSize(1600, 1200, 2, 4096, [800, 600]), { width: 800, height: 600, ratio: .5 });
  for (const args of [[0, 10, 1], [10, -1, 1], [10, 10, NaN], [Infinity, 10, 1], [10, 10, 1, 0]]) {
    assert.throws(() => creamOutputSize(...args), RangeError);
  }
});

test('inactive and accessibility gates hide all cream without overriding explicit pause', () => {
  assert.deepEqual(creamLifecycle({}), { visible: true, animate: true, reason: 'moving' });
  assert.deepEqual(creamLifecycle({ paused: true }), { visible: true, animate: false, reason: 'paused' });
  assert.deepEqual(creamLifecycle({ blurred: true }), { visible: true, animate: true, reason: 'moving' });
  assert.deepEqual(creamLifecycle({ blurred: true, paused: true }), { visible: true, animate: false, reason: 'paused' });
  assert.deepEqual(creamLifecycle({ dialog: true }), { visible: true, animate: true, reason: 'moving' });
  assert.deepEqual(creamLifecycle({ dialog: true, paused: true }), { visible: true, animate: false, reason: 'paused' });
  for (const [flag, reason] of Object.entries({ failed: 'failed', lost: 'context-lost', reduced: 'reduced-motion',
    forced: 'forced-colors', printing: 'print', hidden: 'hidden',
    pageHidden: 'page-hidden', entrance: 'entrance' })) {
    for (const paused of [false, true]) {
      const state = { [flag]: true, paused };
      assert.deepEqual(creamLifecycle(state), { visible: false, animate: false, reason });
      assert.equal(creamLifecycle({ ...state, [flag]: false }).animate, !paused);
    }
  }
  assert.equal(creamLifecycle({ enabled: false }).reason, 'disabled');
});

test('only exact Alt+Shift+P outside editable and composing targets toggles motion', () => {
  const shortcut = { key: 'P', altKey: true, shiftKey: true };
  assert.equal(creamPauseShortcut(shortcut), true);
  assert.equal(creamPauseShortcut({ ...shortcut, key: 'p' }), true);
  for (const extra of [{ key: 'x' }, { key: 'Escape' }, { altKey: false }, { shiftKey: false },
    { ctrlKey: true }, { metaKey: true }, { repeat: true }, { isComposing: true }, { defaultPrevented: true },
    { target: { isContentEditable: true } }, { target: { closest: () => ({}) } },
    { composedPath: () => [{}, { isContentEditable: true }] }]) {
    assert.equal(creamPauseShortcut({ ...shortcut, ...extra }), false);
  }
  assert.equal(creamPauseShortcut({ ...shortcut, target: { closest: () => null } }), true);
});

test('30fps clock excludes inactive gaps and caps frame catch-up at 50ms', () => {
  assert.equal(CREAM_FRAME_INTERVAL, 1000 / 30);
  assert.equal(creamElapsed(0, 120000), 0);
  assert.equal(creamElapsed(100, 130), 30);
  assert.equal(creamElapsed(100, 900000), 50);
  assert.throws(() => creamElapsed(100, 99), RangeError);
  assert.throws(() => creamElapsed(-1, 100), RangeError);
});

test('all transitive imports preserve the controller version and remain public-local', async () => {
  assert.equal(creamModuleUrl('./cream-material.mjs', 'https://example.test/WhiskAndCrumbs/cream.mjs?v=abc&x=2'),
    'https://example.test/WhiskAndCrumbs/cream-material.mjs?v=abc&x=2');
  const controller = await text('../web/cream.mjs');
  assert.match(controller, /await import\(creamModuleUrl\('\.\/cream-material\.mjs'\)\)/);
  assert.doesNotMatch(controller, /experiments|\.local|PLACEMENT_SLOTS|scoops\.push|localStorage|AudioContext|requestPointerLock|requestPermission|fetch\(/);
  assert.equal((controller.match(/preventDefault\(/g) || []).length, 2, 'Only context loss and the exact pause shortcut may cancel defaults.');
  assert.match(controller, /on\(canvas, 'webglcontextlost', event => \{\s*event\.preventDefault\(\)/);
  assert.match(controller, /Pause cream motion/);
  assert.match(controller, /Resume cream motion/);
  assert.match(controller, /gl\.uniform1i\(uniforms\.trailCount, 0\)/);
  assert.match(controller, /gl\.uniform1f\(uniforms\.cursorTint, 0\)/);
  assert.match(controller, /gl\.disable\(gl\.SCISSOR_TEST\);\s*gl\.drawArrays/);
});

function controllerFixture() {
  class Target extends EventTarget {
    constructor() {
      super();
      this.dataset = {};
      this.hidden = false;
      this.style = {};
      this.textContent = '';
      this.attributes = {};
      this.clientWidth = this.scrollWidth = 190;
      this.clientHeight = this.scrollHeight = 48;
      const names = new Set();
      this.classList = { add: name => names.add(name), remove: name => names.delete(name),
        contains: name => names.has(name), toggle: (name, value) => value ? names.add(name) : names.delete(name) };
    }
    addEventListener(type, handler, options) {
      if (options?.signal) setMaxListeners(0, options.signal);
      super.addEventListener(type, handler, options);
    }
    setAttribute(name, value) { this.attributes[name] = value; }
    getBoundingClientRect() { return { left: 12, top: 720, right: 202, bottom: 768, width: 190, height: 48 }; }
  }
  const nodes = Object.fromEntries(['cream-effects', 'cream-material', 'cream-cursor',
    'cream-motion-control', 'cream-motion-toggle', 'bakery-entrance'].map(id => [id, new Target()]));
  nodes['bakery-entrance'].hidden = true;
  const calls = { contexts: 0, draws: 0, uploads: 0, programs: 0, deletedPrograms: 0,
    buffers: 0, deletedBuffers: 0, copies: 0, shapeUploads: [], contactShapeUploads: [] };
  let lost = false, focused = true, dialog = false, marker = '1';
  const uniforms = {};
  const gl = {
    NO_ERROR: 0, COMPILE_STATUS: 1, LINK_STATUS: 2, MAX_TEXTURE_SIZE: 3, MAX_RENDERBUFFER_SIZE: 4,
    MAX_VIEWPORT_DIMS: 5, SCISSOR_TEST: 6, ARRAY_BUFFER: 7, STATIC_DRAW: 8, FLOAT: 9,
    TRIANGLES: 10, VERTEX_SHADER: 11, FRAGMENT_SHADER: 12,
    createProgram() { calls.programs++; return {}; }, deleteProgram() { calls.deletedPrograms++; },
    createBuffer() { calls.buffers++; return {}; }, deleteBuffer() { calls.deletedBuffers++; },
    createShader: () => ({}), deleteShader() {}, shaderSource() {}, compileShader() {}, attachShader() {},
    detachShader() {}, getShaderParameter: () => true, getProgramParameter: () => true, linkProgram() {},
    useProgram() {}, bindBuffer() {}, bufferData() {}, getAttribLocation: () => 0,
    enableVertexAttribArray() {}, vertexAttribPointer() {}, getUniformLocation: (_, name) => name,
    getParameter: key => key === 5 ? [16384, 16384] : 16384,
    getError: () => 0, isContextLost: () => lost, viewport() {}, enable() {}, disable() {},
    scissor() {}, clearColor() {}, clear() {},
    uniform1i(name, value) { uniforms[name] = value; },
    uniform1f(name, value) { uniforms[name] = value; }, uniform2f() {},
    uniform4f(name, ...values) {
      uniforms[name] = values;
      if (name === 'cursorShape') calls.shapeUploads.push(values);
      if (name === 'contactShape') calls.contactShapeUploads.push(values);
    },
    uniform4fv(name, value) { calls.uploads++; uniforms[name] = Array.from(value); }, drawArrays() { calls.draws++; },
  };
  nodes['cream-material'].getContext = () => { calls.contexts++; return gl; };
  nodes['cream-cursor'].getContext = () => ({ clearRect() {}, drawImage() { calls.copies++; } });
  const document = Object.assign(new Target(), { body: new Target(), head: new Target(), documentElement: new Target(),
    hidden: false, hasFocus: () => focused, getElementById: id => nodes[id],
    querySelector: selector => selector === 'dialog[open]' && dialog ? {} : null });
  document.body.dataset.creamEffects = 'enabled';
  const window = new Target(), frames = new Map(), queries = new Map(), intervals = new Map();
  let nextFrame = 0, nextInterval = 0, now = 0;
  const globals = {
    document, window, innerWidth: 1000, innerHeight: 800, devicePixelRatio: 1,
    crypto: { getRandomValues: array => { array[0] = 4; return array; } },
    getComputedStyle: node => ({ display: 'block', visibility: 'visible', getPropertyValue: () => node === nodes['cream-effects'] ? marker : '' }),
    matchMedia: query => {
      if (!queries.has(query)) queries.set(query, Object.assign(new Target(), { matches: query.includes('pointer: fine') }));
      return queries.get(query);
    },
    requestAnimationFrame: callback => { frames.set(++nextFrame, callback); return nextFrame; },
    cancelAnimationFrame: id => frames.delete(id),
    performance: { now: () => now },
    setInterval: callback => { intervals.set(++nextInterval, callback); return nextInterval; },
    clearInterval: id => intervals.delete(id),
    MutationObserver: class { observe() {} disconnect() {} },
    ResizeObserver: class { observe() {} disconnect() {} },
  };
  const saved = new Map(Object.keys(globals).map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  Object.entries(globals).forEach(([key, value]) => Object.defineProperty(globalThis, key, { configurable: true, writable: true, value }));
  const fire = (node, type, properties = {}) => {
    const event = new Event(type, { cancelable: true });
    for (const [key, value] of Object.entries(properties)) Object.defineProperty(event, key, { value });
    node.dispatchEvent(event);
    return event;
  };
  return {
    nodes, calls, uniforms, document, window, frames, intervals, queries, fire,
    setLost(value) { lost = value; }, setFocus(value) { focused = value; },
    setDialog(value) { dialog = value; }, setMarker(value) { marker = value; },
    setButtonTop(top) {
      nodes['cream-motion-toggle'].getBoundingClientRect = () =>
        ({ left: 12, top, right: 202, bottom: top + 48, width: 190, height: 48 });
    },
    flush(time) { now = time; const pending = [...frames.values()]; frames.clear(); pending.forEach(callback => callback(time)); },
    heartbeat(time) { now = time; [...intervals.values()].forEach(callback => callback()); },
    restore() {
      for (const [key, descriptor] of saved) {
        if (descriptor) Object.defineProperty(globalThis, key, descriptor);
        else delete globalThis[key];
      }
    },
  };
}

test('real controller defers GPU through async entrance races and preserves user pause across interruptions', async () => {
  const f = controllerFixture();
  let controller;
  try {
    const pending = initCreamEffect({ model });
    f.nodes['bakery-entrance'].hidden = false;
    controller = await pending;
    assert.equal(f.nodes['cream-effects'].dataset.state, 'entrance');
    assert.equal(f.calls.contexts, 0);
    assert.equal(f.frames.size, 0);
    f.nodes['bakery-entrance'].hidden = true;
    f.fire(f.window, 'resize');
    assert.equal(f.calls.contexts, 1);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'scheduled');
    assert.equal(f.frames.size, 1);
    f.flush(100); f.flush(110); f.flush(134);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, '0.0340');
    assert.equal(f.frames.size, 1);
    const count = f.nodes['cream-effects'].dataset.scoopCount;
    f.fire(f.window, 'pointerdown');
    assert.equal(f.nodes['cream-effects'].dataset.scoopCount, count);
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    const held = { ...f.calls }, clock = f.nodes['cream-effects'].dataset.motionTime;
    assert.equal(f.frames.size, 0);
    f.fire(f.window, 'blur');
    assert.ok(!f.nodes['cream-effects'].hidden);
    f.fire(f.window, 'pageshow');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.ok(!f.nodes['cream-motion-control'].hidden);
    f.setDialog(true); f.fire(f.window, 'resize');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.equal(f.nodes['cream-effects'].dataset.viewerOpen, 'true');
    f.setDialog(false); f.fire(f.window, 'resize');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.equal(f.nodes['cream-motion-toggle'].textContent, 'Resume cream motion');
    assert.equal(f.calls.uploads, held.uploads);
    assert.equal(f.calls.draws, held.draws);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, clock);
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    f.flush(10000);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, clock, 'Inactive wall-clock time must not advance the recipe.');
    controller.dispose();
    assert.equal(f.frames.size, 0);
    assert.equal(f.intervals.size, 0);
    assert.equal(f.calls.deletedPrograms, f.calls.programs);
    assert.equal(f.calls.deletedBuffers, f.calls.buffers);
  } finally { controller?.dispose(); f.restore(); }
});

test('native viewers retain ambient uploads and global pause preserves focus and explicit state', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: 500, clientY: 500 });
    f.flush(100);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    f.setDialog(true); f.fire(f.window, 'resize');
    const focus = {};
    f.document.activeElement = focus;
    const before = f.calls.uploads;
    f.flush(134);
    assert.ok(f.calls.uploads > before);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.equal(f.nodes['cream-effects'].dataset.viewerOpen, 'true');
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
    assert.ok(!f.nodes['cream-effects'].hidden);
    assert.equal(f.nodes['cream-motion-toggle'].attributes['aria-keyshortcuts'], 'Alt+Shift+P');
    const shortcut = { key: 'P', altKey: true, shiftKey: true };
    const pause = f.fire(f.window, 'keydown', shortcut);
    assert.ok(pause.defaultPrevented);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.equal(f.document.activeElement, focus);
    const clock = f.nodes['cream-effects'].dataset.motionTime, uploads = f.calls.uploads;
    f.setDialog(false); f.fire(f.window, 'resize');
    f.setDialog(true); f.fire(f.window, 'resize');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.equal(f.calls.uploads, uploads);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, clock);
    assert.ok(!f.fire(f.window, 'keydown', { ...shortcut, composedPath: () => [{ isContentEditable: true }] }).defaultPrevented);
    assert.ok(!f.fire(f.window, 'keydown', { ...shortcut, ctrlKey: true }).defaultPrevented);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    f.fire(f.window, 'keydown', shortcut);
    f.flush(10000); f.flush(10034);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.equal(f.document.activeElement, focus);
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
  } finally { controller?.dispose(); f.restore(); }
});

test('real controller uploads a morphing cursor but freezes its phase during explicit pause', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: 500, clientY: 500 });
    f.flush(100); f.flush(134); f.flush(168);
    const data = f.nodes['cream-effects'].dataset;
    assert.ok(Number(data.cursorPhase) > 0 && Number(data.cursorStretch) > 1.08);
    assert.ok([...f.calls.shapeUploads, ...f.calls.contactShapeUploads].some(value => value[1] > 1.08 && value[2] > 0));
    assert.deepEqual(f.uniforms.cursorShape, [0, 1, 0, 0]);
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    const phase = data.cursorPhase, count = f.calls.shapeUploads.length;
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: 600, clientY: 500 });
    f.flush(10000);
    assert.equal(data.cursorPhase, phase);
    assert.equal(f.calls.shapeUploads.length, count);
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
  } finally { controller?.dispose(); f.restore(); }
});

test('real renderer restores ambient uniforms, native pointer, and handles after graphics loss', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: 500, clientY: 500 });
    f.flush(100);
    assert.equal(f.calls.copies, 1);
    assert.equal(f.uniforms.cursorTint, 0);
    assert.equal(f.uniforms.trailCount, 0);
    assert.deepEqual(f.uniforms.cursorShape, [0, 1, 0, 0]);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    f.fire(f.document.documentElement, 'pointerleave');
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    const clock = f.nodes['cream-effects'].dataset.motionTime;
    f.setLost(true);
    const loss = f.fire(f.nodes['cream-material'], 'webglcontextlost');
    assert.ok(loss.defaultPrevented);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'context-lost');
    assert.equal(f.frames.size, 0);
    f.setLost(false); f.fire(f.nodes['cream-material'], 'webglcontextrestored');
    assert.equal(f.calls.programs, 8);
    assert.equal(f.calls.deletedPrograms, 4);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, clock);
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
  } finally { controller?.dispose(); f.restore(); }
});

test('a frame observing lost graphics before its DOM event remains recoverable with spawn shapes intact', async () => {
  const f = controllerFixture(), warn = console.warn;
  let controller;
  console.warn = () => {};
  try {
    controller = await initCreamEffect({ model });
    const mouse = { isTrusted: true, isPrimary: true, pointerId: 1, pointerType: 'mouse', button: 0, clientX: 500, clientY: 400 };
    f.fire(f.window, 'pointerdown', { ...mouse, buttons: 1 });
    f.fire(f.window, 'pointerup', { ...mouse, buttons: 0 });
    f.fire(f.window, 'click', { ...mouse, detail: 1 });
    f.flush(100);
    const records = f.nodes['cream-effects'].dataset.spawnRecords;
    f.setLost(true);
    f.flush(140);
    f.fire(f.nodes['cream-material'], 'webglcontextlost');
    f.setLost(false);
    f.fire(f.nodes['cream-material'], 'webglcontextrestored');
    f.flush(180);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.equal(f.nodes['cream-effects'].dataset.spawnRecords, records);
    assert.equal(f.uniforms.spawnShapeCount, 1);
    assert.equal(f.frames.size, 1);
  } finally { controller?.dispose(); console.warn = warn; f.restore(); }
});

test('visible blur keeps ambient alive while only focused input restores the replacement cursor', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    f.flush(100);
    f.fire(f.window, 'blur');
    f.setFocus(false);
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: 100, clientY: 100 });
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.equal(f.frames.size, 1);
    assert.ok(f.document.body.classList.contains('has-cream-effects'));
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
    f.flush(134);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, '0.0340');
    f.setFocus(true);
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: 100, clientY: 100 });
    f.flush(168);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, '0.0680', 'Focus recovery must not reset a running ambient clock.');
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    const query = f.queries.get('(prefers-reduced-motion: reduce)');
    query.matches = true; f.fire(query, 'change');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'reduced-motion');
    const uploads = f.calls.uploads;
    f.fire(f.window, 'pageshow');
    assert.equal(f.frames.size, 0);
    assert.equal(f.calls.uploads, uploads);
    assert.ok(f.nodes['cream-effects'].hidden && f.nodes['cream-motion-control'].hidden);
    query.matches = false; f.fire(query, 'change');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'scheduled');
  } finally { controller?.dispose(); f.restore(); }
});

test('a visible return without a focus event restarts ambient and keeps the native cursor', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    f.flush(100); f.flush(134);
    f.setFocus(false); f.fire(f.window, 'blur');
    f.document.hidden = true; f.fire(f.document, 'visibilitychange');
    assert.equal(f.frames.size, 0);
    assert.equal(f.intervals.size, 0);
    const clock = f.nodes['cream-effects'].dataset.motionTime, uploads = f.calls.uploads;
    f.document.hidden = false; f.fire(f.document, 'visibilitychange');
    assert.equal(f.frames.size, 1);
    assert.equal(f.calls.uploads, uploads);
    f.flush(5000);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, clock);
    f.flush(5034);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, '0.0680');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
    assert.ok(f.document.body.classList.contains('has-cream-effects'));
  } finally { controller?.dispose(); f.restore(); }
});

test('a normal-flow footer pause button outside the viewport never blocks ambient motion', async () => {
  const f = controllerFixture();
  let controller;
  try {
    f.setButtonTop(6000);
    controller = await initCreamEffect({ model });
    assert.equal(f.nodes['cream-effects'].dataset.state, 'scheduled');
    assert.ok(!f.nodes['cream-motion-control'].hidden);
    f.flush(100); f.flush(134);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    const uploads = f.calls.uploads;
    f.setButtonTop(-300); f.fire(f.window, 'resize');
    f.flush(168);
    assert.ok(f.calls.uploads > uploads);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, '0.0680');
    assert.ok(f.document.body.classList.contains('has-cream-effects'));
    f.setButtonTop(720); f.fire(f.window, 'resize');
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
    assert.equal(f.nodes['cream-motion-toggle'].textContent, 'Resume cream motion');
    assert.equal(f.frames.size, 0);
  } finally { controller?.dispose(); f.restore(); }
});

test('actual renderer uploads match the group-aware production adapter at 2t', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    for (let time = 100; time <= 30100; time += 40) f.flush(time);
    const data = f.nodes['cream-effects'].dataset;
    assert.equal(Number(data.motionTime), 30);
    assert.equal(Number(data.sampleTime), 60);
    assert.equal(Number(data.groupGeometryMultiplier), 4 / 3);
    assert.equal(Number(data.largeGroupGeometryMultiplier), 2 / 3);
    assert.equal(data.groupMotionMode, 'repel-attract');
    const recipe = createProductionRecipe(model, 4);
    const expected = sampleProductionScene(model, recipe, 1000, 800, 60).primitives
      .flatMap(s => [s.x, s.y, s.radius, s.peak]);
    assert.deepEqual(f.uniforms['scoops[0]'].slice(0, expected.length), Array.from(new Float32Array(expected)));
    assert.equal(f.uniforms.cursorTint, 0);
    assert.equal(f.uniforms.trailCount, 0);
  } finally { controller?.dispose(); f.restore(); }
});

test('primary down, held movement, up and spawn keep the follower painted without resetting its shape', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    const mouse = { isTrusted: true, isPrimary: true, pointerId: 1, pointerType: 'mouse', button: 0, clientX: 500, clientY: 400 };
    f.fire(f.window, 'pointerdown', { ...mouse, buttons: 1 });
    f.flush(100);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '0');
    f.fire(f.window, 'pointerup', { ...mouse, buttons: 0 });
    const click = f.fire(f.window, 'click', { ...mouse, detail: 1 });
    assert.equal(click.defaultPrevented, false);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    f.flush(140);
    assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '1');
    assert.equal(f.nodes['cream-effects'].dataset.spawnGeometryMultiplier, '1');
    assert.equal(f.uniforms.spawnShapeCount, 1);
    const spawnShape = createSpawnShape(4, 1);
    assert.deepEqual(f.uniforms['spawnShapes[0]'].slice(0, 4),
      Array.from(new Float32Array([spawnShape.angle, spawnShape.aspect, spawnShape.phase, spawnShape.kind])));
    assert.ok(f.uniforms['spawnShapes[0]'].slice(4).every(value => value === 0));
    assert.equal(f.uniforms.strawberryStart, Number(f.nodes['cream-effects'].dataset.ambientPrimitiveCount));
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    const phase = Number(f.nodes['cream-effects'].dataset.cursorPhase);
    f.fire(f.window, 'pointerdown', { ...mouse, buttons: 1 });
    f.fire(f.window, 'pointermove', { ...mouse, clientX: 700, buttons: 1 });
    f.flush(180);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    assert.ok(Number(f.nodes['cream-effects'].dataset.cursorPhase) > phase);
    f.fire(f.window, 'pointerup', { ...mouse, clientX: 700, buttons: 0 });
    f.fire(f.window, 'click', { ...mouse, clientX: 700, detail: 1 });
    f.flush(220);
    assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '1', 'Dragging is not a second placement.');
    for (let i = 0; i < 20; i++) {
      f.fire(f.window, 'pointerdown', { ...mouse, buttons: 1 });
      f.fire(f.window, 'pointerup', { ...mouse, buttons: 0 });
      f.fire(f.window, 'click', { ...mouse, detail: 1 });
    }
    f.flush(260);
    assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '8');
    assert.equal(f.frames.size, 1);
    assert.equal(f.intervals.size, 1);
    assert.deepEqual(JSON.parse(f.nodes['cream-effects'].dataset.spawnRecords).map(p => p.id), [14, 15, 16, 17, 18, 19, 20, 21]);
    const queue = f.nodes['cream-effects'].dataset.spawnRecords;
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    const uploads = f.calls.uploads;
    f.fire(f.window, 'pointerdown', { ...mouse, buttons: 1 });
    f.fire(f.window, 'pointerup', { ...mouse, buttons: 0 });
    f.fire(f.window, 'click', { ...mouse, detail: 1 });
    f.flush(10000);
    assert.equal(f.calls.uploads, uploads);
    assert.equal(f.nodes['cream-effects'].dataset.spawnRecords, queue);
    f.setLost(true); f.fire(f.nodes['cream-material'], 'webglcontextlost');
    f.setLost(false); f.fire(f.nodes['cream-material'], 'webglcontextrestored');
    assert.equal(f.nodes['cream-effects'].dataset.spawnRecords, queue);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'paused');
  } finally { controller?.dispose(); f.restore(); }
});

test('touch taps place once, but swipes, cancellation, multitouch and keyboard clicks never place', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    f.flush(100);
    const touch = { isTrusted: true, isPrimary: true, pointerId: 1, pointerType: 'touch',
      button: 0, clientX: 500, clientY: 400 };
    f.fire(f.window, 'pointerdown', touch);
    f.fire(f.window, 'pointerup', touch);
    f.fire(f.window, 'click', { ...touch, detail: 1 });
    f.flush(140);
    assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '1');
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
    for (const path of ['swipe', 'cancel', 'multi', 'keyboard']) {
      f.fire(f.window, 'pointerdown', touch);
      if (path === 'swipe') f.fire(f.window, 'pointermove', { ...touch, clientY: 450 });
      if (path === 'cancel') f.fire(f.window, 'pointercancel', touch);
      if (path === 'multi') f.fire(f.window, 'pointerdown', { ...touch, pointerId: 2, isPrimary: false });
      f.fire(f.window, 'pointerup', touch);
      f.fire(f.window, 'click', { ...touch, detail: path === 'keyboard' ? 0 : 1 });
      f.flush(180);
      assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '1', path);
    }
    const records = f.nodes['cream-effects'].dataset.spawnRecords;
    globalThis.innerWidth = 500; globalThis.innerHeight = 900;
    f.fire(f.window, 'resize');
    assert.equal(f.nodes['cream-effects'].dataset.spawnRecords, records);
    assert.equal(f.nodes['cream-effects'].dataset.cursorRadius, '12.000');
    f.setDialog(true);
    f.fire(f.window, 'pointerdown', touch);
    f.fire(f.window, 'pointerup', touch);
    f.fire(f.window, 'click', { ...touch, detail: 1 });
    f.flush(220);
    assert.equal(f.nodes['cream-effects'].dataset.spawnRecords, records);
  } finally { controller?.dispose(); f.restore(); }
});

test('secondary-button release retains the native context-menu cursor until ordinary mouse return', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    const mouse = { isTrusted: true, isPrimary: true, pointerId: 1, pointerType: 'mouse', clientX: 500, clientY: 400 };
    f.fire(f.window, 'pointermove', { ...mouse, buttons: 0 });
    f.flush(100);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    for (const button of [1, 2]) {
      f.fire(f.window, 'pointerdown', { ...mouse, button, buttons: button === 2 ? 2 : 4 });
      f.fire(f.window, 'contextmenu', mouse);
      f.fire(f.window, 'pointerup', { ...mouse, button, buttons: 0 });
      f.flush(140);
      assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
      assert.equal(f.nodes['cream-effects'].dataset.spawnCount, '0');
    }
    f.fire(f.window, 'pointermove', { ...mouse, buttons: 0 });
    f.flush(180);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
  } finally { controller?.dispose(); f.restore(); }
});

test('shared contact appends only a render-time head, keeps neutral legacy state, and clears when paused or native', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    const recipe = createProductionRecipe(model, 4);
    const scene = sampleProductionScene(model, recipe, 1000, 800, 0);
    const target = scene.primitives.find(p => p.parent === 6);
    const before = structuredClone(scene.primitives), draws = f.calls.draws;
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: target.x, clientY: target.y });
    f.flush(100);
    const data = f.nodes['cream-effects'].dataset;
    assert.equal(data.contactActive, 'true');
    assert.equal(f.calls.draws-draws, 2, 'Only one small foreground pass and one main pass are allowed.');
    assert.equal(Number(data.primitiveCount), scene.primitives.length+1);
    assert.equal(Number(data.scenePrimitiveCount), scene.primitives.length);
    assert.equal(f.uniforms.contactPass, 0);
    assert.equal(f.uniforms.contactActive, 1);
    assert.equal(f.uniforms.ambientCount, scene.primitives.length);
    assert.equal(f.uniforms.cursorTint, 0);
    assert.equal(f.uniforms.trailCount, 0);
    assert.deepEqual(f.uniforms.cursorShape, [0, 1, 0, 0]);
    const expected = Array.from(new Float32Array(scene.primitives.flatMap(p => [p.x,p.y,p.radius,p.peak])));
    assert.deepEqual(f.uniforms['scoops[0]'].slice(0, expected.length), expected);
    assert.deepEqual(scene.primitives, before);
    assert.ok(f.document.body.classList.contains('cream-cursor-active'));
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    assert.equal(data.contactActive, 'false');
    assert.equal(Number(data.primitiveCount), scene.primitives.length);
    const uploads = f.calls.uploads;
    f.flush(5000);
    assert.equal(f.calls.uploads, uploads);
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    f.fire(f.window, 'pointermove', { pointerType: 'mouse', buttons: 0, clientX: target.x, clientY: target.y });
    f.flush(6000);
    assert.equal(data.contactActive, 'true');
    f.document.hidden = true;
    f.fire(f.document, 'visibilitychange');
    assert.equal(data.contactActive, 'false');
    f.document.hidden = false;
    f.fire(f.document, 'visibilitychange');
    assert.equal(data.contactActive, 'false', 'A visible return must not briefly expose the old contact image.');
    assert.ok(!f.document.body.classList.contains('cream-cursor-active'));
  } finally { controller?.dispose(); f.restore(); }
});

test('stalled frame delivery is not reported as moving and heartbeat never paints', async () => {
  const f = controllerFixture();
  let controller;
  try {
    controller = await initCreamEffect({ model });
    assert.equal(f.nodes['cream-effects'].dataset.state, 'scheduled');
    f.flush(100); f.flush(134);
    const uploads = f.calls.uploads, clock = f.nodes['cream-effects'].dataset.motionTime;
    f.heartbeat(2000);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'waiting-for-frame');
    assert.equal(f.calls.uploads, uploads);
    assert.equal(f.nodes['cream-effects'].dataset.motionTime, clock);
    f.flush(2034);
    assert.equal(f.nodes['cream-effects'].dataset.state, 'moving');
    assert.ok(Number(f.nodes['cream-effects'].dataset.motionTime) > Number(clock));
    f.fire(f.nodes['cream-motion-toggle'], 'click');
    assert.equal(f.intervals.size, 0);
  } finally { controller?.dispose(); f.restore(); }
});
