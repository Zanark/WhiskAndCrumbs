import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { resolve, dirname } from 'node:path';
import { createBakeryScene, MATERIALS } from '../web/bakery-scene.mjs';
import { bakeryLight } from '../web/bakery-view.mjs';
import { bakeryGeometryKey } from '../web/bakery-interior.mjs';

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const sub = (a, b) => a.map((v, i) => v - b[i]);
const add = (a, b, k = 1) => a.map((v, i) => v + b[i] * k);
const unit = a => a.map(v => v / Math.hypot(...a));
const SUN = bakeryLight().direction;
const epsilon = 0.006;

export function windowRay(point, direction = SUN) {
  if (direction[0] >= -0.001) return null;
  const distance = (-4.24 - point[0]) / direction[0];
  if (distance <= 0) return null;
  const hit = add(point, direction, distance);
  return hit[1] > 1.3 && hit[1] < 3.8 && hit[2] > -4.8 && hit[2] < -1.2 ? { distance, hit } : null;
}

export function createTracer(scene) {
  const p = scene.opaque.positions, m = scene.opaque.materials;
  const triangles = [];
  for (let i = 0; i < m.length; i += 3) {
    if (m[i] === MATERIALS.window || m[i] === MATERIALS.glass) continue;
    const a = Array.from(p.subarray(i * 3, i * 3 + 3));
    const b = Array.from(p.subarray((i + 1) * 3, (i + 2) * 3));
    const c = Array.from(p.subarray((i + 2) * 3, (i + 3) * 3));
    const e1 = sub(b, a), e2 = sub(c, a);
    triangles.push({ a, e1, e2, normal: unit(cross(e1, e2)), material: m[i],
      min: a.map((_, axis) => Math.min(a[axis], b[axis], c[axis])),
      max: a.map((_, axis) => Math.max(a[axis], b[axis], c[axis])) });
  }
  function tree(items) {
    const min = [0, 1, 2].map(axis => Math.min(...items.map(t => t.min[axis])));
    const max = [0, 1, 2].map(axis => Math.max(...items.map(t => t.max[axis])));
    if (items.length <= 8) return { min, max, items };
    const extents = max.map((v, i) => v - min[i]);
    const axis = extents.indexOf(Math.max(...extents));
    items.sort((a, b) => a.min[axis] + a.max[axis] - b.min[axis] - b.max[axis]);
    const half = Math.floor(items.length / 2);
    return { min, max, children: [tree(items.slice(0, half)), tree(items.slice(half))] };
  }
  const root = tree(triangles);
  function ray(origin, direction, maximum = 30) {
    let nearest = maximum, result = null;
    function visit(node) {
      let lower = 0, upper = nearest;
      for (let axis = 0; axis < 3; axis++) {
        if (Math.abs(direction[axis]) < 1e-10) {
          if (origin[axis] < node.min[axis] - 1e-7 || origin[axis] > node.max[axis] + 1e-7) return;
        } else {
          const a = (node.min[axis] - origin[axis]) / direction[axis];
          const b = (node.max[axis] - origin[axis]) / direction[axis];
          lower = Math.max(lower, Math.min(a, b));
          upper = Math.min(upper, Math.max(a, b));
          if (upper < lower) return;
        }
      }
      if (node.children) {
        visit(node.children[0]); visit(node.children[1]); return;
      }
      for (const triangle of node.items) {
        const h = cross(direction, triangle.e2), det = dot(triangle.e1, h);
        if (Math.abs(det) < 1e-10) continue;
        const s = sub(origin, triangle.a), u = dot(s, h) / det;
        if (u < -1e-7 || u > 1.0000001) continue;
        const q = cross(s, triangle.e1), v = dot(direction, q) / det;
        if (v < -1e-7 || u + v > 1.0000001) continue;
        const distance = dot(triangle.e2, q) / det;
        if (distance > 0.001 && distance < nearest) {
          nearest = distance; result = { distance, point: add(origin, direction, distance), triangle };
        }
      }
    }
    visit(root);
    return result;
  }
  return { ray, triangles: triangles.length };
}

