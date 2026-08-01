/**
 * Copy the bundled .wasm binaries into an example's public/ directory.
 *
 * The browser examples fetch modules over HTTP from `/wasm/<name>.wasm` (see
 * getModulePath in packages/wasm/src/loader.ts), so the binaries have to be
 * served by the dev server and emitted into the production bundle. Vite serves
 * `publicDir` at the site root but only accepts a single directory inside the
 * project, and pointing it at packages/wasm would also publish that package's
 * source and node_modules — so the files are copied in instead.
 *
 * Run via each example's `predev` / `prebuild` script, which means a reader who
 * follows the README never has to know this step exists. The destination is
 * gitignored: it is a build input, not source.
 *
 * Usage (from an example directory):
 *   node ../copy-wasm.mjs
 */

import { cp, mkdir, readdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, '../../packages/wasm/wasm');
const destination = resolve(process.cwd(), 'public/wasm');

let names;
try {
  names = (await readdir(source)).filter((name) => name.endsWith('.wasm'));
} catch (error) {
  throw new Error(
    `Cannot read WASM binaries from ${source}. ` +
      'Run this from an examples/browser/* directory inside the agenkit repo.',
    { cause: error }
  );
}

if (names.length === 0) {
  throw new Error(`No .wasm files found in ${source}`);
}

await mkdir(destination, { recursive: true });
for (const name of names) {
  await cp(join(source, name), join(destination, name));
}

console.log(`[copy-wasm] copied ${names.length} modules -> ${destination}`);
