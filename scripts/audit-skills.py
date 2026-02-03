# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "rich"]
# ///
"""
Audit all Expanso skills to identify stubs, fakes, and broken implementations.

Usage:
    uv run -s scripts/audit-skills.py
    uv run -s scripts/audit-skills.py --output audit-report.json
    uv run -s scripts/audit-skills.py --category ai
"""

import argparse
import json
import re
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

# Patterns that indicate stub/fake implementations
FAKE_URL_PATTERNS = [
    r"https?://storage\.example\.com",
    r"https?://example\.com",
    r"https?://placeholder",
    r"/pull/42",  # Hardcoded PR number
    r"\.example\.",
]

TODO_PATTERNS = [
    r"# .*placeholder",  # Only match "placeholder" in comments
    r"# .*\bTODO\b",  # Word boundary to avoid matching "todoist"
    r"# .*\bFIXME\b",
    r"would query",
    r"in production.*would",
    r"# .*\bstub\b",
    r"for demo",  # "For demo, return empty"
]

# Processors that indicate real API calls (not just mapping)
REAL_API_PROCESSORS = [
    "openai_chat_completion",
    "openai_image_generation",
    "openai_audio_transcription",
    "openai_speech",
    "openai_embeddings",
    "ollama_chat",
    "ollama_embeddings",
    "http",  # External HTTP calls
    "aws_lambda",
    "gcp_cloud_function",
    "while",  # Control flow for polling APIs
    "command",  # External command execution
]


