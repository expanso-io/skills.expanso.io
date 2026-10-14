// The consent lanes with the real posthog-js, as on the main sites: the shared .expanso.io
// identity cookie after an accept or for an undecided visitor outside the EU; cookieless for
// an undecided EU visitor (or one without the expanso-geo cookie) and after a decline, also
// one made on an earlier visit. A later choice (here, in another tab, on another Expanso site)
// moves the SDK to its lane. In-app navigation adds no page view. Without the consent runtime
// there is no analytics at all. Last, the local preview's debug mode, which never loads the SDK.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import {
  closeSite, consentCookie, COOKIELESS_ID, geoCookie, identityCookie, identityCookies, launchBrowser,
  LOCAL_PREVIEW, openSite, OPT_OUT_FLAG, SITE, sdkEvents, storedIdentity,
} from './harness.mjs';

const NOTHING_STORED = { cookies: [], localStorage: [], sessionStorage: [] };
// After a decline posthog-js keeps one key: its opt-out flag (0), the choice, not an identity.
const ONLY_THE_OPT_OUT_FLAG = { cookies: [], localStorage: [OPT_OUT_FLAG], sessionStorage: [] };
const optOutFlag = (page) => page.evaluate((key) => localStorage.getItem(key), OPT_OUT_FLAG);
const OTHER_SITE_ID = '0199d6f2-6c1e-7a3b-9c4d-5e6f7a8b9c0d';

let browser;
before(async () => {
  browser = await launchBrowser();
});
after(async () => {
  await browser?.close();
});

const banner = (page) => page.getByRole('region', { name: 'Analytics privacy choices' });
const button = (page, name) => page.getByRole('button', { name });

function assertCookieless(event, consentState) {
  assert.equal(event.properties.consent_state, consentState, `${event.event} consent_state`);
  assert.equal(event.properties.identity_mode, 'ephemeral', `${event.event} identity_mode`);
  assert.equal(event.properties.$cookieless_mode, true, `${event.event} $cookieless_mode`);
  assert.equal(event.properties.distinct_id, COOKIELESS_ID, `${event.event} distinct_id`);
}

function assertPersistent(event, consentState) {
  assert.equal(event.properties.consent_state, consentState, `${event.event} consent_state`);
  assert.equal(event.properties.identity_mode, 'persistent', `${event.event} identity_mode`);
  assert.equal(event.properties.$cookieless_mode, undefined, `${event.event} $cookieless_mode`);
  assert.notEqual(event.properties.distinct_id, COOKIELESS_ID, `${event.event} distinct_id`);
}

// posthog-js writes its cookie 250 ms after a change (persistence_save_debounce_ms with the
// contract's defaults date). Wait longer, so a wrong write would show.
const afterCookieWrite = (page) => page.waitForTimeout(500);

test('an EU visitor without a choice is counted cookieless, with nothing stored', async () => {
  for (const [label, cookies] of [['no geo cookie', []], ['eu', [geoCookie('eu')]]]) {
    const visit = await openSite(browser, { cookies });
    const { page } = visit;
    const [pageview] = await sdkEvents(page, '$pageview');
    assertCookieless(pageview, 'unset');
    await afterCookieWrite(page);
    assert.deepEqual(await storedIdentity(page), NOTHING_STORED, label);
    await closeSite(visit);
  }
});

test('a visitor outside the EU without a choice gets the shared .expanso.io identity cookie', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')] });
  const { context, page } = visit;
  const [pageview] = await sdkEvents(page, '$pageview');
  assertPersistent(pageview, 'unset');
  await afterCookieWrite(page);
  assert.deepEqual(await identityCookies(context), [`${pageview.properties.distinct_id}@.expanso.io`]);
  await closeSite(visit);
});

test('a visitor outside the EU who declined on an earlier visit stays cookieless, with no identity stored', async () => {
  // The decline wins over the rest-of-world default.
  const visit = await openSite(browser, { cookies: [consentCookie('false'), geoCookie('row')] });
  const { context, page } = visit;
  const [pageview] = await sdkEvents(page, '$pageview');
  assertCookieless(pageview, 'denied');
  assert.equal(await banner(page).isVisible(), false);
  await afterCookieWrite(page);
  assert.deepEqual(await identityCookies(context), []);
  assert.deepEqual(await storedIdentity(page), ONLY_THE_OPT_OUT_FLAG);
  assert.equal(await optOutFlag(page), '0');
  assert.deepEqual(await page.evaluate(() => Object.keys(sessionStorage)), []);
  await closeSite(visit);
});

