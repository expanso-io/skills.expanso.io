// The test browser for skills.expanso.io. Nothing a test does may reach the network, and
// PostHog must never receive a test event:
//
// - context.route serves https://skills.expanso.io/* from the local docs/ folder, answers
//   every web.t.expanso.io request here, and aborts every other request;
// - the browser runs behind a proxy where nothing listens (bypassed only for
//   skills.expanso.io, which the route serves), so a request the route cannot see, such as an
//   unload beacon, fails instead of leaving; launchBrowser() proves this before any test;
// - navigator.sendBeacon is a stub that stores each payload in the page (window.__beacons)
//   and sends nothing; fetch loses keepalive and fetchLater is removed, for the same reason;
// - the page cannot tell it runs in an automated browser (no HeadlessChrome in the user agent
//   or in navigator.userAgentData, navigator.webdriver false), because posthog-js drops every
//   event from a browser it takes for a bot. Copied from expanso.io's
//   scripts/test-posthog-real-sdk.mjs.
//
// Before the tests run: pages.yml's copy step (in CI) and `npm run build`, which writes
// docs/js/consent-runtime.js.
import assert from 'node:assert/strict';
import { existsSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

export const SITE = 'https://skills.expanso.io';
const SITE_HOST = 'skills.expanso.io';
const POSTHOG_HOST = 'web.t.expanso.io';
const DEAD_PROXY = 'http://127.0.0.1:9';
const PROBE_URL = `https://${POSTHOG_HOST}/static/array.js?fence-probe=1`;
const DOCS = fileURLToPath(new URL('../../docs/', import.meta.url));

const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.yaml': 'text/yaml; charset=utf-8',
  '.yml': 'text/yaml; charset=utf-8',
  '.sh': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.xml': 'application/xml',
};

// Until the site serves its own pinned posthog-js, analytics.js loads /static/array.js from
// the PostHog proxy. The tests answer it with this stub: it records what analytics.js passes
// to init and capture (window.__sdkInit, window.__sdkCaptured) and sends nothing.
export const STUB_SDK = `window.posthog = {
  init: function (token, options) { window.__sdkInit = { token: token, options: options }; },
  capture: function (event, properties) {
    (window.__sdkCaptured = window.__sdkCaptured || []).push({ event: event, properties: properties });
  }
};
`;

/** The shared consent cookie, as an Expanso site writes it: Domain=expanso.io. */
export function consentCookie(value) {
  return { name: 'expanso-cookie-consent', value, domain: '.expanso.io', path: '/', secure: true, sameSite: 'Lax' };
}

/** The host-only region cookie the docs-geo Worker sets on skills.expanso.io. */
export function geoCookie(value) {
  return { name: 'expanso-geo', value, url: SITE };
}

// Init scripts. They run in the page, so they cannot close over anything here.
function maskAutomation() {
  Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => false, configurable: true });
  const swap = (list) => list.map((b) => (b.brand.includes('HeadlessChrome') ? { ...b, brand: 'Google Chrome' } : b));
  const uaData = navigator.userAgentData;
  if (uaData) {
    const proto = Object.getPrototypeOf(uaData);
    const brands = Object.getOwnPropertyDescriptor(proto, 'brands');
    if (brands && brands.get) {
      const read = brands.get;
      Object.defineProperty(proto, 'brands', { configurable: true, get() { return swap(read.call(this)); } });
    }
    const highEntropy = proto.getHighEntropyValues;
    if (highEntropy) {
      proto.getHighEntropyValues = function (hints) {
        return highEntropy.call(this, hints).then((values) => {
          const out = { ...values };
          for (const key of ['brands', 'fullVersionList']) if (Array.isArray(out[key])) out[key] = swap(out[key]);
          return out;
        });
      };
    }
  }
}

function stubUnloadRequests() {
  const beacons = [];
  Object.defineProperty(window, '__beacons', { value: beacons });
  // Must return true, or posthog-js falls back to fetch.
  Navigator.prototype.sendBeacon = function (url, data) {
    beacons.push({ url: String(url), data: data === undefined ? null : data });
    return true;
  };
  const nativeFetch = window.fetch;
  window.fetch = (input, init) => nativeFetch(
    input instanceof Request && input.keepalive ? new Request(input, { keepalive: false }) : input,
    init && init.keepalive ? { ...init, keepalive: false } : init,
  );
  delete window.fetchLater;
}

/** The docs/ file GitHub Pages would serve for a path, or null. */
function siteFile(pathname) {
  let file = path.join(DOCS, decodeURIComponent(pathname));
  if (!file.startsWith(DOCS)) return null;
  try {
    if (statSync(file).isDirectory()) file = path.join(file, 'index.html');
    return statSync(file).isFile() ? file : null;
  } catch {
    return null;
  }
}

/** Every request a context made, how it was answered, and the requests that got past. */
class Traffic {
  posthog = [];
  aborted = [];
  leaks = [];
  answered = new WeakSet();

