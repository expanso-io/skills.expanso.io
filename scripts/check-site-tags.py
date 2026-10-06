#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""
Check the built site for retired third-party tags.

The shared Google Tag Manager container (GTM-MPSKFDMF) fired GA4, Google Ads,
HubSpot, Clarity and other vendors on every page before any consent choice.
expanso.io and docs.expanso.io removed it, and so does this site. PostHog goes
through the managed proxy web.t.expanso.io; ph.expanso.io is being retired.

Run it on the directory GitHub Pages publishes, after build-seo.py has written
the per-skill pages:

    python scripts/check-site-tags.py docs
"""

import sys
from pathlib import Path

RETIRED = [
    "GTM-MPSKFDMF",
    "googletagmanager.com/gtm.js",
    "googletagmanager.com/ns.html",
    "ph.expanso.io",
]
POSTHOG_HOST = "https://web.t.expanso.io"


def problems(site: Path) -> list[str]:
    found = []
    pages = sorted(site.rglob("*.html")) + sorted(site.rglob("*.js"))
    if not pages:
        return [f"{site}: no HTML or JavaScript files to check"]
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        for marker in RETIRED:
            if marker in text:
                found.append(f"{page.relative_to(site)}: carries retired tag {marker}")
    loader = site / "js" / "analytics.js"
    if not loader.is_file():
        found.append("js/analytics.js: missing")
    elif POSTHOG_HOST not in loader.read_text(encoding="utf-8"):
        found.append(f"js/analytics.js: does not send to {POSTHOG_HOST}")
    return found


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "docs")
    found = problems(site)
    for line in found:
        print(line, file=sys.stderr)
    if found:
        print(f"Site tag check failed: {len(found)} problem(s)", file=sys.stderr)
        return 1
    print(f"Site tag check passed for {site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