test('Accept moves an EU visitor to the shared identity cookie, with one more $pageview', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('eu')], referer: 'https://www.google.com/' });
  const { context, page } = visit;
  assertCookieless((await sdkEvents(page, '$pageview'))[0], 'unset');
  await button(page, 'Accept analytics').click();
  const pageviews = await sdkEvents(page, '$pageview', 2);
  assert.equal(pageviews.length, 2);
  assertPersistent(pageviews[1], 'granted');
  // The new identity's first page view keeps the visit's source; the landing is counted once.
  assert.equal(pageviews[0].properties.referrer_host, 'www.google.com');
  assert.equal(pageviews[1].properties.referrer_host, 'www.google.com');
  assert.equal('landing_skill_path' in pageviews[1].properties, false);
  const [choice] = await sdkEvents(page, 'cookie_consent');
  assertPersistent(choice, 'granted');
  assert.equal(choice.properties.consent, 'yes');
  assert.equal(choice.properties.distinct_id, pageviews[1].properties.distinct_id);
  await afterCookieWrite(page);
  const id = pageviews[1].properties.distinct_id;
  assert.deepEqual(await identityCookies(context), [`${id}@.expanso.io`]);

  // The next page load keeps the identity.
  await page.reload({ waitUntil: 'load' });
  const reloaded = await sdkEvents(page, '$pageview', 3);
  assertPersistent(reloaded[2], 'granted');
  assert.equal(reloaded[2].properties.distinct_id, id);
  await closeSite(visit);
});

test('Decline moves a visitor to the cookieless lane and clears the stored identity', async () => {
  const visit = await openSite(browser, { cookies: [consentCookie('true')] });
  const { context, page } = visit;
  const [accepted] = await sdkEvents(page, '$pageview');
  assertPersistent(accepted, 'granted');
  await afterCookieWrite(page);
  assert.equal((await identityCookies(context)).length, 1);

  await button(page, 'Cookie settings').click();
  await button(page, 'Decline analytics').click();
  const pageviews = await sdkEvents(page, '$pageview', 2);
  assertCookieless(pageviews[1], 'denied');
  const [choice] = await sdkEvents(page, 'cookie_consent');
  assertCookieless(choice, 'denied');
  assert.equal(choice.properties.consent, 'no');
  assert.equal(choice.properties.method, 'settings');
  await afterCookieWrite(page);
  assert.deepEqual(await storedIdentity(page), ONLY_THE_OPT_OUT_FLAG);
  assert.equal(await optOutFlag(page), '0');
  await closeSite(visit);
});

test('a visitor who accepted on another Expanso site is tracked on the first page load, without the banner', async () => {
  const visit = await openSite(browser, {
    cookies: [consentCookie('true'), geoCookie('eu'), identityCookie(OTHER_SITE_ID)],
  });
  const { context, page } = visit;
  assert.equal(await banner(page).isVisible(), false);
  const [pageview] = await sdkEvents(page, '$pageview');
  assertPersistent(pageview, 'granted');
  // The same person as on the other site.
  assert.equal(pageview.properties.distinct_id, OTHER_SITE_ID);
  await afterCookieWrite(page);
  assert.deepEqual(await identityCookies(context), [`${OTHER_SITE_ID}@.expanso.io`]);
  await closeSite(visit);
});

test('only a lane change sends one more $pageview, also for a choice made on another Expanso site', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')] });
  const { context, page, traffic } = visit;
  const [first] = await sdkEvents(page, '$pageview');
  assertPersistent(first, 'unset');

  // An undecided visitor outside the EU already runs in the persistent lane: Accept keeps it.
  await button(page, 'Accept analytics').click();
  const [choice] = await sdkEvents(page, 'cookie_consent');
  assertPersistent(choice, 'granted');
  assert.equal(choice.properties.distinct_id, first.properties.distinct_id);
  assert.equal(traffic.events.filter((e) => e.event === '$pageview').length, 1);

  // A decline on another Expanso site; this tab re-reads the shared cookie when it gets focus.
  await context.addCookies([consentCookie('false')]);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  const pageviews = await sdkEvents(page, '$pageview', 2);
  assert.equal(pageviews.length, 2);
  assertCookieless(pageviews[1], 'denied');
  await afterCookieWrite(page);
  assert.deepEqual(await identityCookies(context), []);
  await closeSite(visit);
});

test('in-app navigation adds no $pageview: a skill opened and closed, Back, Forward, a category tab', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')] });
  const { page, traffic } = visit;
  await sdkEvents(page, '$pageview');
  const card = page.locator('.skill-card').first();
  const name = await card.getAttribute('data-skill');
  const closed = () => page.locator('#modal-overlay.active').waitFor({ state: 'detached' });

  // app.js pushes /skill/<name> when a card opens the skill, and / when the modal closes.
  // Each open is reported once the skill's title shows, so wait for it before the next step.
  await card.click();
  await sdkEvents(page, 'skill_modal_open', 1);
  assert.equal(page.url(), `${SITE}/skill/${name}`);
  await page.locator('#skill-modal').getByRole('button', { name: 'Close' }).click();
  await closed();
  assert.equal(page.url(), `${SITE}/`);
  // Back reopens the skill (popstate), Forward closes it again.
  await page.goBack();
  await sdkEvents(page, 'skill_modal_open', 2);
  assert.equal(page.url(), `${SITE}/skill/${name}`);
  await page.goForward();
  await closed();
  assert.equal(page.url(), `${SITE}/`);
  await page.locator('.tab[data-category="jobs"]').click();

  // PostHog receives the events in the order they were captured: the tab event comes last.
  await sdkEvents(page, 'skills_category_tab');
  const urls = (event) => traffic.events.filter((e) => e.event === event).map((e) => e.properties.$current_url);
  assert.deepEqual(urls('$pageview'), [`${SITE}/`]);
  assert.deepEqual(urls('skill_modal_open'), [`${SITE}/skill/${name}`, `${SITE}/skill/${name}`]);
  await closeSite(visit);
});

