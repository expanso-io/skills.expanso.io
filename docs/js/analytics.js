/*
 * PostHog analytics for skills.expanso.io.
 *
 * Consent is owned by the shared contract (src/cookieConsentUtils.ts, a copy of
 * expanso-cloud's canonical file), which js/consent-runtime.js installs at
 * window.__expansoConsent just before this script. The lanes are the main sites'
 * (expanso.io's posthog-loader.js, docs.expanso.io's Providers.tsx): after an accept, or
 * for an undecided visitor outside the EU, posthog-js keeps its identity in the shared
 * .expanso.io cookie; an undecided EU visitor (or one without the expanso-geo cookie) and a
 * visitor who declined are counted cookieless, with no identity stored on the device (after a
 * decline posthog-js keeps only its opt-out flag). A later choice (in this tab, in another
 * tab, on another Expanso site) moves the SDK to its lane.
 * PostHog ignores Do Not Track, as on the main sites: the consent lanes decide.
 *
 * Everything else is this site's own: the token, the proxy (events go through
 * web.t.expanso.io), the events below, the context fields on each of them, and URLs reduced
 * to origin + path. The capture settings are docs.expanso.io's: autocapture, page leave,
 * heatmaps, web vitals and session replay (when the PostHog project turns it on). Replay masks
 * every input, as on cloud.expanso.io, so the search text is never recorded, and its URLs are
 * origin + path too. The events the
 * SDK sends by itself get the same context fields as the events below.
 *
 * This only sees people using a browser. It does NOT show whether pages are
 * indexed, whether agents fetch llms.txt or pipeline files directly,
 * whether install.sh runs, or whether any skill is deployed or executed.
 * Those need request logs or Cloud-side data, which this script does not add.
 *
 * Only runs on skills.expanso.io. On localhost, `?analytics_debug=1`
 * records events in window.__expansoAnalyticsEvents instead of sending
 * them, so behaviour can be checked without touching production data. The
 * SDK does not load then, so those events have no identity_mode.
 */
