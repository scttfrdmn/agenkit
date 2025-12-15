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
      '@agenkit/wasm': '/../../packages/wasm/src/index.ts',
    },
  },
});