test("skills' own events carry their context fields, the consent state and the lane", async () => {
  // A per-skill page redirects to / and leaves its path for analytics.js (the landing skill).
  const deep = await openSite(browser, { cookies: [geoCookie('row')], pathname: '/skill/json-pretty/' });
  const [landing] = await sdkEvents(deep.page, '$pageview');
  assert.equal(landing.properties.landing_skill_path, '/skill/json-pretty/');
  const [modal] = await sdkEvents(deep.page, 'skill_modal_open');
  assert.equal(modal.properties.skill, 'json-pretty');
  assert.equal(modal.properties.via, 'deep_link');
  await closeSite(deep);

  const visit = await openSite(browser, { pathname: '/?utm_source=qa&email=private%40example.test#secret' });
  const { page } = visit;
  await page.locator('.tab[data-category="jobs"]').click();
  const [tab] = await sdkEvents(page, 'skills_category_tab');
  for (const event of [landing, modal, tab]) {
    assert.equal(event.properties.site_id, 'expanso_skills', event.event);
    assert.equal(event.properties.site_host, 'skills.expanso.io', event.event);
    assert.equal(event.properties.analytics_schema_version, '2026-09-18', event.event);
    assert.equal(event.properties.traffic_class, 'browser_unclassified', event.event);
    assert.equal(event.properties.is_synthetic, false, event.event);
  }
  assertPersistent(landing, 'unset');
  assertPersistent(modal, 'unset');
  assertCookieless(tab, 'unset');
  assert.equal(tab.properties.category, 'jobs');
  assert.equal(tab.properties.utm_source, 'qa');
  assert.equal(tab.properties.$current_url, 'https://skills.expanso.io/');
  assert.equal(tab.properties.$pathname, '/');
  assert.doesNotMatch(JSON.stringify(visit.traffic.events), /private|secret/);
  await closeSite(visit);
});

test('without the consent runtime (a 404) the page runs no analytics, and the skills still show', async () => {
  const visit = await openSite(browser, { unavailable: { '/js/consent-runtime.js': 404 } });
  const { page, traffic } = visit;
  await page.locator('.skill-card').first().waitFor();
  assert.ok(await page.locator('.skill-card').count() > 0);
  await page.locator('.tab[data-category="jobs"]').click();
  await afterCookieWrite(page);
  assert.deepEqual(traffic.posthog, [], 'requests to web.t.expanso.io');
  assert.deepEqual(traffic.site.filter((pathname) => pathname.startsWith('/js/array')), [], 'the SDK core');
  assert.deepEqual(await storedIdentity(page), NOTHING_STORED);
  // closeSite fails on an uncaught page error.
  await closeSite(visit);
});

test('debug mode on a local preview records the events without loading the SDK', async () => {
  const visit = await openSite(browser, { origin: LOCAL_PREVIEW, pathname: '/?analytics_debug=1' });
  const { page, traffic } = visit;
  await page.locator('.tab[data-category="jobs"]').click();
  const recorded = await page.evaluate(() => window.__expansoAnalyticsEvents.map((e) => e.event));
  assert.deepEqual(recorded, ['$pageview', 'skills_category_tab']);
  const [pageview] = await page.evaluate(() => window.__expansoAnalyticsEvents);
  assert.equal(pageview.properties.site_id, 'expanso_skills');
  assert.equal(pageview.properties.consent_state, 'unset');
  assert.equal('identity_mode' in pageview.properties, false, 'the SDK sets no lane in debug mode');
  assert.deepEqual(traffic.site.filter((pathname) => pathname.startsWith('/js/array')), []);
  assert.deepEqual(traffic.posthog, []);
  await closeSite(visit);

  // Without the switch, a local preview runs no analytics at all.
  const plain = await openSite(browser, { origin: LOCAL_PREVIEW });
  await plain.page.locator('.tab[data-category="jobs"]').click();
  assert.equal(await plain.page.evaluate(() => window.__expansoAnalyticsEvents), undefined);
  assert.deepEqual(plain.traffic.posthog, []);
  await closeSite(plain);
});
