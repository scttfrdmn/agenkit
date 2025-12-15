import { defineConfig } from 'astro/config';

export default defineConfig({
  server: {
    port: 3003,
  },
  vite: {
    resolve: {
      alias: {
        '@agenkit/wasm': '/../../packages/wasm/src/index.ts',
      },
    },
  },
});
