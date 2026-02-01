#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Expanso Skills Lookup CLI

A simple CLI for browsing the skills catalog.

Usage:
    uv run -s scripts/skill-lookup.py list [category]
    uv run -s scripts/skill-lookup.py show <skill-name>
    uv run -s scripts/skill-lookup.py search <query>
"""

import json
import sys
from pathlib import Path


def load_catalog():
    """Load the catalog.json file."""
    catalog_path = Path(__file__).parent.parent / "catalog.json"
    if not catalog_path.exists():
        print("Error: catalog.json not found. Run build-catalog.py first.", file=sys.stderr)
        sys.exit(1)
    with open(catalog_path) as f:
        return json.load(f)


def cmd_list(catalog, category=None):
    """List skills, optionally filtered by category."""
    if category is None:
        # List categories
        print("Categories:")
        for cat, info in sorted(catalog["categories"].items()):
            print(f"  {cat:12} {info['skill_count']:3} skills - {info['description']}")
        print(f"\nTotal: {catalog['total_skills']} skills")
    else:
        # List skills in category
        skills = [
            (name, s)
            for name, s in catalog["skills"].items()
            if s["category"] == category
        ]
        if not skills:
            print(f"No skills found in category: {category}", file=sys.stderr)
            sys.exit(1)

        print(f"{category.upper()} ({len(skills)} skills):\n")
        for name, skill in sorted(skills):
            print(f"  {name:25} {skill['description'][:50]}")


def cmd_show(catalog, skill_name):
    """Show details for a specific skill."""
    skill = catalog["skills"].get(skill_name)
    if not skill:
        print(f"Skill not found: {skill_name}", file=sys.stderr)
        # Suggest similar
        similar = [n for n in catalog["skills"] if skill_name in n]
        if similar:
            print(f"Did you mean: {', '.join(similar[:5])}")
        sys.exit(1)

    print(f"# {skill['name']}")
    print(f"\n{skill['description']}")
    print(f"\nCategory: {skill['category']} | Version: {skill['version']}")

    if skill.get("credentials"):
        print("\n## Credentials")
        for cred in skill["credentials"]:
            req = "required" if cred.get("required") else "optional"
            print(f"  - {cred['name']} ({req}): {cred.get('description', '')}")

    if skill.get("inputs"):
        print("\n## Inputs")
        for inp in skill["inputs"]:
            req = "required" if inp.get("required") else "optional"
            default = f" (default: {inp['default']})" if "default" in inp else ""
            print(f"  - {inp['name']}: {inp.get('type', 'any')} ({req}){default}")
            if inp.get("description"):
                print(f"    {inp['description']}")

    if skill.get("outputs"):
        print("\n## Outputs")
        for out in skill["outputs"]:
            print(f"  - {out['name']}: {out.get('type', 'any')}")
            if out.get("description"):
                print(f"    {out['description']}")

    if skill.get("backends"):
        print(f"\n## Backends: {', '.join(skill['backends'])}")

    if skill.get("tags"):
        print(f"\n## Tags: {', '.join(skill['tags'])}")


def cmd_search(catalog, query):
    """Search skills by name or description."""
    query = query.lower()
    matches = []

    for name, skill in catalog["skills"].items():
        if query in name.lower() or query in skill.get("description", "").lower():
            matches.append((name, skill))

    if not matches:
        print(f"No skills found matching: {query}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(matches)} skills matching '{query}':\n")
    for name, skill in sorted(matches):
        print(f"  [{skill['category']:10}] {name:25} {skill['description'][:40]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    catalog = load_catalog()
    cmd = sys.argv[1]

    if cmd == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(catalog, category)
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: skill-lookup.py show <skill-name>", file=sys.stderr)
            sys.exit(1)
        cmd_show(catalog, sys.argv[2])
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: skill-lookup.py search <query>", file=sys.stderr)
            sys.exit(1)
        cmd_search(catalog, sys.argv[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
