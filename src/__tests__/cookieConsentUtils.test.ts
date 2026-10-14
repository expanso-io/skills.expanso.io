/**
 * Shared scenario test for cookieConsentUtils.ts. It is copied with the contract to every repo
 * on the list in expanso-cloud's CLAUDE.md (expanso.io's copy differs only in its import
 * line). It runs under Jest here and under node --test with a describe/it globals shim in
 * the copies. Uses node:assert rather than expect so the same file runs under both runners,
 * and declares the runner globals it needs so it type-checks without @types/jest.
 */
import assert from 'node:assert/strict';

import {
  COOKIE_CONSENT_CHANGE_EVENT,
  COOKIE_CONSENT_KEY,
  COOKIE_CONSENT_UTILS_VERSION,
  CONSENT_BANNER_DISMISSED_KEY,
  GEO_COOKIE_KEY,
  type ConsentEnvironment,
  type ConsentPostHog,
  type ConsentWatchTarget,
  type CookieConsentStatus,
  type KeyValueStorage,
  applyConsent,
  applySdkConsent,
  captureConsentChoice,
  consentCookieDomain,
  consentInitOptions,
  dismissConsentBanner,
  getCookieConsent,
  isConsentBannerDismissed,
  readGeo,
  sdkConsentFor,
  setCookieConsent,
  sweepPostHogSessionStorage,
  syncSdkConsentFlag,
  watchConsent,
} from '../cookieConsentUtils.ts';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void) => void;
declare const beforeEach: (fn: () => void) => void;

interface JarCookie {
  name: string;
  value: string;
  domain?: string;
}

/** A cookie jar that models the Domain attribute, which document.cookie hides on read. */
class CookieJar {
  cookies: JarCookie[] = [];

  seed(name: string, value: string, domain?: string) {
    this.cookies.push({ name, value, domain });
  }

  /** What document.cookie returns: name=value pairs only, in insertion order. */
  read(): string {
    return this.cookies.map((c) => `${c.name}=${c.value}`).join('; ');
  }

  /** What `document.cookie = ...` does, for the attribute subset this module writes. */
  write(header: string) {
    const [pair, ...attrs] = header.split(';').map((part) => part.trim());
    const eq = pair.indexOf('=');
    const name = pair.slice(0, eq);
    const value = pair.slice(eq + 1);
    const domainAttr = attrs.find((a) => a.toLowerCase().startsWith('domain='));
    const domain = domainAttr ? domainAttr.slice('domain='.length) : undefined;
    const expired = attrs.some((a) => a.toLowerCase() === 'max-age=0');
    this.cookies = this.cookies.filter((c) => !(c.name === name && c.domain === domain));
    if (!expired) this.cookies.push({ name, value, domain });
  }
}

function memoryStorage(entries: Record<string, string> = {}): KeyValueStorage {
  const map = new Map(Object.entries(entries));
  return {
    get length() {
      return map.size;
    },
    key: (i) => Array.from(map.keys())[i] ?? null,
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => {
      map.set(k, v);
    },
    removeItem: (k) => {
      map.delete(k);
    },
  };
}

function fakeEnvironment(hostname: string, options: { secure?: boolean } = {}) {
  const jar = new CookieJar();
  const dispatched: Array<{ type: string; detail: Record<string, unknown> }> = [];
  const localStorage = memoryStorage();
  const sessionStorage = memoryStorage();
  const env: ConsentEnvironment = {
    hostname,
    secure: options.secure ?? true,
    getCookie: () => jar.read(),
    setCookie: (value) => jar.write(value),
    dispatchEvent: (type, detail) => {
      dispatched.push({ type, detail });
    },
    localStorage,
    sessionStorage,
  };
  return { env, jar, dispatched, localStorage, sessionStorage };
}

function fakePostHog() {
  const calls: Array<[string, unknown?]> = [];
  const posthog: ConsentPostHog = {
    opt_in_capturing: (options) => {
      calls.push(['opt_in_capturing', options]);
    },
    opt_out_capturing: () => {
      calls.push(['opt_out_capturing']);
    },
    clear_opt_in_out_capturing: () => {
      calls.push(['clear_opt_in_out_capturing']);
    },
    capture: (event, properties) => {
      calls.push(['capture', { event, properties }]);
    },
  };
  return { posthog, calls };
}