def load_yaml_file(path: Path) -> dict | None:
    """Load a YAML file, return None if it doesn't exist or is invalid."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def check_for_fake_urls(content: str) -> list[str]:
    """Check if content contains fake/placeholder URLs in actual code (not comments)."""
    found = []
    # Remove comment lines (lines starting with #)
    code_lines = [
        line for line in content.split("\n")
        if not line.strip().startswith("#")
    ]
    code_only = "\n".join(code_lines)

    for pattern in FAKE_URL_PATTERNS:
        if re.search(pattern, code_only, re.IGNORECASE):
            found.append(pattern)
    return found


def check_for_todos(content: str) -> list[str]:
    """Check if content contains TODO/placeholder comments."""
    found = []
    for pattern in TODO_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(pattern)
    return found


def check_for_real_processors(pipeline: dict) -> list[str]:
    """Check if pipeline uses real API processors."""
    found = []
    if not pipeline:
        return found

    # Convert to string for simple pattern matching
    pipeline_str = yaml.dump(pipeline)
    for processor in REAL_API_PROCESSORS:
        if processor in pipeline_str:
            found.append(processor)
    return found


def check_tests_skipped(test_yaml: dict | None) -> bool:
    """Check if tests are skipped."""
    if not test_yaml:
        return True  # No tests = effectively skipped

    tests = test_yaml.get("tests", [])
    if not tests:
        return True

    # Check if all tests are skipped
    all_skipped = all(t.get("skip", False) for t in tests)
    return all_skipped


def audit_skill(skill_path: Path) -> dict:
    """Audit a single skill directory."""
    skill_name = skill_path.name
    category = skill_path.parent.name

    result = {
        "name": skill_name,
        "category": category,
        "path": str(skill_path),
        "status": "unknown",
        "issues": [],
        "has_readme": False,
        "has_skill_yaml": False,
        "has_cli_pipeline": False,
        "has_mcp_pipeline": False,
        "has_tests": False,
        "tests_skipped": True,
        "real_processors": [],
        "fake_urls": [],
        "todos": [],
    }

    # Check for required files
    result["has_readme"] = (skill_path / "README.md").exists()
    result["has_skill_yaml"] = (skill_path / "skill.yaml").exists()
    result["has_cli_pipeline"] = (skill_path / "pipeline-cli.yaml").exists()
    result["has_mcp_pipeline"] = (skill_path / "pipeline-mcp.yaml").exists()
    result["has_tests"] = (skill_path / "test" / "test.yaml").exists()

    # Load and analyze pipeline
    cli_pipeline = load_yaml_file(skill_path / "pipeline-cli.yaml")
    if cli_pipeline:
        cli_content = (skill_path / "pipeline-cli.yaml").read_text()
        result["fake_urls"] = check_for_fake_urls(cli_content)
        result["todos"] = check_for_todos(cli_content)
        result["real_processors"] = check_for_real_processors(cli_pipeline)

    # Check tests
    test_yaml = load_yaml_file(skill_path / "test" / "test.yaml")
    result["tests_skipped"] = check_tests_skipped(test_yaml)

    # Determine status
    if result["fake_urls"]:
        result["status"] = "fake"
        result["issues"].append(f"Contains fake URLs: {result['fake_urls']}")
    elif result["todos"]:
        result["status"] = "stub"
        result["issues"].append(f"Contains TODO/placeholder: {result['todos']}")
    elif not result["real_processors"] and category == "ai":
        # AI skills should have real API calls
        # Other categories can legitimately be local-only
        result["status"] = "stub"
        result["issues"].append("No real API processors found (only mapping)")
    elif result["tests_skipped"]:
        result["status"] = "untested"
        result["issues"].append("Tests are skipped or missing")
    else:
        result["status"] = "working"

    return result


def audit_all_skills(skills_dir: Path, category_filter: str | None = None) -> dict:
    """Audit all skills in the skills directory."""
    results = {
        "skills": [],
        "summary": {
            "total": 0,
            "working": 0,
            "untested": 0,
            "stub": 0,
            "fake": 0,
            "unknown": 0,
        },
        "by_category": {},
    }

    # Find all skill directories
    for category_dir in sorted(skills_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        if category_dir.name.startswith(".") or category_dir.name.startswith("_"):
            continue

        category = category_dir.name
        if category_filter and category != category_filter:
            continue

        results["by_category"][category] = {
            "total": 0,
            "working": 0,
            "untested": 0,
            "stub": 0,
            "fake": 0,
        }

        for skill_dir in sorted(category_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("."):
                continue

            # Must have at least a pipeline file
            if not (skill_dir / "pipeline-cli.yaml").exists():
                continue

            skill_result = audit_skill(skill_dir)
            results["skills"].append(skill_result)

            # Update counts
            results["summary"]["total"] += 1
            results["summary"][skill_result["status"]] += 1
            results["by_category"][category]["total"] += 1
            results["by_category"][category][skill_result["status"]] += 1

    return results


def print_report(results: dict) -> None:
    """Print a formatted report to the console."""
    console.print("\n[bold]EXPANSO SKILLS AUDIT REPORT[/bold]\n")

    # Summary table
    summary = results["summary"]
    table = Table(title="Overall Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    total = summary["total"]
    for status in ["working", "untested", "stub", "fake"]:
        count = summary[status]
        pct = (count / total * 100) if total > 0 else 0
        style = {
            "working": "green",
            "untested": "yellow",
            "stub": "red",
            "fake": "red bold",
        }.get(status, "white")
        table.add_row(status.upper(), str(count), f"{pct:.1f}%", style=style)

    table.add_row("TOTAL", str(total), "100%", style="bold")
    console.print(table)

    # By category
    console.print("\n[bold]By Category:[/bold]")
    cat_table = Table()
    cat_table.add_column("Category")
    cat_table.add_column("Total", justify="right")
    cat_table.add_column("Working", justify="right", style="green")
    cat_table.add_column("Untested", justify="right", style="yellow")
    cat_table.add_column("Stub", justify="right", style="red")
    cat_table.add_column("Fake", justify="right", style="red bold")

    for cat, counts in sorted(results["by_category"].items()):
        cat_table.add_row(
            cat,
            str(counts["total"]),
            str(counts["working"]),
            str(counts["untested"]),
            str(counts["stub"]),
            str(counts["fake"]),
        )
    console.print(cat_table)

    # List problematic skills
    problems = [s for s in results["skills"] if s["status"] in ["stub", "fake"]]
    if problems:
        console.print(f"\n[bold red]Problematic Skills ({len(problems)}):[/bold red]")
        for skill in problems[:20]:  # Show first 20
            console.print(
                f"  [{skill['status'].upper()}] {skill['category']}/{skill['name']}: "
                f"{', '.join(skill['issues'][:1])}"
            )
        if len(problems) > 20:
            console.print(f"  ... and {len(problems) - 20} more")


def main():
    parser = argparse.ArgumentParser(description="Audit Expanso skills")
    parser.add_argument(
        "--output", "-o", help="Output JSON file path", type=Path, default=None
    )
    parser.add_argument(
        "--category", "-c", help="Filter by category (ai, security, etc.)", default=None
    )
    parser.add_argument(
        "--skills-dir",
        help="Path to skills directory",
        type=Path,
        default=Path(__file__).parent.parent / "skills",
    )
    args = parser.parse_args()

    console.print(f"[dim]Scanning {args.skills_dir}...[/dim]")
    results = audit_all_skills(args.skills_dir, args.category)

    print_report(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]Report saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
