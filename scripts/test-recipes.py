# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute published recipes and standalone variants on Expanso Edge.

The published processor graph is preserved. Each disposable job replaces only
the external input and output with localhost HTTP/sync response, removes the
five-minute event-time buffer, and replaces the three internal provider HTTP
processors with deterministic mappings. The generated report records tool,
pipeline, input, expectation, output, and Edge-error evidence.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import hmac
import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

import requests
import yaml


REPO = Path(__file__).resolve().parents[1]
RECIPES = REPO / "skills" / "recipes"
CONFORMANCE = REPO / ".conformance"

FIXTURE_ENV = {
    "ACCESS_POLICY": "fixture-agent:slack-read:read",
    "ACCOUNT_PSEUDONYM_KEY": "fixture-account-pseudonym-key-32-chars",
    "EXPANSO_API_KEYS": "fixture-key:fixture-agent",
    "FIELD_ENCRYPTION_KEY_HEX": "0123456789abcdef" * 4,
    "FIELD_MAC_KEY": "fixture-field-mac-key-at-least-32-characters",
    "LOG_PSEUDONYM_KEY": "fixture-log-pseudonym-key-32-characters",
    "PSEUDONYM_KEY": "fixture-pseudonym-key-at-least-32-characters",
    "SLACK_API_URL": "https://slack.com/api",
    "SLACK_BOT_TOKEN": "fixture-token",
    "TRANSFER_POLICY_ID": "fixture-transfer-policy",
    "WEBHOOK_SECRET": "fixture-webhook-secret",
}

SPECIAL_VARIANTS: dict[Path, dict[str, Any]] = {
    REPO / "skills" / "transforms" / "json-pretty" / "pipeline-cloud.yaml": {
        "input": {
            "sample": {"hello": "expanso", "nested": {"a": 1}},
            "seq": 0,
        },
        "expected": {"formatted": "__present__", "valid": True},
    },
}