/**
 * A fake SDK that keeps consent state the way posthog-js does: has_opted_in_capturing
 * reads it, and clear_opt_in_out_capturing only resets it to pending.
 */
function statefulPostHog(initial: 'granted' | 'denied' | 'pending') {
  const calls: string[] = [];
  let consent = initial;
  const posthog: ConsentPostHog = {
    has_opted_in_capturing: () => consent === 'granted',
    opt_in_capturing: () => {
      calls.push('opt_in_capturing');
      consent = 'granted';
    },
    opt_out_capturing: () => {
      calls.push('opt_out_capturing');
      consent = 'denied';
    },
    clear_opt_in_out_capturing: () => {
      calls.push('clear_opt_in_out_capturing');
      consent = 'pending';
    },
  };
  return { posthog, calls, consent: () => consent };
}

function fakeTarget() {
  const listeners = new Map<string, Set<() => void>>();
  const make = () => ({
    addEventListener: (type: string, listener: () => void) => {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type)?.add(listener);
    },
    removeEventListener: (type: string, listener: () => void) => {
      listeners.get(type)?.delete(listener);
    },
  });
  const target: ConsentWatchTarget = { ...make(), document: make(), cookieStore: make() };
  const fire = (type: string) => {
    for (const listener of listeners.get(type) ?? []) listener();
  };
  const count = () => Array.from(listeners.values()).reduce((n, set) => n + set.size, 0);
  return { target, fire, count };
}

describe('cookieConsentUtils version', () => {
  it('is the version every repo pins', () => {
    assert.equal(COOKIE_CONSENT_UTILS_VERSION, '1.3.0');
  });
});

describe('consentCookieDomain', () => {
  it('shares on the two Expanso domains and nowhere else', () => {
    assert.equal(consentCookieDomain('expanso.io'), 'expanso.io');
    assert.equal(consentCookieDomain('www.expanso.io'), 'expanso.io');
    assert.equal(consentCookieDomain('docs.expanso.io'), 'expanso.io');
    assert.equal(consentCookieDomain('cloud.expanso.io'), 'expanso.io');
    assert.equal(consentCookieDomain('dev-cloud.expanso.dev'), 'expanso.dev');
    assert.equal(consentCookieDomain('localhost'), undefined);
    assert.equal(consentCookieDomain('abc123.expanso-io.pages.dev'), undefined);
    assert.equal(consentCookieDomain('notexpanso.io'), undefined);
  });
});

