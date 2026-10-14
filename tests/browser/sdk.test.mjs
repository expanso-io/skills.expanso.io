// The pinned posthog-js: analytics.js loads posthog-js's own dist/array.js from this site
// (js/array-<version>.js, which npm run build writes), never the proxy's newest
// /static/array.js. Events still go to web.t.expanso.io. When the core does not load (a
// blocker, a network error, a half deploy), the banner still works and PostHog gets nothing.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { closeSite, cookiesNamed, launchBrowser, openSite, SDK_CORE_PATH, SDK_VERSION, sdkEvents } from './harness.mjs';

let browser;
before(async () => {
  browser = await launchBrowser();
});
after(async () => {
  await browser?.close();
});

test('analytics.js loads the pinned posthog-js from this site, not from the PostHog proxy', async () => {
  const visit = await openSite(browser);
  const { page, traffic } = visit;
  const [pageview] = await sdkEvents(page, '$pageview');
  assert.equal(pageview.properties.$lib_version, SDK_VERSION);
  assert.equal(pageview.properties.site_id, 'expanso_skills');
  assert.deepEqual(traffic.site.filter((pathname) => pathname.startsWith('/js/array')), [SDK_CORE_PATH]);
  assert.deepEqual(traffic.posthog.filter((request) => request.includes('/static/')), []);
  await closeSite(visit);
});

test('without the SDK core (a 404 or a blocked file) the banner still records the choice, and PostHog gets nothing', async () => {
  for (const failure of [404, 'abort']) {
    const visit = await openSite(browser, { unavailable: { [SDK_CORE_PATH]: failure } });
    const { context, page, traffic } = visit;
    const choices = page.getByRole('region', { name: 'Analytics privacy choices' });
    const consent = async () => (await cookiesNamed(context, 'expanso-cookie-consent'))
      .map((cookie) => `${cookie.value}@${cookie.domain}`);

    await choices.getByRole('button', { name: 'Accept analytics' }).click();
    await choices.waitFor({ state: 'hidden' });
    assert.deepEqual(await consent(), ['true@.expanso.io'], `${failure}: Accept`);
    await page.getByRole('button', { name: 'Cookie settings' }).click();
    await choices.getByRole('button', { name: 'Decline analytics' }).click();
    await choices.waitFor({ state: 'hidden' });
    assert.deepEqual(await consent(), ['false@.expanso.io'], `${failure}: Decline`);

    // The page asked for the core once, and asked PostHog for nothing (no other SDK either).
    assert.deepEqual(traffic.site.filter((pathname) => pathname.startsWith('/js/array')), [SDK_CORE_PATH], `${failure}`);
    assert.deepEqual(traffic.posthog, [], `${failure}: requests to web.t.expanso.io`);
    // closeSite fails on an uncaught page error.
    await closeSite(visit);
  }
});
