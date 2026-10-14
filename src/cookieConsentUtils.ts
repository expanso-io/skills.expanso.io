/**
 * Shared cookie-consent contract for the Expanso sites.
 *
 * CANONICAL COPY: expanso-io/expanso-cloud, src/components/cookies/cookieConsentUtils.ts.
 * Other repos carry byte-identical copies of this file and its test (expanso.io's test differs
 * only in its import line). The one list of those repos is in expanso-cloud's CLAUDE.md, in
 * the cookie consent section. Change this file here first, bump COOKIE_CONSENT_UTILS_VERSION,
 * run the tests, then copy this file and its test to every repo on that list. Never edit a
 * copy in place.
 *
 * No imports on purpose: the marketing site inlines this file into every page through
 * esbuild and Node runs the test with type stripping only, so it must stay dependency-free
 * and use erasable TypeScript syntax (no enums, no parameter properties, no namespaces).
 */

export const COOKIE_CONSENT_UTILS_VERSION = '1.3.0';

export type CookieConsentStatus = 'undecided' | 'yes' | 'no';
export type CookieConsentChoice = Exclude<CookieConsentStatus, 'undecided'>;
export type CookieConsentSource = 'banner' | 'settings';
/** The visitor's region, from each site's own host-only geo cookie. */
export type ConsentGeo = 'eu' | 'row';
/** What the PostHog SDK is told. See sdkConsentFor. */
export type SdkConsent = 'granted' | 'denied' | 'pending';

export const COOKIE_CONSENT_KEY = 'expanso-cookie-consent';
/** Set per site by its edge: marketing's Pages middleware, cloud's proxy, the docs Worker. */
export const GEO_COOKIE_KEY = 'expanso-geo';
/** Same-tab notification, dispatched on window with `detail: { status }`. */
export const COOKIE_CONSENT_CHANGE_EVENT = 'cookie_consent_change';
export const COOKIE_CONSENT_POSTHOG_EVENT = 'cookie_consent';
/** Set, host-only, when a site's banner is closed without a choice. See dismissConsentBanner. */
export const CONSENT_BANNER_DISMISSED_KEY = 'expanso-cookie-banner-dismissed';
export const CONSENT_BANNER_DISMISSED_POSTHOG_EVENT = 'cookie_banner_dismissed';
/** posthog-js behaviour set. Changing this date is a reviewed, deliberate act. */
export const POSTHOG_DEFAULTS_DATE = '2026-08-29';

const COOKIE_CONSENT_MAX_AGE_SECONDS = 31536000;
/**
 * 30 days, after which an undecided visitor sees the banner again. Safari's tracking
 * prevention caps cookies set from script at 7 days, so there it is a week.
 */
const CONSENT_BANNER_DISMISSED_MAX_AGE_SECONDS = 2592000;
const SDK_CONSENT_KEY_PREFIX = '__ph_opt_in_out_';
const SDK_SESSION_STORAGE_PREFIX = 'ph_';

