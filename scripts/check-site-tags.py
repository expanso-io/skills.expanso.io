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

It also checks the PostHog SDK core. js/analytics.js loads the pinned
posthog-js from the site (SDK_CORE_PATH, for example /js/array-1.435.6.js),
which `npm run build` copies from node_modules. The check fails unless that
file is in the site and equals node_modules/posthog-js/dist/array.js, so a
posthog-js update that forgets the name in analytics.js fails the build.

Run it on the directory GitHub Pages publishes, after build-seo.py has written
the per-skill pages and `npm run build` has run:

    python scripts/check-site-tags.py docs
"""

import re
import sys
from pathlib import Path

RETIRED = [
    "GTM-MPSKFDMF",
    "googletagmanager.com/gtm.js",
    "googletagmanager.com/ns.html",
    "ph.expanso.io",
]
POSTHOG_HOST = "https://web.t.expanso.io"
SDK_CORE_PATH = re.compile(r"SDK_CORE_PATH = '(/js/[^'/]+\.js)'")
# The core the site must serve, from `npm ci`. Relative to this script, because
# CI runs the check on a copy of docs/ outside the checkout.
PINNED_CORE = Path(__file__).resolve().parent.parent / "node_modules" / "posthog-js" / "dist" / "array.js"


def problems(site: Path) -> list[str]:
    found = []
    pages = sorted(site.rglob("*.html")) + sorted(site.rglob("*.js"))
    if not pages:
        return [f"{site}: no HTML or JavaScript files to check"]
    # The SDK core is vendor code, checked byte for byte against the pinned posthog-js below,
    # so a string in it never fails the retired-tag scan.
    core = sdk_core_name(site)
    for page in pages:
        if core and page == site / core:
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        for marker in RETIRED:
            if marker in text:
                found.append(f"{page.relative_to(site)}: carries retired tag {marker}")
    loader = site / "js" / "analytics.js"
    if not loader.is_file():
        found.append("js/analytics.js: missing")
        return found
    text = loader.read_text(encoding="utf-8")
    if POSTHOG_HOST not in text:
        found.append(f"js/analytics.js: does not send to {POSTHOG_HOST}")
    found.extend(sdk_core_problems(site, text))
    return found


def sdk_core_name(site: Path) -> str | None:
    loader = site / "js" / "analytics.js"
    if not loader.is_file():
        return None
    match = SDK_CORE_PATH.search(loader.read_text(encoding="utf-8"))
    return match.group(1).lstrip("/") if match else None


def sdk_core_problems(site: Path, loader: str) -> list[str]:
    match = SDK_CORE_PATH.search(loader)
    if not match:
        return ["js/analytics.js: names no SDK core file (SDK_CORE_PATH = '/js/array-<version>.js')"]
    name = match.group(1).lstrip("/")
    core = site / name
    if not core.is_file():
        return [f"{name}: missing; js/analytics.js loads it "
                "(npm run build writes js/array-<the posthog-js version in package.json>.js)"]
    if not PINNED_CORE.is_file():
        return [f"{PINNED_CORE}: missing; run npm ci"]
    if core.read_bytes() != PINNED_CORE.read_bytes():
        return [f"{name}: differs from node_modules/posthog-js/dist/array.js; run npm run build"]
    return []


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
