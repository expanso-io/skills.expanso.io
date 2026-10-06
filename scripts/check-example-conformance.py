# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Fail closed when a published pipeline is invalid or a platform shape is unsafe."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

import yaml


REPO = Path(__file__).resolve().parents[1]
PIPELINE_NAMES = {
    "pipeline.yaml",
    "pipeline-cli.yaml",
    "pipeline-mcp.yaml",
    "pipeline-cloud.yaml",
    "pipeline-query.yaml",
}
KNOWN_AUTH_SERVICES = (
    "api.github.com",
    "api.openai.com",
    "api.slack.com",
    "hooks.slack.com",
    "api.stripe.com",
    "googleapis.com",
    "atlassian.net",
    "todoist.com",
    "elasticsearch",
)
FAKE_SUCCESS_PATTERNS = (
    ("simulated behavior", re.compile(r"(?i)\bsimulat(?:e|ed|ion)\b")),
    (
        "placeholder sample result",
        re.compile(
            r"(?i)\bsample\s+(?:metrics|data|task|issue|transcription|result|response)s?\b"
        ),
    ),
    ("provider call left for later", re.compile(r"(?i)replace with .*\bapi\b")),
    ("production-only behavior", re.compile(r"(?i)production would")),
    ("invented AI output", re.compile(r"(?i)generate a plausible")),
    (
        "unimplemented side effect",
        re.compile(r"(?i)\bwould (?:call|fetch|send|transcribe|create|deploy)\b"),
    ),
    ("hard-coded passing tests", re.compile(r"(?i)tests_passed\s*[:=]\s*true")),
    (
        "hard-coded successful CI",
        re.compile(r"(?i)ci_status\s*[:=]\s*[\"']?success"),
    ),
)
PUBLISHED_TEXT_ROOTS = (
    REPO / "README.md",
    REPO / "skills",
    REPO / "plugin",
)
INVALID_COMMAND_PATTERNS = (
    (
        "expanso-edge cannot run a pipeline path",
        re.compile(r"\bexpanso-edge\s+run\s+(?:<pipeline>|[^\s`]*pipeline[^\s`]*)"),
    ),
    (
        "obsolete expanso run command",
        re.compile(r"\bexpanso\s+run\s+-c\b"),
    ),
    (
        "expanso-cli deploy cannot fetch an HTTPS URL",
        re.compile(r"\bexpanso-cli\s+job\s+deploy\s+https?://"),
    ),
)
EXPLANATORY_COMMAND_PHRASES = (
    "there is no",
    "no supported",
    "does not run",
    "cannot run",
)


def pipeline_files() -> list[Path]:
    return sorted(
        path
        for path in (REPO / "skills").glob("*/*/pipeline*.yaml")
        if path.name in PIPELINE_NAMES
    )


def walk(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, (*path, str(index)))


def component_context(path: tuple[str, ...]) -> str:
    return ".".join(path) or "root"


def check_kafka(path: Path, where: tuple[str, ...], config: Any) -> list[str]:
    if not isinstance(config, dict):
        return [f"{path}: {component_context(where)} must be a mapping"]
    issues: list[str] = []
    addresses = config.get("addresses")
    rendered_addresses = json.dumps(addresses)
    if not addresses or "KAFKA_BROKERS" not in rendered_addresses:
        issues.append(f"{path}: {component_context(where)} must use KAFKA_BROKERS")
    if "localhost" in rendered_addresses or ":9092" in rendered_addresses:
        issues.append(
            f"{path}: {component_context(where)} has an insecure localhost Kafka default"
        )
    tls = config.get("tls")
    if not isinstance(tls, dict) or tls.get("enabled") is not True:
        issues.append(f"{path}: {component_context(where)} must enable Kafka TLS")
    sasl = config.get("sasl")
    if not isinstance(sasl, dict):
        issues.append(f"{path}: {component_context(where)} must configure Kafka SASL")
    else:
        if sasl.get("mechanism") not in {"SCRAM-SHA-256", "SCRAM-SHA-512"}:
            issues.append(
                f"{path}: {component_context(where)} must use a SCRAM SASL mechanism"
            )
        if not sasl.get("user") or not sasl.get("password"):
            issues.append(
                f"{path}: {component_context(where)} must provide SASL user and password"
            )
    if "topic" in config and config.get("ack_replicas") is not True:
        issues.append(
            f"{path}: {component_context(where)} output must require replica acknowledgements"
        )
    return issues


