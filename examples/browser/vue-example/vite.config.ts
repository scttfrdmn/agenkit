import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3001,
    open: true,
  },
  resolve: {
    alias: {
      '@agenkit/wasm': '/../../packages/wasm/src/index.ts',
    },
  },
});