  async handle(route) {
    const request = route.request();
    const url = new URL(request.url());
    try {
      if (url.protocol === 'https:' && url.hostname === SITE_HOST && request.method() === 'GET') {
        const file = siteFile(url.pathname);
        if (file) return await this.fulfill(route, 200, CONTENT_TYPES[path.extname(file)], readFileSync(file));
        return await this.fulfill(route, 404, CONTENT_TYPES['.html'], readFileSync(path.join(DOCS, '404.html')));
      }
      if (url.protocol === 'https:' && url.hostname === POSTHOG_HOST) {
        this.posthog.push(`${request.method()} ${url.pathname}`);
        if (request.method() === 'GET' && url.pathname === '/static/array.js') {
          return await this.fulfill(route, 200, CONTENT_TYPES['.js'], STUB_SDK);
        }
        if (request.method() === 'POST') return await this.fulfill(route, 200, CONTENT_TYPES['.json'], '{"status":1}');
        return await this.fulfill(route, 404, CONTENT_TYPES['.txt'], 'not found');
      }
      this.aborted.push(`${request.method()} ${url.href}`);
      await route.abort('blockedbyclient');
    } catch {
      // The page closed while the request was in flight; nothing was sent.
      await route.abort('blockedbyclient').catch(() => {});
    }
  }

  async fulfill(route, status, contentType, body) {
    this.answered.add(route.request());
    await route.fulfill({ status, contentType, body });
  }

  /** A request that completed must be one answered here. */
  inspect(request) {
    if (!/^https?:/.test(request.url()) || this.answered.has(request)) return;
    this.leaks.push(`${request.method()} ${request.url()}`);
  }
}

let userAgent;

/** Chromium behind the dead proxy. Proves the proxy stops a request the route lets through. */
export async function launchBrowser() {
  assert.ok(existsSync(path.join(DOCS, 'js', 'consent-runtime.js')),
    'docs/js/consent-runtime.js is missing; run npm run build first');
  const browser = await chromium.launch({ proxy: { server: DEAD_PROXY, bypass: SITE_HOST } });
  try {
    const cdp = await browser.newBrowserCDPSession();
    userAgent = (await cdp.send('Browser.getVersion')).userAgent.replace(/HeadlessChrome/g, 'Chrome');
    await cdp.detach();

    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', (route) => (route.request().url() === PROBE_URL ? route.continue() : route.abort()));
    const page = await context.newPage();
    const outcome = await page.goto(PROBE_URL).then(
      (response) => `reached the network: HTTP ${response?.status()}`,
      (error) => error.message,
    );
    await context.close();
    assert.match(outcome, /ERR_PROXY_CONNECTION_FAILED/,
      `a request past the route must die at the dead proxy, not reach ${POSTHOG_HOST}: ${outcome}`);
    return browser;
  } catch (error) {
    await browser.close();
    throw error;
  }
}

/**
 * A fresh context with the given cookies, on https://skills.expanso.io/ (or `pathname`).
 * Returns the page, its context, the page errors and the traffic record.
 */
export async function openSite(browser, { cookies = [], viewport, pathname = '/' } = {}) {
  const context = await browser.newContext({
    userAgent,
    locale: 'en-US',
    serviceWorkers: 'block',
    ...(viewport ? { viewport } : {}),
  });
  // Short waits, so a missing element fails a test in seconds rather than after 30.
  context.setDefaultTimeout(10_000);
  const traffic = new Traffic();
  await context.addInitScript(maskAutomation);
  await context.addInitScript(stubUnloadRequests);
  if (cookies.length) await context.addCookies(cookies);
  await context.route('**/*', (route) => traffic.handle(route));
  await context.routeWebSocket(/.*/, (ws) => { traffic.aborted.push(`websocket ${ws.url()}`); ws.close(); });
  context.on('requestfinished', (request) => traffic.inspect(request));
  context.on('response', (response) => traffic.inspect(response.request()));
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${SITE}${pathname}`, { waitUntil: 'load' });
  return { context, page, pageErrors, traffic };
}

/** Fails on a page error or a request that reached the network, then closes the context. */
export async function closeSite({ context, pageErrors, traffic }) {
  try {
    assert.deepEqual(pageErrors, [], 'uncaught page errors');
    assert.deepEqual(traffic.leaks, [], 'requests reached the network');
  } finally {
    await context.close();
  }
}

/** The cookies with this name in the context's jar. */
export async function cookiesNamed(context, name) {
  return (await context.cookies()).filter((cookie) => cookie.name === name);
}

/** What analytics.js passed to the SDK's capture, once an event with this name arrived. */
export async function sdkEvents(page, name) {
  await page.waitForFunction(
    (event) => (window.__sdkCaptured || []).some((e) => e.event === event), name, { timeout: 5000 });
  return page.evaluate((event) => window.__sdkCaptured.filter((e) => e.event === event), name);
}