/** Satisfied by localStorage and sessionStorage. */
export interface KeyValueStorage {
  readonly length: number;
  key(index: number): string | null;
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** Everything this module touches in a browser, injectable so tests need no DOM. */
export interface ConsentEnvironment {
  hostname: string;
  secure: boolean;
  getCookie(): string;
  setCookie(value: string): void;
  dispatchEvent(type: string, detail: Record<string, unknown>): void;
  localStorage?: KeyValueStorage;
  sessionStorage?: KeyValueStorage;
}

/** The posthog-js surface this module calls. Structural, so no posthog-js import is needed. */
export interface ConsentPostHog {
  opt_in_capturing?(options?: { captureEventName?: string | null | false }): void;
  opt_out_capturing?(): void;
  clear_opt_in_out_capturing?(): void;
  has_opted_in_capturing?(): boolean;
  capture?(event: string, properties?: Record<string, unknown>): void;
}

interface EventTargetLike {
  addEventListener(type: string, listener: () => void): void;
  removeEventListener(type: string, listener: () => void): void;
}

/** window, structurally: the pieces watchConsent listens on. */
export interface ConsentWatchTarget extends EventTargetLike {
  document?: EventTargetLike;
  cookieStore?: EventTargetLike;
}

function safeStorage(read: () => KeyValueStorage | undefined): KeyValueStorage | undefined {
  try {
    return read();
  } catch {
    return undefined;
  }
}

/** The real browser, or undefined during SSR and in Node. */
export function browserEnvironment(): ConsentEnvironment | undefined {
  if (typeof window === 'undefined' || typeof document === 'undefined') return undefined;
  return {
    hostname: window.location.hostname,
    secure: window.location.protocol === 'https:',
    getCookie: () => document.cookie,
    setCookie: (value) => {
      document.cookie = value;
    },
    dispatchEvent: (type, detail) => {
      window.dispatchEvent(new CustomEvent(type, { detail }));
    },
    localStorage: safeStorage(() => window.localStorage),
    sessionStorage: safeStorage(() => window.sessionStorage),
  };
}

function browserWatchTarget(): ConsentWatchTarget | undefined {
  if (typeof window === 'undefined') return undefined;
  return window as unknown as ConsentWatchTarget;
}

/**
 * The cookie domain a production host shares its choice on. Anything else (localhost,
 * *.pages.dev previews) writes a host-only cookie and is never purged.
 */
export function consentCookieDomain(hostname: string): string | undefined {
  if (hostname === 'expanso.io' || hostname.endsWith('.expanso.io')) return 'expanso.io';
  if (hostname === 'expanso.dev' || hostname.endsWith('.expanso.dev')) return 'expanso.dev';
  return undefined;
}

function cookieAttributes(env: ConsentEnvironment, domain?: string): string {
  const secure = env.secure ? '; Secure' : '';
  const scope = domain ? `; Domain=${domain}` : '';
  return `; Path=/; SameSite=Lax${secure}${scope}`;
}

function readCookieValues(env: ConsentEnvironment, name: string): string[] {
  const prefix = `${name}=`;
  const raw = env.getCookie();
  const entries = raw ? raw.split(';') : [];
  const values: string[] = [];
  for (const entry of entries) {
    const trimmed = entry.trim();
    if (!trimmed.startsWith(prefix)) continue;
    try {
      values.push(decodeURIComponent(trimmed.slice(prefix.length)));
    } catch {
      values.push('');
    }
  }
  return values;
}

function writeSharedConsentCookie(env: ConsentEnvironment, value: string): void {
  env.setCookie(
    `${COOKIE_CONSENT_KEY}=${encodeURIComponent(value)}; Max-Age=${COOKIE_CONSENT_MAX_AGE_SECONDS}${cookieAttributes(env, consentCookieDomain(env.hostname))}`,
  );
}

/**
 * Delete the host-only copy of the consent cookie on production hosts, so that only the
 * shared domain cookie is ever read. A delete with no Domain attribute removes only the
 * host-only copy, and JavaScript cannot tell the two apart by reading, which is why deletion
 * rather than filtering is the mechanism. This holds on the apex hosts too (expanso.io,
 * expanso.dev): browsers keep a host-only and a Domain cookie of the same name apart there as
 * well, so this delete never removes the shared cookie (checked in Chromium 140, Firefox 141
 * and WebKit 26).
 *
 * Does nothing on localhost or previews, where the host-only cookie is the real one.
 */
export function purgeHostOnlyConsentCookie(
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  if (!env || !consentCookieDomain(env.hostname)) return;
  env.setCookie(`${COOKIE_CONSENT_KEY}=; Max-Age=0${cookieAttributes(env)}`);
}

/** The visitor's recorded choice. Only the shared domain cookie counts on production hosts. */
export function getCookieConsent(
  env: ConsentEnvironment | undefined = browserEnvironment(),
): CookieConsentStatus {
  if (!env) return 'undecided';
  try {
    purgeHostOnlyConsentCookie(env);
    const distinct = Array.from(new Set(readCookieValues(env, COOKIE_CONSENT_KEY)));
    if (distinct.length === 0) return 'undecided';
    // Two disagreeing copies should be impossible after the purge (our writers always use
    // Path=/). If it happens anyway, fail closed: a withdrawal must never lose to a stale
    // accept, and on sites where "undecided" means default-on tracking that is the only
    // safe answer.
    if (distinct.length > 1) return 'no';
    if (distinct[0] === 'true') return 'yes';
    if (distinct[0] === 'false') return 'no';
    return 'undecided';
  } catch {
    return 'undecided';
  }
}

/**
 * The visitor's region. A missing cookie means eu, and so does more than one distinct
 * value: the same fail-closed rule as the consent cookie. This keeps Part 2's rollout safe
 * for privacy in any order — a site whose geo signal is not live yet behaves as before.
 * It does not keep identity whole: when two sites classify the same undecided visitor
 * differently (a site whose geo signal is not live yet, or a VPN/geo-database mismatch),
 * the eu site resets PostHog to pending. That disables persistence and removes the shared
 * .expanso.io identity cookie the row site wrote, so identity splits until the sites agree.
 */
export function readGeo(env: ConsentEnvironment | undefined = browserEnvironment()): ConsentGeo {
  if (!env) return 'eu';
  try {
    const distinct = Array.from(new Set(readCookieValues(env, GEO_COOKIE_KEY)));
    return distinct.length === 1 && distinct[0] === 'row' ? 'row' : 'eu';
  } catch {
    return 'eu';
  }
}

/**
 * The single place the Part 2 rule lives. An undecided rest-of-world visitor is granted
 * on the SDK — not left pending. Under our init (opt_out_capturing_by_default: true,
 * cookieless_mode: 'on_reject'), a pending visitor counts as rejected and runs cookieless
 * (verified against posthog-js 1.427.2); only a granted SDK tracks fully. Our consent
 * cookie stays undecided, so the banner still shows.
 */
export function sdkConsentFor(status: CookieConsentStatus, geo: ConsentGeo): SdkConsent {
  if (status === 'yes') return 'granted';
  if (status === 'no') return 'denied';
  return geo === 'row' ? 'granted' : 'pending';
}

/**
 * Record a choice: clear the host-only copy, overwrite the cookie that holds the choice,
 * notify this tab. That cookie is overwritten in place, never deleted first: a write with the
 * same name, Domain and Path replaces it, and a delete would give other tabs' cookieStore
 * listeners a moment in which no choice is recorded.
 */
export function setCookieConsent(
  status: CookieConsentChoice,
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  if (!env) return;
  const value = status === 'yes' ? 'true' : 'false';
  purgeHostOnlyConsentCookie(env);
  writeSharedConsentCookie(env, value);
  env.dispatchEvent(COOKIE_CONSENT_CHANGE_EVENT, { status });
}

/** True once the visitor closed this site's banner without choosing. */
export function isConsentBannerDismissed(
  env: ConsentEnvironment | undefined = browserEnvironment(),
): boolean {
  if (!env) return false;
  try {
    return readCookieValues(env, CONSENT_BANNER_DISMISSED_KEY).includes('1');
  } catch {
    return false;
  }
}

/**
 * Close the banner without recording a choice. The consent cookie is not touched, so the
 * visitor stays undecided and the SDK stays in the lane sdkConsentFor gives undecided:
 * granted in the rest of the world, cookieless in the EU. Closing is never consent.
 *
 * Unlike the consent cookie, the marker is host-only and lasts 30 days (7 in Safari, which
 * caps cookies set from script). Each site's banner
 * is its own notice (docs discloses Scarf; cloud keeps identify running for signed-in
 * users), so closing one must not hide another the visitor has never seen.
 *
 * Does nothing unless the visitor is undecided and has not closed this site's banner yet,
 * read now rather than from the caller's state, so a close in a second tab is not counted
 * twice. Captures the close, so the close rate can be read next to cookie_consent, only
 * once the marker reads back: a browser that blocks cookies drops the write silently and
 * shows the banner again on every page, and each of those closes would otherwise count.
 * `source` says which banner was closed, 'banner' (first visit) or 'settings' (reopened
 * from a site's privacy control), and rides the event as `method`, as on cookie_consent.
 * Dispatches no change event: nothing but the banner reacts to it. Never throws into the
 * page.
 */
export function dismissConsentBanner(
  posthog: ConsentPostHog | undefined,
  source: CookieConsentSource,
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  if (!env || getCookieConsent(env) !== 'undecided' || isConsentBannerDismissed(env)) return;
  try {
    env.setCookie(
      `${CONSENT_BANNER_DISMISSED_KEY}=1; Max-Age=${CONSENT_BANNER_DISMISSED_MAX_AGE_SECONDS}${cookieAttributes(env)}`,
    );
  } catch {
    // Locked-down cookies: the banner comes back on the next page, which is harmless.
  }
  if (!isConsentBannerDismissed(env)) return;
  try {
    posthog?.capture?.(CONSENT_BANNER_DISMISSED_POSTHOG_EVENT, {
      scope: 'analytics',
      method: source,
    });
  } catch {
    // Analytics must never throw into the page.
  }
}

/** The consent slice of posthog.init options. Sites spread their own capture settings on top. */
export function consentInitOptions(hostname: string) {
  return {
    opt_out_capturing_by_default: true,
    cookieless_mode: 'on_reject',
    persistence: 'localStorage+cookie',
    cross_subdomain_cookie: consentCookieDomain(hostname) === 'expanso.io',
    disable_surveys: true,
    defaults: POSTHOG_DEFAULTS_DATE,
  } as const;
}

/**
 * Mirror our cookie into posthog-js's own per-origin consent flag BEFORE init.
 *
 * posthog-js stores consent per origin in localStorage. Without the positive half of this
 * sync, a visitor who accepted on another Expanso site arrives here with no flag, the SDK
 * treats them as rejected, starts cookieless and wipes the shared identity cookie the other
 * site wrote. The negative half is the stale-grant clear: a flag left by an earlier accept
 * must not outlive a later decline made anywhere.
 */
export function syncSdkConsentFlag(
  token: string,
  status: CookieConsentStatus,
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  const storage = env?.localStorage;
  if (!storage || !token) return;
  const key = `${SDK_CONSENT_KEY_PREFIX}${token}`;
  try {
    if (sdkConsentFor(status, readGeo(env)) === 'granted') storage.setItem(key, '1');
    else storage.removeItem(key);
  } catch {
    // Locked-down storage: nothing to sync, the SDK will fall back to opt-out by default.
  }
}

/** opt_out_capturing() leaves a ph_<token>_window_id key in sessionStorage; remove it. */
export function sweepPostHogSessionStorage(
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  const storage = env?.sessionStorage;
  if (!storage) return;
  try {
    const doomed: string[] = [];
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      if (key && key.startsWith(SDK_SESSION_STORAGE_PREFIX)) doomed.push(key);
    }
    for (const key of doomed) storage.removeItem(key);
  } catch {
    // Locked-down storage throws on access; there is nothing to sweep.
  }
}

