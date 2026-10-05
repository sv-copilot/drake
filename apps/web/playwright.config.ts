import { defineConfig, devices } from '@playwright/test';

// The port is configurable so the suite can run when something else already
// owns 3000. Passing PLAYWRIGHT_PORT also forces a dedicated server, because
// reusing a stranger's server on that port silently tests the wrong app.
const PORT = process.env.PLAYWRIGHT_PORT ?? '3000';
const BASE_URL = `http://localhost:${PORT}`;
const REUSE_EXISTING_SERVER = !process.env.CI && !process.env.PLAYWRIGHT_PORT;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npm run dev -- --port ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: REUSE_EXISTING_SERVER,
  },
});