describe('getCookieConsent', () => {
  it('reads a single shared cookie', () => {
    const { env, jar } = fakeEnvironment('docs.expanso.io');
    assert.equal(getCookieConsent(env), 'undecided');
    jar.seed(COOKIE_CONSENT_KEY, 'true', 'expanso.io');
    assert.equal(getCookieConsent(env), 'yes');
    jar.cookies = [];
    jar.seed(COOKIE_CONSENT_KEY, 'false', 'expanso.io');
    assert.equal(getCookieConsent(env), 'no');
  });

  it('treats a malformed value as undecided', () => {
    const { env, jar } = fakeEnvironment('docs.expanso.io');
    jar.seed(COOKIE_CONSENT_KEY, 'maybe', 'expanso.io');
    assert.equal(getCookieConsent(env), 'undecided');
  });

  it('honours only the shared cookie when a stale host-only copy disagrees, in either order', () => {
    for (const [shared, hostOnly, expected] of [
      ['true', 'false', 'yes'],
      ['false', 'true', 'no'],
    ] as const) {
      const first = fakeEnvironment('cloud.expanso.io');
      first.jar.seed(COOKIE_CONSENT_KEY, hostOnly);
      first.jar.seed(COOKIE_CONSENT_KEY, shared, 'expanso.io');
      assert.equal(getCookieConsent(first.env), expected, `host-only first, shared=${shared}`);
      assert.deepEqual(
        first.jar.cookies.map((c) => c.domain),
        ['expanso.io'],
        'the host-only copy is gone after the read',
      );

      const second = fakeEnvironment('cloud.expanso.io');
      second.jar.seed(COOKIE_CONSENT_KEY, shared, 'expanso.io');
      second.jar.seed(COOKIE_CONSENT_KEY, hostOnly);
      assert.equal(getCookieConsent(second.env), expected, `shared first, shared=${shared}`);
    }
  });

  it('drops a lone host-only cookie on a production host and asks again', () => {
    for (const seeded of ['true', 'false'] as const) {
      const { env, jar } = fakeEnvironment('www.expanso.io');
      jar.seed(COOKIE_CONSENT_KEY, seeded);
      assert.equal(getCookieConsent(env), 'undecided', seeded);
      assert.equal(jar.cookies.length, 0, `${seeded}: the stale host-only copy is gone`);
    }
  });

  it('keeps a host-only cookie on localhost and previews, where it is the real one', () => {
    for (const hostname of ['localhost', 'abc123.expanso-io.pages.dev']) {
      const { env, jar } = fakeEnvironment(hostname, { secure: hostname !== 'localhost' });
      jar.seed(COOKIE_CONSENT_KEY, 'false');
      assert.equal(getCookieConsent(env), 'no', hostname);
      assert.equal(jar.cookies.length, 1, hostname);
    }
  });

  it('fails closed when two disagreeing copies survive the purge', () => {
    // Two host-only entries with different paths, as a browser would present them on a
    // non-production host where nothing is purged; the accept sorts first.
    const { env, jar } = fakeEnvironment('localhost', { secure: false });
    jar.seed(COOKIE_CONSENT_KEY, 'true');
    jar.seed(COOKIE_CONSENT_KEY, 'false');
    assert.equal(getCookieConsent(env), 'no');
    assert.equal(jar.cookies.length, 2, 'nothing is purged off a non-production host');
  });

  it('returns undecided without a browser', () => {
    assert.equal(getCookieConsent(undefined), 'undecided');
  });
});

describe('setCookieConsent', () => {
  it('writes one shared cookie on production hosts and clears the host-only copy', () => {
    for (const [hostname, domain] of [
      ['cloud.expanso.io', 'expanso.io'],
      ['docs.expanso.io', 'expanso.io'],
      ['www.expanso.io', 'expanso.io'],
      ['dev-cloud.expanso.dev', 'expanso.dev'],
    ] as const) {
      const { env, jar } = fakeEnvironment(hostname);
      jar.seed(COOKIE_CONSENT_KEY, 'true');
      jar.seed(COOKIE_CONSENT_KEY, 'true', domain);
      setCookieConsent('no', env);
      assert.deepEqual(
        jar.cookies,
        [{ name: COOKIE_CONSENT_KEY, value: 'false', domain }],
        hostname,
      );
    }
  });

  it('writes a host-only cookie on localhost and previews', () => {
    for (const hostname of ['localhost', 'abc123.expanso-io.pages.dev']) {
      const { env, jar } = fakeEnvironment(hostname);
      setCookieConsent('yes', env);
      assert.deepEqual(jar.cookies, [
        { name: COOKIE_CONSENT_KEY, value: 'true', domain: undefined },
      ]);
    }
  });

  it('clears the host-only copy, then overwrites the shared cookie in place', () => {
    const written: string[] = [];
    const { env } = fakeEnvironment('cloud.expanso.io');
    setCookieConsent('yes', { ...env, setCookie: (v) => written.push(v) });
    assert.deepEqual(written, [
      'expanso-cookie-consent=; Max-Age=0; Path=/; SameSite=Lax; Secure',
      'expanso-cookie-consent=true; Max-Age=31536000; Path=/; SameSite=Lax; Secure; Domain=expanso.io',
    ]);
  });

  it('never leaves another tab a moment without the recorded choice', () => {
    for (const [hostname, domain] of [
      ['docs.expanso.io', 'expanso.io'],
      ['expanso.io', 'expanso.io'],
      ['localhost', undefined],
    ] as const) {
      for (const [before, choice] of [
        ['true', 'yes'],
        ['false', 'no'],
        ['true', 'no'],
        ['false', 'yes'],
      ] as const) {
        const { env, jar } = fakeEnvironment(hostname);
        jar.seed(COOKIE_CONSENT_KEY, before, domain);
        const seen: CookieConsentStatus[] = [];
        setCookieConsent(choice, {
          ...env,
          setCookie: (v) => {
            jar.write(v);
            seen.push(getCookieConsent(env));
          },
        });
        const trace = `${hostname} ${before} -> ${choice}: ${seen.join(',')}`;
        assert.ok(!seen.includes('undecided'), trace);
        assert.equal(seen[seen.length - 1], choice, trace);
      }
    }
  });

  it('omits Secure on http', () => {
    const written: string[] = [];
    const { env } = fakeEnvironment('localhost', { secure: false });
    setCookieConsent('no', { ...env, setCookie: (v) => written.push(v) });
    assert.equal(
      written[written.length - 1],
      'expanso-cookie-consent=false; Max-Age=31536000; Path=/; SameSite=Lax',
    );
  });

  it('notifies the tab with the status', () => {
    const { env, dispatched } = fakeEnvironment('cloud.expanso.io');
    setCookieConsent('yes', env);
    assert.deepEqual(dispatched, [
      { type: COOKIE_CONSENT_CHANGE_EVENT, detail: { status: 'yes' } },
    ]);
  });
});

