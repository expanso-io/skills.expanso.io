#!/usr/bin/env node

const os = require('node:os');

const path = require('node:path');

const process = require('node:process');

const FORBIDDEN_CHANNELS = new Set(['chrome', 'msedge']);

function isWithin(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));

  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function playwrightCacheRoots() {
  const roots = [];
  const configured = process.env.PLAYWRIGHT_BROWSERS_PATH;

  if (configured && configured !== '0') {
    roots.push(path.resolve(configured));
  }

  if (configured === '0') {
    roots.push(path.resolve('node_modules/playwright-core/.local-browsers'));
  }

  if (process.platform === 'darwin') {
    roots.push(path.join(os.homedir(), 'Library/Caches/ms-playwright'));
  } else if (process.platform === 'win32') {
    const localAppData = process.env.LOCALAPPDATA;

    if (localAppData) {
      roots.push(path.join(localAppData, 'ms-playwright'));
    }
  } else {
    roots.push(path.join(os.homedir(), '.cache/ms-playwright'));
  }

  roots.push(path.resolve('node_modules/playwright-core/.local-browsers'));

  return roots;
}

function inspectUse(label, use, cacheRoots) {
  if (!use) {
    return [];
  }

  const errors = [];

  const channel = use.channel?.toLowerCase();

  if (FORBIDDEN_CHANNELS.has(channel)) {
    errors.push(`${label}: channel ${JSON.stringify(use.channel)} is forbidden`);
  }

  const browserName = use.browserName?.toLowerCase();

  if (browserName && browserName !== 'chromium') {
    errors.push(`${label}: browserName must be "chromium"`);
  }

  if (use.headless === false) {
    errors.push(`${label}: headless must not be false`);
  }

  const executablePath = use.launchOptions?.executablePath;

  if (
    executablePath &&
    !cacheRoots.some((cacheRoot) => isWithin(cacheRoot, executablePath))
  ) {
    errors.push(
      `${label}: launchOptions.executablePath must stay inside Playwright's browser cache`
    );
  }

  return errors;
}

function inspectConfig(config, cacheRoots = playwrightCacheRoots()) {
  const errors = inspectUse('config.use', config.use, cacheRoots);

  for (const project of config.projects || []) {
    const label = `project ${JSON.stringify(project.name || '<unnamed>')}.use`;
    errors.push(...inspectUse(label, project.use, cacheRoots));
  }

  return errors;
}

async function main() {
  const configPath = path.resolve(process.argv[2] || 'playwright.config.js');
  const loaded = require(configPath);
  const config = await Promise.resolve(loaded.default || loaded);
  const errors = inspectConfig(config);

  if (errors.length > 0) {
    console.error('Playwright runtime policy violations:');

    for (const error of errors) {
      console.error(`- ${error}`);
    }

    process.exitCode = 1;

    return;
  }

  console.log('Playwright runtime policy passed: bundled headless Chromium only.');
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}

module.exports = { inspectConfig, inspectUse, isWithin };
