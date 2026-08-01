import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 3002,
    open: true,
  },
  resolve: {
    alias: {
      // Resolved from this file's location, not the filesystem root. The
      // previous '/../../packages/wasm/src/index.ts' had a leading slash, making
      // it absolute, so it resolved against / and could never exist (#735).
      // Points at the built package rather than src/ so the example exercises
      // what an installed consumer actually gets; run `npm run build` in
      // packages/wasm first (the prebuild script handles it).
      '@agenkit/wasm': fileURLToPath(
        new URL('../../../packages/wasm/dist/index.mjs', import.meta.url)
      ),
    },
  },
});
