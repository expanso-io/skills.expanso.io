# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Reject silent feature loss in changed public pipeline examples.

The check compares every changed published pipeline variant with the merge-base
version. It also reads the adjacent skill contract, because inputs, outputs and
credentials are published there even when the pipeline accesses them indirectly.
Intentional removals must be recorded as platform-realism replacements in
``feature-preservation-exceptions.yaml``. Each exception names the exact removed
feature and a replacement token that must exist in the current example.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

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
ENV_PATTERNS = (
    re.compile(r'env\(\s*["\']([A-Z][A-Z0-9_]*)["\']\s*\)'),
    re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}"),
)
ROOT_ASSIGN_PATTERN = re.compile(
    r"^\s*root((?:\.[A-Za-z_][A-Za-z0-9_-]*)+)\s*=",
)
ROOT_OBJECT_PATTERN = re.compile(
    r"^(?P<indent>\s*)root(?P<path>(?:\.[A-Za-z_][A-Za-z0-9_-]*)*)\s*=\s*\{",
)
OBJECT_KEY_PATTERN = re.compile(
    r"^(?P<indent>\s*)[\"'](?P<key>[A-Za-z_][A-Za-z0-9_-]*)[\"']\s*:\s*(?P<value>.*)$",
)
INLINE_KEY_PATTERN = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_-]*)[\"']\s*:")
META_ASSIGN_PATTERN = re.compile(r"^\s*meta\s+([A-Za-z_][A-Za-z0-9_-]*)\s*=")
GUARD_PATTERNS = (
    re.compile(r"(?:this|\$(?:input|request))\.([A-Za-z_][A-Za-z0-9_]*)\.or\("),
    re.compile(r"(?:this|\$(?:input|request))\.([A-Za-z_][A-Za-z0-9_]*)\s*(?:==|!=)\s*null"),
    re.compile(r"(?:this|\$(?:input|request))\.exists\([\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\)"),
)
PROTECTED_PATTERN = re.compile(
    r"(?i)(?:encrypt|cipher|redact|mask|pseudonym|tokeniz|anonym|hash|pii|secret)",
)


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


def resolve_base(explicit: str | None) -> str:
    if explicit:
        return git("rev-parse", explicit)
    candidates: list[str] = []
    if os.environ.get("GITHUB_BASE_REF"):
        candidates.append(f"origin/{os.environ['GITHUB_BASE_REF']}")
    candidates.extend(("origin/main", "main"))
    for candidate in candidates:
        if not git("rev-parse", "--verify", candidate, check=False):
            continue
        base = git("merge-base", "HEAD", candidate, check=False)
        if base:
            return base
    return git("rev-parse", "HEAD")


def changed_pipelines(base: str) -> list[Path]:
    names = git("diff", "--name-only", base, "--", "skills").splitlines()
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


