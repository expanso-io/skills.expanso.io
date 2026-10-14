// The test browser for skills.expanso.io. Nothing a test does may reach the network, and
// PostHog must never receive a test event:
//
// - context.route serves https://skills.expanso.io/* (and the local preview
//   http://localhost:8080/*) from the local docs/ folder, answers
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
// The SDK is the real posthog-js: the site serves its own pinned copy (js/array-<version>.js,
// from npm run build), and the PostHog answers here (remote config, event POSTs) are the
// ones the real proxy gives. The events the SDK sends are decoded and kept per context.
//
// Before the tests run: pages.yml's copy step (in CI) and `npm run build`, which writes
// docs/js/consent-runtime.js and docs/js/array-<version>.js.
import assert from 'node:assert/strict';
import { existsSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { chromium } from 'playwright';

export const SITE = 'https://skills.expanso.io';
const SITE_HOST = 'skills.expanso.io';
// A local preview, where only ?analytics_debug=1 turns analytics.js on. Served from docs/ too.
export const LOCAL_PREVIEW = 'http://localhost:8080';
const SITE_ORIGINS = new Set([SITE, LOCAL_PREVIEW]);
const POSTHOG_HOST = 'web.t.expanso.io';
const DEAD_PROXY = 'http://127.0.0.1:9';
const PROBE_URL = `https://${POSTHOG_HOST}/static/array.js?fence-probe=1`;
const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const DOCS = path.join(ROOT, 'docs') + path.sep;

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

// The posthog-js that package.json pins, and the copy of its core that the site serves.
const SDK_PACKAGE = path.join(ROOT, 'node_modules', 'posthog-js');
export const SDK_VERSION = JSON.parse(readFileSync(path.join(SDK_PACKAGE, 'package.json'), 'utf8')).version;
export const SDK_CORE_PATH = `/js/array-${SDK_VERSION}.js`;
const PINNED = JSON.parse(readFileSync(path.join(ROOT, 'package.json'), 'utf8')).devDependencies['posthog-js'];
assert.equal(SDK_VERSION, PINNED,
  `node_modules has posthog-js ${SDK_VERSION}, package.json pins ${PINNED}: run npm ci`);

// The project token, as analytics.js carries it.
const TOKEN = readFileSync(path.join(DOCS, 'js', 'analytics.js'), 'utf8').match(/POSTHOG_KEY = '(phc_\w+)'/)[1];

// The remote config, as the PostHog project serves it (GET
// https://web.t.expanso.io/array/<token>/config on 2026-10-14), with every key that changes
// what the SDK loads or where it sends: events go to /i/v0/e/, feature flags exist, replay
// loads posthog-recorder and records network timing and console logs. The project has surveys;
// their definitions are left out, and the consent contract's disable_surveys keeps them off.
// The local init options decide what of this runs on skills. Update it when the project
// changes.
const REMOTE_CONFIG = {
  token: TOKEN,
  analytics: { endpoint: '/i/v0/e/' },
  supportedCompression: ['gzip', 'gzip-js'],
  hasFeatureFlags: true,
  autocapture_opt_out: false,
  autocaptureExceptions: false,
  errorTracking: { autocaptureExceptions: false, suppressionRules: [] },
  captureDeadClicks: true,
  capturePerformance: { network_timing: true, web_vitals: true, web_vitals_allowed_metrics: null },
  sessionRecording: {
    endpoint: '/s/',
    recorderVersion: 'v2',
    scriptConfig: { script: 'posthog-recorder' },
    consoleLogRecordingEnabled: true,
    recordCanvas: false,
    canvasFps: null,
    canvasQuality: null,
    sampleRate: null,
    minimumDurationMilliseconds: null,
    linkedFlag: null,
    networkPayloadCapture: null,
    masking: null,
    urlTriggers: [],
    urlBlocklist: [],
    eventTriggers: [],
    triggerMatchType: null,
    version: 1,
  },
  heatmaps: { captureMode: 'all', urlAllowlist: [], urlAllowlistEnforced: false },
  surveys: true,
  productTours: false,
  conversations: false,
  logs: { captureConsoleLogs: false },
  elementsChainAsString: true,
  defaultIdentifiedOnly: true,
};
const REMOTE_CONFIG_JS = 'window._POSTHOG_REMOTE_CONFIG = window._POSTHOG_REMOTE_CONFIG || {};\n' +
  `window._POSTHOG_REMOTE_CONFIG[${JSON.stringify(TOKEN)}] = ${JSON.stringify({ config: REMOTE_CONFIG, siteApps: [] })};\n`;

// posthog-js's identity cookie for this project, and the id every cookieless event carries.
export const IDENTITY_COOKIE = `ph_${TOKEN}_posthog`;
// The localStorage key where posthog-js records an opt-in or opt-out (the choice, not an identity).
export const OPT_OUT_FLAG = `__ph_opt_in_out_${TOKEN}`;
export const COOKIELESS_ID = '$posthog_cookieless';

/** The identity cookie another Expanso site leaves on .expanso.io (from expanso.io's real-SDK test). */
export function identityCookie(distinctId) {
  return {
    name: IDENTITY_COOKIE,
    value: encodeURIComponent(JSON.stringify({ distinct_id: distinctId, $device_id: distinctId, $user_state: 'anonymous' })),
    domain: '.expanso.io',
    path: '/',
    secure: true,
    sameSite: 'Lax',
  };
}

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

/**
 * A posthog-js request body as text: gzip (1f 8b), a `data=<base64>` form body, plain JSON,
 * or, without a body, the `data` query parameter.
 */
function decodeBody(body, url) {
  const fromBase64 = (data) => Buffer.from(data ?? '', 'base64').toString('utf8');
  if (!body || body.length === 0) return fromBase64(url.searchParams.get('data'));
  if (body[0] === 0x1f && body[1] === 0x8b) return gunzipSync(body).toString('utf8');
  const raw = body.toString('utf8');
  return raw.startsWith('data=') ? fromBase64(new URLSearchParams(raw).get('data')) : raw;
}

/** The events in a decoded event body: posthog-js 1.435 sends { api_key, batch: [...] }. */
function eventsIn(text) {
  const parsed = JSON.parse(text);
  const list = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.batch) ? parsed.batch : [parsed];
  return list.map((raw) => ({ event: raw.event, properties: raw.properties ?? {}, uuid: raw.uuid }));
}

