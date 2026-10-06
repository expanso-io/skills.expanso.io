const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/site',
  forbidOnly: true,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'line',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    browserName: 'chromium',
    viewport: { width: 1280, height: 900 }
  },
  webServer: {
    command: 'uv run -s scripts/serve-site.py --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 30_000
  }
});
