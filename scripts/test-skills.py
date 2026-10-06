# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Run Expanso skill tests in local Edge mode.

Usage:
  uv run -s scripts/test-skills.py [skill_name ...]
  uv run -s scripts/test-skills.py --limit-skills 10
  uv run -s scripts/test-skills.py --limit-tests 10
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import hmac
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
CONFORMANCE_DIR = REPO_ROOT / ".conformance"
HARNESS_MCP_BEARER_TOKEN = "expanso-harness-mcp-token-32-chars"


class DupKeyLoader(yaml.SafeLoader):
    """YAML loader that merges duplicate keys into lists for known fields."""

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            value = self.construct_object(value_node, deep=deep)
            if key in mapping:
                if key in {"has_field", "metadata_has", "extracted_contains", "analysis_has", "command_contains"}:
                    if not isinstance(mapping[key], list):
                        mapping[key] = [mapping[key]]
                    mapping[key].append(value)
                else:
                    # Preserve duplicates as list for visibility
                    if not isinstance(mapping[key], list):
                        mapping[key] = [mapping[key]]
                    mapping[key].append(value)
            else:
                mapping[key] = value
        return mapping


@dataclass
class EdgeProcess:
    api_url: str
    data_dir: Path
    log_file: Path
    env: dict[str, str] | None = None
    edge_bin: str | None = None
    process: subprocess.Popen | None = None

    def start(self) -> None:
        expanso_edge = self.edge_bin or os.environ.get("EXPANSO_EDGE_BIN") or shutil.which("expanso-edge")
        if not expanso_edge:
            raise RuntimeError("expanso-edge not found in PATH")

        env = os.environ.copy()
        env.setdefault("MCP_BEARER_TOKEN", HARNESS_MCP_BEARER_TOKEN)
        if self.env:
            env.update(self.env)

        cmd = [
            expanso_edge,
            "run",
            "--local",
            "--no-watch",
            "--api-listen",
            self.api_url.replace("http://", ""),
            "--data-dir",
            str(self.data_dir),
            "--log-level",
            "warn",
        ]
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = open(self.log_file, "w")
        self.process = subprocess.Popen(cmd, stdout=log_handle, stderr=log_handle, env=env)

    def stop(self) -> None:
        if not self.process:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None


def load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with open(path, "r") as f:
        return yaml.load(f, Loader=DupKeyLoader)  # type: ignore[arg-type]


def find_skills(names: list[str] | None) -> list[Path]:
    skill_dirs = []
    for category in sorted(SKILLS_DIR.iterdir()):
        if not category.is_dir():
            continue
        for skill in sorted(category.iterdir()):
            if not skill.is_dir():
                continue
            if not (skill / "skill.yaml").exists():
                continue
            if names and skill.name not in names:
                continue
            skill_dirs.append(skill)
    return skill_dirs


def cache_key(category: str, skill_name: str, test_name: str | None) -> str:
    return f"{category}/{skill_name}:{test_name or ''}"


def load_previous_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def build_cache_index(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    index: dict[str, dict[str, Any]] = {}
    for skill in report.get("skills", []) if isinstance(report, dict) else []:
        category = skill.get("category") or ""
        name = skill.get("name") or ""
        for test in skill.get("tests", []) or []:
            key = cache_key(category, name, test.get("name"))
            index[key] = test
    return index


def hash_bytes(*parts: bytes) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part)
    return h.hexdigest()


