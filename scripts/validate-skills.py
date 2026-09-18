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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Readiness vocabulary. Nothing here may reach `verified-executed`; that label is
# earned only by a dated Cloud run record with pinned versions, control-plane
# identifiers and a downstream receipt.
READY_VALIDATED = "validated-not-executed"
READY_INVALID = "invalid-does-not-validate"

# Two validators, two different questions. Keep them apart: a pipeline can be
# accepted as a job spec and still be semantically invalid.
#   expanso-cli job validate --offline  -> is this a well-formed JOB SPEC?
#   expanso-edge validate               -> is the inner PIPELINE CONFIG valid?
# The repository CI gate runs the first. Only the second catches unknown
# component fields, bloblang arity and type errors, so `job_spec_accepted`
# must never be reported as semantic validity.

# Every published pipeline variant is validated. A skill is only
# `validated-not-executed` when all of its variants validate. `cloud` is the
# input path a remotely scheduled node can satisfy on its own.
VARIANTS = {
    "cli": "pipeline-cli.yaml",
    "mcp": "pipeline-mcp.yaml",
    "cloud": "pipeline-cloud.yaml",
    # Recipes ship a single `pipeline.yaml` instead of the cli/mcp pair. They
    # were invisible to this report until this entry was added.
    "recipe": "pipeline.yaml",
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


def _normalise_errors(detail: str) -> str:
    """Make a validator message byte-stable without dropping any of it.

    The validator reports the same error SET every run (verified: identical
    hash over five runs) but in varying ORDER. The trailing "hint:" / "Error ="
    text follows whichever fragment happened to come last, so naively sorting
    the fragments moved that tail around and the message still differed run to
    run. Detach the tail, sort the fragments, then re-attach it.

    Every fragment and the tail are preserved; only their order is fixed.
    """
    marker = " - ("
    if marker not in detail:
        return detail

    head, _, rest = detail.partition(marker)
    fragments = rest.split(marker)

    # The tail belongs to the message, not to the last fragment.
    tail = ""
    for cue in (" hint: ", " Error = "):
        idx = fragments[-1].find(cue)
        if idx != -1:
            tail = fragments[-1][idx:] + tail
            fragments[-1] = fragments[-1][:idx]
            break

    return head + marker + marker.join(sorted(fragments)) + tail


def job_spec_accepted(path: Path) -> bool | None:
    """Job-spec acceptance via the validator the repository CI gate runs.

    This answers a DIFFERENT question from `validate()` above. It checks that the
    file is a well-formed job spec; it does NOT check the inner component
    configuration, so acceptance here is never semantic validity. Returns None
    when expanso-cli is unavailable, so a missing tool is never silently
    reported as acceptance.
    Timeouts and launch failures also return None: an unknown result is not a
    rejection.
    """
    cli = shutil.which("expanso-cli")
    if cli is None:
        return None
    try:
        res = subprocess.run(
            [cli, "job", "validate", str(path.relative_to(REPO)), "--offline"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.returncode == 0


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
    # The validator emits its individual errors in nondeterministic order, so
    # two runs over identical files produce different strings. Sort the error
    # fragments to make the stored report stable; otherwise `--check` reports
    # drift that is only reordering, and a flaky gate gets ignored.
    detail = _normalise_errors(detail)
    # Keep the whole diagnostic. Truncating here silently dropped error
    # fragments from files with several problems, which is the opposite of
    # what this report is for. The cap only guards against a runaway message.
    return False, detail[:4000]


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
    cli = shutil.which("expanso-cli")
    if cli is None and not args.check:
        print(
            "expanso-cli not found on PATH; refusing to write a report without "
            "job-spec results",
            file=sys.stderr,
        )
        return 1
    cli_version = tool_version(cli) if cli else "unavailable"
    skills: dict[str, dict] = {}
    skill_dirs = {p.parent for p in args.source.glob("*/*/pipeline-cli.yaml")}
    skill_dirs |= {p.parent for p in args.source.glob("*/*/pipeline.yaml")}
    name_counts = Counter(d.name for d in skill_dirs)
    for skill_dir in sorted(skill_dirs):
        # Keys stay bare skill names because docs/js/app.js looks entries up
        # that way; only a recipe sharing a name with a skill gets a
        # `recipes/` prefix. Any remaining clash fails rather than overwrites.
        key = skill_dir.name
        if name_counts[key] > 1 and skill_dir.parent.name == "recipes":
            key = f"recipes/{key}"
        if key in skills:
            print(
                f"report key collision: {key} ({skill_dir.relative_to(REPO)})",
                file=sys.stderr,
            )
            return 1
        variants: dict[str, dict] = {}
        for variant, filename in VARIANTS.items():
            pipeline = skill_dir / filename
            if not pipeline.exists():
                continue
            ok, detail = validate(binary, pipeline)
            result = {
                "pipeline": str(pipeline.relative_to(REPO)),
                "validates": ok,
                "job_spec_accepted": job_spec_accepted(pipeline),
                "readiness": READY_VALIDATED if ok else READY_INVALID,
            }
            if not ok:
                result["error"] = detail
            variants[variant] = result
        all_ok = all(v["validates"] for v in variants.values())
        skills[key] = {
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
        "job_spec_validator": {
            "tool": "expanso-cli job validate --offline",
            "version": cli_version,
        },
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
        "validators": {
            "pipeline_config": (
                "expanso-edge validate -- strict; decides `validates` and `readiness`"
            ),
            "job_spec": (
                "expanso-cli job validate --offline -- what the repository CI gate "
                "runs; decides `job_spec_accepted`. Acceptance here is NOT semantic "
                "validity: it does not check inner component configuration."
            ),
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
        current = json.loads(rendered)
        current.pop("generated")
        if cli is None:
            print(
                "expanso-cli not found on PATH; job-spec results not checked",
                file=sys.stderr,
            )
            for side in (existing, current):
                side.pop("job_spec_validator", None)
                for entry in side.get("skills", {}).values():
                    for result in entry.get("variants", {}).values():
                        result.pop("job_spec_accepted", None)
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
