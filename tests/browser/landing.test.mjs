// A skill link (a search result, an AI assistant's answer) opens a per-skill page: the one
// scripts/build-seo.py writes, or 404.html for a skill without one. Both send the visitor on
// to /, and index.html puts the skill's address back before analytics.js records the page
// view. The page view is the skill page's, with the visit's own source: the page that linked
// to the skill and the link's campaign tags, not the redirect.
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { after, before, test } from 'node:test';
import { closeSite, geoCookie, launchBrowser, openSite, SITE, sdkEvents } from './harness.mjs';

const SKILL = 'json-pretty';
const SKILL_PATH = `/skill/${SKILL}/`;
const QUERY = '?utm_source=chatgpt.com&email=private%40example.test#secret';
// The per-skill pages exist only after pages.yml's SEO step, which CI's browser job runs too.
const SEO_PAGE = new URL(`../../docs/skill/${SKILL}/index.html`, import.meta.url);

let browser;
before(async () => {
  assert.ok(existsSync(SEO_PAGE),
    'docs/skill/ is missing: run python3 scripts/build-seo.py --catalog catalog.json --output docs');
  browser = await launchBrowser();
});
after(async () => {
  await browser?.close();
});

const spaKeys = (page) => page.evaluate(() => Object.keys(sessionStorage).filter((key) => key.startsWith('spa-')));

for (const [label, unavailable] of [['the per-skill page', {}], ['404.html', { [SKILL_PATH]: 404 }]]) {
  test(`a skill link through ${label} records the skill page, its referrer and its campaign tags`, async () => {
    const visit = await openSite(browser, {
      cookies: [geoCookie('row')],
      pathname: SKILL_PATH + QUERY,
      referer: 'https://www.google.com/',
      unavailable,
    });
    const { page, traffic } = visit;
    const [pageview] = await sdkEvents(page, '$pageview');
    assert.equal(pageview.properties.$pathname, SKILL_PATH);
    assert.equal(pageview.properties.$current_url, `${SITE}${SKILL_PATH}`);
    assert.equal(pageview.properties.landing_skill_path, SKILL_PATH);
    assert.equal(pageview.properties.referrer_host, 'www.google.com');
    assert.equal(pageview.properties.utm_source, 'chatgpt.com');
    const [modal] = await sdkEvents(page, 'skill_modal_open');
    assert.equal(modal.properties.skill, SKILL);
    assert.equal(modal.properties.via, 'deep_link');
    // The address bar shows the link as the visitor opened it; the redirect leaves nothing behind.
    assert.equal(page.url(), SITE + SKILL_PATH + QUERY);
    assert.deepEqual(await spaKeys(page), []);
    assert.doesNotMatch(JSON.stringify(traffic.events), /private|secret/);
    await closeSite(visit);
  });
}

test('a skill link without a referrer is a direct visit, not a visit from skills itself', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')], pathname: SKILL_PATH });
  const [pageview] = await sdkEvents(visit.page, '$pageview');
  assert.equal(pageview.properties.$pathname, SKILL_PATH);
  assert.equal(pageview.properties.referrer_host, '');
  await closeSite(visit);
});

test('the home page keeps its own address and referrer', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')], referer: 'https://www.google.com/' });
  const { page } = visit;
  const [pageview] = await sdkEvents(page, '$pageview');
  assert.equal(pageview.properties.$pathname, '/');
  assert.equal(pageview.properties.landing_skill_path, null);
  assert.equal(pageview.properties.referrer_host, 'www.google.com');
  assert.equal(page.url(), `${SITE}/`);
  await closeSite(visit);
});

// The redirect pages store the path and the referrer for one page load only. When app.js does
// not get to put the address back (the catalog fails, app.js is blocked), the keys must not
// make a later visit in the same tab look like the old skill link.
test('a skill link whose page does not finish leaves no keys, and the next visit is its own', async () => {
  const failed = await openSite(browser, {
    cookies: [geoCookie('row')], pathname: SKILL_PATH, referer: 'https://www.google.com/',
    unavailable: { '/catalog.json': 404 },
  });
  await failed.page.getByText('Failed to load skills').waitFor();
  assert.deepEqual(await spaKeys(failed.page), []);
  await closeSite(failed);

  const blocked = await openSite(browser, {
    cookies: [geoCookie('row')], pathname: SKILL_PATH, referer: 'https://www.google.com/',
    unavailable: { '/js/app.js': 'abort' },
  });
  const { page } = blocked;
  await sdkEvents(page, '$pageview');
  await page.goto(`${SITE}/`, { referer: 'https://expanso.io/' });
  const [, next] = await sdkEvents(page, '$pageview', 2);
  assert.equal(next.properties.$pathname, '/');
  assert.equal(next.properties.landing_skill_path, null);
  assert.equal(next.properties.referrer_host, 'expanso.io');
  assert.deepEqual(await spaKeys(page), []);
  await closeSite(blocked);
});

// Chrome and Firefox throw on window.sessionStorage when the visitor blocks site data.
function blockSessionStorage() {
  Object.defineProperty(window, 'sessionStorage', {
    configurable: true,
    get() { throw new DOMException('Access is denied for this document.', 'SecurityError'); },
  });
}

test('with sessionStorage blocked, a skill link still ends on the working skill list', async () => {
  const visit = await openSite(browser, {
    cookies: [geoCookie('row')], pathname: SKILL_PATH + '?utm_source=chatgpt.com', initScripts: [blockSessionStorage],
  });
  const { page } = visit;
  await page.locator('.skill-card').first().waitFor();
  assert.equal(await page.getByText('Failed to load skills').count(), 0);
  assert.equal(page.url(), `${SITE}/?utm_source=chatgpt.com`);
  const [pageview] = await sdkEvents(page, '$pageview');
  assert.equal(pageview.properties.$pathname, '/');
  assert.equal(pageview.properties.utm_source, 'chatgpt.com');
  await closeSite(visit);
});