/** Every request a context made, how it was answered, and the events PostHog received. */
class Traffic {
  site = [];
  posthog = [];
  events = [];
  problems = [];
  aborted = [];
  leaks = [];
  answered = new WeakSet();
  seen = new Set();

  // Site files that fail on purpose, as { '/js/<file>': 404 | 'abort' }: 404 is a half
  // deploy, 'abort' a blocker or a network error.
  constructor(unavailable = {}) {
    this.unavailable = unavailable;
  }

  async handle(route) {
    const request = route.request();
    const url = new URL(request.url());
    try {
      if (SITE_ORIGINS.has(url.origin) && request.method() === 'GET') {
        this.site.push(url.pathname);
        const failure = this.unavailable[url.pathname];
        if (failure === 'abort') {
          this.aborted.push(`${request.method()} ${url.href}`);
          return await route.abort('blockedbyclient');
        }
        const file = failure === 404 ? null : siteFile(url.pathname);
        if (file) return await this.fulfill(route, 200, CONTENT_TYPES[path.extname(file)], readFileSync(file));
        return await this.fulfill(route, 404, CONTENT_TYPES['.html'], readFileSync(path.join(DOCS, '404.html')));
      }
      if (url.protocol === 'https:' && url.hostname === POSTHOG_HOST) return await this.answerPostHog(route, request, url);
      this.aborted.push(`${request.method()} ${url.href}`);
      await route.abort('blockedbyclient');
    } catch {
      // The page closed while the request was in flight; nothing was sent.
      await route.abort('blockedbyclient').catch(() => {});
    }
  }

  async answerPostHog(route, request, url) {
    const method = request.method();
    this.posthog.push(`${method} ${url.pathname}`);
    if (method === 'GET' && url.pathname === `/array/${TOKEN}/config.js`) {
      return this.fulfill(route, 200, CONTENT_TYPES['.js'], REMOTE_CONFIG_JS);
    }
    if (method === 'GET' && url.pathname === `/array/${TOKEN}/config`) {
      return this.fulfill(route, 200, CONTENT_TYPES['.json'], JSON.stringify(REMOTE_CONFIG));
    }
    if (method === 'POST' && /^\/(flags|decide)(\/|$)/.test(url.pathname)) {
      this.problems.push(`unexpected ${url.pathname} request: skills reads no feature flags`);
      return this.fulfill(route, 200, CONTENT_TYPES['.json'], '{}');
    }
    if (method === 'POST') {
      this.record(request, url);
      return this.fulfill(route, 200, CONTENT_TYPES['.json'], '{"status":1}');
    }
    // Among others the proxy's /static/array.js, its newest SDK: the site serves its own.
    this.problems.push(`unexpected PostHog request ${method} ${url.pathname}`);
    return this.fulfill(route, 404, CONTENT_TYPES['.txt'], 'not found');
  }

