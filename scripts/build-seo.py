#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Generate SEO assets from the skills catalog:
  - sitemap.xml
  - Per-skill HTML pages with meta tags, canonical URLs, and Open Graph tags

Usage:
    uv run -s scripts/build-seo.py
    uv run -s scripts/build-seo.py --catalog catalog.json --output docs
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape
from pathlib import Path

SITE_URL = "https://skills.expanso.io"


CATEGORY_DISPLAY = {
    "ai": "AI",
    "security": "Security",
    "transforms": "Transforms",
    "utilities": "Utilities",
    "workflows": "Workflows",
    "connectors": "Connectors",
}


def build_meta_title(skill_name: str, skill: dict) -> str:
    """Build an SEO-optimized meta title from the skill name and category."""
    pretty_name = skill_name.replace("-", " ").title()
    category = CATEGORY_DISPLAY.get(skill["category"], skill["category"].title())
    return f"{pretty_name} – {category} Skill | Expanso Skills"


def build_meta_description(skill: dict) -> str:
    """Build an SEO-optimized meta description from the skill description."""
    desc = skill.get("description", "")
    if not desc:
        return "Pre-built data processing pipeline for AI agents. Works offline, keeps credentials local, and runs anywhere."
    # Ensure description ends with a period before appending suffix
    if desc and not desc.endswith((".","!","?")):
        desc = desc + "."
    # Truncate to ~155 chars for SERP display, append CTA if room
    suffix = " Install and deploy with Expanso."
    if len(desc) + len(suffix) <= 160:
        return desc + suffix
    if len(desc) > 160:
        return desc[:157] + "..."
    return desc


def generate_sitemap(catalog: dict, output_dir: Path) -> None:
    """Generate sitemap.xml from the catalog."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urlset = ET.Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    # Homepage
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = SITE_URL + "/"
    ET.SubElement(url, "lastmod").text = now
    ET.SubElement(url, "changefreq").text = "weekly"
    ET.SubElement(url, "priority").text = "1.0"

    # Skill pages
    for skill_name in sorted(catalog.get("skills", {})):
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"{SITE_URL}/skill/{skill_name}/"
        ET.SubElement(url, "lastmod").text = now
        ET.SubElement(url, "changefreq").text = "monthly"
        ET.SubElement(url, "priority").text = "0.8"

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    sitemap_path = output_dir / "sitemap.xml"
    tree.write(sitemap_path, xml_declaration=True, encoding="UTF-8")
    print(f"Wrote sitemap.xml with {len(catalog.get('skills', {})) + 1} URLs")


def generate_skill_pages(catalog: dict, output_dir: Path) -> None:
    """Generate per-skill index.html pages with SEO meta tags."""
    skills = catalog.get("skills", {})
    count = 0

    for skill_name, skill in skills.items():
        title = escape(build_meta_title(skill_name, skill))
        description = escape(build_meta_description(skill))
        canonical = f"{SITE_URL}/skill/{skill_name}/"
        category = escape(CATEGORY_DISPLAY.get(skill.get("category", ""), skill.get("category", "").title()))
        pretty_name = escape(skill_name.replace("-", " ").title())

        # Collect structured data for JSON-LD
        backends = skill.get("backends", [])
        tags = skill.get("tags", [])
        keywords = ", ".join([skill_name, category.lower()] + tags[:5])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google Tag Manager -->
    <script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
    new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    }})(window,document,'script','dataLayer','GTM-MPSKFDMF');</script>
    <!-- End Google Tag Manager -->
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{escape(keywords)}">
    <link rel="canonical" href="{canonical}">

    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:site_name" content="Expanso Skills Marketplace">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">

    <!-- JSON-LD Structured Data -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "{pretty_name}",
        "description": "{escape(skill.get('description', ''))}",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Any",
        "url": "{canonical}",
        "author": {{
            "@type": "Organization",
            "name": "Expanso",
            "url": "https://expanso.io"
        }},
        "offers": {{
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
        }}
    }}
    </script>

    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>E</text></svg>">
    <script>
        // SPA redirect: preserve path for the main app
        sessionStorage.setItem('spa-redirect', window.location.pathname);
        window.location.replace('/');
    </script>
</head>
<body>
    <!-- Google Tag Manager (noscript) -->
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-MPSKFDMF"
    height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
    <!-- End Google Tag Manager (noscript) -->
    <h1>{pretty_name}</h1>
    <p>{escape(skill.get('description', ''))}</p>
    <p>Category: {category}</p>
    <p><a href="/">Browse all skills</a> | <a href="{canonical}">View {pretty_name}</a></p>
</body>
</html>"""

        # Write to docs/skill/<skill-name>/index.html
        skill_dir = output_dir / "skill" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "index.html").write_text(html, encoding="utf-8")
        count += 1

    print(f"Generated {count} skill SEO pages")


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate SEO assets for skills.expanso.io")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=repo_root / "catalog.json",
        help="Path to catalog.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "docs",
        help="Path to output directory (docs/)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.catalog.exists():
        print(f"Error: catalog not found at {args.catalog}", file=sys.stderr)
        sys.exit(1)

    with open(args.catalog) as f:
        catalog = json.load(f)

    print(f"Generating SEO assets for {catalog.get('total_skills', 0)} skills...")
    generate_sitemap(catalog, args.output)
    generate_skill_pages(catalog, args.output)
    print("Done!")


if __name__ == "__main__":
    main()
