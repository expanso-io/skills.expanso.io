// The analytics privacy banner (js/privacy-choices.js) and the footer's "Cookie settings"
// control, in Chromium, on https://skills.expanso.io/ served from docs/ (see harness.mjs).
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { AxeBuilder } from '@axe-core/playwright';
import { closeSite, consentCookie, cookiesNamed, geoCookie, launchBrowser, openSite, sdkEvents } from './harness.mjs';

const EU_TEXT = 'We use analytics to understand how people browse these skills. Until you accept, ' +
  'we measure anonymously and keep no analytics cookies or data on your device. Accepting lets ' +
  'us recognise repeat visits.';
const ROW_TEXT = 'We use analytics to understand how people browse these skills. It is running ' +
  'now; decline below to turn it off.';
const CONSENT = 'expanso-cookie-consent';
const DISMISSED = 'expanso-cookie-banner-dismissed';

let browser;
before(async () => {
  browser = await launchBrowser();
});
after(async () => {
  await browser?.close();
});

const banner = (page) => page.getByRole('region', { name: 'Analytics privacy choices' });
const acceptButton = (page) => banner(page).getByRole('button', { name: 'Accept analytics' });
const declineButton = (page) => banner(page).getByRole('button', { name: 'Decline analytics' });
const closeButton = (page) => banner(page).getByRole('button', { name: 'Close' });
const settingsButton = (page) => page.getByRole('button', { name: 'Cookie settings' });
const bannerText = (page) => page.locator('#privacy-choices-text').textContent();
const currentChoice = (page) => page.locator('#privacy-choices-current');
const focusedId = (page) => page.evaluate(() => document.activeElement && document.activeElement.id);

async function assertHidden(page) {
  await page.locator('#privacy-choices').waitFor({ state: 'hidden' });
  assert.equal(await page.locator('#privacy-choices').getAttribute('hidden'), '');
}

test('first visit: the banner shows the EU text and does not take focus', async () => {
  const visit = await openSite(browser);
  const { page } = visit;
  await banner(page).waitFor();
  assert.equal(await bannerText(page), EU_TEXT);
  assert.equal(await page.evaluate(() => document.activeElement === document.body), true);
  const link = banner(page).getByRole('link', { name: 'Read our privacy policy' });
  assert.equal(await link.getAttribute('href'), 'https://expanso.io/privacy-policy/');
  assert.equal(await currentChoice(page).isVisible(), false, 'the first-visit banner shows no current choice');
  await closeSite(visit);
});

test('Accept records yes on .expanso.io, reports cookie_consent and stays hidden after a reload', async () => {
  const visit = await openSite(browser);
  const { context, page } = visit;
  await acceptButton(page).click();
  await assertHidden(page);
  const [cookie] = await cookiesNamed(context, CONSENT);
  assert.equal(cookie.value, 'true');
  assert.equal(cookie.domain, '.expanso.io');
  const [event] = await sdkEvents(page, 'cookie_consent');
  assert.equal(event.properties.consent, 'yes');
  assert.equal(event.properties.scope, 'analytics');
  assert.equal(event.properties.method, 'banner');
  assert.equal(event.properties.site_id, 'expanso_skills');
  await page.reload({ waitUntil: 'load' });
  await assertHidden(page);
  await closeSite(visit);
});

test('Decline records no on .expanso.io, reports cookie_consent and stays hidden after a reload', async () => {
  const visit = await openSite(browser);
  const { context, page } = visit;
  await declineButton(page).click();
  await assertHidden(page);
  const [cookie] = await cookiesNamed(context, CONSENT);
  assert.equal(cookie.value, 'false');
  assert.equal(cookie.domain, '.expanso.io');
  const [event] = await sdkEvents(page, 'cookie_consent');
  assert.equal(event.properties.consent, 'no');
  assert.equal(event.properties.method, 'banner');
  assert.equal(event.properties.site_id, 'expanso_skills');
  await page.reload({ waitUntil: 'load' });
  await assertHidden(page);
  await closeSite(visit);
});

test('Close writes the host-only dismissed marker, no consent cookie, and stays closed after a reload', async () => {
  const visit = await openSite(browser);
  const { context, page } = visit;
  await closeButton(page).click();
  await assertHidden(page);
  assert.deepEqual(await cookiesNamed(context, CONSENT), []);
  const [marker] = await cookiesNamed(context, DISMISSED);
  assert.equal(marker.value, '1');
  assert.equal(marker.domain, 'skills.expanso.io');
  const [event] = await sdkEvents(page, 'cookie_banner_dismissed');
  assert.equal(event.properties.scope, 'analytics');
  assert.equal(event.properties.method, 'banner');
  assert.equal(event.properties.site_id, 'expanso_skills');
  await page.reload({ waitUntil: 'load' });
  await assertHidden(page);
  await closeSite(visit);
});

