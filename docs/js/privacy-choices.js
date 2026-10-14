/*
 * The analytics privacy banner for skills.expanso.io, and the footer's "Cookie settings"
 * control that reopens it. Modelled on expanso.io's banner (cookie-consent.js and
 * CookieConsent.astro there); the Escape rule and the region text rule come from
 * examples.expanso.io's CookieConsentCard.
 *
 * The choice is read and written only through the shared consent contract
 * (window.__expansoConsent, from js/consent-runtime.js). The banner's events go through
 * analytics.js's capture (window.__expansoSkillsCapture), so they get the skills context
 * fields, the host gate and the debug mode. Until analytics.js moves to the consent lanes, a
 * choice applies from the next page load.
 *
 * The file name has no "cookie-consent" in it: the EasyList Cookie and Fanboy Cookiemonster
 * lists block paths like /cookie-consent.js, and a blocked banner is a page where nobody can
 * accept or decline. The ids and classes avoid "cookie" for the same reason.
 */
(function () {
    'use strict';

    var EU_TEXT = 'We use analytics to understand how people browse these skills. Until you ' +
        'accept, we measure anonymously and keep no analytics cookies or data on your ' +
        'device. Accepting lets us recognise repeat visits.';
    var ROW_TEXT = 'We use analytics to understand how people browse these skills. It is ' +
        'running now; decline below to turn it off.';

    var consent = window.__expansoConsent;
    var banner = document.getElementById('privacy-choices');
    var text = document.getElementById('privacy-choices-text');
    var current = document.getElementById('privacy-choices-current');
    var accept = document.getElementById('privacy-accept');
    var decline = document.getElementById('privacy-decline');
    var closeButton = document.getElementById('privacy-close');
    var settings = document.getElementById('privacy-settings');
    var skillWindow = document.getElementById('modal-overlay');
    if (!banner) return;

    // examples.expanso.io's labels for the choice on record.
    var CHOICE_LABEL = { yes: 'Accepted', no: 'Declined', undecided: 'Undecided' };

    // How the visitor reached the banner: 'banner' (shown on its own) or 'settings' (reopened
    // from the footer). It rides cookie_consent and cookie_banner_dismissed as `method`.
    var choiceSource = 'banner';
    // The control that reopened the banner, so that closing it can hand focus back.
    var opener = null;

    // The contract calls client.capture. analytics.js defines the hook only on
    // skills.expanso.io (or in its localhost debug mode); anywhere else the events are dropped.
    var client = {
        capture: function (event, properties) {
            var send = window.__expansoSkillsCapture;
            if (typeof send === 'function') send(event, properties);
        }
    };

    function readChoice() {
        return consent ? consent.getCookieConsent() : 'undecided';
    }

    function isDismissed() {
        return !!consent && consent.isConsentBannerDismissed();
    }

    // Set on every show: the choice or the region can change while the page is open. A
    // rest-of-world visitor who declined runs without cookies, so "running now" would be false.
    function setText() {
        if (!text) return;
        var row = !!consent && consent.readGeo() === 'row';
        text.textContent = row && readChoice() !== 'no' ? ROW_TEXT : EU_TEXT;
    }

    // The reopened banner also shows the choice on record (examples' "Your current choice"),
    // so a visitor who already chose sees it before they change it.
    function setCurrentChoice() {
        if (!current) return;
        current.textContent = 'Your current choice: ' +
            (CHOICE_LABEL[readChoice()] || CHOICE_LABEL.undecided);
        current.hidden = choiceSource !== 'settings';
    }

    function showBanner() {
        setText();
        setCurrentChoice();
        banner.hidden = false;
    }

    // Hiding the banner drops the focus it holds, so hand focus back to whatever reopened it.
    // The banner that shows on its own never takes focus and has no opener, so focus falls to
    // <body> there, as on expanso.io. Safari and Firefox on macOS do not focus a clicked
    // button, so a click in the banner leaves focus on <body>; byVisitor counts that as the
    // banner's too. A change made in another tab or on another site never moves focus.
    function hideBanner(byVisitor) {
        if (banner.hidden) return;
        var active = document.activeElement;
        var hadFocus = banner.contains(active) ||
            (!!byVisitor && (!active || active === document.body));
        banner.hidden = true;
        if (hadFocus && opener && typeof opener.focus === 'function') opener.focus();
        opener = null;
    }

    // Without the contract there is nothing to record the choice in: the banner stays up, so
    // the visitor can see that the click did not register.
    function persistChoice(granted) {
        if (!consent) return;
        var status = granted ? 'yes' : 'no';
        var source = choiceSource;
        hideBanner(true);
        consent.setCookieConsent(status);
        consent.captureConsentChoice(client, status, source);
    }

    // Records no choice. For an undecided visitor the contract writes this site's host-only
    // dismissed marker (30 days) and reports cookie_banner_dismissed; otherwise it does nothing.
    function closeBanner() {
        if (consent) consent.dismissConsentBanner(client, choiceSource);
        hideBanner(true);
    }

    // The footer control: the reopened banner takes focus, on Accept.
    function showChoices() {
        choiceSource = 'settings';
        var active = document.activeElement;
        opener = active && active !== document.body ? active : settings;
        showBanner();
        if (accept) accept.focus();
    }

    // Show the banner to an undecided visitor who has not closed it here; hide it otherwise.
    // Runs at load and whenever the recorded choice changes (this tab, another tab, another
    // Expanso site). A banner that comes back on its own is the first-visit banner again.
    function syncBannerToChoice() {
        if (readChoice() !== 'undecided' || isDismissed()) return hideBanner(false);
        choiceSource = 'banner';
        showBanner();
    }

    // Only the reopened banner closes on Escape (examples' rule): a visitor who opened
    // "Cookie settings" just to look can leave without a choice. The banner that shows on its
    // own never takes focus, so an Escape meant for something else must not close it. Escape
    // records nothing; for an undecided visitor the banner stays, as the first-visit banner.
    function closeOnEscape(event) {
        if (event.key !== 'Escape' || banner.hidden || choiceSource !== 'settings') return;
        // A skill open above the banner takes this Escape: app.js closes the skill window, and
        // the banner stays. This listener runs first (privacy-choices.js loads before app.js),
        // so the skill window is still open here.
        if (skillWindow && skillWindow.classList.contains('active')) return;
        if (readChoice() !== 'undecided' || isDismissed()) return hideBanner(true);
        choiceSource = 'banner';
        setCurrentChoice();
        if (opener && typeof opener.focus === 'function') opener.focus();
        opener = null;
    }

    syncBannerToChoice();
    if (consent) consent.watchConsent(syncBannerToChoice);
    if (accept) accept.addEventListener('click', function () { persistChoice(true); });
    if (decline) decline.addEventListener('click', function () { persistChoice(false); });
    if (closeButton) closeButton.addEventListener('click', closeBanner);
    if (settings) settings.addEventListener('click', showChoices);
    document.addEventListener('keydown', closeOnEscape);
})();