FIXTURES: dict[str, dict[str, Any]] = {
    "aggregate-time-windows": {
        "input": {
            "sensor_id": "sensor-1",
            "location": "lab",
            "temperature": 21.5,
            "timestamp": "2026-10-05T12:00:00Z",
        },
        "expected": {"aggregation_level": "sensor", "event_count": 1},
    },
    "circuit-breakers": {
        "input": {"event_id": "evt-1", "kind": "fixture"},
        "expected": {"enrichment_source": "primary_api"},
    },
    "content-routing": {
        "input": {
            "event_type": "payment.failed",
            "severity": "ERROR",
            "user_tier": "premium",
        },
        "expected": {"event_family": "payment", "priority": "critical"},
    },
    "content-splitting": {
        "input": {"items": [{"id": "one"}]},
        "expected": {"id": "one"},
    },
    "cross-border-gdpr": {
        "input": {
            "customer_id": "customer-1",
            "customer_name": "Fixture Person",
            "customer_email": "fixture@example.test",
            "customer_dob": "1990-01-01",
            "customer_address": "1 Fixture Way",
            "iban": "DE89370400440532013000",
            "ip_address": "192.0.2.10",
            "transaction_amount": 125,
            "transaction_timestamp": "2026-10-05T12:00:00Z",
        },
        "expected": {
            "email_domain": "example.test",
            "bank_country": "DE",
            "amount_bucket": "100-500",
        },
    },
    "csv-to-json": {
        "input": {"name": "fixture", "count": "42"},
        "expected": {"name": "fixture", "count": 42},
    },
    "db2-to-bigquery": {
        "input": {
            "TRANSACTION_ID": "txn-1",
            "CUSTOMER_ID": "customer-1",
            "AMOUNT": 10,
            "CURRENCY": "EUR",
            "USD_RATE": 1.1,
            "ACCOUNT_NUMBER": "1234567890123456",
            "MERCHANT_CATEGORY_CODE": "5411",
            "TRANSACTION_DATE": "2026-10-05T12:00:00Z",
            "TRANSACTION_TYPE": "purchase",
            "MERCHANT_NAME": "Fixture Store",
            "SOURCE_SYSTEM": "DB2",
            "CREATED_AT": "2026-10-05T12:00:00Z",
        },
        "expected": {"transaction_id": "txn-1", "transaction_category": "GROCERY"},
    },
    "dead-letter-queue": {
        "input": {"data": {"id": "fixture"}},
        "expected": {"status": "success"},
    },
    "deduplicate-events": {
        "input": {"event_id": "evt-1", "timestamp": "2026-10-05T12:00:00Z"},
        "expected": {"is_duplicate": False},
    },
    "encrypt-data": {
        "input": {
            "payment": {"card_number": "4111111111111111", "expiration": "12/30"},
            "customer": {
                "email": "fixture@example.test",
                "ssn": "123-45-6789",
                "phone": "202-555-0100",
            },
            "address": {
                "zip": "20001",
                "city": "Washington",
                "state": "DC",
                "country": "US",
            },
        },
        "expected": {"encryption_metadata": {"encrypted": True}},
    },
    "encryption-patterns": {
        "input": {
            "payment": {"card_number": "4111111111111111", "expiration": "12/30"},
            "customer": {
                "email": "fixture@example.test",
                "ssn": "123-45-6789",
                "phone": "202-555-0100",
            },
            "billing_address": {
                "zip": "20001",
                "city": "Washington",
                "state": "DC",
                "country": "US",
            },
        },
        "expected": {"processing_metadata": {"encryption_status": "success"}},
    },
    "enforce-schema": {
        "input": {
            "event_id": "evt-1",
            "event_type": "fixture.created",
            "timestamp": "2026-10-05T12:00:00Z",
            "data": {"value": 1},
        },
        "expected": {"event_id": "evt-1"},
    },
    "enrich-export": {
        "input": {"level": "INFO", "message": "fixture", "service": "api"},
        "expected": {"event": {"application": {"service": "api"}}},
    },
    "fan-out-kafka": {
        "input": {"event_id": "evt-1", "value": 1},
        "expected": {"event_id": "evt-1"},
    },
    "fan-out-pattern": {
        "input": {"event_id": "evt-1", "value": 1},
        "expected": {"event_id": "evt-1"},
    },
    "fan-out-s3": {
        "input": {"event_id": "evt-1", "value": 1},
        "expected": {"event_id": "evt-1"},
    },
    "filter-severity": {
        "input": "2026-10-05 12:00:00 [ERROR] fixture failure",
        "expected": {"level": "ERROR", "original_format": "structured_text"},
        "raw": True,
    },
    "http-webhook-ingestion": {
        "input": {"event": {"id": "evt-1", "type": "fixture.created"}},
        "expected": {"_event_type": "fixture.created"},
        "signed": True,
    },
    "kafka-to-s3": {
        "input": {"event_id": "evt-1", "value": 1},
        "expected": {"event_id": "evt-1"},
    },
    "nightly-backup": {
        "input": {"id": "row-1", "sku": "fixture", "quantity": 2},
        "expected": {"id": "row-1"},
    },
    "normalize-timestamps": {
        "input": {"event_id": "evt-1", "timestamp": "2026-10-05T12:00:00Z"},
        "expected": {"format_detected": "iso8601_offset"},
    },
    "parse-logs": {
        "input": '{"level":"ERROR","message":"fixture"}',
        "expected": {"format": "json", "level": "ERROR"},
        "raw": True,
    },
    "priority-queues": {
        "input": {
            "event_id": "evt-1",
            "severity": "ERROR",
            "customer_tier": "premium",
            "event_type": "payment.failed",
        },
        "expected": {"priority_queue": "high"},
    },
    "production-log-pipeline": {
        "input": {
            "timestamp": "2026-10-05T12:00:00Z",
            "level": "ERROR",
            "service": "api",
            "message": "Contact fixture@example.test",
            "source_ip": "192.0.2.10",
        },
        "expected": {"priority": "high", "message": "Contact [EMAIL]"},
    },
    "rate-limiting": {
        "input": {"event_id": "evt-1", "value": 1},
        "expected": {"event_id": "evt-1"},
    },
    "remove-pii": {
        "input": {
            "user_name": "Fixture Person",
            "email": "fixture@example.test",
            "ip_address": "192.0.2.10",
            "payment_method": {
                "type": "card",
                "last_four": "1111",
                "full_number": "4111111111111111",
                "expiry": "12/30",
            },
            "location": {
                "city": "Washington",
                "state": "DC",
                "country": "US",
                "latitude": 38.9,
                "longitude": -77.0,
            },
        },
        "expected": {"email_domain": "example.test", "user_id": "__present__"},
    },
    "s3-to-postgres": {
        "input": '{"id":"row-1","value":1}',
        "expected": {"id": "row-1"},
        "raw": True,
    },
    "secure-slack-pipeline": {
        "input": {"channel": "C123", "limit": 1},
        "expected": {"source": "slack", "count": 1, "sensitivity": "redacted"},
        "headers": {"X-Expanso-Api-Key": "fixture-key"},
    },
    "smart-buffering": {
        "input": {
            "event_id": "evt-1",
            "category": "important",
            "timestamp": "2026-10-05T12:00:00Z",
        },
        "expected": {"priority_label": "important", "priority_tier": 1},
    },
    "transform-formats": {
        "input": '{"event_id":"evt-1","value":1}',
        "expected": {
            "transformation": {"source_format": "json", "target_format": "json"}
        },
        "raw": True,
    },
}


