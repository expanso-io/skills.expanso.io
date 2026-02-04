#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Build the skills catalog.json and organize skills into categories.

Usage:
    uv run -s scripts/build-catalog.py
    uv run -s scripts/build-catalog.py --source skills --target .
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

# Define skill categories with patterns
CATEGORY_RULES = {
    "workflows": {
        "description": "End-to-end automation workflows combining multiple services",
        "patterns": [
            "morning-briefing",
            "email-triage",
            "stripe-reports",
            "devops-monitor",
            "jira-automate",
            "todoist-automate",
            "seo-pipeline",
            "marketing-auto",
            "catalog-reconcile",
            "task-dashboard",
            "backup-verify",
            "health-integrate",
            "site-migrate",
            "terminal-services",
            "meal-planner",
            "multi-platform-chat",
            "voice-admin",
            "auto-coder",
            "llm-router",
        ],
        "tags": ["automation", "workflow", "orchestration"],
    },
    "ai": {
        "description": "AI-powered skills for text, image, audio, and video processing",
        "patterns": [
            "text-embed",
            "text-summarize",
            "text-translate",
            "text-to-speech",
            "text-to-image",
            "text-to-command",
            "audio-transcribe",
            "speaker-diarize",
            "meeting-notes",
            "image-analyze",
            "image-alttext",
            "image-caption",
            "image-describe",
            "image-moderate",
            "video-generate",
            "sentiment-score",
            "keyword-extract",
            "language-detect",
            "grammar-check",
            "code-explain",
            "sql-generate",
            "json-extract",
            "url-to-article",
        ],
        "tags": ["ai", "ml", "llm", "nlp"],
    },
    "security": {
        "description": "Security, compliance, and cryptographic operations",
        "patterns": [
            "cve-scan",
            "pii-detect",
            "pii-redact",
            "sign-envelope",
            "verify-signature",
            "audit-envelope",
            "secrets-scan",
            "sbom-generate",
            "policy-check",
            "jwt-verify",
            "tls-inspect",
            "log-sanitize",
            "hash-digest",
            "password-generate",
        ],
        "tags": ["security", "compliance", "crypto", "privacy"],
    },
    "transforms": {
        "description": "Data transformation, parsing, and format conversion",
        "patterns": [
            # JSON operations
            "json-",
            # Array operations
            "array-",
            # String operations
            "string-",
            # Text operations (non-AI)
            "text-analyze",
            "text-capitalize",
            "text-diff",
            "text-escape",
            "text-format",
            "text-indent",
            "text-lines",
            "text-reverse",
            "text-stats",
            "text-truncate",
            "text-wrap",
            # Object operations
            "object-",
            # Math operations
            "math-",
            # Date/time operations
            "date-",
            "time-parse",
            "timestamp-parse",
            "timezone-convert",
            "duration-format",
            "cron-explain",
            # Format conversions
            "csv-to-json",
            "xml-to-json",
            "yaml-to-json",
            "json-to-csv",
            "json-to-yaml",
            "yaml-validate",
            # Encoding/decoding
            "base64-codec",
            "binary-encode",
            "hex-encode",
            "url-encode",
            "jwt-decode",
            # Parsing
            "url-parse",
            "path-parse",
            "ip-parse",
            "semver-parse",
            "env-parse",
            "query-string",
            "boolean-parse",
            # Formatting
            "number-format",
            "number-round",
            "percentage-calc",
            "color-convert",
            "color-rgb",
            # Misc transforms
            "html-strip",
            "emoji-strip",
            "whitespace-normalize",
            "markdown-format",
            "markdown-toc",
            "line-numbers",
            "slug-generate",
            "lorem-ipsum",
            "regex-extract",
            "http-status",
            "file-size",
            "type-check",
            "word-count",
        ],
        "tags": ["transform", "parse", "convert", "format"],
    },
    "utilities": {
        "description": "General utilities and helper functions",
        "patterns": [
            "uuid-generate",
            "random-number",
            "email-validate",
            "mime-type",
            "media-type-detect",
            "media-info",
            "audio-duration",
            "image-dimensions",
            "image-metadata",
            "image-resize-calc",
            "video-thumbnail",
            "config-normalize",
            "openapi-validate",
            "determinism-test",
            "idempotent-cache",
            "retry-wrapper",
        ],
        "tags": ["utility", "helper", "validation"],
    },
}