def tool_evidence(binary: str) -> dict[str, str]:
    resolved = Path(binary).resolve()
    version = subprocess.run(
        [str(resolved), "version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "path": str(resolved),
        "version": (version.stdout or version.stderr).strip(),
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def compute_test_fingerprint(
    skill_dir: Path,
    pipeline_path: Path,
    variant: str,
    test: dict[str, Any],
    input_value: str,
    env_overrides: dict[str, Any],
    provider_responses: list[Any],
    ai_responses: list[Any],
    mock_openai: bool,
    harness_hash: str,
) -> str:
    h = hashlib.sha256()
    for path in (
        pipeline_path,
        skill_dir / "skill.yaml",
        skill_dir / "test" / "test.yaml",
    ):
        if path.exists():
            h.update(path.read_bytes())
    h.update(json.dumps(test, sort_keys=True, default=str).encode())
    h.update(str(input_value).encode())
    h.update(json.dumps(env_overrides, sort_keys=True, default=str).encode())
    h.update(json.dumps(provider_responses, sort_keys=True, default=str).encode())
    h.update(json.dumps(ai_responses, sort_keys=True, default=str).encode())
    h.update(b"mock_openai=1" if mock_openai else b"mock_openai=0")
    h.update(f"variant={variant}".encode())
    h.update(harness_hash.encode())
    return h.hexdigest()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(port: int, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def wait_for_api(endpoint: str, timeout: float = 10.0) -> bool:
    expanso_cli = os.environ.get("EXPANSO_CLI_BIN") or shutil.which("expanso-cli")
    if not expanso_cli:
        raise RuntimeError("expanso-cli not found in PATH")
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            [expanso_cli, "job", "list", "--endpoint", endpoint],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return True
        time.sleep(0.3)
    return False


def generate_command(instruction: str, shell: str) -> str:
    inst = instruction.lower()
    shell = (shell or "bash").lower()
    if "find" in inst and ("python" in inst or ".py" in inst):
        return 'find . -name "*.py"'
    if "disk" in inst and "usage" in inst:
        return "du -sh ."
    if shell == "powershell":
        return "Get-Process"
    return 'echo "mock command"'


def placeholder_for_key(key: str, instruction: str = "", shell: str = "") -> Any:
    key_lower = key.lower()
    if key_lower == "name":
        return "John Doe"
    if key_lower == "email":
        return "john@example.com"
    if key_lower == "phone":
        return "555-123-4567"
    if key_lower == "address":
        return "123 Main St"
    if key_lower == "date":
        return "2026-01-15"
    if key_lower == "amount":
        return "99.99"
    if key_lower == "company":
        return "Acme Corp"
    if key_lower == "summary":
        return "- Mock summary line 1\n- Mock summary line 2"
    if key_lower == "explanation":
        return "Mock explanation"
    if key_lower == "command":
        return generate_command(instruction, shell)
    if key_lower == "sql":
        return "SELECT 1;"
    if key_lower == "dialect":
        return "generic"
    if key_lower == "language":
        return "English"
    if key_lower == "code":
        return "en"
    if key_lower == "confidence":
        return 0.9
    if key_lower == "score":
        return 0.1
    if key_lower == "label":
        return "neutral"
    if key_lower == "flagged":
        return False
    if key_lower == "reasoning":
        return "Mock reasoning"
    if key_lower == "categories":
        return {
            "violence": False,
            "sexual": False,
            "hate": False,
            "self_harm": False,
            "illegal": False,
            "dangerous": False,
        }
    if key_lower == "scores":
        return {
            "violence": 0.0,
            "sexual": 0.0,
            "hate": 0.0,
            "self_harm": 0.0,
            "illegal": 0.0,
            "dangerous": 0.0,
        }
    if key_lower == "entities":
        return [{"text": "Mock", "type": "ORG", "start": 0, "end": 4}]
    if key_lower in {"topics", "keywords"}:
        return ["mock"]
    return "mock"


def build_findings(count: int, kind: str) -> list[dict[str, Any]]:
    if count <= 0:
        return []

    findings = []
    for idx in range(count):
        if kind == "secrets":
            findings.append({
                "type": "api_key",
                "value": f"mock-secret-{idx}",
                "line": idx + 1,
                "severity": "high",
            })
        else:
            findings.append({
                "type": "email",
                "value": f"mock{idx}@example.com",
                "start": 0,
                "end": 10,
                "confidence": 0.9,
            })
    return findings


def mapping_uses_parse_json(processors: list[dict[str, Any]], start_idx: int) -> bool:
    for proc in processors[start_idx + 1:]:
        if "mapping" in proc:
            return "parse_json" in proc.get("mapping", "")
        if any(key.startswith("openai_") for key in proc.keys()):
            return False
    return False


def command_from_tokens(tokens: list[str], instruction: str) -> str:
    lowered = [t.lower() for t in tokens]
    if "find" in lowered and any(".py" in t for t in tokens):
        return 'find . -name "*.py"'
    if "du" in lowered:
        return "du -sh ."
    if any("process" in t.lower() for t in tokens):
        return "Get-Process"
    return generate_command(instruction, "bash")


def build_json_payload_from_expected(expected: dict[str, Any], instruction: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    extracted = expected.get("extracted_contains")
    if extracted:
        for key in extracted:
            payload[key] = placeholder_for_key(key)

    analysis_keys = expected.get("analysis_has")
    if analysis_keys:
        for key in analysis_keys:
            if key == "sentiment":
                payload[key] = {"label": "neutral", "score": 0.5, "explanation": "Mock sentiment"}
            elif key == "entities":
                payload[key] = placeholder_for_key("entities")
            elif key == "topics":
                payload[key] = placeholder_for_key("topics")
            elif key == "keywords":
                payload[key] = placeholder_for_key("keywords")
            else:
                payload[key] = "mock"

    command_tokens = expected.get("command_contains")
    if command_tokens:
        payload["command"] = command_from_tokens(command_tokens, instruction)
        payload.setdefault("explanation", "Mock explanation")

    explanation_tokens = expected.get("explanation_contains")
    if explanation_tokens:
        payload["explanation"] = " ".join(explanation_tokens)

    has_field = expected.get("has_field")
    allowed_keys = {
        "corrected",
        "issues",
        "score",
        "label",
        "confidence",
        "language",
        "code",
        "command",
        "explanation",
        "sql",
        "dialect",
        "flagged",
        "categories",
        "scores",
        "reasoning",
    }
    if has_field:
        fields = has_field if isinstance(has_field, list) else [has_field]
        for field in fields:
            if field in allowed_keys:
                payload.setdefault(field, placeholder_for_key(field, instruction))

    if "has_pii" in expected or "has_secrets" in expected or "findings_length" in expected:
        has_pii = expected.get("has_pii")
        has_secrets = expected.get("has_secrets")
        findings_length = expected.get("findings_length")
        if findings_length is None:
            findings_length = 1 if (has_pii or has_secrets) else 0
        kind = "secrets" if has_secrets else "pii"
        payload.setdefault("findings", build_findings(int(findings_length), kind))
        payload.setdefault("summary", "Mock summary")

    if payload:
        return payload

    return {"result": "mock"}


def mock_content_for_test(skill_name: str, expected: dict[str, Any], instruction: str, expects_json: bool) -> str:
    if expects_json:
        payload = build_json_payload_from_expected(expected, instruction)
        return json.dumps(payload)

    if expected.get("summary_contains_bullets"):
        return "- Mock summary line 1\n- Mock summary line 2"

    explanation_tokens = expected.get("explanation_contains")
    if explanation_tokens:
        return " ".join(explanation_tokens)

    if "transcribe" in skill_name:
        return "Mock transcript."
    if "image" in skill_name or "caption" in skill_name or "alttext" in skill_name:
        return "Mock image description."
    if "summarize" in skill_name:
        return "- Mock summary line 1\n- Mock summary line 2"

    if instruction:
        return f"Mock response: {instruction[:200]}".strip()
    return "Mock response."


def apply_openai_mocks(
    processors: list[dict[str, Any]],
    skill_name: str,
    expected: dict[str, Any],
    instruction: str,
    responses: list[Any] | None = None,
    response_index: list[int] | None = None,
) -> None:
    structured_response_skills = {
        "json-extract",
        "pii-detect",
        "secrets-scan",
        "text-analyze",
        "text-to-command",
    }
    response_values = responses or []
    index = response_index or [0]

    def next_response(default: Any) -> Any:
        if not response_values:
            return default
        response = response_values[min(index[0], len(response_values) - 1)]
        index[0] += 1
        return response

    for idx, proc in enumerate(processors):
        if "openai_chat_completion" in proc:
            expects_json = (
                mapping_uses_parse_json(processors, idx)
                or skill_name in structured_response_skills
            )
            default_content = mock_content_for_test(
                skill_name, expected, instruction, expects_json
            )
            response = next_response(default_content)
            content = response if isinstance(response, str) else json.dumps(response)
            literal = json.dumps(content)
            mapping = (
                "root = {\"choices\": [{\"message\": {\"content\": "
                + literal +
                "}}]}"
            )
            processors[idx] = {"mapping": mapping}
        elif "openai_image_generation" in proc:
            response = next_response(
                {"data": [{"url": "https://example.com/mock.png", "revised_prompt": "mock prompt"}]}
            )
            processors[idx] = {"mapping": f"root = {json.dumps(response)}"}
        elif "openai_embeddings" in proc:
            response = next_response(
                {"data": [{"embedding": [0.0, 0.0, 0.0, 0.0]}]}
            )
            processors[idx] = {"mapping": f"root = {json.dumps(response)}"}
        elif "openai_speech" in proc:
            response = next_response("MOCK_AUDIO")
            processors[idx] = {"mapping": f"root = {json.dumps(str(response))}"}
        elif "openai_transcription" in proc:
            response = next_response("Mock transcript.")
            processors[idx] = {"mapping": f"root = {json.dumps(str(response))}"}
        else:
            # AI processors can be nested under switch, branch, try/catch,
            # and other processor containers. Walk every nested processor
            # list so tests never initialize a live provider accidentally.
            for value in proc.values():
                apply_openai_mocks_nested(
                    value,
                    skill_name,
                    expected,
                    instruction,
                    response_values,
                    index,
                )


def apply_openai_mocks_nested(
    value: Any,
    skill_name: str,
    expected: dict[str, Any],
    instruction: str,
    responses: list[Any],
    response_index: list[int],
) -> None:
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            apply_openai_mocks(
                value,
                skill_name,
                expected,
                instruction,
                responses,
                response_index,
            )
        else:
            for item in value:
                apply_openai_mocks_nested(
                    item,
                    skill_name,
                    expected,
                    instruction,
                    responses,
                    response_index,
                )
    elif isinstance(value, dict):
        for nested in value.values():
            apply_openai_mocks_nested(
                nested,
                skill_name,
                expected,
                instruction,
                responses,
                response_index,
            )


def apply_provider_mocks(
    processors: list[dict[str, Any]],
    responses: list[Any],
    response_index: list[int] | None = None,
) -> None:
    """Replace outbound HTTP processors only in the disposable test job.

    The published pipeline keeps its real provider adapter. Tests replace that
    adapter with deterministic provider responses and still execute every
    downstream mapping, branch, and output assertion.
    """
    if not responses:
        return
    index = response_index or [0]
    for processor in processors:
        if "http" in processor:
            response = responses[min(index[0], len(responses) - 1)]
            processor.clear()
            processor["mapping"] = f"root = {json.dumps(response, separators=(',', ':'))}"
            index[0] += 1
            continue
        for value in processor.values():
            if isinstance(value, list) and all(
                isinstance(item, dict) for item in value
            ):
                apply_provider_mocks(value, responses, index)
            elif isinstance(value, dict):
                for nested in value.values():
                    if isinstance(nested, list) and all(
                        isinstance(item, dict) for item in nested
                    ):
                        apply_provider_mocks(nested, responses, index)

def missing_credentials(skill_yaml: dict[str, Any], ignore: set[str] | None = None) -> list[str]:
    credentials = []
    for cred in skill_yaml.get("credentials", []) if isinstance(skill_yaml, dict) else []:
        if isinstance(cred, dict):
            if cred.get("required", True):
                name = cred.get("name")
                if name:
                    credentials.append(name)
    for backend in skill_yaml.get("backends", []) if isinstance(skill_yaml, dict) else []:
        if isinstance(backend, dict):
            for req in backend.get("requires", []) or []:
                credentials.append(req)

    credentials = sorted({c for c in credentials if c})
    if not credentials:
        return []

    ignore = ignore or set()
    missing = [c for c in credentials if c not in ignore and not os.environ.get(c)]

    # If there is a local backend, allow tests to proceed (it may still fail).
    has_local = any(
        isinstance(b, dict) and b.get("type") == "local" for b in skill_yaml.get("backends", []) if isinstance(skill_yaml, dict)
    )
    if missing and not has_local:
        return missing
    return []


def normalize_input_value(value: str, input_type: str | None) -> Any:
    if input_type in {"object", "array"}:
        try:
            return json.loads(value)
        except Exception:
            if input_type == "array":
                return [item.strip() for item in value.split(",") if item.strip()]
            return value
    if input_type in {"integer", "number"}:
        try:
            return int(value) if input_type == "integer" else float(value)
        except Exception:
            return value
    if input_type == "boolean":
        lowered = value.strip().lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        return value
    return value


def build_payload(
    input_value: str,
    skill_inputs: list[dict[str, Any]],
    env_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    env_overrides = env_overrides or {}

    parsed_value = None
    parsed_is_object = False
    if input_value.strip():
        try:
            parsed_value = json.loads(input_value)
            parsed_is_object = isinstance(parsed_value, dict)
        except Exception:
            parsed_value = None

    input_names = [i.get("name") for i in skill_inputs if isinstance(i, dict) and i.get("name")]
    input_types = {i.get("name"): i.get("type") for i in skill_inputs if isinstance(i, dict)}

    payload: dict[str, Any] = {}

    required_inputs = [
        item.get("name")
        for item in skill_inputs
        if isinstance(item, dict) and item.get("required") and item.get("name")
    ]

    if (
        parsed_is_object
        and len(input_names) == 1
        and input_types.get(input_names[0]) == "object"
        and input_names[0] not in parsed_value
    ):
        payload[input_names[0]] = parsed_value
    elif (
        parsed_is_object
        and len(required_inputs) == 1
        and not any(name in parsed_value for name in input_names)
    ):
        payload[required_inputs[0]] = parsed_value
    elif parsed_is_object:
        payload = parsed_value  # type: ignore[assignment]
    elif input_names:
        primary = input_names[0]
        payload[primary] = normalize_input_value(input_value, input_types.get(primary))
    else:
        payload["text"] = input_value

    # Apply env overrides if they map to inputs
    for key, value in env_overrides.items():
        lower = key.lower()
        match = None
        for name in input_names:
            if name and name.lower() == lower:
                match = name
                break
        if match:
            payload[match] = normalize_input_value(str(value), input_types.get(match))

    return payload


def parse_env_overrides(env: dict[str, Any] | None, skill_inputs: list[dict[str, Any]]) -> dict[str, Any]:
    if not env:
        return {}
    overrides = {}
    input_names = [i.get("name") for i in skill_inputs if isinstance(i, dict) and i.get("name")]
    for key, value in env.items():
        if key.lower() in {"openai_api_key", "stripe_api_key", "slack_webhook", "github_token"}:
            continue
        if any(name and name.lower() == key.lower() for name in input_names):
            overrides[key] = value
        else:
            # Map common env names to input names
            if key.lower() == "algorithm" and "algorithm" in input_names:
                overrides["algorithm"] = value
            if key.lower() == "extract_fields" and "fields" in input_names:
                overrides["fields"] = value
            if key.lower() == "analyses" and "analyses" in input_names:
                overrides["analyses"] = value
            if key.lower() == "shell_type" and "shell" in input_names:
                overrides["shell"] = value
            if key.lower() == "language" and "language" in input_names:
                overrides["language"] = value
            if key.lower() == "detail_level" and "detail_level" in input_names:
                overrides["detail_level"] = value
            if key.lower() == "target" and "target" in input_names:
                overrides["target"] = value
            if key.lower() == "pii_types" and "types" in input_names:
                overrides["types"] = value
            if key.lower() == "secret_types" and "types" in input_names:
                overrides["types"] = value
    return overrides


def check_expectations(expected: dict[str, Any], output: dict[str, Any], status_code: int) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if expected.get("error_or_empty"):
        if status_code >= 400 or not output or ("error" in output or "message" in output):
            return True, []
        if isinstance(output, dict):
            metadata = output.get("metadata")
            if not metadata:
                return True, []
            if isinstance(metadata, dict) and not metadata.get("trace_id"):
                return True, []
        return False, ["Expected error_or_empty but got output"]

    json_contains = expected.get("json_contains")
    if json_contains is not None:
        errors.extend(check_expected_output(json_contains, output))

    has_field = expected.get("has_field")
    if has_field:
        fields = has_field if isinstance(has_field, list) else [has_field]
        for field in fields:
            if field not in output:
                errors.append(f"Missing field: {field}")

    metadata_has = expected.get("metadata_has")
    if metadata_has:
        metadata = output.get("metadata") if isinstance(output, dict) else None
        for key in metadata_has:
            if not isinstance(metadata, dict) or key not in metadata:
                errors.append(f"Missing metadata key: {key}")

    extracted_contains = expected.get("extracted_contains")
    if extracted_contains:
        extracted = output.get("extracted", {})
        if isinstance(extracted, str):
            try:
                extracted = json.loads(extracted)
            except Exception:
                pass
        for key in extracted_contains:
            if isinstance(extracted, dict):
                if key not in extracted:
                    errors.append(f"Missing extracted key: {key}")
            else:
                if key not in str(extracted):
                    errors.append(f"Missing extracted token: {key}")

    analysis_has = expected.get("analysis_has")
    if analysis_has:
        analysis = output.get("analysis", {})
        for key in analysis_has:
            if not isinstance(analysis, dict) or key not in analysis:
                errors.append(f"Missing analysis key: {key}")

    command_contains = expected.get("command_contains")
    if command_contains:
        command = output.get("command", "")
        for token in command_contains:
            if token not in str(command):
                errors.append(f"Command missing token: {token}")

    if "hash_length" in expected:
        hash_value = output.get("hash", "")
        if len(str(hash_value)) != int(expected["hash_length"]):
            errors.append("Hash length mismatch")

    if "hash" in expected:
        if output.get("hash") != expected["hash"]:
            errors.append("Hash mismatch")

    if "algorithm" in expected:
        if output.get("algorithm") != expected["algorithm"]:
            errors.append("Algorithm mismatch")

    if "has_pii" in expected:
        if output.get("has_pii") != expected["has_pii"]:
            errors.append("has_pii mismatch")

    if "has_secrets" in expected:
        if output.get("has_secrets") != expected["has_secrets"]:
            errors.append("has_secrets mismatch")

    if "findings_length" in expected:
        findings = output.get("findings", [])
        if not isinstance(findings, list) or len(findings) != expected["findings_length"]:
            errors.append("findings_length mismatch")

    if "summary_contains_bullets" in expected:
        summary = output.get("summary", "")
        if not any(bullet in summary for bullet in ["\n-", "\n*", "\n•", "\n1."]):
            errors.append("summary does not contain bullets")

    if "min_length" in expected:
        target = output.get("summary") or output.get("explanation") or ""
        if len(str(target)) < int(expected["min_length"]):
            errors.append("min_length not satisfied")

    if "max_length" in expected:
        target = output.get("summary") or output.get("explanation") or ""
        if len(str(target)) > int(expected["max_length"]):
            errors.append("max_length exceeded")

    if "explanation_contains" in expected:
        explanation = output.get("explanation", "")
        for token in expected["explanation_contains"]:
            if token not in str(explanation):
                errors.append(f"explanation missing token: {token}")

    return len(errors) == 0, errors


def replace_fixture_env(value: Any, env: dict[str, Any]) -> Any:
    """Replace env() calls in the disposable job copy with test fixture values."""
    if isinstance(value, dict):
        return {key: replace_fixture_env(child, env) for key, child in value.items()}
    if isinstance(value, list):
        return [replace_fixture_env(child, env) for child in value]
    if not isinstance(value, str):
        return value
    rendered = value
    for key, fixture in env.items():
        rendered = rendered.replace(f'env("{key}")', json.dumps(str(fixture)))
    return rendered


def check_expected_output(expected: Any, output: Any, path: str = "root") -> list[str]:
    """Check that an expected fixture is a recursive subset of the response."""
    if isinstance(expected, dict):
        if not isinstance(output, dict):
            return [f"{path}: expected object, got {type(output).__name__}"]
        errors: list[str] = []
        for key, value in expected.items():
            if key not in output:
                errors.append(f"{path}: missing key {key}")
                continue
            errors.extend(check_expected_output(value, output[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if not isinstance(output, list):
            return [f"{path}: expected array, got {type(output).__name__}"]
        if len(expected) != len(output):
            return [f"{path}: expected {len(expected)} items, got {len(output)}"]
        errors: list[str] = []
        for index, value in enumerate(expected):
            errors.extend(check_expected_output(value, output[index], f"{path}[{index}]"))
        return errors
    if expected != output:
        return [f"{path}: expected {expected!r}, got {output!r}"]
    return []


def check_output_conditions(
    conditions: Any,
    output: Any,
) -> list[str]:
    """Evaluate simple comparisons against paths in the serialized response."""
    if not conditions:
        return []
    if not isinstance(conditions, list):
        return ["output_conditions must be a list"]

    errors: list[str] = []
    for entry in conditions:
        if not isinstance(entry, dict):
            errors.append("output condition must be an object")
            continue
        path = str(entry.get("path", "")).strip()
        expression = str(entry.get("condition", "")).strip()
        current = output
        missing = False
        for part in path.split(".") if path else []:
            if not isinstance(current, dict) or part not in current:
                errors.append(f"output condition path missing: {path}")
                missing = True
                break
            current = current[part]
        if missing:
            continue

        match = re.fullmatch(r"(?:(length)\s+)?(==|!=|>=|<=|>|<)\s+(.+)", expression)
        if not match:
            errors.append(f"unsupported output condition for {path}: {expression}")
            continue
        if match.group(1):
            try:
                current = len(current)
            except TypeError:
                errors.append(f"output condition path has no length: {path}")
                continue
        expected = yaml.safe_load(match.group(3))
        operator = match.group(2)
        comparisons = {
            "==": lambda: current == expected,
            "!=": lambda: current != expected,
            ">=": lambda: current >= expected,
            "<=": lambda: current <= expected,
            ">": lambda: current > expected,
            "<": lambda: current < expected,
        }
        try:
            passed = comparisons[operator]()
        except TypeError:
            passed = False
        if not passed:
            errors.append(
                f"output condition failed: {path} value {current!r} {expression}"
            )
    return errors


def is_transient_failure(entry: dict[str, Any]) -> bool:
    reason = (entry.get("reason") or "").lower()
    if "http server did not start" in reason:
        return True
    if "request error" in reason:
        return True
    if "timeout" in reason:
        return True
    if "connection" in reason:
        return True
    return False


def failure_signature(entry: dict[str, Any]) -> str:
    payload = {
        "reason": entry.get("reason"),
        "errors": entry.get("errors") or [],
        "status_code": entry.get("status_code"),
    }
    return json.dumps(payload, sort_keys=True, default=str)


def is_permanent_failure(entry: dict[str, Any]) -> bool:
    history = entry.get("history") or []
    if len(history) < 2:
        return False
    last_sig = failure_signature(history[-1])
    prev_sig = failure_signature(history[-2])
    return last_sig == prev_sig


def record_attempt(entry: dict[str, Any], result: dict[str, Any]) -> None:
    history = entry.setdefault("history", [])
    history.append({
        "status": result.get("status"),
        "reason": result.get("reason"),
        "errors": result.get("errors"),
        "status_code": result.get("status_code"),
    })
    entry.update(result)
    entry["attempts"] = len(history)
    if entry.get("status") == "failed" and is_permanent_failure(entry):
        entry["permanent_failure"] = True


def execute_test(
    skill_name: str,
    pipeline_path: Path,
    variant: str,
    input_value: str,
    payload: dict[str, Any],
    expected: dict[str, Any],
    api_url: str,
    expanso_cli: str,
    mock_openai: bool,
    run_dir: Path,
    expected_output: Any = None,
    output_conditions: Any = None,
    fixture_env: dict[str, Any] | None = None,
    provider_responses: list[Any] | None = None,
    ai_responses: list[Any] | None = None,
    require_mcp_auth: bool = False,
    edge_log: Path | None = None,
    repeat: int = 1,
    expected_sequence: list[Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    pipeline_spec = load_yaml(pipeline_path)
    if not pipeline_spec:
        return {
            "status": "failed",
            "reason": f"failed to parse {pipeline_path.name}",
            "errors": [],
            "status_code": 0,
            "output": {},
        }, True

    port = find_free_port()
    config = pipeline_spec.setdefault("config", {})
    if variant == "cli":
        # Scheduled Edge jobs cannot receive terminal stdin. For execution
        # proof, wrap the published CLI processor graph with a disposable
        # localhost HTTP input and synchronous output. The pipeline itself is
        # never edited, and its processors run unchanged in expanso-edge.
        config["input"] = {
            "http_server": {
                "address": f"127.0.0.1:{port}",
                "path": "/test",
                "allowed_verbs": ["POST"],
                "timeout": "60s",
            }
        }
        config["output"] = {"sync_response": {}}
        http_server = config["input"]["http_server"]
    else:
        input_cfg = config.get("input", {})
        http_server = input_cfg.get("http_server") if isinstance(input_cfg, dict) else None
        if not isinstance(http_server, dict):
            return {
                "status": "failed",
                "reason": f"{pipeline_path.name} has no http_server input",
                "errors": [],
                "status_code": 0,
                "output": {},
            }, True

    http_server["address"] = f"127.0.0.1:{port}"
    config.pop("http", None)
    path = http_server.get("path", "/")
    allowed = http_server.get("allowed_verbs", ["POST"])
    method = allowed[0] if isinstance(allowed, list) and allowed else "POST"

    if mock_openai:
        processors = config.get("pipeline", {}).get("processors", [])
        if isinstance(processors, list):
            apply_openai_mocks(
                processors,
                skill_name,
                expected,
                str(input_value),
                ai_responses,
            )
    if provider_responses:
        processors = config.get("pipeline", {}).get("processors", [])
        if isinstance(processors, list):
            apply_provider_mocks(processors, provider_responses)
    if fixture_env:
        pipeline_spec = replace_fixture_env(pipeline_spec, fixture_env)

    pipeline_spec["name"] = f"{skill_name}-{variant}-test-{port}"

    jobs_dir = run_dir / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    temp_job = jobs_dir / f"{skill_name}-{variant}-{port}-{uuid.uuid4().hex}.yaml"
    with open(temp_job, "w") as f:
        yaml.safe_dump(pipeline_spec, f, sort_keys=False)

    deploy = subprocess.run(
        [expanso_cli, "job", "deploy", str(temp_job), "--endpoint", api_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if deploy.returncode != 0:
        return {
            "status": "failed",
            "reason": f"job deploy failed: {deploy.stderr.strip()}",
            "errors": [],
            "status_code": 0,
            "output": {},
        }, False

    if not wait_for_port(port, timeout=15.0):
        subprocess.run(
            [expanso_cli, "job", "delete", pipeline_spec["name"], "--endpoint", api_url, "--yes", "--force"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "status": "failed",
            "reason": "http server did not start within 15 seconds",
            "errors": [],
            "status_code": 0,
            "output": {},
        }, False

    url = f"http://127.0.0.1:{port}{path}"
    status_code = 0
    output: dict[str, Any] = {}
    responses: list[dict[str, Any]] = []
    status_codes: list[int] = []
    log_offset = edge_log.stat().st_size if edge_log and edge_log.exists() else 0
    try:
        request_payload = payload
        request_headers: dict[str, str] = {}
        webhook_cli_body: bytes | None = None
        if skill_name == "webhook-receive":
            if isinstance(payload.get("headers"), dict) and "body" in payload:
                request_payload = payload["body"]
                request_headers.update(
                    {str(key): str(value) for key, value in payload["headers"].items()}
                )
            raw_body_text = json.dumps(request_payload, separators=(",", ":"))
            raw_body = raw_body_text.encode()
            secret = str((fixture_env or {}).get("WEBHOOK_SECRET", ""))
            request_headers["X-Hub-Signature-256"] = (
                "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
            )
            request_headers["Content-Type"] = "application/json"
            if variant == "cli":
                webhook_cli_body = json.dumps(
                    {
                        "headers": request_headers,
                        "body": request_payload,
                        "raw_body": raw_body_text,
                    },
                    separators=(",", ":"),
                ).encode()
        auth_probe_status: int | None = None
        auth_probe_body = ""
        if variant == "mcp" and require_mcp_auth:
            auth_probe = requests.request(
                method,
                url,
                json=request_payload,
                timeout=30,
            )
            auth_probe_status = auth_probe.status_code
            auth_probe_body = auth_probe.text
        for _ in range(max(1, repeat)):
            if skill_name == "webhook-receive":
                response = requests.request(
                    method,
                    url,
                    data=webhook_cli_body if variant == "cli" else raw_body,
                    headers=(
                        {"Content-Type": "application/json"}
                        if variant == "cli"
                        else request_headers
                    ),
                    timeout=30,
                )
            elif variant == "cli":
                response = requests.request(
                    method,
                    url,
                    data=str(input_value).encode(),
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                    timeout=30,
                )
            else:
                response = requests.request(
                    method,
                    url,
                    json=request_payload,
                    headers={"Authorization": f"Bearer {HARNESS_MCP_BEARER_TOKEN}"},
                    timeout=30,
                )
            status_code = response.status_code
            output = response.json() if response.text else {}
            responses.append(output)
            status_codes.append(status_code)
    except Exception as exc:
        subprocess.run(
            [expanso_cli, "job", "delete", pipeline_spec["name"], "--endpoint", api_url, "--yes", "--force"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "status": "failed",
            "reason": f"request error: {exc}",
            "errors": [],
            "status_code": 0,
            "output": {},
        }, False

    time.sleep(0.1)
    edge_log_text = ""
    if edge_log and edge_log.exists():
        with edge_log.open("rb") as log_handle:
            log_handle.seek(log_offset)
            edge_log_text = log_handle.read().decode(errors="replace")

    ok, errors = check_expectations(expected, output, status_code)
    if expected_output is not None:
        errors.extend(check_expected_output(expected_output, output))
        ok = not errors
    errors.extend(check_output_conditions(output_conditions, output))
    if require_mcp_auth and (
        auth_probe_status is None
        or (auth_probe_status < 400 and auth_probe_body.strip())
    ):
        errors.append(
            "MCP endpoint accepted a request without its bearer token"
        )
    if expected_sequence is not None:
        if len(expected_sequence) != len(responses):
            errors.append(
                f"expected {len(expected_sequence)} responses, got {len(responses)}"
            )
        else:
            for index, expected_response in enumerate(expected_sequence):
                errors.extend(
                    check_expected_output(
                        expected_response,
                        responses[index],
                        f"responses[{index}]",
                    )
                )
    expected_error = expected.get("error_contains")
    if expected_error and str(expected_error) not in edge_log_text:
        errors.append(f"edge log did not contain expected error: {expected_error}")
    unexpected_errors = [
        line
        for line in edge_log_text.splitlines()
        if " ERR " in line
        and not (require_mcp_auth and "unauthorized" in line.lower())
    ]
    if unexpected_errors and not (expected_error or expected.get("error_or_empty")):
        errors.append("unexpected Edge errors: " + " | ".join(unexpected_errors))
    ok = not errors
    result = {
        "status": "passed" if ok else "failed",
        "errors": errors,
        "status_code": status_code,
        "output": output,
        "edge_errors": unexpected_errors,
    }
    if require_mcp_auth:
        result["auth_probe_status"] = auth_probe_status
        result["auth_probe_body"] = auth_probe_body
    if repeat > 1:
        result["responses"] = responses
        result["status_codes"] = status_codes

    subprocess.run(
        [expanso_cli, "job", "delete", pipeline_spec["name"], "--endpoint", api_url, "--yes", "--force"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return result, False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Expanso skill tests in local Edge mode")
    parser.add_argument("skills", nargs="*", help="Skill names to test")
    parser.add_argument(
        "--variant",
        choices=("cli", "mcp"),
        default="mcp",
        help="Published pipeline variant to execute (default: mcp)",
    )
    parser.add_argument("--limit-skills", type=int, default=None, help="Limit number of skills")
    parser.add_argument("--limit-tests", type=int, default=None, help="Limit number of tests")
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path to JSON report",
    )
    parser.add_argument("--api-url", type=str, default=None, help="Existing Edge API URL (skip starting Edge)")
    parser.add_argument("--keep-edge", action="store_true", help="Keep Edge running after tests")
    parser.add_argument(
        "--restart-edge-every",
        type=int,
        default=30,
        help="Restart a harness-managed Edge after this many skills (0 disables; default: 30)",
    )
    parser.add_argument("--allow-external", action="store_true", help="Run tests even if credentials are missing")
    parser.add_argument("--mock-openai", dest="mock_openai", action="store_true", default=True, help="Mock OpenAI processors (default)")
    parser.add_argument("--no-mock-openai", dest="mock_openai", action="store_false", help="Disable OpenAI mocking")
    parser.add_argument("--rerun-failed", dest="rerun_failed", action="store_true", default=True, help="Automatically rerun failed tests (default)")
    parser.add_argument("--no-rerun-failed", dest="rerun_failed", action="store_false", help="Disable automatic reruns")
    parser.add_argument("--max-reruns", type=int, default=3, help="Maximum total attempts per test (default: 3)")
    parser.add_argument("--use-cache", dest="use_cache", action="store_true", default=True, help="Reuse cached passing results when inputs are unchanged (default)")
    parser.add_argument("--no-cache", dest="use_cache", action="store_false", help="Disable cached results")
    parser.add_argument("--respect-skip", action="store_true", help="Respect skip flags in test.yaml (default: run anyway)")
    parser.add_argument("--test-name", type=str, default=None, help="Run only tests whose name contains this string")
    parser.add_argument("--show-io", action="store_true", help="Print request/response for each executed test")
    args = parser.parse_args()

    skills = find_skills(args.skills or None)
    if args.limit_skills:
        skills = skills[: args.limit_skills]

    report_path = Path(
        args.report
        or CONFORMANCE_DIR / f"test-harness-{args.variant}-report.json"
    )
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    run_dir = CONFORMANCE_DIR / (
        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{os.getpid()}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    previous_report = load_previous_report(report_path) if args.use_cache else None
    cache_index = build_cache_index(previous_report)
    harness_hash = hash_bytes(Path(__file__).read_bytes())

    report = {
        "schema": "expanso-local-execution/1",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_directory": str(run_dir.relative_to(REPO_ROOT)),
        "mode": (
            f"expanso-edge local API; {args.variant} variant; "
            "explicit fixtures; OpenAI processors mocked"
        ),
        "variant": args.variant,
        "skills": [],
        "summary": {"total_skills": 0, "passed": 0, "failed": 0, "skipped": 0, "manual": 0},
    }

    edge = None
    api_url = args.api_url
    temp_dir = None
    if not api_url:
        api_port = find_free_port()
        api_url = f"http://127.0.0.1:{api_port}"
        temp_dir = run_dir / "edge-data"
        edge = EdgeProcess(api_url=api_url, data_dir=temp_dir, log_file=run_dir / "edge.log")
        edge.start()
        atexit.register(edge.stop)
        if not wait_for_api(api_url):
            print("Failed to start expanso-edge local API", file=sys.stderr)
            edge.stop()
            return 1

    expanso_cli = shutil.which("expanso-cli")
    if not expanso_cli:
        raise RuntimeError("expanso-cli not found in PATH")
    expanso_edge = os.environ.get("EXPANSO_EDGE_BIN") or shutil.which("expanso-edge")
    if not expanso_edge:
        raise RuntimeError("expanso-edge not found in PATH")
    report["tools"] = {
        "expanso_edge": tool_evidence(expanso_edge),
        "expanso_cli": tool_evidence(expanso_cli),
    }

    total_tests_run = 0
    rerun_candidates: list[dict[str, Any]] = []

    for skill_index, skill_dir in enumerate(skills):
        if (
            edge
            and args.restart_edge_every > 0
            and skill_index > 0
            and skill_index % args.restart_edge_every == 0
        ):
            atexit.unregister(edge.stop)
            edge.stop()
            api_port = find_free_port()
            api_url = f"http://127.0.0.1:{api_port}"
            temp_dir = run_dir / f"edge-data-{skill_index // args.restart_edge_every + 1}"
            edge = EdgeProcess(
                api_url=api_url,
                data_dir=temp_dir,
                log_file=run_dir / f"edge-{skill_index // args.restart_edge_every + 1}.log",
            )
            edge.start()
            atexit.register(edge.stop)
            if not wait_for_api(api_url):
                print("Failed to restart expanso-edge local API", file=sys.stderr)
                edge.stop()
                return 1

        skill_name = skill_dir.name
        category = skill_dir.parent.name
        skill_result = {
            "name": skill_name,
            "category": category,
            "path": str(skill_dir.relative_to(REPO_ROOT)),
            "status": "unknown",
            "reason": None,
            "tests": [],
        }

        test_yaml_path = skill_dir / "test" / "test.yaml"
        pipeline_path = skill_dir / f"pipeline-{args.variant}.yaml"
        skill_yaml = load_yaml(skill_dir / "skill.yaml") or {}

        print(f"==> {category}/{skill_name}")

        if not test_yaml_path.exists():
            skill_result["status"] = "skipped"
            skill_result["reason"] = "no tests defined"
            report["skills"].append(skill_result)
            print("  - skipped (no tests)")
            continue

        if not pipeline_path.exists():
            skill_result["status"] = "manual"
            skill_result["reason"] = f"missing {pipeline_path.name}"
            report["skills"].append(skill_result)
            print(f"  - manual (missing {pipeline_path.name})")
            continue

        test_yaml = load_yaml(test_yaml_path) or {}
        tests = test_yaml.get("tests", [])
        fixtures_dir = test_yaml.get("fixtures_dir")

        if not tests:
            skill_result["status"] = "skipped"
            skill_result["reason"] = "tests empty"
            report["skills"].append(skill_result)
            print("  - skipped (tests empty)")
            continue

        if args.respect_skip and all(t.get("skip") for t in tests):
            skill_result["status"] = "skipped"
            skill_result["reason"] = "tests skipped"
            report["skills"].append(skill_result)
            print("  - skipped (tests marked skip)")
            continue

        ignore_creds = {"MCP_BEARER_TOKEN"}
        if args.mock_openai:
            ignore_creds.add("OPENAI_API_KEY")
        if any(test.get("provider_responses") for test in tests):
            for credential in skill_yaml.get("credentials", []):
                if isinstance(credential, dict) and credential.get("name"):
                    ignore_creds.add(str(credential["name"]))
        missing = missing_credentials(skill_yaml, ignore=ignore_creds)
        if missing and not args.allow_external:
            skill_result["status"] = "skipped"
            skill_result["reason"] = f"missing credentials: {', '.join(missing)}"
            report["skills"].append(skill_result)
            print(f"  - skipped (missing credentials: {', '.join(missing)})")
            continue

        skill_inputs = skill_yaml.get("inputs", []) if isinstance(skill_yaml, dict) else []
        fatal_manual = False

        for test in tests:
            if args.limit_tests and total_tests_run >= args.limit_tests:
                break
            if args.test_name and args.test_name.lower() not in str(test.get("name", "")).lower():
                continue
            if test.get("skip") and args.respect_skip:
                skill_result["tests"].append({"name": test.get("name"), "status": "skipped", "reason": "test marked skip"})
                print(f"    - {test.get('name')}: skipped")
                continue

            input_value = test.get("input", "")
            if "input_file" in test:
                raw_path = str(test["input_file"])
                if Path(raw_path).is_absolute():
                    file_path = raw_path
                else:
                    fixtures_prefix = fixtures_dir.lstrip("./") if fixtures_dir else ""
                    raw_parts = Path(raw_path).parts
                    if fixtures_prefix and raw_parts and raw_parts[0] == fixtures_prefix:
                        file_path = str((test_yaml_path.parent / raw_path).resolve())
                    elif fixtures_dir:
                        file_path = str((test_yaml_path.parent / fixtures_dir / raw_path).resolve())
                    else:
                        file_path = str((test_yaml_path.parent / raw_path).resolve())
                try:
                    input_value = Path(file_path).read_text()
                except Exception as exc:
                    skill_result["tests"].append({
                        "name": test.get("name"),
                        "status": "failed",
                        "reason": f"failed to read input_file: {exc}",
                    })
                    print(f"    - {test.get('name')}: failed (input_file read)")
                    total_tests_run += 1
                    continue

            env_overrides = parse_env_overrides(test.get("env"), skill_inputs)
            payload = build_payload(str(input_value), skill_inputs, env_overrides)
            expected = test.get("expected", {}) or {}
            expected_output = test.get("expected_output")
            output_conditions = test.get("output_conditions")
            expected_sequence = test.get("expected_sequence")
            repeat = int(test.get("repeat", 1))
            fixture_env = test.get("env", {}) or {}
            provider_responses = test.get("provider_responses", []) or []
            ai_responses = test.get("ai_responses", []) or []
            require_mcp_auth = args.variant == "mcp" and any(
                isinstance(credential, dict)
                and credential.get("name") == "MCP_BEARER_TOKEN"
                for credential in skill_yaml.get("credentials", [])
            )

            fingerprint = compute_test_fingerprint(
                skill_dir,
                pipeline_path,
                args.variant,
                test,
                str(input_value),
                env_overrides,
                provider_responses,
                ai_responses,
                args.mock_openai,
                harness_hash,
            )

            test_entry = {
                "name": test.get("name"),
                "fingerprint": fingerprint,
            }
            if test.get("skip") and not args.respect_skip:
                test_entry["forced_run"] = True

            cache_entry = cache_index.get(cache_key(category, skill_name, test.get("name")))
            if args.use_cache and cache_entry and cache_entry.get("fingerprint") == fingerprint and cache_entry.get("status") == "passed":
                test_entry.update({
                    "status": "passed",
                    "errors": cache_entry.get("errors", []),
                    "status_code": cache_entry.get("status_code", 0),
                    "output": cache_entry.get("output", {}),
                    "cached": True,
                    "attempts": cache_entry.get("attempts", 0),
                })
                skill_result["tests"].append(test_entry)
                print(f"    - {test.get('name')}: passed (cached)")
                total_tests_run += 1
                continue

            result, fatal_manual = execute_test(
                skill_name=skill_name,
                pipeline_path=pipeline_path,
                variant=args.variant,
                input_value=str(input_value),
                payload=payload,
                expected=expected,
                api_url=api_url,
                expanso_cli=expanso_cli,
                mock_openai=args.mock_openai,
                run_dir=run_dir,
                expected_output=expected_output,
                output_conditions=output_conditions,
                fixture_env=fixture_env,
                provider_responses=provider_responses,
                ai_responses=ai_responses,
                require_mcp_auth=require_mcp_auth,
                edge_log=edge.log_file if edge else None,
                repeat=repeat,
                expected_sequence=expected_sequence,
            )

            if fatal_manual:
                skill_result["status"] = "manual"
                skill_result["reason"] = result.get("reason")
                print(f"  - manual ({result.get('reason')})")
                fatal_manual = True
                break

            record_attempt(test_entry, result)
            skill_result["tests"].append(test_entry)
            print(f"    - {test.get('name')}: {result['status']}")
            if args.show_io:
                print("      request:", json.dumps(payload, indent=2))
                print("      response:", json.dumps(result.get("output", {}), indent=2))
            total_tests_run += 1

            if result["status"] == "failed" and args.rerun_failed:
                rerun_candidates.append({
                    "category": category,
                    "skill_name": skill_name,
                    "test_name": test.get("name"),
                    "pipeline_path": pipeline_path,
                    "variant": args.variant,
                    "input_value": str(input_value),
                    "payload": payload,
                    "expected": expected,
                    "expected_output": expected_output,
                    "output_conditions": output_conditions,
                    "expected_sequence": expected_sequence,
                    "repeat": repeat,
                    "fixture_env": fixture_env,
                    "provider_responses": provider_responses,
                    "ai_responses": ai_responses,
                    "require_mcp_auth": require_mcp_auth,
                    "test_entry": test_entry,
                })

        if fatal_manual:
            report["skills"].append(skill_result)
            continue

        failed_tests = [t for t in skill_result["tests"] if t.get("status") == "failed"]
        if failed_tests:
            skill_result["status"] = "failed"
            print("  - status: failed")
        else:
            skill_result["status"] = "passed"
            print("  - status: passed")

        report["skills"].append(skill_result)

        if args.limit_tests and total_tests_run >= args.limit_tests:
            break

    if args.rerun_failed and rerun_candidates and args.max_reruns > 1:
        attempts = 1
        remaining = rerun_candidates
        while attempts < args.max_reruns and remaining:
            attempts += 1
            print(f"\n==> Rerun failed tests (attempt {attempts}/{args.max_reruns})")
            next_remaining: list[dict[str, Any]] = []
            for ctx in remaining:
                if ctx["test_entry"].get("permanent_failure"):
                    continue
                result, _ = execute_test(
                    skill_name=ctx["skill_name"],
                    pipeline_path=ctx["pipeline_path"],
                    variant=ctx["variant"],
                    input_value=ctx["input_value"],
                    payload=ctx["payload"],
                    expected=ctx["expected"],
                    api_url=api_url,
                    expanso_cli=expanso_cli,
                    mock_openai=args.mock_openai,
                    run_dir=run_dir,
                    expected_output=ctx["expected_output"],
                    output_conditions=ctx["output_conditions"],
                    fixture_env=ctx["fixture_env"],
                    provider_responses=ctx["provider_responses"],
                    ai_responses=ctx["ai_responses"],
                    require_mcp_auth=ctx["require_mcp_auth"],
                    edge_log=edge.log_file if edge else None,
                    repeat=ctx["repeat"],
                    expected_sequence=ctx["expected_sequence"],
                )
                record_attempt(ctx["test_entry"], result)
                print(f"    - {ctx['category']}/{ctx['skill_name']} :: {ctx['test_name']}: {result['status']}")
                if result["status"] == "failed" and not ctx["test_entry"].get("permanent_failure"):
                    next_remaining.append(ctx)
            remaining = next_remaining

    if edge and not args.keep_edge:
        edge.stop()
        atexit.unregister(edge.stop)

    def finalize_report(report_data: dict[str, Any]) -> None:
        summary = {"total_skills": 0, "passed": 0, "failed": 0, "skipped": 0, "manual": 0}
        for skill in report_data.get("skills", []):
            summary["total_skills"] += 1
            status = skill.get("status")
            if status in {"skipped", "manual"}:
                summary[status] += 1
                continue
            failed_tests = [t for t in skill.get("tests", []) if t.get("status") == "failed"]
            if failed_tests:
                skill["status"] = "failed"
                summary["failed"] += 1
            else:
                skill["status"] = "passed"
                summary["passed"] += 1
        report_data["summary"] = summary

    finalize_report(report)
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\nSummary:")
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
