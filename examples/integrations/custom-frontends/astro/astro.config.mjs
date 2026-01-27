import { defineConfig } from 'astro/config';

export default defineConfig({
  server: {
    port: 3004,
  },
  vite: {
    server: {
      proxy: {
        '/agui': 'http://localhost:8000',
      },
    },
  },
});
