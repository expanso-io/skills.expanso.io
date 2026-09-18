/*
 * PostHog analytics for skills.expanso.io.
 *
 * Same project, proxy and privacy defaults as docs.expanso.io
 * (src/analytics/client.mjs there): events go through ph.expanso.io, no
 * autocapture, no session recording, no person profiles, Do Not Track is
 * respected, and URLs are reduced to origin + path. Nothing is stored in
 * cookies or localStorage unless the visitor accepted the shared
 * `expanso-cookie-consent` cookie on an expanso.io site; otherwise the
 * identity lives in memory for this page view only.
 *
 * This only sees people using a browser. It does NOT show whether pages are
 * indexed, whether agents fetch llms.txt or pipeline files directly,
 * whether install.sh runs, or whether any skill is deployed or executed.
 * Those need request logs or Cloud-side data, which this script does not add.
 *
 * Only runs on skills.expanso.io. On localhost, `?analytics_debug=1`
 * records events in window.__expansoAnalyticsEvents instead of sending
 * them, so behaviour can be checked without touching production data.
 */
(function () {
    'use strict';

    var POSTHOG_KEY = 'phc_f467hBf7ZUEc5HDT3xFcbhZ4tL7wUYJH0COw9Y2bzSK';
    var API_HOST = 'https://ph.expanso.io';
    var SITE_HOST = 'skills.expanso.io';
    var CONSENT_COOKIE = 'expanso-cookie-consent';
    var SCHEMA_VERSION = '2026-09-18';

    var host = window.location.hostname;
    var params = new URLSearchParams(window.location.search);
    var debug = (host === 'localhost' || host === '127.0.0.1') &&
        params.get('analytics_debug') === '1';
    if (host !== SITE_HOST && !debug) return;

    function dntEnabled() {
        return [navigator.doNotTrack, window.doNotTrack, navigator.msDoNotTrack]
            .some(function (v) { return ['1', 'yes'].indexOf(String(v).toLowerCase()) !== -1; });
    }
    if (dntEnabled()) return;

    function consent() {
        var part = document.cookie.split(';').map(function (p) { return p.trim(); })
            .filter(function (p) { return p.indexOf(CONSENT_COOKIE + '=') === 0; })[0];
        var value = part ? part.slice(CONSENT_COOKIE.length + 1) : '';
        return value === 'true' ? 'granted' : value === 'false' ? 'denied' : 'unset';
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

    var state = consent();
    var campaign = {};
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(function (k) {
        if (params.has(k)) campaign[k] = params.get(k).slice(0, 200);
    });

    function context() {
        var ctx = {
            site_id: 'expanso_skills',
            site_host: window.location.hostname,
            analytics_schema_version: SCHEMA_VERSION,
            consent_state: state,
            identity_mode: state === 'granted' ? 'persistent' : 'ephemeral',
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
    function capture(event, props) {
        var payload = Object.assign({}, props || {}, context());
        if (debug) {
            (window.__expansoAnalyticsEvents = window.__expansoAnalyticsEvents || [])
                .push({ event: event, properties: payload });
            return;
        }
        if (sdk) sdk.capture(event, payload); else queue.push([event, payload]);
    }

    if (!debug) {
        var script = document.createElement('script');
        script.async = true;
        script.src = API_HOST + '/static/array.js';
        script.onload = function () {
            if (!window.posthog || typeof window.posthog.init !== 'function') return;
            window.posthog.init(POSTHOG_KEY, {
                api_host: API_HOST,
                persistence: state === 'granted' ? 'localStorage+cookie' : 'memory',
                capture_pageview: false,
                capture_pageleave: false,
                autocapture: false,
                capture_dead_clicks: false,
                capture_heatmaps: false,
                capture_performance: false,
                disable_session_recording: true,
                disable_surveys: true,
                advanced_disable_feature_flags: true,
                person_profiles: 'never',
                respect_dnt: true,
                save_campaign_params: false,
                save_referrer: false,
                before_send: function (ev) {
                    // Never send full URLs with query strings or fragments. The SDK
                    // adds its own URL properties (e.g. $session_entry_url), so clean
                    // every *url / *referrer value that is an http(s) URL; sentinels
                    // such as '$direct' are left alone.
                    [ev.properties, ev.$set, ev.$set_once].forEach(function (props) {
                        if (!props) return;
                        Object.keys(props).forEach(function (k) {
                            var v = props[k];
                            if (/(url|referrer)$/i.test(k) && typeof v === 'string' &&
                                /^https?:\/\//i.test(v)) {
                                props[k] = cleanUrl(v);
                            }
                        });
                    });
                    return ev;
                }
            });
            sdk = window.posthog;
            queue.splice(0).forEach(function (item) { sdk.capture(item[0], item[1]); });
        };
        document.head.appendChild(script);
    }

    // Page view. A per-skill page (/skill/<name>) redirects here and leaves
    // its path in sessionStorage; record it as the landing skill.
    var landing = null;
    try { landing = sessionStorage.getItem('spa-redirect'); } catch (e) {}
    capture('$pageview', {
        landing_skill_path: landing || null,
        referrer_host: document.referrer ? (function () {
            try { return new URL(document.referrer).hostname; } catch (e) { return ''; }
        })() : ''
    });

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
