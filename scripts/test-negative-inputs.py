# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise one fail-closed input for every published CLI and MCP skill."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".conformance" / "negative-inputs.json"
TOKEN = "negative-audit-bearer-token-32-chars"
CLAIM_KEYS = {
    "completed",
    "created",
    "deployed",
    "executed",
    "passed",
    "sent",
    "success",
    "valid",
    "verified",
}
FAILURE_STATUSES = {"error", "failed", "invalid", "rejected", "unsupported"}
IGNORED_DATA_KEYS = {
    "action",
    "capability_gap",
    "code",
    "error",
    "errors",
    "message",
    "metadata",
    "mode",
    "publication",
    "reason",
    "skill",
    "status",
    "trace_id",
}
NO_REQUIRED_INPUT_CASES: dict[str, dict[str, Any]] = {
    "ai/audio-transcribe": {"cli": {}, "mcp": {}},
    "connectors/gmail-read": {"cli": {}, "mcp": {}},
    "connectors/webhook-receive": {
        "cli": {"headers": {}, "body": {}, "raw_body": "{}"},
        "mcp": {},
    },
    "security/password-generate": {
        "cli": {"length": 0},
        "mcp": {"length": 0},
    },
    "transforms/date-now": {"cli": {"invalid": True}, "mcp": {"invalid": True}},
    "transforms/lorem-ipsum": {
        "cli": {"paragraphs": 0},
        "mcp": {"paragraphs": 0},
    },
    "transforms/timestamp-parse": {
        "cli": "not-a-timestamp",
        "mcp": {"timestamp": "not-a-timestamp"},
    },
    "utilities/media-type-detect": {"cli": "", "mcp": {}},
    "utilities/random-number": {
        "cli": {"min": 10, "max": 1},
        "mcp": {"min": 10, "max": 1},
    },
    "utilities/uuid-generate": {"cli": {"count": 0}, "mcp": {"count": 0}},
    "workflows/devops-monitor": {"cli": {}, "mcp": {}},
    "workflows/meal-planner": {
        "cli": {"days": 0, "people": 0},
        "mcp": {"days": 0, "people": 0},
    },
    "workflows/morning-briefing": {"cli": {}, "mcp": {}},
    "workflows/seo-pipeline": {"cli": {}, "mcp": {}},
    "workflows/stripe-reports": {"cli": {}, "mcp": {}},
    "workflows/todoist-automate": {
        "cli": {"action": "complete", "task_id": "missing-id"},
        "mcp": {"action": "complete", "task_id": "missing-id"},
    },
    "workflows/voice-admin": {"cli": {}, "mcp": {}},
}
NO_INPUT_GENERATORS = {
    "security/password-generate",
    "transforms/date-now",
    "transforms/lorem-ipsum",
    "utilities/random-number",
    "utilities/uuid-generate",
}


