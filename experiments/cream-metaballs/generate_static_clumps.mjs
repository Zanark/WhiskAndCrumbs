import {writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {CLUMP_PROFILES, DEFAULT_SCENE} from './model.mjs';

export function staticClumpCss() {
  const number = value => Number(value.toFixed(5));
  const layers = DEFAULT_SCENE.clumps.flatMap(({x, y, radius, clump}) => {
    const size = `${number(radius * 100)}vmin`;
    const centerY = y * 100;
    const position = (center, offset) => offset === 0 ? `${number(center)}%`
      : `calc(${number(center)}% ${offset < 0 ? '-' : '+'} ${size} * ${number(Math.abs(offset))})`;
    return (clump === undefined ? [[0, 0, 1]] : CLUMP_PROFILES[clump]).map(([offsetX, offsetY, scale]) =>
      `    radial-gradient(circle calc(${size} * ${number(scale)}) at ${position(x * 100, offsetX)} ${position(centerY, offsetY)}, #fffaf1 85%, transparent 100%)`);
  });
  return `/* Generated from the same bounded clump profiles used by the material renderer. */\n.static-material {\n  background-image:\n${layers.join(',\n')};\n}\n`;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  writeFileSync(new URL('./static-clumps.css', import.meta.url), staticClumpCss());
  console.log(`Generated fallback lobes in ${DEFAULT_SCENE.clumps.length} clumps.`);
}