describe('consentInitOptions', () => {
  it('pins the lane and shares the identity cookie only under expanso.io', () => {
    const prod = consentInitOptions('cloud.expanso.io');
    assert.deepEqual(prod, {
      opt_out_capturing_by_default: true,
      cookieless_mode: 'on_reject',
      persistence: 'localStorage+cookie',
      cross_subdomain_cookie: true,
      disable_surveys: true,
      defaults: '2026-08-29',
    });
    assert.equal(consentInitOptions('www.expanso.io').cross_subdomain_cookie, true);
    assert.equal(consentInitOptions('dev-cloud.expanso.dev').cross_subdomain_cookie, false);
    assert.equal(consentInitOptions('localhost').cross_subdomain_cookie, false);
    assert.equal(consentInitOptions('abc123.expanso-io.pages.dev').cross_subdomain_cookie, false);
  });
});

describe('syncSdkConsentFlag', () => {
  const token = 'phc_test';
  const key = `__ph_opt_in_out_${token}`;

  it('writes the SDK grant when the cookie says yes', () => {
    const { env, localStorage } = fakeEnvironment('cloud.expanso.io');
    syncSdkConsentFlag(token, 'yes', env);
    assert.equal(localStorage.getItem(key), '1');
  });

  it('removes a stale grant when the cookie says no or nothing', () => {
    for (const status of ['no', 'undecided'] as const) {
      const { env, localStorage } = fakeEnvironment('cloud.expanso.io');
      localStorage.setItem(key, '1');
      syncSdkConsentFlag(token, status, env);
      assert.equal(localStorage.getItem(key), null, status);
    }
  });

  it('does nothing without a token or storage', () => {
    const { env, localStorage } = fakeEnvironment('cloud.expanso.io');
    localStorage.setItem(key, '1');
    syncSdkConsentFlag('', 'no', env);
    assert.equal(localStorage.getItem(key), '1');
    syncSdkConsentFlag(token, 'yes', { ...env, localStorage: undefined });
    syncSdkConsentFlag(token, 'yes', undefined);
  });
});

