# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Reject silent semantic feature loss in changed public examples."""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO = Path(__file__).resolve().parents[1]
EXCEPTIONS = REPO / "scripts" / "feature-preservation-exceptions.yaml"
PIPELINE_NAMES = {
    "pipeline.yaml",
    "pipeline-cli.yaml",
    "pipeline-mcp.yaml",
    "pipeline-cloud.yaml",
    "pipeline-query.yaml",
}
TRACKED_CATEGORIES = {
    "declared_input",
    "optional_input",
    "declared_output",
    "environment_control",
    "input_component",
    "output_component",
}


@dataclass(frozen=True, order=True)
class Feature:
    category: str
    name: str


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


def is_revision(value: str) -> bool:
    return bool(git("rev-parse", "--verify", value, check=False))


def resolve_base(explicit: str | None) -> str:
    if explicit:
        return git("rev-parse", explicit)

    before = os.environ.get("GITHUB_EVENT_BEFORE", "")
    if before and before != "0" * 40 and is_revision(before):
        return git("rev-parse", before)

    branch = git("branch", "--show-current", check=False)
    origin_main = git("rev-parse", "origin/main", check=False)
    head = git("rev-parse", "HEAD")
    if branch == "main" or (origin_main and origin_main == head):
        parent = git("rev-parse", "HEAD^", check=False)
        return parent or head

    for candidate in (
        f"origin/{os.environ.get('GITHUB_BASE_REF', '')}",
        "origin/main",
        "main",
    ):
        if candidate.endswith("/") or not is_revision(candidate):
            continue
        base = git("merge-base", "HEAD", candidate, check=False)
        if base:
            return base
    parent = git("rev-parse", "HEAD^", check=False)
    return parent or head


def changed_pipelines(base: str) -> list[Path]:
    names = git("diff", "--name-only", base, "HEAD", "--", "skills").splitlines()
    return sorted(
        REPO / name
        for name in names
        if Path(name).name in PIPELINE_NAMES and (REPO / name).is_file()
    )


def old_text(base: str, relative: str) -> str:
    return git("show", f"{base}:{relative}", check=False)


def load_yaml(text: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return value if isinstance(value, dict) else {}


def skill_features(skill_text: str) -> set[Feature]:
    document = load_yaml(skill_text)
    features: set[Feature] = set()
    for item in document.get("inputs", []):
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = str(item["name"])
        features.add(Feature("declared_input", name))
        if item.get("required") is False or "default" in item:
            features.add(Feature("optional_input", name))
    for item in document.get("outputs", []):
        if isinstance(item, dict) and item.get("name"):
            features.add(Feature("declared_output", str(item["name"])))
    for item in document.get("credentials", []):
        if isinstance(item, dict) and item.get("name"):
            features.add(Feature("environment_control", str(item["name"])))
    return features


def pipeline_features(pipeline_text: str, skill_text: str) -> set[Feature]:
    document = load_yaml(pipeline_text)
    features = skill_features(skill_text)
    config = document.get("config") if isinstance(document.get("config"), dict) else {}
    for kind in ("input", "output"):
        components = config.get(kind) if isinstance(config, dict) else None
        if isinstance(components, dict):
            for component in components:
                features.add(Feature(f"{kind}_component", str(component)))
    return features


def load_exceptions() -> list[dict[str, Any]]:
    document = load_yaml(EXCEPTIONS.read_text())
    rows = document.get("exceptions", [])
    if not isinstance(rows, list):
        raise RuntimeError("exceptions must be a list")
    return [row for row in rows if isinstance(row, dict)]


def exception_for(
    exceptions: list[dict[str, Any]],
    relative: str,
    feature: Feature,
) -> dict[str, Any] | None:
    for row in exceptions:
        if not fnmatch.fnmatch(relative, str(row.get("pipeline", ""))):
            continue
        if row.get("category") != feature.category:
            continue
        values = row.get("features", [])
        if isinstance(values, list) and feature.name in {
            str(value) for value in values
        }:
            return row
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git revision containing the prior examples")
    args = parser.parse_args()
    base = resolve_base(args.base)
    exceptions = load_exceptions()
    issues: list[str] = []
    used: set[tuple[int, str]] = set()
    relevant: set[tuple[int, str]] = set()
    pipelines = changed_pipelines(base)
    changed_names = {str(path.relative_to(REPO)) for path in pipelines}

    for path in pipelines:
        relative = str(path.relative_to(REPO))
        previous_pipeline = old_text(base, relative)
        if not previous_pipeline:
            continue
        skill_relative = str(path.parent.relative_to(REPO) / "skill.yaml")
        previous_skill = old_text(base, skill_relative)
        current_skill_path = REPO / skill_relative
        current_skill = (
            current_skill_path.read_text() if current_skill_path.is_file() else ""
        )
        previous = pipeline_features(previous_pipeline, previous_skill)
        current = pipeline_features(path.read_text(), current_skill)

        for row in exceptions:
            if not fnmatch.fnmatch(relative, str(row.get("pipeline", ""))):
                continue
            category = str(row.get("category", ""))
            features = row.get("features", [])
            if not isinstance(features, list):
                continue
            for name in features:
                if Feature(category, str(name)) in previous:
                    relevant.add((id(row), str(name)))

        for feature in sorted(previous - current):
            exception = exception_for(exceptions, relative, feature)
            if exception is None:
                issues.append(f"{relative}: removed {feature.category} {feature.name}")
                continue
            reason = str(exception.get("reason", "")).strip()
            replacement = str(exception.get("replacement", "")).strip()
            if len(reason) < 24 or not replacement:
                issues.append(
                    f"{relative}: incomplete exception for "
                    f"{feature.category} {feature.name}"
                )
                continue
            used.add((id(exception), feature.name))

    for row in exceptions:
        category = str(row.get("category", ""))
        pattern = str(row.get("pipeline", ""))
        if category not in TRACKED_CATEGORIES:
            continue
        if not any(fnmatch.fnmatch(path, pattern) for path in changed_names):
            continue
        features = row.get("features", [])
        if not isinstance(features, list):
            issues.append(f"invalid exception feature list: {pattern} {category}")
            continue
        for feature in features:
            key = (id(row), str(feature))
            if key in relevant and key not in used:
                issues.append(f"stale scoped exception: {pattern} {category} {feature}")

    if issues:
        print("Feature preservation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        print(
            f"{len(issues)} issue(s) across {len(pipelines)} changed pipelines",
            file=sys.stderr,
        )
        return 1

    print(
        f"Feature preservation passed: {len(pipelines)} changed pipelines, "
        f"{len(used)} documented semantic replacements (base {base[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
