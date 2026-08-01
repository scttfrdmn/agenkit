import { fileURLToPath } from 'node:url';

import { defineConfig } from 'astro/config';

export default defineConfig({
  server: {
    port: 3003,
  },
  vite: {
    resolve: {
      alias: {
        // Resolved from this file's location, not the filesystem root. The
        // previous '/../../packages/wasm/src/index.ts' had a leading slash,
        // making it absolute, so it resolved against / and could never exist
        // (#735). Points at the built package rather than src/ so the example
        // exercises what an installed consumer actually gets; run
        // `npm run build` in packages/wasm first (the prebuild script does).
        '@agenkit/wasm': fileURLToPath(
          new URL('../../../packages/wasm/dist/index.mjs', import.meta.url)
        ),
      },
    },
  },
});