describe('applyConsent', () => {
  it('opts in without the SDK opt-in event', () => {
    const { posthog, calls } = fakePostHog();
    applyConsent(posthog, 'yes', fakeEnvironment('cloud.expanso.io').env);
    assert.deepEqual(calls, [['opt_in_capturing', { captureEventName: null }]]);
  });

  it('opts out and sweeps ph_* sessionStorage for no, in either region', () => {
    for (const geo of [undefined, 'row'] as const) {
      const { posthog, calls } = fakePostHog();
      const { env, jar, sessionStorage } = fakeEnvironment('cloud.expanso.io');
      if (geo) jar.seed(GEO_COOKIE_KEY, geo);
      sessionStorage.setItem('ph_phc_test_window_id', 'w1');
      sessionStorage.setItem('unrelated', 'keep');
      applyConsent(posthog, 'no', env);
      assert.deepEqual(calls, [['opt_out_capturing']], String(geo));
      assert.equal(sessionStorage.getItem('ph_phc_test_window_id'), null, String(geo));
      assert.equal(sessionStorage.getItem('unrelated'), 'keep', String(geo));
    }
  });

  it('resets undecided EU visitors to pending instead of recording a denial', () => {
    const { posthog, calls } = fakePostHog();
    const { env, sessionStorage } = fakeEnvironment('cloud.expanso.io');
    sessionStorage.setItem('ph_phc_test_window_id', 'w1');
    applyConsent(posthog, 'undecided', env);
    assert.deepEqual(calls, [['clear_opt_in_out_capturing']]);
    assert.equal(sessionStorage.getItem('ph_phc_test_window_id'), null);
  });

  it('opts in for yes in the rest of the world too', () => {
    const { posthog, calls } = fakePostHog();
    const { env, jar } = fakeEnvironment('cloud.expanso.io');
    jar.seed(GEO_COOKIE_KEY, 'row');
    applyConsent(posthog, 'yes', env);
    assert.deepEqual(calls, [['opt_in_capturing', { captureEventName: null }]]);
  });

  it('opts undecided rest-of-world visitors in, silently', () => {
    const { posthog, calls } = fakePostHog();
    const { env, jar } = fakeEnvironment('cloud.expanso.io');
    jar.seed(GEO_COOKIE_KEY, 'row');
    applyConsent(posthog, 'undecided', env);
    assert.deepEqual(calls, [['opt_in_capturing', { captureEventName: null }]]);
  });

  it('never throws: missing SDK, missing methods, throwing SDK', () => {
    applyConsent(undefined, 'yes');
    applyConsent({}, 'no', fakeEnvironment('cloud.expanso.io').env);
    applyConsent(
      {
        opt_out_capturing: () => {
          throw new Error('boom');
        },
      },
      'no',
      fakeEnvironment('cloud.expanso.io').env,
    );
  });
});

describe('sweepPostHogSessionStorage', () => {
  it('survives a storage that throws', () => {
    const throwing: KeyValueStorage = {
      get length(): number {
        throw new Error('blocked');
      },
      key: () => null,
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    };
    sweepPostHogSessionStorage({
      ...fakeEnvironment('cloud.expanso.io').env,
      sessionStorage: throwing,
    });
  });
});

describe('captureConsentChoice', () => {
  it('captures cookie_consent with the shared property shape', () => {
    const { posthog, calls } = fakePostHog();
    captureConsentChoice(posthog, 'no', 'settings');
    assert.deepEqual(calls, [
      [
        'capture',
        {
          event: 'cookie_consent',
          properties: { consent: 'no', scope: 'analytics', method: 'settings' },
        },
      ],
    ]);
  });

  it('tolerates a missing SDK', () => {
    captureConsentChoice(undefined, 'yes', 'banner');
  });

  it('takes only banner or settings as source, here and in dismissConsentBanner', () => {
    // The type checker is the test: each line fails it if that source parameter widens to string.
    const capture: string extends Parameters<typeof captureConsentChoice>[2] ? never : true = true;
    const dismiss: string extends Parameters<typeof dismissConsentBanner>[1] ? never : true = true;
    assert.ok(capture && dismiss);
  });
});