@dataclass
class Edge:
    api_url: str
    data_dir: Path
    log_file: Path
    process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        binary = shutil.which("expanso-edge")
        if not binary:
            raise RuntimeError("expanso-edge is required")
        env = os.environ.copy()
        env.update(FIXTURE_ENV)
        command = [
            binary,
            "run",
            "--local",
            "--no-watch",
            "--api-listen",
            self.api_url.removeprefix("http://"),
            "--data-dir",
            str(self.data_dir),
            "--log-level",
            "warn",
        ]
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log = self.log_file.open("w")
        self.process = subprocess.Popen(command, stdout=log, stderr=log, env=env, text=True)

    def stop(self) -> None:
        if not self.process:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(port: int, timeout: float = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


def wait_for_api(cli: str, api_url: str, timeout: float = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            [cli, "job", "list", "--endpoint", api_url],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True
        time.sleep(0.2)
    return False


def tool_evidence(binary: str) -> dict[str, str]:
    resolved = Path(binary).resolve()
    version = subprocess.run(
        [str(resolved), "version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return {
        "path": str(resolved),
        "version": (version.stdout or version.stderr).strip(),
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def mock_internal_http(value: Any) -> int:
    """Replace provider HTTP processors in a disposable recipe job."""
    replaced = 0
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and set(item) == {"http"}:
                url = str(item["http"].get("url", ""))
                if "slack" in url.lower() or "this.url" in url:
                    fixture = {
                        "ok": True,
                        "messages": [
                            {
                                "ts": "1728136800.000001",
                                "text": "Contact fixture@example.test",
                            }
                        ],
                    }
                else:
                    fixture = {"fixture": True, "provider": "enrichment"}
                item.clear()
                item["mapping"] = "root = " + json.dumps(fixture, separators=(",", ":"))
                replaced += 1
            else:
                replaced += mock_internal_http(item)
    elif isinstance(value, dict):
        for child in value.values():
            replaced += mock_internal_http(child)
    return replaced


def expected_errors(expected: Any, actual: Any, path: str = "root") -> list[str]:
    if expected == "__present__":
        return [] if actual not in (None, "") else [f"{path} is not present"]
    if isinstance(expected, dict):
        if isinstance(actual, list):
            candidates = [expected_errors(expected, item, path) for item in actual]
            if any(not errors for errors in candidates):
                return []
            return candidates[0] if candidates else [f"{path} contains no outputs"]
        if not isinstance(actual, dict):
            return [f"{path} expected object, got {type(actual).__name__}"]
        errors: list[str] = []
        for key, expected_value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key} is missing")
                continue
            errors.extend(expected_errors(expected_value, actual[key], f"{path}.{key}"))
        return errors
    if expected != actual:
        return [f"{path} expected {expected!r}, got {actual!r}"]
    return []


def response_output(response: requests.Response) -> Any:
    content_type = response.headers.get("Content-Type", "")
    if content_type.lower().startswith("multipart/"):
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\n\r\n".encode() + response.content
        )
        outputs: list[Any] = []
        for part in message.iter_parts():
            body = part.get_content()
            try:
                outputs.append(json.loads(body))
            except (json.JSONDecodeError, TypeError):
                outputs.append(body)
        return outputs
    if not response.text:
        return None
    try:
        return response.json()
    except requests.JSONDecodeError:
        return response.text


def execute_recipe(
    path: Path,
    fixture: dict[str, Any],
    cli: str,
    edge_bin: str,
    api_url: str,
    run_dir: Path,
    edge_log: Path,
) -> dict[str, Any]:
    name = path.parent.name
    original = path.read_bytes()
    validate = subprocess.run(
        [edge_bin, "validate", str(path.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if validate.returncode != 0:
        return {
            "name": name,
            "pipeline": str(path.relative_to(REPO)),
            "sha256": hashlib.sha256(original).hexdigest(),
            "status": "fail",
            "reason": "published pipeline does not validate",
            "validation_output": (validate.stdout + validate.stderr).strip(),
        }

    spec = yaml.safe_load(original)
    config = spec.setdefault("config", {})
    port = free_port()
    config["input"] = {
        "http_server": {
            "address": f"127.0.0.1:{port}",
            "path": "/test",
            "allowed_verbs": ["POST"],
            "timeout": "30s",
        }
    }
    config["output"] = {"sync_response": {}}
    removed_buffer = config.pop("buffer", None) is not None
    mocked_http = mock_internal_http(config.get("pipeline", {}).get("processors", []))
    spec["name"] = f"recipe-{name}-test-{port}"

    jobs = run_dir / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    job = jobs / f"{name}-{uuid.uuid4().hex}.yaml"
    job.write_text(yaml.safe_dump(spec, sort_keys=False))
    deploy = subprocess.run(
        [cli, "job", "deploy", str(job), "--endpoint", api_url],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    evidence = {
        "name": name,
        "pipeline": str(path.relative_to(REPO)),
        "sha256": hashlib.sha256(original).hexdigest(),
        "input": fixture["input"],
        "expected": fixture["expected"],
        "fixture_changes": {
            "localhost_io": True,
            "removed_event_time_buffer": removed_buffer,
            "mocked_internal_http_processors": mocked_http,
        },
    }
    if deploy.returncode != 0:
        return evidence | {
            "status": "fail",
            "reason": "job deploy failed",
            "deploy_output": (deploy.stdout + deploy.stderr).strip(),
        }
    try:
        if not wait_for_port(port):
            return evidence | {"status": "fail", "reason": "HTTP input did not start"}
        request_input = fixture["input"]
        headers = {str(k): str(v) for k, v in fixture.get("headers", {}).items()}
        if fixture.get("raw"):
            body = request_input if isinstance(request_input, str) else json.dumps(request_input)
            raw = body.encode()
            headers.setdefault("Content-Type", "text/plain; charset=utf-8")
        else:
            raw = json.dumps(request_input, separators=(",", ":")).encode()
            headers.setdefault("Content-Type", "application/json")
        if fixture.get("signed"):
            signature = hmac.new(
                FIXTURE_ENV["WEBHOOK_SECRET"].encode(), raw, hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        offset = edge_log.stat().st_size if edge_log.exists() else 0
        response = requests.post(
            f"http://127.0.0.1:{port}/test",
            data=raw,
            headers=headers,
            timeout=30,
        )
        output = response_output(response)
        time.sleep(0.1)
        with edge_log.open("rb") as handle:
            handle.seek(offset)
            log_text = handle.read().decode(errors="replace")
        edge_errors = [line for line in log_text.splitlines() if " ERR " in line]
        errors = []
        if not 200 <= response.status_code < 300:
            errors.append(f"HTTP status {response.status_code}")
        errors.extend(expected_errors(fixture["expected"], output))
        if edge_errors:
            errors.append("unexpected Edge errors")
        return evidence | {
            "status": "pass" if not errors else "fail",
            "status_code": response.status_code,
            "output": output,
            "edge_errors": edge_errors,
            "errors": errors,
        }
    except Exception as exc:
        return evidence | {"status": "fail", "reason": f"request failed: {exc}"}
    finally:
        subprocess.run(
            [
                cli,
                "job",
                "delete",
                spec["name"],
                "--endpoint",
                api_url,
                "--yes",
                "--force",
            ],
            capture_output=True,
            text=True,
            check=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipes", nargs="*", help="Recipe names to run")
    parser.add_argument(
        "--report",
        default=".conformance/recipe-execution.json",
        help="JSON evidence report path",
    )
    args = parser.parse_args()

    cli = shutil.which("expanso-cli")
    edge_bin = shutil.which("expanso-edge")
    if not cli or not edge_bin:
        print("expanso-cli and expanso-edge are required", file=os.sys.stderr)
        return 1

    paths = sorted(RECIPES.glob("*/pipeline.yaml"))
    if args.recipes:
        selected = set(args.recipes)
        paths = [path for path in paths if path.parent.name in selected]
    missing_fixtures = [path.parent.name for path in paths if path.parent.name not in FIXTURES]
    if not paths or missing_fixtures:
        print(
            "recipe fixture coverage failed: "
            + (", ".join(missing_fixtures) if missing_fixtures else "no recipes found"),
            file=os.sys.stderr,
        )
        return 1

    run_dir = CONFORMANCE / (time.strftime("recipes-%Y%m%dT%H%M%SZ", time.gmtime()))
    run_dir.mkdir(parents=True, exist_ok=False)
    api_url = f"http://127.0.0.1:{free_port()}"
    edge = Edge(api_url, run_dir / "edge-data", run_dir / "edge.log")
    edge.start()
    atexit.register(edge.stop)
    if not wait_for_api(cli, api_url):
        edge.stop()
        print("expanso-edge local API did not start", file=os.sys.stderr)
        return 1

    report = {
        "schema": "expanso-recipe-execution/1",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "Expanso Edge local; deterministic fixtures; published processors",
        "tools": {
            "expanso_edge": tool_evidence(edge_bin),
            "expanso_cli": tool_evidence(cli),
        },
        "recipes": [],
        "variants": [],
    }
    try:
        for path in paths:
            result = execute_recipe(
                path,
                FIXTURES[path.parent.name],
                cli,
                edge_bin,
                api_url,
                run_dir,
                edge.log_file,
            )
            report["recipes"].append(result)
            suffix = "" if result["status"] == "pass" else f": {result.get('errors') or result.get('reason')}"
            print(f"{result['status'].upper():4} {result['name']}{suffix}")
        if not args.recipes:
            for path, fixture in SPECIAL_VARIANTS.items():
                result = execute_recipe(
                    path,
                    fixture,
                    cli,
                    edge_bin,
                    api_url,
                    run_dir,
                    edge.log_file,
                )
                report["variants"].append(result)
                suffix = (
                    ""
                    if result["status"] == "pass"
                    else f": {result.get('errors') or result.get('reason')}"
                )
                print(f"{result['status'].upper():4} {result['name']} cloud{suffix}")
    finally:
        edge.stop()
        atexit.unregister(edge.stop)

    all_results = report["recipes"] + report["variants"]
    passing = sum(row["status"] == "pass" for row in all_results)
    report["totals"] = {
        "recipes": len(report["recipes"]),
        "variants": len(report["variants"]),
        "pass": passing,
        "fail": len(all_results) - passing,
        "skipped": 0,
    }
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["totals"], sort_keys=True))
    return 0 if passing == len(all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