def load_regression_module():
    path = ROOT / "scripts" / "test-review-regressions.py"
    spec = importlib.util.spec_from_file_location("negative_regressions", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def is_pulled(document: dict[str, Any]) -> bool:
    publication = document.get("publication", {})
    return isinstance(publication, dict) and publication.get("status") == "pulled"


def published_skills(selected: set[str]) -> list[tuple[str, Path, dict[str, Any]]]:
    rows = []
    for metadata in sorted((ROOT / "skills").glob("*/*/skill.yaml")):
        document = yaml.safe_load(metadata.read_text()) or {}
        relative = str(metadata.parent.relative_to(ROOT / "skills"))
        if is_pulled(document) or (selected and metadata.parent.name not in selected):
            continue
        variants = [metadata.parent / f"pipeline-{name}.yaml" for name in ("cli", "mcp")]
        if not all(path.exists() for path in variants):
            continue
        rows.append((relative, metadata.parent, document))
    return rows


def required_inputs(document: dict[str, Any]) -> list[str]:
    return [
        str(item["name"])
        for item in document.get("inputs", [])
        if isinstance(item, dict) and item.get("required") and item.get("name")
    ]


def fixture_value(name: str) -> str:
    upper = name.upper()
    if "URL" in upper or upper.endswith("HOST"):
        return "https://127.0.0.1:1"
    if "EMAIL" in upper:
        return "agent@example.test"
    if upper.endswith("_HEX"):
        return "00" * 32
    if any(marker in upper for marker in ("KEY", "PASSWORD", "SECRET", "TOKEN")):
        return "negative-audit-fixture-value-32-chars"
    return "negative-audit-fixture"


def environment(skills: list[tuple[str, Path, dict[str, Any]]]) -> dict[str, str]:
    result = {"MCP_BEARER_TOKEN": TOKEN}
    for _, _, document in skills:
        for credential in document.get("credentials", []):
            if isinstance(credential, dict) and credential.get("name"):
                name = str(credential["name"])
                result.setdefault(name, fixture_value(name))
        for backend in document.get("backends", []):
            if not isinstance(backend, dict):
                continue
            for name in backend.get("requires", []) or []:
                result.setdefault(str(name), fixture_value(str(name)))
    result.update(
        {
            "OPENAI_API_KEY": "negative-audit-fixture-value-32-chars",
            "VERIFY_KEY": "negative-audit-fixture-value-32-chars",
            "WEBHOOK_SECRET": "negative-audit-fixture-value-32-chars",
        }
    )
    return result


def isolate_external_failures(value: Any) -> None:
    """Keep the processor graph but make external boundaries fail on loopback."""
    if isinstance(value, list):
        for child in value:
            isolate_external_failures(child)
        return
    if not isinstance(value, dict):
        return
    if any(str(key).startswith("openai_") for key in value):
        value.clear()
        value["mapping"] = 'root = throw("negative audit provider failure")'
        return
    for key, child in list(value.items()):
        if key == "http" and isinstance(child, dict):
            child["url"] = "http://127.0.0.1:1"
            child["retries"] = 0
            child["timeout"] = "250ms"
        else:
            isolate_external_failures(child)


def truthy_claims(value: Any, path: str = "root") -> list[str]:
    issues = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in CLAIM_KEYS and child is True:
                issues.append(f"{child_path} reported true")
            issues.extend(truthy_claims(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(truthy_claims(child, f"{path}[{index}]"))
    return issues


def has_failure_signal(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    status = value.get("status")
    if isinstance(status, str) and status.lower() in FAILURE_STATUSES:
        return True
    if value.get("error") or value.get("errors"):
        return True
    for key in CLAIM_KEYS:
        if key in value and value[key] is False:
            return True
    return any(has_failure_signal(child) for child in value.values())


def has_domain_data(value: Any, key: str = "") -> bool:
    if key.lower() in IGNORED_DATA_KEYS:
        return False
    if value in (None, False, "", 0):
        return False
    if isinstance(value, dict):
        return any(has_domain_data(child, str(child_key)) for child_key, child in value.items())
    if isinstance(value, list):
        return any(has_domain_data(child) for child in value)
    return True


def output_issues(output: Any, require_failure_or_empty: bool) -> list[str]:
    issues = truthy_claims(output)
    if not require_failure_or_empty:
        return issues
    if output in (None, {}, []):
        return issues
    if has_failure_signal(output):
        return issues
    if has_domain_data(output):
        issues.append("negative input produced domain data without a failure signal")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", help="Optional skill names")
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    selected = set(args.skills)
    skills = published_skills(selected)
    if not skills:
        raise SystemExit("no published CLI/MCP skills selected")
    missing_cases = [
        relative
        for relative, _, document in skills
        if not required_inputs(document) and relative not in NO_REQUIRED_INPUT_CASES
    ]
    if missing_cases:
        raise SystemExit(f"negative-case coverage missing: {missing_cases}")

    reg = load_regression_module()
    directory = ROOT / ".conformance" / f"negative-inputs-{time.time_ns()}"
    directory.mkdir(parents=True)
    suite = reg.Suite(directory, environment(skills))
    rows = []
    try:
        for relative, _, document in skills:
            required = required_inputs(document)
            for variant in ("cli", "mcp"):
                config = copy.deepcopy(reg.config(relative, variant))
                isolate_external_failures(config.get("pipeline", {}))
                case = (
                    NO_REQUIRED_INPUT_CASES[relative][variant]
                    if not required
                    else ("" if variant == "cli" else {})
                )
                raw = variant == "cli"
                payload = (
                    case
                    if isinstance(case, str)
                    else json.dumps(case, separators=(",", ":"))
                    if raw
                    else case
                )
                headers = {"Authorization": f"Bearer {TOKEN}"} if variant == "mcp" else None
                result = suite.execute(config, payload, headers=headers, raw=raw)
                needs_failure = bool(required) or relative not in NO_INPUT_GENERATORS
                issues = output_issues(result, needs_failure)
                row = {
                    "pipeline": f"skills/{relative}/pipeline-{variant}.yaml",
                    "case": "missing required field" if required else "invalid or unreachable dependency input",
                    "required_fields": required,
                    "status": "failed" if issues else "passed",
                    "issues": issues,
                    "output": result,
                }
                rows.append(row)
                print(f"{row['status'].upper()} {row['pipeline']}")
        expected = {
            f"skills/{relative}/pipeline-{variant}.yaml"
            for relative, _, _ in skills
            for variant in ("cli", "mcp")
        }
        covered = {row["pipeline"] for row in rows}
        if covered != expected:
            raise AssertionError(
                f"negative-case coverage drift: missing={sorted(expected - covered)} "
                f"extra={sorted(covered - expected)}"
            )
        report = {
            "schema": "expanso-negative-input-audit/1",
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "coverage": {"published_variants": len(expected), "tested_variants": len(covered)},
            "counts": {
                "passed": sum(row["status"] == "passed" for row in rows),
                "failed": sum(row["status"] == "failed" for row in rows),
            },
            "cases": rows,
        }
        report_path = args.report if args.report.is_absolute() else ROOT / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report["coverage"] | report["counts"], sort_keys=True))
        return 1 if report["counts"]["failed"] else 0
    finally:
        suite.close()


if __name__ == "__main__":
    raise SystemExit(main())
