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
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"


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
    process: subprocess.Popen | None = None

    def start(self) -> None:
        expanso_edge = shutil.which("expanso-edge")
        if not expanso_edge:
            raise RuntimeError("expanso-edge not found in PATH")

        env = os.environ.copy()
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
    expanso_cli = shutil.which("expanso-cli")
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
) -> None:
    for idx, proc in enumerate(processors):
        if "openai_chat_completion" in proc:
            expects_json = mapping_uses_parse_json(processors, idx)
            content = mock_content_for_test(skill_name, expected, instruction, expects_json)
            literal = json.dumps(content)
            mapping = (
                "root = {\"choices\": [{\"message\": {\"content\": "
                + literal +
                "}}]}"
            )
            processors[idx] = {"mapping": mapping}
        elif "openai_image_generation" in proc:
            processors[idx] = {"mapping": "root = {\"data\": [{\"url\": \"https://example.com/mock.png\", \"revised_prompt\": \"mock prompt\"}]}"}
        elif "openai_embeddings" in proc:
            processors[idx] = {"mapping": "root = {\"data\": [{\"embedding\": [0.0, 0.0, 0.0, 0.0]}]}"}
        elif "openai_speech" in proc:
            processors[idx] = {"mapping": "root = \"MOCK_AUDIO\""}

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

    if parsed_is_object:
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
            payload[match] = value

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Expanso skill tests in local Edge mode")
    parser.add_argument("skills", nargs="*", help="Skill names to test")
    parser.add_argument("--limit-skills", type=int, default=None, help="Limit number of skills")
    parser.add_argument("--limit-tests", type=int, default=None, help="Limit number of tests")
    parser.add_argument("--report", type=str, default="test-harness-report.json", help="Path to JSON report")
    parser.add_argument("--api-url", type=str, default=None, help="Existing Edge API URL (skip starting Edge)")
    parser.add_argument("--keep-edge", action="store_true", help="Keep Edge running after tests")
    parser.add_argument("--allow-external", action="store_true", help="Run tests even if credentials are missing")
    parser.add_argument("--mock-openai", dest="mock_openai", action="store_true", default=True, help="Mock OpenAI processors (default)")
    parser.add_argument("--no-mock-openai", dest="mock_openai", action="store_false", help="Disable OpenAI mocking")
    parser.add_argument("--respect-skip", action="store_true", help="Respect skip flags in test.yaml (default: run anyway)")
    parser.add_argument("--test-name", type=str, default=None, help="Run only tests whose name contains this string")
    parser.add_argument("--show-io", action="store_true", help="Print request/response for each executed test")
    args = parser.parse_args()

    skills = find_skills(args.skills or None)
    if args.limit_skills:
        skills = skills[: args.limit_skills]

    report = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "skills": [],
        "summary": {"total_skills": 0, "passed": 0, "failed": 0, "skipped": 0, "manual": 0},
    }

    edge = None
    api_url = args.api_url
    temp_dir = None
    if not api_url:
        api_port = find_free_port()
        api_url = f"http://127.0.0.1:{api_port}"
        temp_dir = Path(tempfile.mkdtemp(prefix="expanso-edge-data-"))
        edge = EdgeProcess(api_url=api_url, data_dir=temp_dir, log_file=temp_dir / "edge.log")
        edge.start()
        if not wait_for_api(api_url):
            print("Failed to start expanso-edge local API", file=sys.stderr)
            edge.stop()
            return 1

    total_tests_run = 0

    for skill_dir in skills:
        skill_name = skill_dir.name
        category = skill_dir.parent.name
        skill_result = {
            "name": skill_name,
            "category": category,
            "path": str(skill_dir),
            "status": "unknown",
            "reason": None,
            "tests": [],
        }

        test_yaml_path = skill_dir / "test" / "test.yaml"
        pipeline_mcp_path = skill_dir / "pipeline-mcp.yaml"
        skill_yaml = load_yaml(skill_dir / "skill.yaml") or {}

        print(f"==> {category}/{skill_name}")

        if not test_yaml_path.exists():
            skill_result["status"] = "skipped"
            skill_result["reason"] = "no tests defined"
            report["skills"].append(skill_result)
            report["summary"]["skipped"] += 1
            print("  - skipped (no tests)")
            continue

        if not pipeline_mcp_path.exists():
            skill_result["status"] = "manual"
            skill_result["reason"] = "missing pipeline-mcp.yaml"
            report["skills"].append(skill_result)
            report["summary"]["manual"] += 1
            print("  - manual (missing pipeline-mcp.yaml)")
            continue

        test_yaml = load_yaml(test_yaml_path) or {}
        tests = test_yaml.get("tests", [])
        fixtures_dir = test_yaml.get("fixtures_dir")

        if not tests:
            skill_result["status"] = "skipped"
            skill_result["reason"] = "tests empty"
            report["skills"].append(skill_result)
            report["summary"]["skipped"] += 1
            print("  - skipped (tests empty)")
            continue

        # Skip if all tests are marked skip and we respect skip flags
        if args.respect_skip and all(t.get("skip") for t in tests):
            skill_result["status"] = "skipped"
            skill_result["reason"] = "tests skipped"
            report["skills"].append(skill_result)
            report["summary"]["skipped"] += 1
            print("  - skipped (tests marked skip)")
            continue

        ignore_creds = {"OPENAI_API_KEY"} if args.mock_openai else set()
        missing = missing_credentials(skill_yaml, ignore=ignore_creds)
        if missing and not args.allow_external:
            skill_result["status"] = "skipped"
            skill_result["reason"] = f"missing credentials: {', '.join(missing)}"
            report["skills"].append(skill_result)
            report["summary"]["skipped"] += 1
            print(f"  - skipped (missing credentials: {', '.join(missing)})")
            continue

        skill_inputs = skill_yaml.get("inputs", []) if isinstance(skill_yaml, dict) else []

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
                    continue

            env_overrides = parse_env_overrides(test.get("env"), skill_inputs)
            payload = build_payload(str(input_value), skill_inputs, env_overrides)

            # Prepare job spec with patched HTTP address + mocked processors
            pipeline_spec = load_yaml(pipeline_mcp_path)
            if not pipeline_spec:
                skill_result["status"] = "manual"
                skill_result["reason"] = "failed to parse pipeline-mcp.yaml"
                report["skills"].append(skill_result)
                report["summary"]["manual"] += 1
                print("  - manual (failed to parse pipeline-mcp.yaml)")
                break

            port = find_free_port()
            config = pipeline_spec.setdefault("config", {})
            input_cfg = config.get("input", {})
            http_server = input_cfg.get("http_server") if isinstance(input_cfg, dict) else None
            if not isinstance(http_server, dict):
                skill_result["status"] = "manual"
                skill_result["reason"] = "pipeline-mcp has no http_server input"
                report["skills"].append(skill_result)
                report["summary"]["manual"] += 1
                print("  - manual (no http_server input)")
                break

            http_server["address"] = f"127.0.0.1:{port}"
            config.pop("http", None)
            path = http_server.get("path", "/")
            allowed = http_server.get("allowed_verbs", ["POST"])
            method = allowed[0] if isinstance(allowed, list) and allowed else "POST"

            expected = test.get("expected", {}) or {}
            if args.mock_openai:
                processors = config.get("pipeline", {}).get("processors", [])
                if isinstance(processors, list):
                    apply_openai_mocks(processors, skill_name, expected, str(input_value))

            pipeline_spec["name"] = f"{skill_name}-mcp-test-{port}"

            temp_job = Path(tempfile.mkdtemp(prefix="expanso-job-")) / "job.yaml"
            with open(temp_job, "w") as f:
                yaml.safe_dump(pipeline_spec, f, sort_keys=False)

            expanso_cli = shutil.which("expanso-cli")
            deploy = subprocess.run(
                [expanso_cli, "job", "deploy", str(temp_job), "--endpoint", api_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if deploy.returncode != 0:
                skill_result["tests"].append({
                    "name": test.get("name"),
                    "status": "failed",
                    "reason": f"job deploy failed: {deploy.stderr.strip()}",
                })
                print(f"    - {test.get('name')}: failed (job deploy)")
                continue

            if not wait_for_port(port, timeout=45.0):
                # One more short wait to avoid flaky startup failures.
                if not wait_for_port(port, timeout=20.0):
                    skill_result["tests"].append({
                        "name": test.get("name"),
                        "status": "failed",
                        "reason": "http server did not start",
                    })
                    subprocess.run(
                        [expanso_cli, "job", "delete", pipeline_spec["name"], "--endpoint", api_url, "--yes", "--force"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    print(f"    - {test.get('name')}: failed (http server)")
                    continue

            url = f"http://127.0.0.1:{port}{path}"
            response = None
            status_code = 0
            output = {}
            try:
                response = requests.request(method, url, json=payload, timeout=30)
                status_code = response.status_code
                if response.text:
                    output = response.json()
            except Exception as exc:
                skill_result["tests"].append({
                    "name": test.get("name"),
                    "status": "failed",
                    "reason": f"request error: {exc}",
                })
                print(f"    - {test.get('name')}: failed (request error)")
                subprocess.run(
                    [expanso_cli, "job", "delete", pipeline_spec["name"], "--endpoint", api_url, "--yes", "--force"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                continue

            ok, errors = check_expectations(expected, output, status_code)
            test_entry = {
                "name": test.get("name"),
                "status": "passed" if ok else "failed",
                "errors": errors,
                "status_code": status_code,
                "output": output,
            }
            if test.get("skip") and not args.respect_skip:
                test_entry["forced_run"] = True
            skill_result["tests"].append(test_entry)
            print(f"    - {test.get('name')}: {'passed' if ok else 'failed'}")
            if args.show_io:
                print("      request:", json.dumps(payload, indent=2))
                print("      response:", json.dumps(output, indent=2))
            total_tests_run += 1

            subprocess.run(
                [expanso_cli, "job", "delete", pipeline_spec["name"], "--endpoint", api_url, "--yes", "--force"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        if args.limit_tests and total_tests_run >= args.limit_tests:
            skill_result["status"] = "partial"
        else:
            failed_tests = [t for t in skill_result["tests"] if t.get("status") == "failed"]
            if failed_tests:
                skill_result["status"] = "failed"
                report["summary"]["failed"] += 1
                print("  - status: failed")
            else:
                skill_result["status"] = "passed"
                report["summary"]["passed"] += 1
                print("  - status: passed")

        report["skills"].append(skill_result)
        report["summary"]["total_skills"] += 1

        if args.limit_tests and total_tests_run >= args.limit_tests:
            break

    if edge and not args.keep_edge:
        edge.stop()

    report_path = Path(args.report)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\nSummary:")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