def categorize_skill(skill_name: str) -> str:
    """Determine the category for a skill based on its name."""
    for category, config in CATEGORY_RULES.items():
        for pattern in config["patterns"]:
            if skill_name.startswith(pattern) or skill_name == pattern:
                return category
    return "utilities"  # Default category


def load_skill_yaml(skill_path: Path) -> dict | None:
    """Load and parse skill.yaml file."""
    skill_file = skill_path / "skill.yaml"
    if not skill_file.exists():
        return None
    try:
        with open(skill_file) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Warning: Failed to parse {skill_file}: {e}", file=sys.stderr)
        return None


def detect_layout(source_dir: Path) -> str:
    """Detect whether skills are in a flat or categorized directory layout."""
    for child in source_dir.iterdir():
        if child.is_dir() and (child / "skill.yaml").exists():
            return "flat"
    return "categorized"


def iter_skill_dirs(source_dir: Path, layout: str) -> list[tuple[str | None, Path]]:
    """Return a list of (category_hint, skill_dir) tuples."""
    skills: list[tuple[str | None, Path]] = []
    if layout == "flat":
        for skill_dir in sorted(source_dir.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "skill.yaml").exists():
                skills.append((None, skill_dir))
        return skills

    # categorized layout: source_dir/<category>/<skill>/
    for category_dir in sorted(source_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        for skill_dir in sorted(category_dir.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "skill.yaml").exists():
                skills.append((category_dir.name, skill_dir))
    return skills


def resolve_category(skill_name: str, category_hint: str | None) -> str:
    """Resolve category using directory hint first, then name patterns."""
    if category_hint and (category_hint in CATEGORY_RULES or category_hint == "utilities"):
        return category_hint
    return categorize_skill(skill_name)


def build_catalog(source_dir: Path, layout: str) -> tuple[dict, dict[str, list[str]]]:
    """Build the skills catalog and organize into categories."""
    catalog = {
        "version": "1.0.0",
        "generated": None,  # Will be set during JSON serialization
        "total_skills": 0,
        "categories": {},
        "skills": {},
    }

    # Track category assignments
    category_skills: dict[str, list[str]] = {cat: [] for cat in CATEGORY_RULES}
    category_skills["utilities"] = []

    # Process each skill
    for category_hint, skill_path in iter_skill_dirs(source_dir, layout):
        if skill_path.name.startswith("_"):
            continue

        skill_name = skill_path.name
        skill_data = load_skill_yaml(skill_path)

        if skill_data is None:
            print(f"Skipping {skill_name}: no valid skill.yaml", file=sys.stderr)
            continue

        # Determine category
        category = resolve_category(skill_name, category_hint)
        category_skills[category].append(skill_name)

        # Extract metadata
        skill_meta = {
            "name": skill_data.get("name", skill_name),
            "version": skill_data.get("version", "1.0.0"),
            "description": skill_data.get("description", ""),
            "category": category,
            "credentials": [
                {
                    "name": c.get("name"),
                    "required": c.get("required", False),
                    "description": c.get("description", ""),
                }
                for c in skill_data.get("credentials", [])
            ],
            "inputs": skill_data.get("inputs", []),
            "outputs": skill_data.get("outputs", []),
            "backends": [b.get("name") for b in skill_data.get("backends", [])],
            "tags": extract_tags(skill_name, skill_data, category),
        }

        catalog["skills"][skill_name] = skill_meta
        catalog["total_skills"] += 1

    # Build category summaries
    for cat_name, config in CATEGORY_RULES.items():
        skills_in_cat = category_skills.get(cat_name, [])
        catalog["categories"][cat_name] = {
            "description": config["description"],
            "skill_count": len(skills_in_cat),
            "tags": config["tags"],
        }

    # Add utilities category
    catalog["categories"]["utilities"] = {
        "description": "General utilities and helper functions",
        "skill_count": len(category_skills.get("utilities", [])),
        "tags": ["utility", "helper", "validation"],
    }

    return catalog, category_skills


def extract_tags(skill_name: str, skill_data: dict, category: str) -> list[str]:
    """Extract relevant tags for a skill."""
    tags = set()

    # Add category tag
    tags.add(category)

    # Add credential-based tags
    for cred in skill_data.get("credentials", []):
        cred_name = cred.get("name", "").lower()
        if "openai" in cred_name:
            tags.add("openai")
        if "ollama" in cred_name or "local" in cred_name:
            tags.add("local")
        if "google" in cred_name:
            tags.add("google")
        if "slack" in cred_name:
            tags.add("slack")
        if "jira" in cred_name:
            tags.add("jira")

    # Add backend-based tags
    for backend in skill_data.get("backends", []):
        backend_type = backend.get("type", "")
        if backend_type == "local":
            tags.add("local")
            tags.add("offline")
        if backend_type == "remote":
            tags.add("remote")

    # Add name-based tags
    name_parts = skill_name.split("-")
    if name_parts[0] in ["json", "yaml", "xml", "csv", "text", "string", "array"]:
        tags.add(name_parts[0])

    return sorted(tags)


def copy_skills_to_categories(
    source_dir: Path, target_dir: Path, category_skills: dict[str, list[str]]
) -> None:
    """Copy skills to their category directories."""
    # Create category directories
    skills_dir = target_dir / "skills"
    for category in category_skills:
        (skills_dir / category).mkdir(parents=True, exist_ok=True)

    # Copy each skill
    for category, skills in category_skills.items():
        for skill_name in skills:
            src = source_dir / skill_name
            dst = skills_dir / category / skill_name
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  {skill_name} -> {category}/")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build Expanso skills catalogs.")
    parser.add_argument(
        "--source",
        type=Path,
        default=repo_root / "skills",
        help="Path to skills directory (flat or categorized).",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=repo_root,
        help="Path to output catalog.json and catalog-minimal.json.",
    )
    parser.add_argument(
        "--sync-categories",
        action="store_true",
        help="Copy flat skills into target skills/<category>/ (disabled by default).",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    source_dir = args.source
    target_dir = args.target

    print("Building Expanso Skills Catalog...")
    print(f"  Source: {source_dir}")
    print(f"  Target: {target_dir}")
    print()

    # Build catalog
    print("Analyzing skills...")
    layout = detect_layout(source_dir)
    catalog, category_skills = build_catalog(source_dir, layout)

    # Print summary
    print(f"\nFound {catalog['total_skills']} skills in {len(category_skills)} categories:")
    for cat, skills in sorted(category_skills.items()):
        if skills:
            print(f"  {cat}: {len(skills)} skills")

    # Copy skills to category directories (optional)
    if args.sync_categories:
        if layout != "flat":
            print("\nSkipping category sync (source is categorized).")
        else:
            print("\nCopying skills to categories...")
            copy_skills_to_categories(source_dir, target_dir, category_skills)

    # Write catalog.json
    from datetime import datetime, timezone

    catalog["generated"] = datetime.now(timezone.utc).isoformat()

    catalog_path = target_dir / "catalog.json"
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"\nWrote catalog to {catalog_path}")

    # Also write a minimal catalog for quick lookups
    minimal_catalog = {
        "version": catalog["version"],
        "total_skills": catalog["total_skills"],
        "categories": {
            cat: {"skill_count": len(skills), "skills": skills}
            for cat, skills in category_skills.items()
            if skills
        },
    }
    minimal_path = target_dir / "catalog-minimal.json"
    with open(minimal_path, "w") as f:
        json.dump(minimal_catalog, f, indent=2)
    print(f"Wrote minimal catalog to {minimal_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
