// A skill link (a search result, an AI assistant's answer) opens a per-skill page: the one
// scripts/build-seo.py writes, or 404.html for a skill without one. Both send the visitor on
// to /, with the query, and leave the skill's path and the page that linked to it in
// sessionStorage. index.html's landing script takes both and puts the skill's address back
// before any other script runs. Every event of the page, the SDK's own page fields too, is
// then the skill page's, with the visit's own source: the page that linked to the skill and
// the link's campaign tags, not the redirect.
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { after, before, test } from 'node:test';
import { beaconEvents, closeSite, geoCookie, launchBrowser, openSite, SITE, sdkEvents } from './harness.mjs';

const SKILL = 'json-pretty';
const SKILL_PATH = `/skill/${SKILL}/`;
// Markers that no page text holds (the skill "secrets-scan" is in the recorded page text).
const QUERY = '?utm_source=chatgpt.com&email=zebra-mail-4417%40example.test#zebra-fragment-4417';
const LEAK = /zebra-mail|zebra-fragment|example\.test/;
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
const modalTitle = (page) => page.locator('#skill-modal .modal-title', { hasText: SKILL });

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
    // The SDK's own page fields name the skill page too.
    await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
    const [leave] = (await beaconEvents(page)).filter((event) => event.event === '$pageleave');
    assert.equal(leave.properties.$prev_pageview_pathname, SKILL_PATH);
    assert.doesNotMatch(JSON.stringify(traffic.events), LEAK);
    assert.doesNotMatch(traffic.bodies.join('\n'), LEAK);
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

test('after a skill link, Back reopens the skill, and a reload is not a visit from skills itself', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')], pathname: SKILL_PATH, referer: 'https://www.google.com/' });
  const { page } = visit;
  await sdkEvents(page, 'skill_modal_open');
  await page.locator('#skill-modal').getByRole('button', { name: 'Close' }).click();
  await page.locator('#modal-overlay.active').waitFor({ state: 'detached' });
  assert.equal(page.url(), `${SITE}/`);
  await page.goBack();
  // The title stays in the page after a close; the open modal has the active class.
  await page.locator('#modal-overlay.active').waitFor();
  await modalTitle(page).waitFor();
  assert.equal(page.url(), SITE + SKILL_PATH);

  // A reload asks for the skill page again, with the redirect page as its referrer.
  await page.reload();
  const [, again] = await sdkEvents(page, '$pageview', 2);
  assert.equal(again.properties.$pathname, SKILL_PATH);
  assert.equal(again.properties.referrer_host, '');
  await closeSite(visit);
});

// The keys last one page load: index.html's landing script takes them at once. When the page
// does not finish (the catalog fails, app.js is blocked), the address is already back, so a
// refresh opens the skill again, and a later visit in the same tab is its own.
test('a skill link whose page does not finish keeps the skill address and leaves no keys', async () => {
  const failed = await openSite(browser, {
    cookies: [geoCookie('row')], pathname: SKILL_PATH, referer: 'https://www.google.com/',
    unavailable: { '/catalog.json': 404 },
  });
  await failed.page.getByText('Failed to load skills').waitFor();
  assert.equal(failed.page.url(), SITE + SKILL_PATH);
  assert.deepEqual(await spaKeys(failed.page), []);
  await closeSite(failed);

  const blocked = await openSite(browser, {
    cookies: [geoCookie('row')], pathname: SKILL_PATH, referer: 'https://www.google.com/',
    unavailable: { '/js/app.js': 'abort' },
  });
  const { page } = blocked;
  await sdkEvents(page, '$pageview');
  assert.deepEqual(await spaKeys(page), []);
  await page.goto(`${SITE}/`, { referer: 'https://expanso.io/' });
  const [, next] = await sdkEvents(page, '$pageview', 2);
  assert.equal(next.properties.$pathname, '/');
  assert.equal(next.properties.landing_skill_path, null);
  assert.equal(next.properties.referrer_host, 'expanso.io');
  await closeSite(blocked);
});

// Chrome and Firefox throw on window.sessionStorage when the visitor blocks site data.
function blockSessionStorage() {
  Object.defineProperty(window, 'sessionStorage', {
    configurable: true,
    get() { throw new DOMException('Access is denied for this document.', 'SecurityError'); },
  });
}

test('with sessionStorage blocked, a skill link stays on the skill page, and the home page works', async () => {
  const skill = await openSite(browser, {
    cookies: [geoCookie('row')], pathname: SKILL_PATH, initScripts: [blockSessionStorage],
  });
  await skill.page.getByRole('heading', { name: 'Json Pretty' }).waitFor();
  assert.equal(skill.page.url(), SITE + SKILL_PATH);
  await closeSite(skill);

  const home = await openSite(browser, { cookies: [geoCookie('row')], initScripts: [blockSessionStorage] });
  await home.page.locator('.skill-card').first().waitFor();
  assert.equal(await home.page.getByText('Failed to load skills').count(), 0);
  await closeSite(home);
});

test('a missing page that is not a skill says so and links to the skill list', async () => {
  const visit = await openSite(browser, { pathname: '/no-such-page' });
  const { page } = visit;
  await page.getByText('Page not found').waitFor();
  assert.equal(await page.getByRole('link', { name: 'Browse all skills' }).getAttribute('href'), '/');
  assert.equal(page.url(), `${SITE}/no-such-page`);
  await closeSite(visit);
});

test('after a link to an unknown skill, Back from a skill closes it', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')], pathname: '/skill/no-such-skill/' });
  const { page } = visit;
  await page.locator('.skill-card[data-skill="csv-to-json"]').click();
  await page.locator('#modal-overlay.active').waitFor();
  await page.goBack();
  await page.locator('#modal-overlay.active').waitFor({ state: 'detached' });
  assert.equal(page.url(), `${SITE}/skill/no-such-skill/`);
  await closeSite(visit);
});