/**
 * Tell the live SDK one decision. Pending is a reset, not a denial: under
 * opt_out_capturing_by_default a pending EU visitor is treated as rejected, so it runs
 * cookieless exactly as a denial does, without recording a choice nobody made.
 *
 * clear_opt_in_out_capturing alone only resets the flag. It does not reset identity, stop
 * the recorder or switch to cookieless, so a live opted-in SDK would keep tracking. For a
 * granted-to-pending change, opt out first to tear it down, then clear, so no denial stays
 * recorded. Never throws into the page.
 */
export function applySdkConsent(
  posthog: ConsentPostHog | undefined,
  decision: SdkConsent,
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  if (!posthog) return;
  try {
    if (decision === 'granted') {
      // captureEventName: null suppresses the SDK's own $opt_in event; cookie_consent is ours.
      posthog.opt_in_capturing?.({ captureEventName: null });
      return;
    }
    if (decision === 'denied') {
      posthog.opt_out_capturing?.();
    } else {
      if (posthog.has_opted_in_capturing?.()) posthog.opt_out_capturing?.();
      posthog.clear_opt_in_out_capturing?.();
    }
    sweepPostHogSessionStorage(env);
  } catch {
    // Consent enforcement must never throw into the page.
  }
}

/** Put the live SDK in the lane the recorded choice and the visitor's region call for. */
export function applyConsent(
  posthog: ConsentPostHog | undefined,
  status: CookieConsentStatus,
  env: ConsentEnvironment | undefined = browserEnvironment(),
): void {
  applySdkConsent(posthog, sdkConsentFor(status, readGeo(env)), env);
}

