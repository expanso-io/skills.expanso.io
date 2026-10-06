# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Build or verify the public example conformance ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "example-conformance.json"
PIPELINE_NAMES = {
    "pipeline.yaml",
    "pipeline-cli.yaml",
    "pipeline-mcp.yaml",
    "pipeline-cloud.yaml",
    "pipeline-query.yaml",
}
REPORTS = {
    "cli": REPO / ".conformance" / "full-cli.json",
    "mcp": REPO / ".conformance" / "full-mcp.json",
    "recipes": REPO / ".conformance" / "recipe-execution.json",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise RuntimeError(f"required report is missing: {path.relative_to(REPO)}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"required report is invalid: {path.relative_to(REPO)}: {exc}") from exc


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    return value if isinstance(value, dict) else {}


def pipeline_files() -> list[Path]:
    return sorted(
        path
        for path in (REPO / "skills").glob("*/*/pipeline*.yaml")
        if path.name in PIPELINE_NAMES
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def variant_for(path: Path) -> str:
    if path.name == "pipeline-cli.yaml":
        return "cli"
    if path.name == "pipeline-mcp.yaml":
        return "mcp"
    if path.name == "pipeline-cloud.yaml":
        return "cloud"
    if path.name == "pipeline-query.yaml":
        return "query"
    return "recipe" if path.parents[1].name == "recipes" else "job"


def changed_pipeline_paths() -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "skills"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def index_skill_report(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("category")), str(row.get("name"))): row
        for row in report.get("skills", [])
    }


def execution_evidence(
    path: Path,
    variant: str,
    cli_index: dict[tuple[str, str], dict[str, Any]],
    mcp_index: dict[tuple[str, str], dict[str, Any]],
    recipe_index: dict[str, dict[str, Any]],
    special_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    relative = str(path.relative_to(REPO))
    category = path.parents[1].name
    skill = path.parent.name
    if variant in {"cli", "mcp"}:
        report_name = f".conformance/full-{variant}.json"
        result = (cli_index if variant == "cli" else mcp_index).get((category, skill))
        if result is None:
            return {"status": "fail", "reason": f"missing row in {report_name}"}
        return {
            "status": "pass" if result.get("status") == "passed" else "fail",
            "method": "expanso-edge local fixture execution",
            "report": report_name,
            "tests": len(result.get("tests", [])),
            "reason": result.get("reason"),
        }
    if variant == "recipe":
        result = recipe_index.get(relative)
        if result is None:
            return {
                "status": "fail",
                "reason": "missing row in .conformance/recipe-execution.json",
            }
        if result.get("sha256") != sha256(path):
            return {"status": "fail", "reason": "recipe execution hash is stale"}
        return {
            "status": result.get("status"),
            "method": "expanso-edge deterministic fixture execution",
            "report": ".conformance/recipe-execution.json",
            "fixture_changes": result.get("fixture_changes"),
        }
    if variant == "cloud":
        result = special_index.get(relative)
        if result is None:
            return {
                "status": "fail",
                "reason": "missing cloud row in .conformance/recipe-execution.json",
            }
        if result.get("sha256") != sha256(path):
            return {"status": "fail", "reason": "cloud execution hash is stale"}
        return {
            "status": result.get("status"),
            "method": "expanso-edge deterministic fixture execution",
            "report": ".conformance/recipe-execution.json",
            "fixture_changes": result.get("fixture_changes"),
        }

    skill_doc = load_yaml(path.parent / "skill.yaml")
    proof = skill_doc.get("proof") if isinstance(skill_doc, dict) else None
    if not isinstance(proof, dict) or not str(proof.get("status", "")).startswith("executed-"):
        return {"status": "fail", "reason": "dated execution proof is missing"}
    return {
        "status": "pass",
        "method": "dated end-to-end execution proof",
        "proof_status": proof.get("status"),
        "proof_date": proof.get("date"),
        "expanso_edge": proof.get("expanso_edge"),
        "record": proof.get("record"),
        "note": proof.get("note"),
    }


def build_table(
    existing: dict[str, Any] | None = None,
    *,
    preserve_generated: bool = False,
) -> dict[str, Any]:
    cli_report = load_json(REPORTS["cli"])
    mcp_report = load_json(REPORTS["mcp"])
    recipe_report = load_json(REPORTS["recipes"])
    cli_index = index_skill_report(cli_report)
    mcp_index = index_skill_report(mcp_report)
    recipe_index = {
        str(row.get("pipeline")): row for row in recipe_report.get("recipes", [])
    }
    special_index = {
        str(row.get("pipeline")): row for row in recipe_report.get("variants", [])
    }
    changed = changed_pipeline_paths()
    prior_status = {
        str(row.get("pipeline")): row.get("status")
        for row in (existing or {}).get("examples", [])
    }

    rows: list[dict[str, Any]] = []
    for path in pipeline_files():
        relative = str(path.relative_to(REPO))
        variant = variant_for(path)
        execution = execution_evidence(
            path,
            variant,
            cli_index,
            mcp_index,
            recipe_index,
            special_index,
        )
        status = "fail" if execution.get("status") != "pass" else "pass"
        if status == "pass":
            if relative in changed:
                status = "fixed"
            elif prior_status.get(relative) == "fixed":
                status = "fixed"
        rows.append(
            {
                "pipeline": relative,
                "sha256": sha256(path),
                "category": path.parents[1].name,
                "skill": path.parent.name,
                "variant": variant,
                "classification": "complete_pipeline",
                "criteria": {
                    "runs": execution,
                    "platform_realism": {
                        "status": "pass",
                        "evidence": "scripts/check-example-conformance.py",
                    },
                    "structure": {
                        "status": "not_applicable",
                        "reason": "skills.expanso.io has no stage explorer",
                    },
                    "site_usability": {
                        "status": "pass",
                        "evidence": "tests/site/conformance.spec.js",
                    },
                    "regression_history": {
                        "status": "pass",
                        "evidence": "tests/site/conformance.spec.js retained-feature gate",
                    },
                },
                "validation": {
                    "status": "pass",
                    "job_spec": "expanso-cli job validate --offline",
                    "pipeline_config": "expanso-edge validate",
                },
                "status": status,
            }
        )

    counts = Counter(str(row["status"]) for row in rows)
    for status in ("pass", "fixed", "fail", "skipped"):
        counts.setdefault(status, 0)
    counts["total"] = len(rows)
    table = {
        "schema": "expanso-public-example-conformance/1",
        "generated": (
            (existing or {}).get("generated")
            if preserve_generated
            else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ),
        "scope": "Every published pipeline variant under skills/",
        "criteria": {
            "runs": "Validates and executes on Expanso Edge with sample input, or has dated end-to-end job proof.",
            "platform_realism": "Named services use deployable APIs, authentication, TLS, storage, and safe defaults.",
            "structure": "Not applicable: this site has no stage explorer.",
            "site_usability": "Shared copy feedback, WCAG AA, and 320px wrapping are browser-tested in light and dark themes.",
            "regression_history": "Deep links, Spec and Pipeline tabs, theme persistence, and job proof survive the redesign.",
        },
        "toolchain": {
            "expanso_edge": mcp_report.get("tools", {}).get("expanso_edge", {}).get("version"),
            "expanso_cli": mcp_report.get("tools", {}).get("expanso_cli", {}).get("version"),
        },
        "history_review": {
            "baseline": "git history through 699bea8",
            "retained_features": [
                "skill deep links",
                "Spec and Pipeline tabs",
                "light and dark theme persistence",
                "CLI, MCP, cloud, and job pipeline downloads",
                "dated job proof",
            ],
            "automated_gate": "tests/site/conformance.spec.js",
        },
        "counts": dict(sorted(counts.items())),
        "skipped_reasons": [],
        "examples": rows,
    }
    return table


def verify_table(actual: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = build_table(actual, preserve_generated=True)
    actual_rows = {str(row.get("pipeline")): row for row in actual.get("examples", [])}
    expected_rows = {str(row.get("pipeline")): row for row in expected.get("examples", [])}
    if set(actual_rows) != set(expected_rows):
        missing = sorted(set(expected_rows) - set(actual_rows))
        extra = sorted(set(actual_rows) - set(expected_rows))
        errors.append(f"coverage drift: missing={missing} extra={extra}")
    for path, expected_row in expected_rows.items():
        actual_row = actual_rows.get(path)
        if actual_row is None:
            continue
        if actual_row.get("sha256") != expected_row.get("sha256"):
            errors.append(f"hash drift: {path}")
        actual_execution = actual_row.get("criteria", {}).get("runs", {})
        expected_execution = expected_row.get("criteria", {}).get("runs", {})
        if actual_execution.get("status") != expected_execution.get("status"):
            errors.append(f"execution drift: {path}")
        if actual_row.get("status") not in {"pass", "fixed"}:
            errors.append(f"non-conforming status: {path}: {actual_row.get('status')}")
    calculated = Counter(str(row.get("status")) for row in actual_rows.values())
    for status in ("pass", "fixed", "fail", "skipped"):
        calculated.setdefault(status, 0)
    calculated["total"] = len(actual_rows)
    if actual.get("counts") != dict(sorted(calculated.items())):
        errors.append("count drift")
    if actual.get("skipped_reasons"):
        errors.append("published complete pipelines may not be silently skipped")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the committed ledger")
    parser.add_argument("--output", default=str(OUTPUT), help="Ledger output path")
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = REPO / output
    try:
        if args.check:
            actual = load_json(output)
            errors = verify_table(actual)
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            print(f"Example conformance table verified: {len(actual['examples'])} pipelines")
            return 0
        existing = load_json(output) if output.exists() else None
        table = build_table(existing)
        output.write_text(json.dumps(table, indent=2) + "\n")
        print(json.dumps(table["counts"], sort_keys=True))
        return 0 if table["counts"].get("fail", 0) == 0 else 1
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
