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
ENV_PLACEHOLDER_PATTERN = re.compile(
    r"\$\{([A-Z][A-Z0-9_]*)(?::[^}]*)?\}"
)
ENV_CALL_PATTERN = re.compile(r'env\("([A-Z][A-Z0-9_]*)"\)')


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


def metadata_names(entries: Any) -> set[str]:
    if not isinstance(entries, list):
        return set()
    return {
        str(entry.get("name"))
        for entry in entries
        if isinstance(entry, dict) and entry.get("name")
    }


def job_security_metadata_issues(
    path: Path,
    document: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Match job security metadata to executable authentication and TLS."""
    if path.parents[1].name != "jobs":
        return []
    metadata_path = path.parent / "skill.yaml"
    if metadata is None:
        if not metadata_path.exists():
            return [f"{path}: authenticated job has no skill metadata"]
        metadata = yaml.safe_load(metadata_path.read_text())
    if not isinstance(metadata, dict):
        return [f"{metadata_path}: metadata must be a mapping"]

    transmitted: set[str] = set()
    for where, value in walk(document):
        if (
            where
            and where[-1].lower() == "authorization"
            and isinstance(value, str)
        ):
            transmitted.update(ENV_PLACEHOLDER_PATTERN.findall(value))
    text = path.read_text()
    local_auth = set(ENV_CALL_PATTERN.findall(text)) if "hmac_" in text else set()
    actual = transmitted | local_auth
    uses_verified_tls = "sslmode=verify-full" in text
    if not actual and not uses_verified_tls:
        return []

    issues: list[str] = []
    dependencies = metadata.get("dependencies")
    dependencies = dependencies if isinstance(dependencies, dict) else {}
    network = dependencies.get("network_egress")
    network = network if isinstance(network, dict) else {}
    proof = metadata.get("proof")
    proof = proof if isinstance(proof, dict) else {}
    if actual:
        declared = metadata_names(metadata.get("credentials"))
        missing = sorted(actual - declared)
        if missing:
            issues.append(
                f"{metadata_path}: authentication credentials are not declared: {missing}"
            )
        declared_transmitted = metadata_names(
            dependencies.get("credentials_transmitted")
        )
        if declared_transmitted != transmitted:
            issues.append(
                f"{metadata_path}: transmitted credentials "
                f"{sorted(declared_transmitted)} do not match Authorization fields "
                f"{sorted(transmitted)}"
            )
        endpoints = network.get("endpoints")
        endpoints = endpoints if isinstance(endpoints, list) else []
        protocols = {
            str(endpoint.get("protocol", "")).lower()
            for endpoint in endpoints
            if isinstance(endpoint, dict)
        }
        if transmitted and protocols != {"https"}:
            issues.append(
                f"{metadata_path}: authenticated receiver metadata must require HTTPS"
            )
        if (
            proof.get("authentication_matches_current") is True
            and not isinstance(proof.get("authentication_execution"), dict)
        ):
            issues.append(
                f"{metadata_path}: current authentication claim lacks execution evidence"
            )
    if uses_verified_tls:
        tls = network.get("tls")
        if not isinstance(tls, dict) or tls.get("required") is not True:
            issues.append(
                f"{metadata_path}: verified database TLS is not declared"
            )
        if (
            proof.get("tls_matches_current") is True
            and not isinstance(proof.get("tls_execution"), dict)
        ):
            issues.append(
                f"{metadata_path}: current TLS claim lacks execution evidence"
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
        document = yaml.safe_load(path.read_text())
        if isinstance(document, dict):
            issues.extend(job_security_metadata_issues(path, document))
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
