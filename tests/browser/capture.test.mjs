// docs.expanso.io's capture settings with the real posthog-js: autocapture, page leave,
// heatmaps, web vitals and session replay. The events the SDK sends by itself get the context
// fields of skills' own events and clean URLs. Replay masks every input, as on cloud, so the
// search text never leaves the browser.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import {
  beaconEvents, closeSite, consentCookie, geoCookie, launchBrowser, openSite, SDK_VERSION, sdkEvents,
} from './harness.mjs';

// A landing URL with personal data in the query string and the fragment. (No click ids such as
// gclid: posthog-js copies those into $session_entry_* properties, which the URL cleaning does
// not touch, before and after this change.)
const DIRTY_LANDING = '/?email=private%40example.test#secret';
const PRIVATE = /private|secret/;
const CLEAN_URL = 'https://skills.expanso.io/';
const CONTEXT_FIELDS = ['site_id', 'site_host', 'analytics_schema_version', 'consent_state', 'traffic_class', 'is_synthetic'];

let browser;
before(async () => {
  browser = await launchBrowser();
});
after(async () => {
  await browser?.close();
});

/** The SDK's own event carries the context fields of skills' own event, with the same values. */
function assertContext(event, own) {
  for (const key of CONTEXT_FIELDS) assert.deepEqual(event.properties[key], own.properties[key], `${event.event} ${key}`);
  assert.equal(event.properties.site_id, 'expanso_skills', `${event.event} site_id`);
}

test('autocapture and web vitals reach PostHog with the context fields and clean URLs; heatmaps with clean URLs only', async () => {
  // An undecided EU visitor: the SDK's own events run cookieless too.
  const visit = await openSite(browser, { pathname: DIRTY_LANDING });
  const { page, traffic } = visit;
  const [pageview] = await sdkEvents(page, '$pageview');
  await page.locator('.tab[data-category="jobs"]').click();

  const [click] = await sdkEvents(page, '$autocapture');
  assert.equal(click.properties.$event_type, 'click');
  assert.equal(click.properties.$el_text, 'Jobs');
  assertContext(click, pageview);
  assert.equal(click.properties.identity_mode, 'ephemeral');
  assert.equal(click.properties.$current_url, CLEAN_URL);
  // A clicked link's href goes into $elements_chain: origin + path only.
  await page.evaluate(() => {
    const link = document.createElement('a');
    link.id = 'test-link';
    link.href = 'https://github.com/expanso-io/skills.expanso.io?ref=private#secret';
    link.textContent = 'Source';
    link.addEventListener('click', (event) => event.preventDefault());
    document.body.prepend(link);
  });
  await page.locator('#test-link').click();
  const clicks = await sdkEvents(page, '$autocapture', 2);
  assert.match(clicks[1].properties.$elements_chain, /href="https:\/\/github\.com\/expanso-io\/skills\.expanso\.io"/);

  // Heatmap batches key their points by page URL. The batch keeps the shape the SDK built: its
  // URLs are cleaned, and it gets no context fields.
  const [heatmap] = await sdkEvents(page, '$$heatmap', 1, 15_000);
  assert.deepEqual(Object.keys(heatmap.properties.$heatmap_data), [CLEAN_URL]);
  assert.equal(heatmap.properties.site_id, undefined);

  // Web vitals copy the page URL into each metric.
  const [vitals] = await sdkEvents(page, '$web_vitals', 1, 15_000);
  assertContext(vitals, pageview);
  assert.equal(vitals.properties.identity_mode, 'ephemeral');
  const metrics = Object.keys(vitals.properties).filter((key) => /^\$web_vitals_\w+_event$/.test(key));
  assert.ok(metrics.length > 0, 'no web vitals metric');
  for (const key of metrics) assert.equal(vitals.properties[key].$current_url, CLEAN_URL, key);

  assert.doesNotMatch(JSON.stringify(traffic.events), PRIVATE);
  await closeSite(visit);
});

test('page leave goes out on pagehide with the context fields and a clean URL', async () => {
  const visit = await openSite(browser, { cookies: [geoCookie('row')], pathname: DIRTY_LANDING });
  const { page } = visit;
  const [pageview] = await sdkEvents(page, '$pageview');
  // What the browser fires when the visitor leaves. posthog-js sends its queue by sendBeacon,
  // which the test browser stores in the page.
  await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
  const [leave] = (await beaconEvents(page)).filter((event) => event.event === '$pageleave');
  assert.ok(leave, 'no $pageleave in the beacons');
  assertContext(leave, pageview);
  assert.equal(leave.properties.identity_mode, 'persistent');
  assert.equal(leave.properties.$current_url, CLEAN_URL);
  assert.doesNotMatch(JSON.stringify(leave), PRIVATE);
  await closeSite(visit);
});

test('session replay masks every input and cleans its URLs: the search text and the landing query never reach PostHog', async () => {
  const MARKER = 'zebra-marker-7341';
  const visit = await openSite(browser, { cookies: [consentCookie('true')], pathname: DIRTY_LANDING });
  const { page, traffic } = visit;
  assert.equal(await page.evaluate(() => window.posthog.config.session_recording.maskAllInputs), true,
    'session_recording.maskAllInputs');
  // The project turns replay on (remote config), so the SDK loads the recorder the project
  // names (posthog-recorder). Type only once it records, so it sees every key. posthog-js holds
  // the recording until the first interaction: the typing.
  await page.waitForFunction(() => window.posthog.sessionRecordingStarted() === true);
  assert.ok(traffic.extensions.includes(`${SDK_VERSION}/posthog-recorder.js`), traffic.extensions.join(', '));
  // Replay's console capture is off: a logged page URL must not reach a recording.
  await page.evaluate(() => console.error('test log ' + window.location.href));
  await page.locator('#search').pressSequentially(MARKER);

  // Replay records the typing as input events, masked.
  const inputs = () => traffic.events.filter((event) => event.event === '$snapshot')
    .flatMap((event) => event.properties.$snapshot_data ?? [])
    .filter((record) => record.type === 3 && record.data?.source === 5)
    .map((record) => record.data.text);
  for (const deadline = Date.now() + 10_000; !inputs().includes('*'.repeat(MARKER.length)) && Date.now() < deadline;) {
    await page.waitForTimeout(100);
  }
  assert.ok(inputs().includes('*'.repeat(MARKER.length)), `replay input events: ${JSON.stringify(inputs())}`);
  // skills' own search event counts characters only.
  const [search] = await sdkEvents(page, 'skills_search');
  assert.equal(search.properties.query_length, MARKER.length);

  // Control: the check reads inside the compressed snapshot data (the page's own text is there).
  assert.ok(traffic.bodies.some((body) => body.includes('Search skills...')), 'no unpacked snapshot data');
  const leaked = traffic.bodies.filter((body) => body.includes(MARKER));
  assert.equal(leaked.length, 0, `${leaked.length} request bodies hold the search text`);
  // Replay URLs (meta hrefs, $url_changed, network names) are origin + path too.
  // Not PRIVATE: the recorded page text holds the skill name "secrets-scan".
  assert.doesNotMatch(traffic.bodies.join('\n'), /private%40|private@|[?&]email=|example\.test|#secret/);
  await closeSite(visit);
});