(function () {
    'use strict';

    var POSTHOG_KEY = 'phc_f467hBf7ZUEc5HDT3xFcbhZ4tL7wUYJH0COw9Y2bzSK';
    var API_HOST = 'https://web.t.expanso.io';
    // The SDK core: posthog-js's own dist/array.js from the version package.json pins, which
    // `npm run build` copies into the site (scripts/copy-sdk-core.mjs). The proxy's
    // /static/array.js was always the newest release, so a PostHog release reached visitors
    // with no test run. Events, remote config and the extensions the core lazy-loads still go
    // through API_HOST. Change the version here together with package.json:
    // scripts/check-site-tags.py fails while this file is not the pinned core.
    var SDK_CORE_PATH = '/js/array-1.435.6.js';
    var SITE_HOST = 'skills.expanso.io';
    var SCHEMA_VERSION = '2026-09-18';
    // The contract's status, as the consent_state value skills' events have always carried.
    var CONSENT_STATE = { yes: 'granted', no: 'denied', undecided: 'unset' };

    var host = window.location.hostname;
    var params = new URLSearchParams(window.location.search);
    var debug = (host === 'localhost' || host === '127.0.0.1') &&
        params.get('analytics_debug') === '1';
    if (host !== SITE_HOST && !debug) return;

    var consent = window.__expansoConsent;
    if (!consent) {
        // js/consent-runtime.js did not run. Never guess a lane: no analytics on this page.
        console.warn('[posthog] consent runtime missing; analytics disabled for this page');
        return;
    }

    function cleanUrl(value) {
        try {
            var url = new URL(value, window.location.href);
            return /^https?:$/.test(url.protocol) ? url.origin + url.pathname : '';
        } catch (e) { return ''; }
    }

    function trafficClass() {
        var ua = navigator.userAgent;
        var automation = /bot|crawler|spider|headless|puppeteer|playwright|selenium|webdriver/i;
        if (automation.test(ua) || navigator.webdriver) {
            return 'known_automation';
        }
        return 'browser_unclassified';
    }

    // A skill link lands on a per-skill page (scripts/build-seo.py) or on 404.html. Both send
    // the visitor here with the query, and leave the skill's path and the page that linked to
    // it in sessionStorage. app.js puts the path back once the catalog has loaded.
    // The keys count only when that redirect page is this page's referrer: keys left by a
    // redirect whose page never finished (app.js did not run) belong to no page load.
    function fromRedirect(path) {
        try {
            var from = new URL(document.referrer);
            return from.origin === window.location.origin && from.pathname === path;
        } catch (e) { return false; }
    }
    var landing = null;
    var landingReferrer = '';
    try {
        landing = sessionStorage.getItem('spa-redirect');
        landingReferrer = sessionStorage.getItem('spa-referrer') || '';
        // This script is the referrer's only reader.
        sessionStorage.removeItem('spa-referrer');
        if (landing && !(/^\/skill\/[^/]+\/?$/.test(landing) && fromRedirect(landing))) {
            sessionStorage.removeItem('spa-redirect');
            landing = null;
        }
    } catch (e) {
        landing = null;
    }
    landing = landing || null;

    // The visit's source, on the page-load $pageview and on the one a lane change sends: with
    // save_referrer off, nothing else gives the new identity's session its source. After a
    // skill link, document.referrer is the per-skill page, so the source is the one it had.
    var referrer = landing ? landingReferrer : document.referrer;
    var referrerHost = '';
    try {
        if (referrer) referrerHost = new URL(referrer).hostname;
    } catch (e) {}

    var campaign = {};
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(function (k) {
        if (params.has(k)) campaign[k] = params.get(k).slice(0, 200);
    });

    // identity_mode is not here: before_send sets it from the lane the SDK captured the event
    // in. consent_state is read from the contract for each event, because the choice can
    // change while the page is open.
    function context() {
        var ctx = {
            site_id: 'expanso_skills',
            site_host: window.location.hostname,
            analytics_schema_version: SCHEMA_VERSION,
            consent_state: CONSENT_STATE[consent.getCookieConsent()],
            traffic_class: trafficClass(),
            is_synthetic: params.get('analytics_test') === '1',
            $current_url: cleanUrl(window.location.href),
            $pathname: window.location.pathname
        };
        for (var k in campaign) ctx[k] = campaign[k];
        return ctx;
    }

    // Events captured before the SDK loads are queued, then flushed.
    var queue = [];
    var sdk = null;
    // `address` replaces the page address in the context fields: only the page-load $pageview
    // after a skill link passes one.
    function capture(event, props, address) {
        var payload = Object.assign({}, props || {}, context(), address || {});
        if (debug) {
            (window.__expansoAnalyticsEvents = window.__expansoAnalyticsEvents || [])
                .push({ event: event, properties: payload });
            return;
        }
        if (sdk) sdk.capture(event, payload); else queue.push([event, payload]);
    }
    // The banner (js/privacy-choices.js) reports cookie_consent and cookie_banner_dismissed
    // through this, so they get the context fields above and go where every event goes.
    window.__expansoSkillsCapture = capture;

    // An http(s) URL reduced to origin + path; any other value stays as it is.
    function cleanIfUrl(value) {
        return typeof value === 'string' && /^https?:\/\//i.test(value) ? cleanUrl(value) : value;
    }

    // Every replay URL (meta href, $url_changed, network request names) passes through the
    // recorder's maskCapturedNetworkRequestFn in posthog-js 1.435.6. It must always return req:
    // a missing return makes the recorder drop the meta event or the network entry.
    function cleanReplayUrl(req) {
        if (req && typeof req.name === 'string') req.name = cleanIfUrl(req.name);
        if (req && typeof req.url === 'string') req.url = cleanIfUrl(req.url);
        return req;
    }

    function isRecord(value) {
        return typeof value === 'object' && value !== null && !Array.isArray(value);
    }

    function beforeSend(ev) {
        if (!ev) return ev;
        // Never send full URLs with query strings or fragments. The SDK
        // adds its own URL properties (e.g. $session_entry_url), so clean
        // every *url / *referrer value that is an http(s) URL; sentinels
        // such as '$direct' are left alone.
        [ev.properties, ev.$set, ev.$set_once].forEach(function (props) {
            if (!props) return;
            Object.keys(props).forEach(function (k) {
                if (/(url|referrer)$/i.test(k)) props[k] = cleanIfUrl(props[k]);
            });
        });
        if (!ev.properties) return ev;
        var props = ev.properties;
        // Autocapture names each clicked link's href in $elements_chain (and $elements).
        if (typeof props.$elements_chain === 'string') {
            props.$elements_chain = props.$elements_chain.replace(/href="([^"]*)"/g,
                function (match, href) { return 'href="' + cleanIfUrl(href) + '"'; });
        }
        if (Array.isArray(props.$elements)) {
            props.$elements.forEach(function (el) {
                if (isRecord(el) && 'attr__href' in el) el.attr__href = cleanIfUrl(el.attr__href);
            });
        }
        // Heatmap batches key their points by page URL; keys that clean to the same URL merge.
        // (The URL cleaning here and below is examples.expanso.io's.)
        if (ev.event === '$$heatmap' && isRecord(props.$heatmap_data)) {
            var heatmap = {};
            Object.keys(props.$heatmap_data).forEach(function (url) {
                var points = props.$heatmap_data[url];
                var key = cleanIfUrl(url);
                heatmap[key] = (heatmap[key] || []).concat(Array.isArray(points) ? points : []);
            });
            props.$heatmap_data = heatmap;
        }
        // Web vitals copy the page URL into each metric and its attribution.
        Object.keys(props).forEach(function (key) {
            var metric = props[key];
            if (!/^\$web_vitals_\w+_event$/.test(key) || !isRecord(metric)) return;
            var cleaned = Object.assign({}, metric);
            ['$current_url', 'navigationURL'].forEach(function (field) {
                if (field in cleaned) cleaned[field] = cleanIfUrl(cleaned[field]);
            });
            if (isRecord(metric.attribution) && 'url' in metric.attribution) {
                cleaned.attribution = Object.assign({}, metric.attribution, {
                    url: cleanIfUrl(metric.attribution.url),
                });
            }
            props[key] = cleaned;
        });
        // High-volume replay and heatmap batches go as the SDK built them.
        if (ev.event === '$snapshot' || ev.event === '$$heatmap') return ev;
        // The events the SDK sends by itself ($autocapture, $pageleave, $web_vitals and the
        // others) get the context fields of skills' own events, as on docs and examples. A field
        // that skills' capture call set keeps its value.
        var ctx = context();
        Object.keys(ctx).forEach(function (k) {
            if (!(k in props)) props[k] = ctx[k];
        });
        // The SDK marks every cookieless event with $cookieless_mode before before_send, so
        // identity_mode reports the lane the event was captured in (examples.expanso.io's rule).
        props.identity_mode = props.$cookieless_mode ? 'ephemeral' : 'persistent';
        return ev;
    }

    // Whether the SDK runs in the persistent lane (opted in), not the cookieless one. Never
    // throws, because the consent change still has to reach the SDK.
    function persistentLane(ph) {
        try {
            return ph.has_opted_in_capturing();
        } catch (e) {
            return false;
        }
    }

    function startSdk() {
        var ph = window.posthog;
        if (!ph || typeof ph.init !== 'function') return;
        var status = consent.getCookieConsent();
        // Before init: mirror the shared cookie into the SDK's per-origin consent flag, or a
        // visitor who accepted on another Expanso site starts cookieless here and loses the
        // shared identity. A flag left by an earlier accept does not outlive a decline.
        consent.syncSdkConsentFlag(POSTHOG_KEY, status);
        // The lane (opt-out by default, cookieless on reject, persistence, the .expanso.io
        // identity cookie on this host, the pinned defaults date) is the contract's. The rest
        // is skills' own. Nothing below may change a key of the contract's slice.
        var options = consent.consentInitOptions(window.location.hostname);
        options.api_host = API_HOST;
        // docs.expanso.io's capture settings (src/analytics/client.mjs there). The toolbar and
        // heatmaps open from the PostHog app, not from the proxy.
        options.ui_host = 'https://us.posthog.com';
        // One $pageview per page load, sent below, and one more per lane change (watchConsent
        // below); app.js's pushState calls add none.
        options.capture_pageview = false;
        options.capture_pageleave = true;
        options.autocapture = true;
        // This starts the recorder only when the PostHog project turns replay on. Typed values
        // are masked, as on cloud.expanso.io: the search box text is never recorded. The two
        // filter checkboxes are inputs too, but rrweb does not mask checkbox state.
        // The custom URL mask replaces posthog-js's body scrubber, so skills records no
        // network bodies or headers, and no console output (a logged message can hold the full
        // page URL). The client values win over the project's remote config.
        options.session_recording = {
            recordCrossOriginIframes: false,
            maskAllInputs: true,
            recordBody: false,
            recordHeaders: false,
            maskCapturedNetworkRequestFn: cleanReplayUrl,
        };
        options.enable_recording_console_log = false;
        options.capture_heatmaps = true;
        // Web vitals.
        options.capture_performance = true;
        options.advanced_disable_feature_flags = true;
        options.save_campaign_params = false;
        options.save_referrer = false;
        options.before_send = beforeSend;
        try {
            ph.init(POSTHOG_KEY, options);
        } catch (e) {
            // posthog-js can throw in locked-down storage contexts. No analytics on this page.
            console.warn('[posthog] init failed; analytics disabled for this page', e);
            return;
        }
        consent.applyConsent(ph, status);
        // A later choice: in this tab, in another tab (focus, visibility), on another Expanso
        // site (the same shared cookie).
        consent.watchConsent(function (next) {
            // A move between the cookieless and the persistent lane makes posthog-js start a
            // new identity and session; give the new session a page view of its own, with the
            // visit's source. The landing skill stays on the page-load one: one landing.
            var wasPersistent = persistentLane(ph);
            consent.applyConsent(ph, next);
            if (persistentLane(ph) !== wasPersistent) {
                capture('$pageview', { referrer_host: referrerHost });
            }
        });
        sdk = ph;
        queue.splice(0).forEach(function (item) { sdk.capture(item[0], item[1]); });
    }

    if (!debug) {
        var script = document.createElement('script');
        script.async = true;
        script.src = SDK_CORE_PATH;
        script.onload = startSdk;
        document.head.appendChild(script);
    }

    // Page view. After a skill link it is the skill page's: its address, not / (app.js puts
    // the address back only later), and its path as the landing skill too.
    capture('$pageview', {
        landing_skill_path: landing,
        referrer_host: referrerHost
    }, landing ? { $current_url: cleanUrl(landing), $pathname: landing } : null);

    var overlay = document.getElementById('modal-overlay');
    function modalOpen() {
        return !!(overlay && overlay.classList.contains('active'));
    }
    function openSkill() {
        if (!modalOpen()) return null;
        var title = document.querySelector('#skill-modal .modal-title');
        return title ? title.textContent.trim() : null;
    }
    function activeSpecLabel() {
        if (!modalOpen()) return null;
        var tab = document.querySelector('#skill-modal .pipeline-sub-tab.active');
        return tab ? tab.textContent.trim() : null;
    }

    document.addEventListener('click', function (e) {
        var target = e.target instanceof Element ? e.target : null;
        if (!target) return;

        var tab = target.closest('.tab[data-category]');
        if (tab) { capture('skills_category_tab', { category: tab.dataset.category }); return; }

        var sub = target.closest('.pipeline-sub-tab');
        if (sub) {
            capture('skills_spec_tab', { skill: openSkill(), spec: sub.textContent.trim() });
            return;
        }

        var full = target.closest('.copy-pipeline-btn');
        if (full) {
            capture('skills_copy', {
                surface: 'pipeline_full', skill: openSkill(), spec: activeSpecLabel()
            });
            return;
        }

        var copy = target.closest('.copy-btn');
        if (copy) {
            var surface = copy.closest('.install-box') ? 'install_command'
                : copy.classList.contains('code-copy-btn') ? 'code_block' : 'other';
            capture('skills_copy', {
                surface: surface, skill: surface === 'install_command' ? null : openSkill()
            });
            return;
        }

        var link = target.closest('a[href]');
        if (link) {
            try {
                var url = new URL(link.href);
                if (/^https?:$/.test(url.protocol) && url.hostname !== window.location.hostname) {
                    capture('skills_outbound_click', {
                        destination_host: url.hostname,
                        destination_path: url.pathname,
                        skill: openSkill()
                    });
                } else if (/\.(ya?ml|md|json|txt|sh)$/.test(url.pathname)) {
                    capture('skills_file_link', { file_path: url.pathname });
                }
            } catch (err) {}
        }
    });

    // Skill detail opens, from a card click or a deep link.
    if (overlay && window.MutationObserver) {
        var wasOpen = false;
        var deepLinkUsed = false;
        new MutationObserver(function () {
            var open = overlay.classList.contains('active');
            if (open && !wasOpen) {
                // The title renders after the skill files load.
                var tries = 0;
                (function waitForTitle() {
                    var skill = openSkill();
                    if (skill || tries++ > 40) {
                        var badge = document.querySelector('#skill-modal .skill-badges .badge');
                        var deep = !!(landing && skill &&
                            landing.replace(/\/$/, '').split('/').pop() === skill);
                        capture('skill_modal_open', {
                            skill: skill,
                            category: badge ? badge.textContent.trim() : null,
                            via: deep && !deepLinkUsed ? 'deep_link' : 'card'
                        });
                        if (deep) deepLinkUsed = true;
                    } else {
                        setTimeout(waitForTitle, 100);
                    }
                })();
            }
            wasOpen = open;
        }).observe(overlay, { attributes: true, attributeFilter: ['class'] });
    }

    // Search: count and length only, never the search text.
    var search = document.getElementById('search');
    var timer = null;
    if (search) {
        search.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(function () {
                if (!search.value.trim()) return;
                var shown = Array.prototype.filter.call(document.querySelectorAll('.skill-card'),
                    function (c) { return c.offsetParent !== null; }).length;
                capture('skills_search', {
                    query_length: search.value.trim().length, result_count: shown
                });
            }, 800);
        });
    }
})();
