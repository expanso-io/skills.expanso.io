// Loads the built consent runtime (docs/js/consent-runtime.js, from `npm run build`) the way
// a browser loads a classic script, and checks that it installs window.__expansoConsent with
// exactly the members the banner (js/privacy-choices.js) and js/analytics.js call.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const BUNDLE = new URL('../docs/js/consent-runtime.js', import.meta.url);
const MEMBERS = [
  'applyConsent',
  'captureConsentChoice',
  'consentInitOptions',
  'dismissConsentBanner',
  'getCookieConsent',
  'isConsentBannerDismissed',
  'readGeo',
  'setCookieConsent',
  'syncSdkConsentFlag',
  'watchConsent',
];

function readBundle() {
  try {
    return readFileSync(BUNDLE, 'utf8');
  } catch (error) {
    assert.fail(`docs/js/consent-runtime.js is missing; run npm run build first (${error.code})`);
  }
}

/** A window and document with just what the contract touches, on the production host. */
function browserLike(cookie) {
  const writes = [];
  const window = {
    location: { hostname: 'skills.expanso.io', protocol: 'https:' },
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {},
  };
  const document = {
    get cookie() {
      return cookie;
    },
    set cookie(value) {
      writes.push(value);
    },
    addEventListener() {},
    removeEventListener() {},
  };
  return { context: vm.createContext({ window, document }), window, writes };
}

test('the bundle is a classic script that installs exactly the members the site calls', () => {
  const { context, window } = browserLike('');
  // vm.Script compiles a classic script: an import or export statement is a SyntaxError here.
  new vm.Script(readBundle(), { filename: 'consent-runtime.js' }).runInContext(context);
  assert.deepEqual(Object.keys(window.__expansoConsent).sort(), MEMBERS);
  for (const name of MEMBERS) {
    assert.equal(typeof window.__expansoConsent[name], 'function', `${name} is not a function`);
  }
});

test('a second copy of the script keeps the first runtime', () => {
  const { context, window } = browserLike('');
  const script = new vm.Script(readBundle(), { filename: 'consent-runtime.js' });
  script.runInContext(context);
  const first = window.__expansoConsent;
  script.runInContext(context);
  assert.equal(window.__expansoConsent, first);
});

test('the members are the shared contract: they read the shared consent and geo cookies', () => {
  const { context, window, writes } = browserLike('expanso-cookie-consent=true; expanso-geo=row');
  new vm.Script(readBundle(), { filename: 'consent-runtime.js' }).runInContext(context);
  assert.equal(window.__expansoConsent.getCookieConsent(), 'yes');
  assert.equal(window.__expansoConsent.readGeo(), 'row');
  // The contract's read first deletes a stale host-only copy of the consent cookie. Check only
  // what makes it that delete: the exact attributes belong to the contract, not to this test.
  assert.equal(writes.length, 1);
  assert.match(writes[0], /^expanso-cookie-consent=;.*\bMax-Age=0\b/);
  assert.doesNotMatch(writes[0], /Domain=/i);
});