def check_s3(path: Path, where: tuple[str, ...], config: Any) -> list[str]:
    if not isinstance(config, dict):
        return [f"{path}: {component_context(where)} must be a mapping"]
    issues: list[str] = []
    bucket = str(config.get("bucket", ""))
    region = str(config.get("region", ""))
    if "${" not in bucket:
        issues.append(f"{path}: {component_context(where)} bucket must be configured")
    if "AWS_REGION" not in region:
        issues.append(f"{path}: {component_context(where)} must set AWS_REGION")
    if "path" in config and not config.get("server_side_encryption"):
        issues.append(
            f"{path}: {component_context(where)} output must enable server-side encryption"
        )
    return issues


def check_http(path: Path, where: tuple[str, ...], config: Any) -> list[str]:
    if not isinstance(config, dict):
        return []
    url = str(config.get("url", ""))
    if not url:
        return []
    issues: list[str] = []
    lowered = url.lower()
    if lowered.startswith("http://") and not lowered.startswith(
        ("http://127.0.0.1", "http://localhost")
    ):
        issues.append(f"{path}: {component_context(where)} must use HTTPS")
    if "example.com" in lowered:
        issues.append(f"{path}: {component_context(where)} uses a placeholder service URL")
    if any(service in lowered for service in KNOWN_AUTH_SERVICES):
        headers = config.get("headers")
        auth = headers.get("Authorization") if isinstance(headers, dict) else None
        if not auth:
            issues.append(
                f"{path}: {component_context(where)} service call must authenticate"
            )
    return issues


def platform_issues(path: Path) -> list[str]:
    text = path.read_text()
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}: YAML parse failed: {exc}"]
    issues: list[str] = []
    for where, value in walk(document):
        if not where:
            continue
        key = where[-1]
        if key == "kafka":
            issues.extend(check_kafka(path, where, value))
        elif key == "aws_s3":
            issues.extend(check_s3(path, where, value))
        elif key in {"http", "http_client"}:
            issues.extend(check_http(path, where, value))
        elif key == "dsn" and isinstance(value, str):
            if value.startswith("postgres://") and not (
                "sslmode=verify-full" in value or "POSTGRES_TLS_DSN" in value
            ):
                issues.append(
                    f"{path}: {component_context(where)} must require verified PostgreSQL TLS"
                )

    if re.search(r"(?i)(gdpr|pci(?:-dss)?|hipaa)[ -]?(?:compliant|compliance)", text):
        issues.append(f"{path}: makes an unprovable regulatory compliance claim")
    secret_defaults = re.findall(
        r'env\("([^\"]+)"\)\.or\("([^\"]+)"\)',
        text,
        flags=re.IGNORECASE,
    )

    def is_secret_name(name: str) -> bool:
        upper = name.upper()
        if upper in {"KEY_ID", "KEY_VERSION"} or upper.endswith("_TYPES"):
            return False
        return any(
            upper.endswith(f"_{marker}") or f"_{marker}_" in upper
            for marker in ("KEY", "PASSWORD", "SALT", "SECRET", "TOKEN")
        )

    if any(is_secret_name(name) for name, _ in secret_defaults):
        issues.append(f"{path}: security secret has a built-in default")
    if re.search(r"\$\{!\s*root\.", text):
        issues.append(f"{path}: interpolation reads the unavailable root context")
    if re.search(r'root\s*=\s*if[^\n]*(?:\n.*){0,8}else\s*\{\s*""\s*\}', text):
        issues.append(f"{path}: validation initializes root as a string")
    title = " ".join(
        str(document.get(key, ""))
        for key in ("name", "description")
        if isinstance(document, dict)
    ).lower()
    if "webhook" in title and "http_server:" in text and "hmac_" not in text:
        issues.append(f"{path}: webhook input lacks HMAC verification")

    names_platform = any(
        marker in text.lower()
        for marker in ("kafka", "aws_s3", "gcp_bigquery", "gcp_cloud_storage")
    )
    if names_platform:
        for where, value in walk(document):
            if where and where[-1] == "file" and isinstance(value, dict):
                file_path = str(value.get("path", ""))
                if file_path.startswith(("/tmp/", "./")):
                    issues.append(
                        f"{path}: {component_context(where)} fallback is not persistent"
                    )
    return issues


