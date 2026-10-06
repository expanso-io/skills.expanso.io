# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render linked Markdown validation reports from generated JSON evidence."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://skills.expanso.io"
SOURCE_URL = "https://github.com/expanso-io/skills.expanso.io/blob/main"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read {path}: {exc}") from exc


def status_cell(status: str, reason: str | None = None) -> str:
    if status in {"pass", "fixed"}:
        return "✅ pass"
    if status == "failing":
        return "❌ fail"
    detail = reason or status.replace("_", " ")
    return f"⏭️ skipped: {detail}"


def row_reason(row: dict[str, Any]) -> str | None:
    run = row.get("criteria", {}).get("runs", {})
    return run.get("reason") or row.get("reason")


def live_url(skill: str, category: str, pipeline: str) -> str:
    if category == "recipes":
        return f"{SITE_URL}/{skill}/{Path(pipeline).name}"
    return f"{SITE_URL}/skill/{skill}/"


def source_url(path: str) -> str:
    return f"{SOURCE_URL}/{path}"


def validation_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for skill in report.get("skills", {}).values():
        for variant in skill.get("variants", {}).values():
            result[str(variant.get("pipeline"))] = variant
    return result


def validation_text(result: dict[str, Any] | None) -> str:
    if result is None:
        return "⏭️ skipped: no validator row"
    if not result.get("validates"):
        return "❌ expanso-edge rejected"
    accepted = result.get("job_spec_accepted")
    if accepted is False:
        return "❌ job spec rejected"
    if accepted is None:
        return "⏭️ skipped: expanso-cli result unavailable"
    return "✅ both validators passed"


def render_table(
    rows: list[dict[str, Any]],
    validations: dict[str, dict[str, Any]],
) -> list[str]:
    lines = [
        "| Status | Example | Validation | Live page | Source |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        path = str(row["pipeline"])
        skill = str(row["skill"])
        lines.append(
            "| "
            + " | ".join(
                (
                    status_cell(str(row["status"]), row_reason(row)),
                    f"`{path}`",
                    validation_text(validations.get(path)),
                    f"[Live page]({live_url(skill, str(row['category']), path)})",
                    f"[Source]({source_url(path)})",
                )
            )
            + " |"
        )
    return lines


def render_fragment_table(fragments: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Status | Fragment | Complete pipeline | Live page | Source |",
        "|---|---|---|---|---|",
    ]
    for fragment in fragments:
        canonical = str(fragment["canonical_pipeline"])
        skill = str(fragment["skill"])
        source = str(fragment["source"])
        category = str(fragment["category"])
        lines.append(
            "| "
            + " | ".join(
                (
                    status_cell(
                        str(fragment["status"]),
                        str(fragment.get("reason") or "canonical context skipped"),
                    ),
                    f"`{fragment['fragment']}`",
                    f"[Complete pipeline]({source_url(canonical)})",
                    f"[Live page]({live_url(skill, category, canonical)})",
                    f"[Source]({source_url(source)})",
                )
            )
            + " |"
        )
    return lines


def check_url(url: str) -> str | None:
    request = Request(url, method="HEAD", headers={"User-Agent": "skills-ci"})
    try:
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                return f"{url}: HTTP {response.status}"
    except HTTPError as exc:
        if exc.code == 405:
            try:
                with urlopen(
                    Request(url, headers={"User-Agent": "skills-ci"}),
                    timeout=30,
                ) as response:
                    if response.status == 200:
                        return None
            except (HTTPError, URLError, TimeoutError) as retry_exc:
                return f"{url}: {retry_exc}"
        return f"{url}: HTTP {exc.code}"
    except (URLError, TimeoutError) as exc:
        return f"{url}: {exc}"
    return None


def check_live_pages(urls: set[str]) -> None:
    urls = sorted(urls)
    with ThreadPoolExecutor(max_workers=12) as executor:
        errors = [error for error in executor.map(check_url, urls) if error]
    if errors:
        raise RuntimeError("dead live page links:\n" + "\n".join(errors))
    print(f"Live page links return 200: {len(urls)}")


def report_text(
    validation: dict[str, Any],
    conformance: dict[str, Any],
) -> str:
    examples = [
        row
        for row in conformance.get("examples", [])
        if row.get("status") != "pulled"
    ]
    fragments = list(conformance.get("fragments", []))
    date = str(validation.get("generated", ""))[:10]
    if len(date) != 10:
        raise RuntimeError("validation report has no generated date")
    validations = validation_index(validation)
    edge_version = validation.get("validator", {}).get("version", "unknown")
    cli_version = validation.get("job_spec_validator", {}).get(
        "version", "unknown"
    )
    lines = [
        f"# Pipeline validation report: {date}",
        "",
        f"Validators: `expanso-edge validate` reported `{edge_version}`; "
        f"`expanso-cli job validate --offline` reported `{cli_version}`. A pass "
        "means the published job spec and inner pipeline both validate. "
        "Execution evidence is recorded separately in "
        "`example-conformance.json`.",
        "",
        "## Complete pipelines",
        "",
        *render_table(examples, validations),
        "",
        "## Fragments",
        "",
        "Fragments are supporting code shown beside a complete pipeline. Their "
        "status comes from the linked complete pipeline, where the fragment has "
        "the context it needs.",
        "",
        *render_fragment_table(fragments),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation",
        type=Path,
        default=ROOT / "validation-report.json",
    )
    parser.add_argument(
        "--conformance",
        type=Path,
        default=ROOT / "example-conformance.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports" / "validation",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-live-check", action="store_true")
    args = parser.parse_args()

    try:
        validation = load_json(args.validation)
        conformance = load_json(args.conformance)
        content = report_text(validation, conformance)
        date = str(validation["generated"])[:10]
        outputs = (args.output_dir / f"{date}.md", args.output_dir / "latest.md")
        if not args.skip_live_check:
            urls = {
                live_url(
                    str(row["skill"]),
                    str(row["category"]),
                    str(row["pipeline"]),
                )
                for row in conformance.get("examples", [])
                if row.get("status") != "pulled"
            }
            check_live_pages(urls)
        if args.check:
            stale = [path for path in outputs if not path.exists() or path.read_text() != content]
            if stale:
                raise RuntimeError(
                    "validation report is stale: "
                    + ", ".join(str(path.relative_to(ROOT)) for path in stale)
                )
            print(f"Validation Markdown report current: {date}")
            return 0
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for output in outputs:
            output.write_text(content)
            print(f"Wrote {output.relative_to(ROOT)}")
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
