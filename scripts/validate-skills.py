#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Validate every published skill pipeline and emit a machine-readable report.

This records what the *local validator* says. It deliberately does NOT claim any
skill executes: passing validation is not execution evidence. See the report's
`readiness` field, which is capped at `validated-not-executed`.

Usage:
    uv run -s scripts/validate-skills.py
    uv run -s scripts/validate-skills.py --output validation-report.json
    uv run -s scripts/validate-skills.py --check   # exit 1 if results changed
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Readiness vocabulary. Nothing here may reach `verified-executed`; that label is
# earned only by a dated Cloud run record with pinned versions, control-plane
# identifiers and a downstream receipt.
READY_VALIDATED = "validated-not-executed"
READY_INVALID = "invalid-does-not-validate"

# Every published pipeline variant is validated. A skill is only
# `validated-not-executed` when all of its variants validate. `cloud` is the
# input path a remotely scheduled node can satisfy on its own.
VARIANTS = {
    "cli": "pipeline-cli.yaml",
    "mcp": "pipeline-mcp.yaml",
    "cloud": "pipeline-cloud.yaml",
}


def edge_bin() -> str:
    return shutil.which("expanso-edge") or "expanso-edge"


def tool_version(binary: str) -> str:
    try:
        out = subprocess.run(
            [binary, "version"], capture_output=True, text=True, timeout=30
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def validate(binary: str, path: Path) -> tuple[bool, str]:
    try:
        res = subprocess.run(
            [binary, "validate", str(path.relative_to(REPO))],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"validator could not run: {exc}"
    if res.returncode == 0 and "[OK]" in res.stdout:
        return True, ""
    detail = " ".join((res.stdout + res.stderr).split())
    return False, detail[:400]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=REPO / "skills")
    ap.add_argument("--output", type=Path, default=REPO / "validation-report.json")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if the report on disk is out of date.",
    )
    args = ap.parse_args()

    binary = edge_bin()
    if shutil.which(binary) is None:
        print(
            "expanso-edge not found on PATH; skipping validation report",
            file=sys.stderr,
        )
        return 0

    version = tool_version(binary)
    skills: dict[str, dict] = {}
    for skill_dir in sorted(
        p.parent for p in args.source.glob("*/*/pipeline-cli.yaml")
    ):
        variants: dict[str, dict] = {}
        for variant, filename in VARIANTS.items():
            pipeline = skill_dir / filename
            if not pipeline.exists():
                continue
            ok, detail = validate(binary, pipeline)
            result = {
                "pipeline": str(pipeline.relative_to(REPO)),
                "validates": ok,
                "readiness": READY_VALIDATED if ok else READY_INVALID,
            }
            if not ok:
                result["error"] = detail
            variants[variant] = result
        all_ok = all(v["validates"] for v in variants.values())
        skills[skill_dir.name] = {
            "category": skill_dir.parent.name,
            "validates": all_ok,
            "readiness": READY_VALIDATED if all_ok else READY_INVALID,
            "variants": variants,
        }

    passing = sum(1 for s in skills.values() if s["validates"])
    report = {
        "schema": "expanso-skills-validation/2",
        "generated": datetime.now(timezone.utc).isoformat(),
        "validator": {"tool": "expanso-edge validate", "version": version},
        "disclaimer": (
            "Local validation only. It checks pipeline syntax, structure and component "
            "types. It does not run the orchestrator's submission validation and it is "
            "NOT evidence that a pipeline executes. No entry here may be promoted to "
            "verified-executed without a dated Expanso Cloud run record."
        ),
        "totals": {
            "skills": len(skills),
            "validates": passing,
            "fails_validation": len(skills) - passing,
            "variants": {
                variant: {
                    "pipelines": sum(
                        1 for s in skills.values() if variant in s["variants"]
                    ),
                    "validates": sum(
                        1
                        for s in skills.values()
                        if s["variants"].get(variant, {}).get("validates")
                    ),
                }
                for variant in VARIANTS
            },
        },
        "readiness_vocabulary": {
            READY_VALIDATED: (
                "Every pipeline variant passes local validation. Never executed end to end."
            ),
            READY_INVALID: (
                "At least one pipeline variant is rejected by the local validator at the "
                "recorded version; see `variants`."
            ),
            "verified-executed": "Reserved. Not in use; requires a Cloud run record.",
        },
        "skills": skills,
    }

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"

    if args.check:
        if not args.output.exists():
            print(f"{args.output} missing", file=sys.stderr)
            return 1
        existing = json.loads(args.output.read_text())
        existing.pop("generated", None)
        current = dict(report)
        current.pop("generated")
        if existing != current:
            print(f"{args.output} is out of date; regenerate it", file=sys.stderr)
            return 1
        print(f"validation report current: {passing}/{len(skills)} validate")
        return 0

    args.output.write_text(rendered)
    print(f"{passing}/{len(skills)} skills pass local validation ({version})")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