def behavior_issues(path: Path) -> list[str]:
    """Reject known fake-success shapes and cross-cutting runtime traps."""
    text = path.read_text()
    issues: list[str] = []
    for label, pattern in FAKE_SUCCESS_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            issues.append(f"{path}: line {line} contains {label}")

    # A capability-gap example may say "not implemented" only when it returns
    # an explicit unsupported status and structured evidence. This allows
    # honest gaps without allowing a pretend successful migration or deploy.
    gap_text = re.sub(
        r'["\']501["\']\s*:\s*["\']Not Implemented["\']',
        "",
        text,
        flags=re.IGNORECASE,
    )
    if re.search(r"(?i)not[_ -]implemented", gap_text):
        explicit_gap = (
            re.search(r"status[^\n]{0,40}unsupported", text, re.IGNORECASE)
            and "capability_gap" in text
        )
        if not explicit_gap:
            issues.append(
                f"{path}: not-implemented behavior lacks unsupported capability-gap evidence"
            )

    if re.search(r'"trace_id"\s*:\s*meta\("trace_id"\)(?!\.or)', text):
        issues.append(f"{path}: trace_id can be null in the mapping that creates it")
    if re.search(
        r"let\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*content\(\)\s*$",
        text,
        re.MULTILINE,
    ):
        issues.append(
            f"{path}: text processing uses raw bytes; call content().string() explicitly"
        )
    return issues


def published_text_files() -> Iterator[Path]:
    for root in PUBLISHED_TEXT_ROOTS:
        if root.is_file():
            yield root
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {
                ".md",
                ".yaml",
                ".yml",
                ".sh",
            }:
                yield path


def command_issues() -> list[str]:
    """Reject CLI forms known to be unrunnable, including in copied snippets."""
    issues: list[str] = []
    for path in published_text_files():
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            lowered = line.lower()
            for label, pattern in INVALID_COMMAND_PATTERNS:
                if not pattern.search(line):
                    continue
                if any(phrase in lowered for phrase in EXPLANATORY_COMMAND_PHRASES):
                    continue
                issues.append(
                    f"{path.relative_to(REPO)}: line {line_number} contains {label}"
                )
    return issues


def validation_issues(files: list[Path]) -> list[str]:
    binary = shutil.which("expanso-edge")
    if binary is None:
        return ["expanso-edge is required; validation cannot be skipped"]
    result = subprocess.run(
        [binary, "validate", "--output", "json", *[str(p.relative_to(REPO)) for p in files]],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [f"expanso-edge returned unreadable output: {result.stdout} {result.stderr}"]
    return [
        f"{row.get('source')}: {row.get('errors', 'validation failed')}"
        for row in rows
        if not row.get("valid")
    ]


def main() -> int:
    files = pipeline_files()
    if not files:
        print("No published pipelines found", file=sys.stderr)
        return 1
    issues = validation_issues(files)
    for path in files:
        issues.extend(platform_issues(path))
        issues.extend(behavior_issues(path))
    issues.extend(command_issues())
    if issues:
        print("Example conformance failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"Example conformance passed: {len(files)} pipelines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
