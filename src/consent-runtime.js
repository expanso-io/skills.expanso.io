// The one place the shared consent contract ships on skills.expanso.io. `npm run build`
// bundles this file with esbuild into docs/js/consent-runtime.js, one classic script (an
// IIFE) that docs/index.html loads before the banner and analytics scripts. Those scripts stay
// plain files and reach the contract through window.__expansoConsent.
//
// Modelled on expanso.io's astro/assets/analytics/consent-runtime.js. The ten members below
// are exactly what the banner (js/privacy-choices.js) and js/analytics.js call. Named imports,
// not `import * as`, so esbuild leaves out the exports nothing here calls.
//
// cookieConsentUtils.ts is a byte-identical copy of expanso-cloud's canonical file. Never
// edit it here; copy it again from expanso-cloud (see AGENTS.md, "Analytics").
import {
  applyConsent,
  captureConsentChoice,
  consentInitOptions,
  dismissConsentBanner,
  getCookieConsent,
  isConsentBannerDismissed,
  readGeo,
  setCookieConsent,
  syncSdkConsentFlag,
  watchConsent,
} from './cookieConsentUtils.ts';

(function () {
  if (window.__expansoConsent) return;
  window.__expansoConsent = {
    applyConsent: applyConsent,
    captureConsentChoice: captureConsentChoice,
    consentInitOptions: consentInitOptions,
    dismissConsentBanner: dismissConsentBanner,
    getCookieConsent: getCookieConsent,
    isConsentBannerDismissed: isConsentBannerDismissed,
    readGeo: readGeo,
    setCookieConsent: setCookieConsent,
    syncSdkConsentFlag: syncSdkConsentFlag,
    watchConsent: watchConsent,
  };
})();