describe('dismissConsentBanner', () => {
  it('writes a host-only 30-day marker on every host, so each site keeps its own notice', () => {
    for (const hostname of [
      'cloud.expanso.io',
      'docs.expanso.io',
      'www.expanso.io',
      'dev-cloud.expanso.dev',
      'localhost',
      'abc123.expanso-io.pages.dev',
    ]) {
      const { env, jar } = fakeEnvironment(hostname);
      dismissConsentBanner(undefined, 'banner', env);
      assert.deepEqual(
        jar.cookies,
        [{ name: CONSENT_BANNER_DISMISSED_KEY, value: '1', domain: undefined }],
        hostname,
      );
    }
    const written: string[] = [];
    const { env } = fakeEnvironment('docs.expanso.io');
    dismissConsentBanner(undefined, 'banner', { ...env, setCookie: (v) => written.push(v) });
    // Reading consent first also purges a host-only consent cookie; only the marker matters.
    assert.deepEqual(
      written.filter((v) => v.startsWith(CONSENT_BANNER_DISMISSED_KEY)),
      ['expanso-cookie-banner-dismissed=1; Max-Age=2592000; Path=/; SameSite=Lax; Secure'],
    );
  });

  it('records no choice: consent stays undecided, the SDK lane is unchanged, no change event', () => {
    for (const geo of ['eu', 'row'] as const) {
      const { env, jar, dispatched, localStorage } = fakeEnvironment('www.expanso.io');
      jar.seed(GEO_COOKIE_KEY, geo);
      dismissConsentBanner(undefined, 'banner', env);
      assert.equal(getCookieConsent(env), 'undecided', geo);
      assert.equal(
        sdkConsentFor(getCookieConsent(env), readGeo(env)),
        sdkConsentFor('undecided', geo),
      );
      syncSdkConsentFlag('phc_test', getCookieConsent(env), env);
      assert.equal(localStorage.getItem('__ph_opt_in_out_phc_test'), geo === 'row' ? '1' : null);
      assert.deepEqual(dispatched, [], geo);
    }
  });

  it('captures cookie_banner_dismissed with the banner it came from as method', () => {
    for (const source of ['banner', 'settings'] as const) {
      const { env } = fakeEnvironment('cloud.expanso.io');
      const { posthog, calls } = fakePostHog();
      dismissConsentBanner(posthog, source, env);
      assert.deepEqual(calls, [
        [
          'capture',
          {
            event: 'cookie_banner_dismissed',
            properties: { scope: 'analytics', method: source },
          },
        ],
      ]);
    }
  });

  it('counts a close once: a second close, e.g. from another tab, writes and captures nothing', () => {
    const { env } = fakeEnvironment('docs.expanso.io');
    const { posthog, calls } = fakePostHog();
    dismissConsentBanner(posthog, 'banner', env);
    const written: string[] = [];
    dismissConsentBanner(posthog, 'banner', { ...env, setCookie: (v) => written.push(v) });
    assert.equal(calls.length, 1);
    assert.deepEqual(
      written.filter((v) => v.startsWith(CONSENT_BANNER_DISMISSED_KEY)),
      [],
    );
  });

  it('captures nothing when the browser drops the write, e.g. all cookies blocked', () => {
    const { env } = fakeEnvironment('docs.expanso.io');
    const { posthog, calls } = fakePostHog();
    const blocked: ConsentEnvironment = { ...env, setCookie: () => {} };
    dismissConsentBanner(posthog, 'banner', blocked);
    dismissConsentBanner(posthog, 'banner', blocked);
    assert.deepEqual(calls, []);
    assert.equal(isConsentBannerDismissed(blocked), false);
  });

  it('does nothing for a visitor who already chose, e.g. closing a reopened settings card', () => {
    for (const value of ['true', 'false']) {
      const { env, jar } = fakeEnvironment('docs.expanso.io');
      jar.seed(COOKIE_CONSENT_KEY, value, 'expanso.io');
      const { posthog, calls } = fakePostHog();
      dismissConsentBanner(posthog, 'banner', env);
      assert.deepEqual(calls, [], value);
      assert.equal(isConsentBannerDismissed(env), false, value);
    }
  });

  it('never throws: throwing cookie jar and SDK', () => {
    const { env } = fakeEnvironment('cloud.expanso.io');
    const throwing: ConsentPostHog = {
      capture: () => {
        throw new Error('boom');
      },
    };
    dismissConsentBanner(throwing, 'banner', {
      ...env,
      setCookie: () => {
        throw new Error('blocked');
      },
    });
    dismissConsentBanner(throwing, 'banner', {
      ...env,
      getCookie: () => {
        throw new Error('blocked');
      },
    });
  });
});