test('"Cookie settings" reopens the banner, focuses Accept, and records the next choice as settings', async () => {
  const visit = await openSite(browser, { cookies: [consentCookie('true')] });
  const { context, page } = visit;
  await assertHidden(page);
  await settingsButton(page).click();
  await banner(page).waitFor();
  assert.equal(await focusedId(page), 'privacy-accept');
  assert.equal(await currentChoice(page).textContent(), 'Your current choice: Accepted');
  assert.equal(await currentChoice(page).isVisible(), true);
  await declineButton(page).click();
  await assertHidden(page);
  assert.equal((await cookiesNamed(context, CONSENT))[0].value, 'false');
  const [event] = await sdkEvents(page, 'cookie_consent');
  assert.equal(event.properties.consent, 'no');
  assert.equal(event.properties.method, 'settings');
  assert.equal(await focusedId(page), 'privacy-settings');
  await closeSite(visit);
});

test('Escape closes the reopened banner and records nothing; with a skill open, only the skill', async () => {
  const visit = await openSite(browser, { cookies: [consentCookie('true')] });
  const { context, page } = visit;
  await settingsButton(page).click();
  await banner(page).waitFor();
  await page.keyboard.press('Escape');
  await assertHidden(page);
  assert.equal(await focusedId(page), 'privacy-settings');
  // A skill opened above the reopened banner takes the next Escape: app.js closes the skill
  // window, and the banner below it stays open.
  await settingsButton(page).click();
  await banner(page).waitFor();
  await page.locator('.skill-card').first().click();
  await page.locator('#modal-overlay.active').waitFor();
  await page.keyboard.press('Escape');
  await page.locator('#modal-overlay.active').waitFor({ state: 'detached' });
  assert.equal(await page.locator('#privacy-choices').getAttribute('hidden'), null, 'the banner stays open');
  assert.equal((await cookiesNamed(context, CONSENT))[0].value, 'true');
  assert.deepEqual(await cookiesNamed(context, DISMISSED), []);
  assert.equal(await page.evaluate(() => (window.__sdkCaptured || [])
    .filter((e) => e.event === 'cookie_consent' || e.event === 'cookie_banner_dismissed').length), 0);
  await closeSite(visit);
});

test('Escape does not close the first-visit banner', async () => {
  const visit = await openSite(browser);
  const { context, page } = visit;
  await banner(page).waitFor();
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  assert.equal(await banner(page).isVisible(), true);
  assert.deepEqual(await cookiesNamed(context, DISMISSED), []);
  await closeSite(visit);
});

test('a choice made on another Expanso site hides the banner, at load and while it is open', async () => {
  const before = await openSite(browser, { cookies: [consentCookie('true')] });
  await assertHidden(before.page);
  await closeSite(before);

  const visit = await openSite(browser);
  const { context, page } = visit;
  await banner(page).waitFor();
  // Another Expanso site writes the shared cookie; this tab re-reads it when it gets focus.
  await context.addCookies([consentCookie('true')]);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await assertHidden(page);
  await closeSite(visit);
});

test('region text: rest of world until a decline, EU text otherwise, set on every show', async () => {
  for (const [label, cookies, expected] of [
    ['no geo cookie', [], EU_TEXT],
    ['eu', [geoCookie('eu')], EU_TEXT],
    ['row', [geoCookie('row')], ROW_TEXT],
  ]) {
    const visit = await openSite(browser, { cookies });
    await banner(visit.page).waitFor();
    assert.equal(await bannerText(visit.page), expected, label);
    await closeSite(visit);
  }

  // A rest-of-world visitor who declines runs without cookies, so "running now" would be false.
  const visit = await openSite(browser, { cookies: [geoCookie('row')] });
  const { page } = visit;
  assert.equal(await bannerText(page), ROW_TEXT);
  await declineButton(page).click();
  await assertHidden(page);
  await settingsButton(page).click();
  await banner(page).waitFor();
  assert.equal(await bannerText(page), EU_TEXT);
  await acceptButton(page).click();
  await assertHidden(page);
  await settingsButton(page).click();
  await banner(page).waitFor();
  assert.equal(await bannerText(page), ROW_TEXT);
  await closeSite(visit);
});