/** Documentary evidence of a choice, one property shape on every site. */
export function captureConsentChoice(
  posthog: ConsentPostHog | undefined,
  status: CookieConsentChoice,
  source: CookieConsentSource,
): void {
  try {
    posthog?.capture?.(COOKIE_CONSENT_POSTHOG_EVENT, {
      consent: status,
      scope: 'analytics',
      method: source,
    });
  } catch {
    // Analytics must never throw into the page.
  }
}

/**
 * Call onChange when the recorded choice differs from the last one seen: after a same-tab
 * write, when the tab regains focus or visibility, and on cookieStore changes where the
 * browser has them. Returns an unsubscribe function.
 */
export function watchConsent(
  onChange: (status: CookieConsentStatus) => void,
  target: ConsentWatchTarget | undefined = browserWatchTarget(),
  env: ConsentEnvironment | undefined = browserEnvironment(),
): () => void {
  if (!target) return () => {};
  let last = getCookieConsent(env);
  const check = () => {
    const next = getCookieConsent(env);
    if (next === last) return;
    last = next;
    onChange(next);
  };
  target.addEventListener('focus', check);
  target.addEventListener(COOKIE_CONSENT_CHANGE_EVENT, check);
  target.document?.addEventListener('visibilitychange', check);
  target.cookieStore?.addEventListener('change', check);
  return () => {
    target.removeEventListener('focus', check);
    target.removeEventListener(COOKIE_CONSENT_CHANGE_EVENT, check);
    target.document?.removeEventListener('visibilitychange', check);
    target.cookieStore?.removeEventListener('change', check);
  };
}
