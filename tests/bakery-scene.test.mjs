import assert from 'node:assert/strict';
import test from 'node:test';
import { createBakeryScene, MATERIALS } from '../web/bakery-scene.mjs';

const scene = createBakeryScene();
const geometries = [scene.opaque, ...scene.transparent];
const near = (actual, expected, tolerance = 1e-6) =>
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} differs from ${expected}`);
const subtract = (a, b) => a.map((value, i) => value - b[i]);
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a.reduce((sum, value, i) => sum + value * b[i], 0);
const getGroup = id => {
  const group = scene.groups.find(candidate => candidate.id === id);
  assert.ok(group, `Missing group ${id}`);
  return group;
};

function vertices(geometry, predicate = () => true) {
  const result = [];
  for (let i = 0; i < geometry.materials.length; i++) {
    const position = Array.from(geometry.positions.subarray(i * 3, i * 3 + 3));
    if (predicate(position, geometry.materials[i])) result.push(position);
  }
  return result;
}

test('the stable material contract is frozen and complete', () => {
  assert.ok(Object.isFrozen(MATERIALS));
  assert.deepEqual(MATERIALS, {
    plaster: 0, wood: 1, darkWood: 2, greenPaint: 3, brass: 4,
    glass: 5, ceramic: 6, bread: 7, icing: 8, chocolate: 9,
    leaf: 10, linen: 11, window: 12, stone: 13, berry: 14
  });
  assert.deepEqual([...new Set(geometries.flatMap(mesh => Array.from(mesh.materials)))].sort((a, b) => a - b),
    Object.values(MATERIALS));
});

test('geometry is finite nonindexed typed data within the render budgets', () => {
  assert.ok(scene.opaque.materials.length > 20000);
  assert.ok(scene.opaque.materials.length < 80000);
  assert.ok(scene.transparent.reduce((total, mesh) => total + mesh.materials.length, 0) < 400);
  for (const mesh of geometries) {
    const count = mesh.materials.length;
    assert.equal(count % 3, 0);
    for (const [key, stride] of Object.entries({ positions: 3, normals: 3, uvs: 2, colors: 4, materials: 1 })) {
      assert.ok(mesh[key] instanceof Float32Array, key);
      assert.equal(mesh[key].length, count * stride);
      assert.ok(mesh[key].every(Number.isFinite), key);
    }
    assert.ok(mesh.materials.every(value => Number.isInteger(value) && value >= 0 && value <= 14));
    assert.ok(mesh.colors.every(value => value >= 0 && value <= 1));
  }
});

test('every triangle is nondegenerate, CCW and consistent with all unit normals', () => {
  for (const mesh of geometries) {
    for (let offset = 0; offset < mesh.positions.length; offset += 9) {
      const a = Array.from(mesh.positions.subarray(offset, offset + 3));
      const b = Array.from(mesh.positions.subarray(offset + 3, offset + 6));
      const c = Array.from(mesh.positions.subarray(offset + 6, offset + 9));
      const face = cross(subtract(b, a), subtract(c, a));
      assert.ok(Math.hypot(...face) > 1e-10, `Degenerate triangle at ${offset}`);
      for (let vertex = 0; vertex < 3; vertex++) {
        const normal = Array.from(mesh.normals.subarray(offset + vertex * 3, offset + vertex * 3 + 3));
        near(Math.hypot(...normal), 1, 1e-5);
        assert.ok(dot(face, normal) > 0, `Reversed normal at ${offset + vertex * 3}`);
      }
    }
  }
});

test('floor, room bounds and semantic bounds agree with emitted world coordinates', () => {
  const allVertices = geometries.flatMap(mesh => vertices(mesh));
  for (let axis = 0; axis < 3; axis++) {
    near(scene.bounds.min[axis], allVertices.reduce((value, point) => Math.min(value, point[axis]), Infinity));
    near(scene.bounds.max[axis], allVertices.reduce((value, point) => Math.max(value, point[axis]), -Infinity));
    near(scene.bounds.min[axis], [-4.4, 0, -7][axis]);
    near(scene.bounds.max[axis], [4.4, 4.5, 3][axis]);
  }
  assert.equal(new Set(scene.groups.map(group => group.id)).size, scene.groups.length);
  for (const group of scene.groups) {
    assert.equal(typeof group.floorContact, 'boolean');
    for (let axis = 0; axis < 3; axis++) {
      assert.ok(Number.isFinite(group.min[axis]) && Number.isFinite(group.max[axis]));
      assert.ok(group.min[axis] <= group.max[axis]);
      assert.ok(group.min[axis] >= scene.bounds.min[axis] && group.max[axis] <= scene.bounds.max[axis]);
      assert.ok(allVertices.some(point => point[axis] === group.min[axis]), `${group.id} min ${axis}`);
      assert.ok(allVertices.some(point => point[axis] === group.max[axis]), `${group.id} max ${axis}`);
    }
    if (group.floorContact) assert.equal(group.min[1], 0, group.id);
  }
  for (const id of ['room-floor', 'counter-cabinet', 'counter-footing', 'back-counter', 'side-prep-table', 'floor-plant']) {
    assert.ok(getGroup(id).floorContact, id);
  }
});

test('counter is a full grounded cabinet rather than a raised or thin display facade', () => {
  const cabinet = getGroup('counter-cabinet');
  const footing = getGroup('counter-footing');
  const glass = getGroup('glass-case');
  assert.equal(cabinet.min[1], 0);
  assert.equal(footing.min[1], 0);
  near(cabinet.max[1], scene.landmarkPoints.counterTop[1]);
  near(glass.min[1], cabinet.max[1]);
  assert.ok(cabinet.max[2] - cabinet.min[2] > 1.4);
  assert.ok(cabinet.max[0] - cabinet.min[0] > 5);
  const body = vertices(scene.opaque, ([x, y, z], material) =>
    material === MATERIALS.wood && Math.abs(x) < 2.52 && z > -1.9 && z < -0.45 && y < 1.1);
  assert.ok(body.some(([, y]) => Math.abs(y - 0.16) < 1e-6));
  assert.ok(body.some(([, y]) => Math.abs(y - 1.04) < 1e-6));
  const feet = vertices(scene.opaque, ([x, y, z]) => Math.abs(x) < 2.6 && y === 0 && z > -2 && z < -0.4);
  assert.ok(feet.some(([x]) => x < -2.3));
  assert.ok(feet.some(([x]) => x > 2.3));
});

test('four distinct three-dimensional bakes sit exactly on plates supported by their shelves', () => {
  const ids = {
    lowerLeft: 'cake-layered-cream', lowerRight: 'cake-cocoa-rosettes',
    upperLeft: 'cake-berry-wreath', upperRight: 'cake-golden-ring'
  };
  for (const tier of ['lower', 'upper']) {
    const shelf = scene.landmarkPoints[`${tier}ShelfTop`];
    near(getGroup(`display-cakes-${tier}`).min[1], shelf[1]);
    for (const side of ['Left', 'Right']) {
      const base = scene.landmarkPoints[`${tier}Cake${side}Base`];
      const plate = scene.landmarkPoints[`${tier}Plate${side}Base`];
      const cake = getGroup(ids[tier + side]);
      near(plate[1], shelf[1]);
      near(base[1], plate[1] + 0.024);
      near(cake.min[1], base[1]);
      assert.ok(cake.max[1] - cake.min[1] > 0.25);
      assert.ok(cake.max[0] - cake.min[0] > 0.60);
      assert.ok(cake.max[2] - cake.min[2] > 0.60);
      const supportVertices = vertices(scene.opaque, ([x, y, z], material) =>
        material === MATERIALS.ceramic && Math.abs(x - base[0]) <= 0.45 && Math.abs(z - base[2]) <= 0.45 &&
        y >= shelf[1] - 1e-6 && y <= base[1] + 1e-6);
      assert.ok(supportVertices.some(([, y]) => Math.abs(y - plate[1]) < 1e-6), 'Plate rests on shelf');
      assert.ok(supportVertices.some(([, y]) => Math.abs(y - base[1]) < 1e-6), 'Cake meets plate');
      assert.ok(cake.max[1] < (tier === 'lower' ? 1.644 : 2.065), 'Cake clears shelf/case above it');
    }
  }
  assert.ok(scene.landmarkPoints.lowerCakeLeftBase[0] < -1);
  assert.ok(scene.landmarkPoints.lowerCakeRightBase[0] > 1);
});

test('contact landmarks lie on actual downward cake faces and upward plate faces', () => {
  const mesh = scene.opaque;
  function onTriangle(point, triangle) {
    if (!triangle.every(vertex => Math.abs(vertex[1] - point[1]) < 1e-6)) return false;
    const edges = triangle.map((a, index) => {
      const b = triangle[(index + 1) % 3];
      return (b[0] - a[0]) * (point[2] - a[2]) - (b[2] - a[2]) * (point[0] - a[0]);
    });
    return edges.every(value => value >= -1e-6) || edges.every(value => value <= 1e-6);
  }
  for (const name of ['lowerCakeLeftContact', 'lowerCakeRightContact', 'upperCakeLeftContact', 'upperCakeRightContact']) {
    const point = scene.landmarkPoints[name];
    let hasCake = false;
    let hasPlate = false;
    for (let vertex = 0; vertex < mesh.materials.length; vertex += 3) {
      const material = mesh.materials[vertex];
      if (![MATERIALS.ceramic, MATERIALS.bread, MATERIALS.icing, MATERIALS.chocolate].includes(material)) continue;
      const triangle = [0, 1, 2].map(i => Array.from(mesh.positions.subarray((vertex + i) * 3, (vertex + i + 1) * 3)));
      if (!onTriangle(point, triangle)) continue;
      const normalY = mesh.normals[vertex * 3 + 1];
      if (material === MATERIALS.ceramic && normalY > 0.99) hasPlate = true;
      if (material !== MATERIALS.ceramic && normalY < -0.99) hasCake = true;
    }
    assert.ok(hasCake, `${name} is on actual cake underside`);
    assert.ok(hasPlate, `${name} is on actual plate top`);
  }
});

test('thin filling bands have outward walls rather than self-folded bevels', () => {
  const mesh = scene.opaque;
  const center = scene.landmarkPoints.lowerCakeLeftBase;
  let count = 0;
  for (let vertex = 0; vertex < mesh.materials.length; vertex++) {
    if (mesh.materials[vertex] !== MATERIALS.icing) continue;
    const [x, y, z] = mesh.positions.subarray(vertex * 3, vertex * 3 + 3);
    const [nx, ny, nz] = mesh.normals.subarray(vertex * 3, vertex * 3 + 3);
    if (y < center[1] + 0.073 || y > center[1] + 0.10 || Math.abs(ny) > 1e-6) continue;
    if (Math.hypot(x - center[0], z - center[2]) > 0.36) continue;
    assert.ok(nx * (x - center[0]) + nz * (z - center[2]) > 0);
    count++;
  }
  assert.ok(count > 0);
});

test('left casement has a genuine hole in the opaque wall, not an emissive overlaid picture', () => {
  const wallTriangles = [];
  const mesh = scene.opaque;
  for (let i = 0; i < mesh.materials.length; i += 3) {
    if (mesh.materials[i] !== MATERIALS.plaster) continue;
    const points = [0, 1, 2].map(j => Array.from(mesh.positions.subarray((i + j) * 3, (i + j) * 3 + 3)));
    if (!points.every(([x]) => x < -4.2)) continue;
    wallTriangles.push(points);
    const minimumY = Math.min(...points.map(point => point[1]));
    const maximumY = Math.max(...points.map(point => point[1]));
    const minimumZ = Math.min(...points.map(point => point[2]));
    const maximumZ = Math.max(...points.map(point => point[2]));
    assert.ok(maximumY <= 1.300001 || minimumY >= 3.799999 ||
      maximumZ <= -4.799999 || minimumZ >= -1.200001, 'Plaster eclipses window opening');
  }
  assert.ok(wallTriangles.length > 0);
  const window = vertices(mesh, ([x], material) => material === MATERIALS.window && x < -4.3);
  assert.equal(window.length, 6);
  assert.ok(window.every(([x]) => Math.abs(x + 4.38) < 1e-6));
});

test('the front remains open below a full downward-facing ceiling', () => {
  const mesh = scene.opaque;
  const ceiling = getGroup('room-ceiling');
  assert.equal(ceiling.floorContact, false);
  near(ceiling.min[1], 4.5);
  near(ceiling.max[1], 4.5);
  near(ceiling.min[0], -4.4);
  near(ceiling.max[0], 4.4);
  near(ceiling.min[2], -7);
  near(ceiling.max[2], 3);
  let ceilingArea = 0;
  let ceilingVertices = 0;
  for (let i = 0; i < mesh.materials.length; i += 3) {
    if (mesh.materials[i] !== MATERIALS.plaster) continue;
    const p = [0, 1, 2].map(j => Array.from(mesh.positions.subarray((i + j) * 3, (i + j) * 3 + 3)));
    const atFront = p.every(([, , z]) => Math.abs(z - 3) < 1e-6);
    const atCeiling = p.every(([, y]) => Math.abs(y - 4.5) < 1e-6);
    if (atFront) assert.ok(p.every(([x]) => Math.abs(x) >= 4.23));
    if (atCeiling && mesh.normals[i * 3 + 1] < -0.99) {
      ceilingArea += Math.hypot(...cross(subtract(p[1], p[0]), subtract(p[2], p[0]))) / 2;
      ceilingVertices += 3;
      for (let vertex = 0; vertex < 3; vertex++) {
        assert.deepEqual(Array.from(mesh.normals.subarray((i + vertex) * 3, (i + vertex) * 3 + 3)), [0, -1, 0]);
      }
    }
  }
  near(ceilingArea, 88, 1e-5);
  assert.equal(ceilingVertices, 6);
});

test('counter-footing contact landmarks share the physical floor level', () => {
  const footing = getGroup('counter-footing');
  for (const key of ['counterFootingLeftContact', 'counterFootingRightContact', 'counterFootingCenterContact']) {
    const point = scene.landmarkPoints[key];
    assert.equal(point[1], 0);
    point.forEach((value, axis) => assert.ok(value >= footing.min[axis] - 1e-6 && value <= footing.max[axis] + 1e-6));
  }
});

test('each glass pane is independently sortable, two-sided and excluded from opaque shadows', () => {
  assert.equal(new Set(scene.transparent.map(mesh => mesh.id)).size, scene.transparent.length);
  assert.equal(scene.transparent.length, 7);
  assert.ok(scene.opaque.materials.every(material => material !== MATERIALS.glass));
  assert.ok(scene.opaque.colors.every((value, i) => i % 4 !== 3 || value === 1));
  const glass = getGroup('glass-case');
  for (const mesh of scene.transparent) {
    assert.ok(mesh.materials.every(material => material === MATERIALS.glass));
    assert.equal(mesh.materials.length, 12);
    const points = vertices(mesh);
    for (let axis = 0; axis < 3; axis++) {
      near(mesh.center[axis], points.reduce((sum, point) => sum + point[axis], 0) / points.length);
      assert.ok(points.every(point => point[axis] >= glass.min[axis] && point[axis] <= glass.max[axis]));
    }
    assert.ok(mesh.colors.every((value, i) => i % 4 !== 3 || value >= 0.07999 && value <= 0.18001));
    for (let axis = 0; axis < 3; axis++) near(mesh.normals[axis], -mesh.normals[18 + axis]);
  }
});

test('UVs use repeating surface distances and all landmarks are finite world points', () => {
  assert.ok(scene.opaque.uvs.some(value => value > 2));
  assert.ok(scene.opaque.uvs.some(value => value < 0));
  assert.ok(Object.keys(scene.landmarkPoints).length >= 20);
  for (const [name, point] of Object.entries(scene.landmarkPoints)) {
    assert.equal(point.length, 3, name);
    assert.ok(point.every(Number.isFinite), name);
    point.forEach((value, axis) => assert.ok(value >= scene.bounds.min[axis] - 1e-6 && value <= scene.bounds.max[axis] + 1e-6, name));
  }
});

test('the tall walnut shelving contains a substantial varied original bread collection', () => {
  const alcove = getGroup('bread-alcove'), bakes = getGroup('stocked-original-breads');
  assert.ok(alcove.max[1] > 3.7);
  assert.ok(getGroup('back-shelves').max[1] >= 4);
  assert.ok(bakes.min[1] >= 1.48 - 1e-6 && bakes.max[1] < 3.7);
  const bread = vertices(scene.opaque, ([, y, z], material) => material === MATERIALS.bread && y > 1.47 && z < -6.1);
  assert.ok(bread.length > 7000);
  for (const shelf of [1.48, 2.10, 2.72, 3.34]) {
    assert.ok(bread.some(([, y]) => Math.abs(y - shelf) < 1e-6), `Bread reaches shelf ${shelf}`);
  }
});

test('generation is deterministic, uses no randomness and returns independent arrays', () => {
  const random = Math.random;
  let next;
  try {
    Math.random = () => { throw new Error('Unseeded randomness is forbidden'); };
    next = createBakeryScene();
  } finally {
    Math.random = random;
  }
  assert.deepEqual(next, scene);
  assert.notEqual(next.opaque.positions, scene.opaque.positions);
  assert.notEqual(next.transparent[0].positions, scene.transparent[0].positions);
  next.opaque.positions[0] = 42;
  next.landmarkPoints.floorCenter[0] = 42;
  assert.notEqual(scene.opaque.positions[0], 42);
  assert.equal(scene.landmarkPoints.floorCenter[0], 0);
});
