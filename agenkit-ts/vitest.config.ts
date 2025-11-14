import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        '**/*.test.ts',
        '**/*.d.ts',
        '**/node_modules/**',
        '**/dist/**',
        'src/index.ts', // Export-only file
        'src/llm/**', // External API wrappers - would require API key mocking
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 65, // Lower threshold - WebSocket needs integration tests
        statements: 70,
      },
    },
  },
});
