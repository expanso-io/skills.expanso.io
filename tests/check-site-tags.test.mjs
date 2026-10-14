// scripts/check-site-tags.py must fail unless the SDK core that js/analytics.js names
// (SDK_CORE_PATH) exists in the built site and equals node_modules/posthog-js/dist/array.js.
// Each case builds a small site in a scratch folder from the real js/analytics.js and runs the
// check on it with python3, as CI and pages.yml run it.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const CHECK = path.join(ROOT, 'scripts', 'check-site-tags.py');
const CORE = readFileSync(path.join(ROOT, 'node_modules', 'posthog-js', 'dist', 'array.js'));
const VERSION = JSON.parse(readFileSync(path.join(ROOT, 'node_modules', 'posthog-js', 'package.json'), 'utf8')).version;
const LOADER = readFileSync(path.join(ROOT, 'docs', 'js', 'analytics.js'), 'utf8');

const scratch = mkdtempSync(path.join(tmpdir(), 'site-tags-'));
after(() => rmSync(scratch, { recursive: true, force: true }));

/** A site with index.html, js/analytics.js and, unless core is null, js/<coreName>. */
function site(name, { loader = LOADER, core = CORE, coreName = `array-${VERSION}.js` } = {}) {
  const dir = path.join(scratch, name);
  mkdirSync(path.join(dir, 'js'), { recursive: true });
  writeFileSync(path.join(dir, 'index.html'), '<!doctype html><script src="js/analytics.js"></script>\n');
  writeFileSync(path.join(dir, 'js', 'analytics.js'), loader);
  if (core) writeFileSync(path.join(dir, 'js', coreName), core);
  return dir;
}

function check(dir) {
  const run = spawnSync('python3', [CHECK, dir], { encoding: 'utf8' });
  return { status: run.status, output: run.stdout + run.stderr };
}

test('a site with the pinned SDK core that analytics.js names passes', () => {
  const dir = site('pinned');
  const { status, output } = check(dir);
  assert.equal(status, 0, output);
  assert.equal(output, `Site tag check passed for ${dir}\n`);
});

test('fails when the SDK core that analytics.js names is not in the site', () => {
  const { status, output } = check(site('missing', { core: null }));
  assert.equal(status, 1, output);
  assert.match(output, new RegExp(`js/array-${VERSION}\\.js: missing; js/analytics\\.js loads it`));
});

test('fails after a posthog-js update that forgets the name in analytics.js', () => {
  // The build then writes array-<new version>.js, and analytics.js still names the old file.
  const { status, output } = check(site('update', { coreName: 'array-9.9.9.js' }));
  assert.equal(status, 1, output);
  assert.match(output, new RegExp(`js/array-${VERSION}\\.js: missing; js/analytics\\.js loads it`));
});

test('fails when the SDK core in the site differs from node_modules/posthog-js/dist/array.js', () => {
  const { status, output } = check(site('differs', { core: Buffer.concat([CORE, Buffer.from('\n')]) }));
  assert.equal(status, 1, output);
  assert.match(output, new RegExp(`js/array-${VERSION}\\.js: differs from node_modules/posthog-js/dist/array\\.js`));
});

test('fails when analytics.js names no SDK core file', () => {
  const loader = LOADER.replace(/SDK_CORE_PATH = '[^']*'/, "SDK_CORE_PATH = API_HOST + '/static/array.js'");
  const { status, output } = check(site('unnamed', { loader }));
  assert.equal(status, 1, output);
  assert.match(output, /js\/analytics\.js: names no SDK core file/);
});