describe('isConsentBannerDismissed', () => {
  it('is false until the banner is dismissed, then true on that site only', () => {
    const { env, jar } = fakeEnvironment('www.expanso.io');
    assert.equal(isConsentBannerDismissed(env), false);
    dismissConsentBanner(undefined, 'banner', env);
    assert.equal(isConsentBannerDismissed(env), true);
    // A host-only cookie is never sent to another host, so docs sees an empty jar.
    assert.equal(jar.cookies[0].domain, undefined);
    assert.equal(isConsentBannerDismissed(fakeEnvironment('docs.expanso.io').env), false);
  });

  it('ignores any value other than 1', () => {
    const { env, jar } = fakeEnvironment('cloud.expanso.io');
    jar.seed(CONSENT_BANNER_DISMISSED_KEY, 'yes');
    assert.equal(isConsentBannerDismissed(env), false);
  });

  it('is false without a browser or when the cookie jar throws', () => {
    assert.equal(isConsentBannerDismissed(undefined), false);
    const { env } = fakeEnvironment('cloud.expanso.io');
    assert.equal(
      isConsentBannerDismissed({
        ...env,
        getCookie: () => {
          throw new Error('blocked');
        },
      }),
      false,
    );
  });
});

describe('watchConsent', () => {
  let world: ReturnType<typeof fakeEnvironment>;
  let watched: ReturnType<typeof fakeTarget>;
  let seen: CookieConsentStatus[];

  beforeEach(() => {
    world = fakeEnvironment('cloud.expanso.io');
    watched = fakeTarget();
    seen = [];
  });

  it('fires once per change and not on identical re-reads', () => {
    const stop = watchConsent((s) => seen.push(s), watched.target, world.env);
    watched.fire('focus');
    assert.deepEqual(seen, []);
    world.jar.seed(COOKIE_CONSENT_KEY, 'true', 'expanso.io');
    watched.fire('visibilitychange');
    watched.fire('focus');
    assert.deepEqual(seen, ['yes']);
    world.jar.cookies = [];
    world.jar.seed(COOKIE_CONSENT_KEY, 'false', 'expanso.io');
    watched.fire('change');
    assert.deepEqual(seen, ['yes', 'no']);
    watched.fire(COOKIE_CONSENT_CHANGE_EVENT);
    assert.deepEqual(seen, ['yes', 'no']);
    stop();
    assert.equal(watched.count(), 0, 'unsubscribe removes every listener');
  });

  it('is a no-op without a window', () => {
    const stop = watchConsent((s) => seen.push(s), undefined, world.env);
    stop();
    assert.deepEqual(seen, []);
  });
});

describe('readGeo', () => {
  it('reads each valid value', () => {
    for (const value of ['eu', 'row'] as const) {
      const { env, jar } = fakeEnvironment('cloud.expanso.io');
      jar.seed(GEO_COOKIE_KEY, value);
      assert.equal(readGeo(env), value);
    }
  });

  it('treats a missing cookie as eu', () => {
    assert.equal(readGeo(fakeEnvironment('cloud.expanso.io').env), 'eu');
  });

  it('treats two agreeing row copies as row', () => {
    const { env, jar } = fakeEnvironment('cloud.expanso.io');
    jar.seed(GEO_COOKIE_KEY, 'row');
    jar.seed(GEO_COOKIE_KEY, 'row', 'expanso.io');
    assert.equal(readGeo(env), 'row');
  });

  it('treats two conflicting copies as eu, whichever comes first', () => {
    for (const order of [
      ['row', 'eu'],
      ['eu', 'row'],
    ] as const) {
      const { env, jar } = fakeEnvironment('cloud.expanso.io');
      jar.seed(GEO_COOKIE_KEY, order[0]);
      jar.seed(GEO_COOKIE_KEY, order[1], 'expanso.io');
      assert.equal(readGeo(env), 'eu', order.join(','));
    }
  });

  it('treats a malformed value as eu', () => {
    // The cookie reader trims each entry, so trailing whitespace is not a case here.
    for (const value of ['ROW', 'us', '', 'eu,row']) {
      const { env, jar } = fakeEnvironment('cloud.expanso.io');
      jar.seed(GEO_COOKIE_KEY, value);
      assert.equal(readGeo(env), 'eu', JSON.stringify(value));
    }
  });
});

