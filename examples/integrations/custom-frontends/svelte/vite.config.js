import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 3003,
    proxy: {
      '/agui': 'http://localhost:8000',
    },
  },
})
