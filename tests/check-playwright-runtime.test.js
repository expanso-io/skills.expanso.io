const test = require('node:test');

const assert = require('node:assert/strict');

const { inspectConfig } = require('../scripts/check-playwright-runtime');

const cacheRoots = ['/opt/playwright/ms-playwright'];

test('accepts bundled headless Chromium', () => {
  const errors = inspectConfig(
    {
      use: {
        browserName: 'chromium',
        headless: true,
        launchOptions: {
          executablePath: '/opt/playwright/ms-playwright/chromium-123/chrome'
        }
      }
    },
    cacheRoots
  );

  assert.deepEqual(errors, []);
});

test('rejects branded browser channels in root and project settings', () => {
  const errors = inspectConfig(
    {
      use: { channel: 'chrome' },
      projects: [{ name: 'edge', use: { channel: 'msedge' } }]
    },
    cacheRoots
  );

  assert.equal(errors.length, 2);
  assert.match(errors[0], /channel "chrome" is forbidden/);
  assert.match(errors[1], /channel "msedge" is forbidden/);
});

test('rejects headed mode', () => {
  const errors = inspectConfig({ use: { headless: false } }, cacheRoots);

  assert.deepEqual(errors, ['config.use: headless must not be false']);
});

test('rejects browsers other than Chromium', () => {
  const errors = inspectConfig({ use: { browserName: 'firefox' } }, cacheRoots);

  assert.deepEqual(errors, ['config.use: browserName must be "chromium"']);
});

test('rejects a system browser executable', () => {
  const errors = inspectConfig(
    {
      use: {
        launchOptions: {
          executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        }
      }
    },
    cacheRoots
  );

  assert.equal(errors.length, 1);
  assert.match(errors[0], /must stay inside Playwright's browser cache/);
});