describe('sdkConsentFor', () => {
  it('maps every status and region to an SDK decision', () => {
    assert.equal(sdkConsentFor('yes', 'eu'), 'granted');
    assert.equal(sdkConsentFor('yes', 'row'), 'granted');
    assert.equal(sdkConsentFor('no', 'eu'), 'denied');
    assert.equal(sdkConsentFor('no', 'row'), 'denied');
    assert.equal(sdkConsentFor('undecided', 'eu'), 'pending');
    assert.equal(sdkConsentFor('undecided', 'row'), 'granted');
  });
});

describe('applySdkConsent', () => {
  it('maps each decision to one SDK call', () => {
    const cases = [
      ['granted', [['opt_in_capturing', { captureEventName: null }]]],
      ['denied', [['opt_out_capturing']]],
      ['pending', [['clear_opt_in_out_capturing']]],
    ] as const;
    for (const [decision, expected] of cases) {
      const { posthog, calls } = fakePostHog();
      applySdkConsent(posthog, decision, fakeEnvironment('cloud.expanso.io').env);
      assert.deepEqual(calls, expected, decision);
    }
  });

  it('does not sweep sessionStorage when granting', () => {
    const { posthog } = fakePostHog();
    const { env, sessionStorage } = fakeEnvironment('cloud.expanso.io');
    sessionStorage.setItem('ph_phc_test_window_id', 'w1');
    applySdkConsent(posthog, 'granted', env);
    assert.equal(sessionStorage.getItem('ph_phc_test_window_id'), 'w1');
  });

  it('tears down a live opted-in SDK on granted to pending, without recording a denial', () => {
    const { posthog, calls, consent } = statefulPostHog('granted');
    const { env, sessionStorage } = fakeEnvironment('cloud.expanso.io');
    sessionStorage.setItem('ph_phc_test_window_id', 'w1');
    applySdkConsent(posthog, 'pending', env);
    assert.deepEqual(calls, ['opt_out_capturing', 'clear_opt_in_out_capturing']);
    assert.equal(consent(), 'pending');
    assert.equal(sessionStorage.getItem('ph_phc_test_window_id'), null);
  });

  it('only clears on pending when the SDK was never opted in', () => {
    const { posthog, calls, consent } = statefulPostHog('pending');
    applySdkConsent(posthog, 'pending', fakeEnvironment('cloud.expanso.io').env);
    assert.deepEqual(calls, ['clear_opt_in_out_capturing']);
    assert.equal(consent(), 'pending');
  });

  it('never throws', () => {
    applySdkConsent(undefined, 'granted');
    applySdkConsent({}, 'pending', fakeEnvironment('cloud.expanso.io').env);
    applySdkConsent(
      {
        clear_opt_in_out_capturing: () => {
          throw new Error('boom');
        },
      },
      'pending',
      fakeEnvironment('cloud.expanso.io').env,
    );
  });
});

describe('syncSdkConsentFlag with geo', () => {
  const token = 'phc_test';
  const key = `__ph_opt_in_out_${token}`;

  it('writes the grant for an undecided rest-of-world visitor', () => {
    const { env, jar, localStorage } = fakeEnvironment('cloud.expanso.io');
    jar.seed(GEO_COOKIE_KEY, 'row');
    syncSdkConsentFlag(token, 'undecided', env);
    assert.equal(localStorage.getItem(key), '1');
  });

  it('removes a grant left by an earlier undecided page once the visitor declines', () => {
    const { env, jar, localStorage } = fakeEnvironment('cloud.expanso.io');
    jar.seed(GEO_COOKIE_KEY, 'row');
    localStorage.setItem(key, '1');
    syncSdkConsentFlag(token, 'no', env);
    assert.equal(localStorage.getItem(key), null);
  });
});