def walk(value: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def mapping_texts(document: dict[str, Any]) -> Iterator[str]:
    for key, value in walk(document):
        if key == "mapping" and isinstance(value, str):
            yield value


def nested_mapping_texts(value: Any) -> list[str]:
    return [child for key, child in walk(value) if key == "mapping" and isinstance(child, str)]


def public_mapping_texts(document: dict[str, Any]) -> list[str]:
    config = document.get("config") if isinstance(document.get("config"), dict) else {}
    pipeline = config.get("pipeline") if isinstance(config, dict) else None
    processors = pipeline.get("processors") if isinstance(pipeline, dict) else None
    selected: list[str] = []
    if isinstance(processors, list):
        for processor in reversed(processors):
            mappings = nested_mapping_texts(processor)
            if mappings:
                selected.extend(mappings)
                break
    output = config.get("output") if isinstance(config, dict) else None
    if output is not None:
        selected.extend(nested_mapping_texts(output))
    return selected


def first_mapping_text(document: dict[str, Any]) -> str:
    config = document.get("config") if isinstance(document.get("config"), dict) else {}
    pipeline = config.get("pipeline") if isinstance(config, dict) else None
    processors = pipeline.get("processors") if isinstance(pipeline, dict) else None
    if not isinstance(processors, list):
        return ""
    for processor in processors:
        if isinstance(processor, dict) and isinstance(processor.get("mapping"), str):
            return str(processor["mapping"])
    return ""


def add_root_paths(features: set[Feature], mapping: str) -> None:
    stack: list[tuple[int, str]] = []
    for line in mapping.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()

        assignment = ROOT_ASSIGN_PATTERN.match(line)
        if assignment:
            path = assignment.group(1).lstrip(".")
            features.add(Feature("output_path", path))

        root_object = ROOT_OBJECT_PATTERN.match(line)
        if root_object:
            base = root_object.group("path").lstrip(".")
            if base:
                features.add(Feature("output_path", base))
            stack.append((indent, base))
            for key in INLINE_KEY_PATTERN.findall(stripped.split("{", 1)[1]):
                path = ".".join(part for part in (base, key) if part)
                features.add(Feature("output_path", path))
            continue

        object_key = OBJECT_KEY_PATTERN.match(line)
        if stack and object_key:
            base = stack[-1][1]
            key = object_key.group("key")
            path = ".".join(part for part in (base, key) if part)
            features.add(Feature("output_path", path))
            if object_key.group("value").lstrip().startswith("{"):
                stack.append((indent, path))


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


def pipeline_features(
    pipeline_text: str,
    skill_text: str,
    *,
    include_undeclared_guards: bool,
) -> set[Feature]:
    document = load_yaml(pipeline_text)
    features = skill_features(skill_text)
    config = document.get("config") if isinstance(document.get("config"), dict) else {}
    for kind in ("input", "output"):
        components = config.get(kind) if isinstance(config, dict) else None
        if isinstance(components, dict):
            for component in components:
                features.add(Feature(f"{kind}_component", str(component)))

    for pattern in ENV_PATTERNS:
        for name in pattern.findall(pipeline_text):
            features.add(Feature("environment_control", name))
    optional_inputs = {
        feature.name for feature in features if feature.category == "optional_input"
    }
    guard_text = first_mapping_text(document) if include_undeclared_guards else pipeline_text
    for pattern in GUARD_PATTERNS:
        for name in pattern.findall(guard_text):
            if include_undeclared_guards or name in optional_inputs:
                features.add(Feature("optional_guard", name))

    for mapping in public_mapping_texts(document):
        add_root_paths(features, mapping)

    for feature in tuple(features):
        if feature.category == "output_path" and feature.name.startswith("metadata."):
            features.add(Feature("metadata_field", feature.name.removeprefix("metadata.")))
        if PROTECTED_PATTERN.search(feature.name):
            features.add(Feature("protected_field", feature.name))
    return features


def named_fields(text: str) -> set[str]:
    fields = set(INLINE_KEY_PATTERN.findall(text))
    for path in re.findall(
        r"\broot((?:\.[A-Za-z_][A-Za-z0-9_-]*)+)\s*=",
        text,
    ):
        fields.update(path.lstrip(".").split("."))
    fields.update(META_ASSIGN_PATTERN.findall(text))
    return fields


def guard_present(text: str, name: str) -> bool:
    escaped = re.escape(name)
    patterns = (
        rf"(?:this|\$(?:input|request))\.{escaped}\.or\(",
        rf"(?:this|\$(?:input|request))\.{escaped}\s*(?:==|!=)\s*null",
        rf"(?:this|\$(?:input|request))\.exists\([\"']{escaped}[\"']\)",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def preserved_by_current_text(
    feature: Feature,
    current_features: set[Feature],
    current_text: str,
) -> bool:
    if feature in current_features:
        return True
    if feature.category == "optional_guard":
        return guard_present(current_text, feature.name)
    if feature.category not in {"output_path", "metadata_field", "protected_field"}:
        return False
    fields = named_fields(current_text)
    parts = feature.name.split(".")
    return all(part in fields for part in parts)


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
        if isinstance(values, list) and feature.name in {str(value) for value in values}:
            return row
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git revision containing the pre-sweep examples")
    args = parser.parse_args()
    base = resolve_base(args.base)
    exceptions = load_exceptions()
    missing: list[str] = []
    used_exception_features: set[tuple[int, str]] = set()
    pipelines = changed_pipelines(base)

    for path in pipelines:
        relative = str(path.relative_to(REPO))
        previous_pipeline = old_text(base, relative)
        if not previous_pipeline:
            continue
        skill_relative = str(path.parent.relative_to(REPO) / "skill.yaml")
        previous_skill = old_text(base, skill_relative)
        current_skill_path = REPO / skill_relative
        current_skill = current_skill_path.read_text() if current_skill_path.is_file() else ""
        include_undeclared_guards = "/recipes/" in f"/{relative}"
        previous = pipeline_features(
            previous_pipeline,
            previous_skill,
            include_undeclared_guards=include_undeclared_guards,
        )
        current_text = path.read_text()
        current = pipeline_features(
            current_text,
            current_skill,
            include_undeclared_guards=include_undeclared_guards,
        )
        test_path = path.parent / "test" / "test.yaml"
        public_mappings = public_mapping_texts(load_yaml(current_text))
        evidence_text = "\n".join(public_mappings)
        if any(
            re.search(r"^\s*root\s*=\s*(?:this|\$[A-Za-z_])", mapping, re.MULTILINE)
            for mapping in public_mappings
        ):
            evidence_text += "\n" + current_text
        evidence_text += "\n" + current_skill
        if test_path.is_file():
            evidence_text += "\n" + test_path.read_text()

        for feature in sorted(previous - current):
            if preserved_by_current_text(feature, current, evidence_text):
                continue
            exception = exception_for(exceptions, relative, feature)
            if exception is None:
                missing.append(f"{relative}: removed {feature.category} {feature.name}")
                continue
            reason = str(exception.get("reason", "")).strip()
            replacement = str(exception.get("replacement", "")).strip()
            if len(reason) < 24:
                missing.append(
                    f"{relative}: exception for {feature.category} {feature.name} lacks a specific reason"
                )
                continue
            if not replacement or replacement not in current_text + "\n" + current_skill:
                missing.append(
                    f"{relative}: exception for {feature.category} {feature.name} "
                    f"has missing replacement token {replacement!r}"
                )
                continue
            used_exception_features.add((id(exception), feature.name))

    for row in exceptions:
        features = row.get("features", [])
        if not isinstance(features, list):
            missing.append(
                "invalid exception feature list: "
                f"{row.get('pipeline')} {row.get('category')} {features}"
            )
            continue
        for feature in features:
            if (id(row), str(feature)) not in used_exception_features:
                missing.append(
                    "stale exception feature: "
                    f"{row.get('pipeline')} {row.get('category')} {feature}"
                )

    if missing:
        print("Feature preservation failed:", file=sys.stderr)
        for issue in missing:
            print(f"- {issue}", file=sys.stderr)
        print(
            f"{len(missing)} issue(s) across {len(pipelines)} changed pipelines",
            file=sys.stderr,
        )
        return 1

    print(
        f"Feature preservation passed: {len(pipelines)} changed pipelines, "
        f"{len(used_exception_features)} documented feature replacements"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
