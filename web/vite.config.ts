import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite-plus';

const apiPort = process.env.AI_PARTNER_PORT ?? '8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': `http://127.0.0.1:${apiPort}`,
    },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
  lint: {
    ignorePatterns: ['dist/**'],
  },
  fmt: {
    singleQuote: true,
    printWidth: 110,
    ignorePatterns: ['dist/**'],
  },
});