  record(request, url) {
    let events;
    try {
      events = eventsIn(decodeBody(request.postDataBuffer(), url));
    } catch (error) {
      this.problems.push(`could not read the body of ${url.pathname}: ${error.message}`);
      return;
    }
    for (const event of events) {
      // Retries resend the same event.
      if (event.uuid && this.seen.has(event.uuid)) continue;
      if (event.uuid) this.seen.add(event.uuid);
      this.events.push(event);
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
const trafficOf = new WeakMap();

/** Chromium behind the dead proxy. Proves the proxy stops a request the route lets through. */
export async function launchBrowser() {
  for (const file of ['consent-runtime.js', `array-${SDK_VERSION}.js`]) {
    assert.ok(existsSync(path.join(DOCS, 'js', file)), `docs/js/${file} is missing; run npm run build first`);
  }
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
 * A fresh context with the given cookies, on https://skills.expanso.io/ (or `pathname`, or
 * another `origin`: LOCAL_PREVIEW). `unavailable` makes site files fail
 * ({ '/js/<file>': 404 | 'abort' }). Returns the page, its context, the page errors and the
 * traffic record.
 */
export async function openSite(browser, { cookies = [], viewport, pathname = '/', origin = SITE, unavailable = {}, referer } = {}) {
  for (const [file, failure] of Object.entries(unavailable)) {
    assert.ok(failure === 404 || failure === 'abort', `unavailable ${file}: ${failure} is not 404 or 'abort'`);
  }
  const context = await browser.newContext({
    userAgent,
    locale: 'en-US',
    serviceWorkers: 'block',
    ...(viewport ? { viewport } : {}),
  });
  // Short waits, so a missing element fails a test in seconds rather than after 30.
  context.setDefaultTimeout(10_000);
  const traffic = new Traffic(unavailable);
  await context.addInitScript(maskAutomation);
  await context.addInitScript(stubUnloadRequests);
  if (cookies.length) await context.addCookies(cookies);
  await context.route('**/*', (route) => traffic.handle(route));
  await context.routeWebSocket(/.*/, (ws) => { traffic.aborted.push(`websocket ${ws.url()}`); ws.close(); });
  context.on('requestfinished', (request) => traffic.inspect(request));
  context.on('response', (response) => traffic.inspect(response.request()));
  const page = await context.newPage();
  trafficOf.set(page, traffic);
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${origin}${pathname}`, { waitUntil: 'load', referer });
  return { context, page, pageErrors, traffic };
}

/** Fails on a page error, a request that reached the network or an unexpected PostHog request, then closes. */
export async function closeSite({ context, pageErrors, traffic }) {
  try {
    assert.deepEqual(pageErrors, [], 'uncaught page errors');
    assert.deepEqual(traffic.leaks, [], 'requests reached the network');
    assert.deepEqual(traffic.problems, [], 'unexpected PostHog traffic');
  } finally {
    await context.close();
  }
}

/** The cookies with this name in the context's jar. */
export async function cookiesNamed(context, name) {
  return (await context.cookies()).filter((cookie) => cookie.name === name);
}

/**
 * The events with this name that PostHog received from the page, once at least `count` arrived.
 * posthog-js sends its queue every 3 seconds, so this waits up to 10.
 */
export async function sdkEvents(page, name, count = 1) {
  const traffic = trafficOf.get(page);
  const matching = () => traffic.events.filter((e) => e.event === name);
  for (const deadline = Date.now() + 10_000; matching().length < count && Date.now() < deadline;) {
    await page.waitForTimeout(100);
  }
  assert.ok(matching().length >= count, `PostHog received ${matching().length} ${name}, expected ${count}; ` +
    `it received: ${traffic.events.map((e) => e.event).join(', ') || 'nothing'}`);
  return matching();
}

/** The distinct_id in each identity cookie of the context, as "<distinct_id>@<domain>". */
export async function identityCookies(context) {
  return (await cookiesNamed(context, IDENTITY_COOKIE)).map((cookie) => {
    try {
      return `${JSON.parse(decodeURIComponent(cookie.value)).distinct_id}@${cookie.domain}`;
    } catch {
      return `unreadable@${cookie.domain}`;
    }
  });
}

/** Everything posthog-js could keep about a visitor in this browser (from examples' collector test). */
export async function storedIdentity(page) {
  const storage = await page.evaluate(() => ({
    localStorage: Object.keys(localStorage).filter((key) => key.startsWith('ph_') || key.startsWith('__ph_opt_in_out_')),
    sessionStorage: Object.keys(sessionStorage).filter((key) => key.startsWith('ph_')),
  }));
  const cookies = (await page.context().cookies())
    .filter((cookie) => cookie.name.startsWith('ph_'))
    .map((cookie) => `${cookie.name}@${cookie.domain}`);
  return { cookies, ...storage };
}