test('a deep link opens the skill above the banner; once the visitor closes it, Accept works', async () => {
  // An undecided EU visitor lands on a per-skill page: it redirects to /, and app.js opens the
  // skill in the modal (z-index 1000), above the banner (z-index 900), by design.
  const visit = await openSite(browser, { pathname: '/skill/json-pretty/' });
  const { context, page } = visit;
  await page.locator('#skill-modal .modal-title', { hasText: 'json-pretty' }).waitFor();
  assert.equal(await page.locator('#privacy-choices').getAttribute('hidden'), null);
  assert.equal(await page.evaluate(() => {
    const accept = document.getElementById('privacy-accept').getBoundingClientRect();
    const top = document.elementFromPoint(accept.left + accept.width / 2, accept.top + accept.height / 2);
    return document.getElementById('modal-overlay').contains(top);
  }), true, 'the open modal covers the banner');

  // The visitor closes the skill with its own close control, then accepts with a plain click.
  await page.locator('#skill-modal').getByRole('button', { name: 'Close' }).click();
  await acceptButton(page).click();
  await assertHidden(page);
  const [cookie] = await cookiesNamed(context, CONSENT);
  assert.equal(cookie.value, 'true');
  assert.equal(cookie.domain, '.expanso.io');
  await closeSite(visit);
});

test('Accept, Decline, Close and "Cookie settings" are at least 44x44 CSS px', async () => {
  for (const viewport of [{ width: 1280, height: 800 }, { width: 375, height: 740 }]) {
    const visit = await openSite(browser, { viewport });
    const { page } = visit;
    await banner(page).waitFor();
    for (const [name, locator] of [
      ['Accept', acceptButton(page)],
      ['Decline', declineButton(page)],
      ['Close', closeButton(page)],
      ['Cookie settings', settingsButton(page)],
    ]) {
      const box = await locator.boundingBox();
      assert.ok(box.width >= 44 && box.height >= 44,
        `${name} is ${box.width}x${box.height} at ${viewport.width}px wide`);
    }
    await closeSite(visit);
  }
});

test('at 320 px wide the banner fits: no sideways scroll, every button in view, nothing overlaps', async () => {
  const viewport = { width: 320, height: 640 };
  const visit = await openSite(browser, { viewport });
  const { page } = visit;
  await banner(page).waitFor();
  const layout = await page.evaluate(() => {
    const box = (rect) => ({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom });
    // The lines of the banner text (the sentence and the privacy link) as drawn.
    const range = document.createRange();
    range.selectNodeContents(document.querySelector('#privacy-choices .privacy-choices__text'));
    return {
      scrollWidth: document.documentElement.scrollWidth,
      buttons: Object.fromEntries(['accept', 'decline', 'close']
        .map((name) => [name, box(document.getElementById(`privacy-${name}`).getBoundingClientRect())])),
      text: [...range.getClientRects()].filter((rect) => rect.width > 0).map(box),
    };
  });
  assert.ok(layout.scrollWidth <= viewport.width, `the page scrolls sideways: scrollWidth ${layout.scrollWidth}`);
  const overlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  const names = Object.keys(layout.buttons);
  for (const [i, name] of names.entries()) {
    const button = layout.buttons[name];
    assert.ok(button.left >= 0 && button.top >= 0 && button.right <= viewport.width && button.bottom <= viewport.height,
      `${name} is not fully in the viewport: ${JSON.stringify(button)}`);
    for (const other of names.slice(i + 1)) {
      assert.ok(!overlap(button, layout.buttons[other]), `${name} overlaps ${other}`);
    }
    assert.ok(!layout.text.some((line) => overlap(button, line)), `${name} overlaps the banner text`);
  }
  await closeSite(visit);
});

// Scoped to the banner and the footer control: the rest of the page has older contrast
// findings (category badges, the footer text) that this change does not touch.
test('axe finds no violations in the banner or "Cookie settings", in both themes', async () => {
  for (const theme of ['light', 'dark']) {
    const visit = await openSite(browser);
    const { page } = visit;
    // The site's own theme switch: stored, then applied before the first paint on reload, so
    // no colour transition is still running when axe reads the colours.
    await page.evaluate((value) => localStorage.setItem('theme', value), theme);
    await page.reload({ waitUntil: 'load' });
    assert.equal(await page.getAttribute('html', 'data-theme'), theme);
    await banner(page).waitFor();
    const results = await new AxeBuilder({ page }).include('#privacy-choices').include('#privacy-settings').analyze();
    const violations = results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(', ')}`);
    assert.deepEqual(violations, [], `${theme} theme`);
    await closeSite(visit);
  }
});