export function sampleLighting(tracer, point, normal, samples = 12) {
  const origin = add(point, normal, epsilon);
  const opening = windowRay(origin);
  const direct = opening && dot(normal, SUN) > 0 && !tracer.ray(origin, SUN, opening.distance + 0.08) ? 1 : 0;
  const tangent = unit(cross(normal, Math.abs(normal[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0]));
  const bitangent = cross(normal, tangent);
  let occlusion = 0, bounce = 0, sky = 0;
  for (let i = 0; i < samples; i++) {
    const r = Math.sqrt((i + 0.5) / samples), angle = i * 2.399963229728653;
    const direction = add(add(normal.map(v => v * Math.sqrt(1 - r * r)), tangent, r * Math.cos(angle)), bitangent, r * Math.sin(angle));
    const hit = tracer.ray(origin, direction, 3.4);
    if (hit) {
      occlusion += Math.max(0, 1 - hit.distance / 1.3);
      const facing = dot(hit.triangle.normal, direction) < 0 ? hit.triangle.normal : hit.triangle.normal.map(v => -v);
      const secondary = add(hit.point, facing, epsilon);
      const aperture = windowRay(secondary);
      if (aperture && !tracer.ray(secondary, SUN, aperture.distance + 0.08)) {
        const albedo = [MATERIALS.wood, MATERIALS.darkWood, MATERIALS.bread].includes(hit.triangle.material) ? 0.52 : 0.70;
        bounce += Math.max(0, dot(facing, SUN)) * albedo / (1 + hit.distance * 0.22);
      }
    }
  }
  for (const [y, z] of [[1.75, -4.32], [2.25, -3.72], [3.28, -4.18],
    [1.83, -2.33], [2.87, -1.68], [3.39, -2.66]]) {
    const delta = sub([-4.22, y, z], origin), distance = Math.hypot(...delta), direction = unit(delta);
    if (!tracer.ray(origin, direction, distance - 0.015)) {
      sky += Math.max(0, dot(normal, direction)) / (1 + distance * distance * 0.06);
    }
  }
  return [Math.max(0.12, 1 - occlusion / samples), sky / 6, direct, Math.min(1, bounce / samples * 3.2)];
}

export function bake(scene, samples = 12) {
  const tracer = createTracer(scene), mesh = scene.opaque;
  const count = mesh.materials.length, buffer = new ArrayBuffer(32 + count * 4), header = new DataView(buffer);
  header.setUint32(0, 0x314c4257, true); header.setUint32(4, count, true);
  header.setUint32(8, bakeryGeometryKey(scene), true);
  SUN.forEach((value, index) => header.setFloat32(12 + index * 4, value, true));
  header.setUint32(24, count * 4, true); header.setUint32(28, 1, true);
  const payload = new Uint8Array(buffer, 32), cache = new Map();
  for (let i = 0; i < count; i++) {
    const point = Array.from(mesh.positions.subarray(i * 3, i * 3 + 3));
    const normal = Array.from(mesh.normals.subarray(i * 3, i * 3 + 3));
    const key = [...point, ...normal].map(v => v.toFixed(5)).join(',');
    let values = cache.get(key);
    if (!values) {
      values = mesh.materials[i] === MATERIALS.window ? [1, 1, 0, 0] : sampleLighting(tracer, point, normal, samples);
      cache.set(key, values);
    }
    for (let channel = 0; channel < 4; channel++) payload[i * 4 + channel] = Math.round(values[channel] * 255);
  }
  return { buffer, uniqueSamples: cache.size, tracer };
}

function generate() {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const scene = createBakeryScene(), start = performance.now();
  const { buffer, uniqueSamples, tracer } = bake(scene);
  const target = resolve(root, 'web', 'assets', 'bakery-light-bake.bin');
  writeFileSync(target, new Uint8Array(buffer));
  const probes = {
    openFloor: { point: [0, 0, -2.4], normal: [0, 1, 0] },
    underCounter: { point: [0, 0, -1.1], normal: [0, 1, 0] },
    counterTop: { point: [-2.52, 1.13, -0.7], normal: [0, 1, 0] },
    shelfRecess: { point: [0.2, 2.73, -6.6], normal: [0, 0, 1] },
    wallOutsideWindow: { point: [0, 0, 2.5], normal: [0, 1, 0] }
  };
  for (const probe of Object.values(probes)) probe.lighting = sampleLighting(tracer, probe.point, probe.normal, 48);
  const bytes = new Uint8Array(buffer, 32);
  const receipt = { version: 1, source: 'Offline deterministic BVH triangle tracing of this original room.',
    channels: ['cosine-weighted short-range ambient visibility', 'occluded six-point window skylight',
      'fixed aperture-limited direct sunlight', 'one-bounce daylight from actual sun-visible hit surfaces'],
    samples: 12, uniqueSamples, vertices: scene.opaque.materials.length, triangles: tracer.triangles,
    seconds: (performance.now() - start) / 1000, bytes: buffer.byteLength,
    geometryKey: bakeryGeometryKey(scene), lightDirection: SUN, probes,
    ranges: [0, 1, 2, 3].map(channel => {
      const values = bytes.filter((_, i) => i % 4 === channel);
      return { min: Math.min(...values), max: Math.max(...values), mean: values.reduce((a, b) => a + b, 0) / values.length };
    }),
    sha256: createHash('sha256').update(readFileSync(target)).digest('hex'),
    limits: '12-ray per-vertex bake is approximate, not a full path-traced lightmap. Runtime aperture and static depth map retain per-pixel direct occlusion; no image viewing.' };
  const evidence = resolve(root, '.local', 'painterly-windowlight-20261008');
  mkdirSync(evidence, { recursive: true });
  writeFileSync(resolve(evidence, 'lighting-bake.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) generate();
