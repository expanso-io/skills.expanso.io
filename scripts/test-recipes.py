# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise published recipe adapters on Expanso Edge without rewriting them.

Recipes whose real dependencies are unavailable in CI are reported as skipped
with the exact adapters that require an integration environment. Validation is
still fail-closed for every published recipe. A skipped row is never execution
proof and is carried into the public conformance ledger as such.
"""

from __future__ import annotations

import argparse
import atexit
import fcntl
import hashlib
import json
import os
import signal
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests
import yaml


REPO = Path(__file__).resolve().parents[1]
RECIPES = REPO / "skills" / "recipes"
CONFORMANCE = REPO / ".conformance"
PORT_RANGE_START = 20_000
PORT_RANGE_STOP = 30_000
_PORT_LOCKS: list[Any] = []

VALID_ENCRYPTION_ENV = {
    "FIELD_ENCRYPTION_KEY_HEX": "0123456789abcdef" * 4,
    "FIELD_MAC_KEY": "fixture-field-mac-key-at-least-32-characters",
}

ENCRYPTION_INPUT = {
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
}


@dataclass
class Edge:
    api_url: str
    data_dir: Path
    log_file: Path
    work_dir: Path
    env: dict[str, str]
    process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        binary = shutil.which("expanso-edge")
        if not binary:
            raise RuntimeError("expanso-edge is required")
        process_env = os.environ.copy()
        process_env.update(self.env)
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
            os.environ.get("EXPANSO_TEST_LOG_LEVEL", "warn"),
        ]
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log = self.log_file.open("w")
        self.process = subprocess.Popen(
            command,
            cwd=self.work_dir,
            stdout=log,
            stderr=log,
            env=process_env,
            text=True,
            start_new_session=True,
        )

    def stop(self) -> None:
        if not self.process:
            return
        process_group = self.process.pid
        if self.process.poll() is None:
            os.killpg(process_group, signal.SIGTERM)
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process_group, signal.SIGKILL)
            self.process.wait(timeout=5)
        self.process = None


class SlackFixtureHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self.__class__.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization", ""),
            }
        )
        payload = {
            "ok": True,
            "messages": [
                {
                    "ts": "1728136800.000001",
                    "text": "Contact fixture@example.test",
                }
            ],
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def port_candidates():
    """Yield the dedicated harness range in a process-specific order."""
    size = PORT_RANGE_STOP - PORT_RANGE_START
    start = (os.getpid() * 7919) % size
    for offset in range(size):
        yield PORT_RANGE_START + ((start + offset) % size)


def free_port() -> int:
    """Lock a non-ephemeral port for this run before returning it."""
    lock_dir = CONFORMANCE / "port-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    for port in port_candidates():
        lock_handle = (lock_dir / f"{port}.lock").open("a+")
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_handle.close()
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("0.0.0.0", port))
        except OSError:
            lock_handle.close()
            continue
        _PORT_LOCKS.append(lock_handle)
        return port
    raise RuntimeError("no free port in dedicated harness range 20000-29999")


def wait_for_port(port: int, timeout: float = 20) -> bool:
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


def wait_for_api(cli: str, api_url: str, timeout: float = 20) -> bool:
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


TERMINAL_EXECUTION_STATES = {
    "cancelled",
    "canceled",
    "completed",
    "failed",
    "stopped",
}


def wait_for_execution_running(
    cli: str,
    job_name: str,
    api_url: str,
    timeout: float = 45,
    namespace: str = "",
) -> tuple[bool, str]:
    """Wait for Edge's execution state, not the earlier TCP bind."""
    deadline = time.monotonic() + timeout
    job_id = ""
    last_state = "missing"
    while time.monotonic() < deadline:
        if not job_id:
            describe_command = [
                cli,
                "job",
                "describe",
                job_name,
                "--endpoint",
                api_url,
                "--format",
                "json",
            ]
            if namespace:
                describe_command.extend(["--namespace", namespace])
            described = subprocess.run(
                describe_command,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if described.returncode == 0:
                try:
                    job_id = str(json.loads(described.stdout).get("id", ""))
                except json.JSONDecodeError:
                    pass
        if job_id:
            listed = subprocess.run(
                [
                    cli,
                    "execution",
                    "list",
                    "--job-id",
                    job_id,
                    "--endpoint",
                    api_url,
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if listed.returncode == 0:
                try:
                    rows = json.loads(listed.stdout)
                except json.JSONDecodeError:
                    rows = []
                states = [
                    str(row.get("status", {}).get("observed_state", {}).get(
                        "state_type", "missing"
                    )).lower()
                    for row in rows
                    if isinstance(row, dict)
                ]
                if "running" in states:
                    return True, "running"
                terminal = next(
                    (state for state in states if state in TERMINAL_EXECUTION_STATES),
                    None,
                )
                if terminal:
                    return False, f"execution reached terminal state {terminal}"
                if states:
                    last_state = ", ".join(states)
        time.sleep(0.2)
    return False, (
        f"execution did not reach running within {timeout:g}s "
        f"(last state: {last_state})"
    )


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


def base_evidence(path: Path) -> dict[str, Any]:
    return {
        "name": path.parent.name,
        "pipeline": str(path.relative_to(REPO)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def validate_pipeline(path: Path, edge_bin: str) -> tuple[bool, str]:
    result = subprocess.run(
        [edge_bin, "validate", str(path.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def unsupported_reason(path: Path) -> str:
    reasons = json.loads((REPO / "scripts/integration-skip-reasons.json").read_text())
    relative = str(path.relative_to(REPO))
    if relative not in reasons:
        raise RuntimeError(f"missing per-example integration reason: {relative}")
    return reasons[relative]


def deploy(path: Path, cli: str, api_url: str) -> tuple[bool, str, str]:
    document = yaml.safe_load(path.read_text())
    name = str(document["name"])
    result = subprocess.run(
        [cli, "job", "deploy", str(path), "--endpoint", api_url],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return result.returncode == 0, name, (result.stdout + result.stderr).strip()


def delete_job(
    cli: str,
    name: str,
    api_url: str,
    namespace: str = "",
) -> None:
    target = name
    if namespace:
        described = subprocess.run(
            [
                cli,
                "job",
                "describe",
                name,
                "--namespace",
                namespace,
                "--endpoint",
                api_url,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if described.returncode == 0:
            try:
                target = str(json.loads(described.stdout).get("id", name))
            except json.JSONDecodeError:
                pass
    subprocess.run(
        [
            cli,
            "job",
            "delete",
            target,
            "--endpoint",
            api_url,
            "--yes",
            "--force",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def run_edge_case(
    path: Path,
    cli: str,
    run_dir: Path,
    env: dict[str, str],
    request: dict[str, Any],
) -> tuple[requests.Response | None, Edge, str | None]:
    api_url = f"http://127.0.0.1:{free_port()}"
    case_dir = run_dir / f"{path.parent.name}-{time.time_ns()}"
    case_dir.mkdir(parents=True)
    edge = Edge(
        api_url=api_url,
        data_dir=case_dir / "edge-data",
        log_file=case_dir / "edge.log",
        work_dir=case_dir,
        env=env,
    )
    edge.start()
    atexit.register(edge.stop)
    if not wait_for_api(cli, api_url):
        return None, edge, "expanso-edge local API did not start"
    document = yaml.safe_load(path.read_text())
    namespace = str(document.get("namespace", ""))
    ok, job_name, deploy_output = deploy(path, cli, api_url)
    if not ok:
        return None, edge, f"job deploy failed: {deploy_output}"
    port = int(request["port"])
    try:
        ready, reason = wait_for_execution_running(
            cli,
            job_name,
            api_url,
            timeout=45,
            namespace=namespace,
        )
        if not ready:
            return None, edge, reason
        if not wait_for_port(port):
            return None, edge, f"published HTTP input did not listen on {port}"
        response = requests.request(
            request.get("method", "POST"),
            f"http://127.0.0.1:{port}{request['path']}",
            data=request.get("data"),
            json=request.get("json"),
            headers=request.get("headers"),
            timeout=30,
        )
        time.sleep(0.3)
        return response, edge, None
    finally:
        delete_job(cli, job_name, api_url, namespace=namespace)


def stop_edge(edge: Edge) -> None:
    edge.stop()
    atexit.unregister(edge.stop)


def run_transform_formats(path: Path, cli: str, run_dir: Path) -> dict[str, Any]:
    evidence = base_evidence(path)
    response, edge, error = run_edge_case(
        path,
        cli,
        run_dir,
        {},
        {
            "port": 8080,
            "path": "/transform",
            "data": '{"event_id":"evt-1","value":1}',
            "headers": {"Content-Type": "application/json"},
        },
    )
    try:
        output = response.json() if response and response.text else None
        errors = []
        if error:
            errors.append(error)
        if response is None or not 200 <= response.status_code < 300:
            errors.append("published HTTP adapter did not return success")
        expected = {"source_format": "json", "target_format": "json"}
        actual = output.get("transformation") if isinstance(output, dict) else None
        if actual is None or any(actual.get(k) != v for k, v in expected.items()):
            errors.append("transformation output did not match the sample")
        return evidence | {
            "status": "pass" if not errors else "fail",
            "input": {"event_id": "evt-1", "value": 1},
            "expected": {"transformation": expected},
            "output": output,
            "errors": errors,
            "published_adapters_intact": True,
        }
    finally:
        stop_edge(edge)


def run_secure_slack(path: Path, cli: str, run_dir: Path) -> dict[str, Any]:
    evidence = base_evidence(path)
    fixture_port = free_port()
    SlackFixtureHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", fixture_port), SlackFixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    response, edge, error = run_edge_case(
        path,
        cli,
        run_dir,
        {
            "ACCESS_POLICY": "*:slack-read:read",
            "EXPANSO_API_KEYS": "fixture-key:fixture-agent",
            "SLACK_API_URL": f"http://127.0.0.1:{fixture_port}",
            "SLACK_BOT_TOKEN": "fixture-token",
        },
        {
            "port": 4195,
            "path": "/secure-slack-read",
            "json": {"channel": "C123", "limit": 1},
            "headers": {"X-Expanso-Api-Key": "fixture-key"},
        },
    )
    try:
        output = response.json() if response and response.text else None
        errors = []
        if error:
            errors.append(error)
        if not isinstance(output, dict) or output.get("count") != 1:
            errors.append("Slack-compatible response was not normalized")
        serialized = json.dumps(output)
        if "fixture@example.test" in serialized or "[EMAIL]" not in serialized:
            errors.append("published redaction stage did not remove the email")
        calls = SlackFixtureHandler.requests
        if len(calls) != 1 or calls[0]["authorization"] != "Bearer fixture-token":
            errors.append(
                "published HTTP adapter did not authenticate the provider call"
            )
        return evidence | {
            "status": "pass" if not errors else "fail",
            "input": {"channel": "C123", "limit": 1},
            "expected": {"count": 1, "sensitivity": "redacted"},
            "output": output,
            "provider_requests": calls,
            "errors": errors,
            "published_adapters_intact": True,
            "test_environment": "local Slack-compatible HTTP fixture",
        }
    finally:
        stop_edge(edge)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_encryption_patterns(path: Path, cli: str, run_dir: Path) -> dict[str, Any]:
    evidence = base_evidence(path)
    response, valid_edge, valid_error = run_edge_case(
        path,
        cli,
        run_dir,
        VALID_ENCRYPTION_ENV,
        {"port": 8080, "path": "/encrypt", "json": ENCRYPTION_INPUT},
    )
    valid_dir = valid_edge.work_dir
    try:
        encrypted_files = list(valid_dir.glob("encrypted-data-*.jsonl"))
        audit_files = list(valid_dir.glob("audit-trail-*.jsonl"))
        output = None
        if encrypted_files:
            output = json.loads(encrypted_files[0].read_text().splitlines()[0])
        valid_errors = []
        if valid_error:
            valid_errors.append(valid_error)
        if response is None or not 200 <= response.status_code < 300:
            valid_errors.append("valid encryption request did not complete")
        if not isinstance(output, dict):
            valid_errors.append("encrypted file output was not produced")
        elif (
            output.get("processing_metadata", {}).get("encryption_status") != "success"
        ):
            valid_errors.append("encrypted output did not report success")
        if not audit_files:
            valid_errors.append("audit output was not produced")
        published_bytes = b"".join(file.read_bytes() for file in encrypted_files)
        for plaintext in (
            b"4111111111111111",
            b"fixture@example.test",
            b"123-45-6789",
        ):
            if plaintext in published_bytes:
                valid_errors.append("plaintext leaked into encrypted output")
                break
    finally:
        stop_edge(valid_edge)

    invalid_env = VALID_ENCRYPTION_ENV | {"FIELD_ENCRYPTION_KEY_HEX": "invalid"}
    invalid_response, invalid_edge, invalid_error = run_edge_case(
        path,
        cli,
        run_dir,
        invalid_env,
        {"port": 8080, "path": "/encrypt", "json": ENCRYPTION_INPUT},
    )
    try:
        invalid_outputs = list(invalid_edge.work_dir.glob("encrypted-data-*.jsonl"))
        invalid_audits = list(invalid_edge.work_dir.glob("audit-trail-*.jsonl"))
        invalid_errors = []
        if invalid_error:
            invalid_errors.append(invalid_error)
        if invalid_response is None:
            invalid_errors.append("invalid-key request was not observed")
        if invalid_outputs or invalid_audits:
            invalid_errors.append("invalid encryption key produced downstream output")
        edge_log = invalid_edge.log_file.read_text(errors="replace")
        for plaintext in (
            "4111111111111111",
            "fixture@example.test",
            "123-45-6789",
        ):
            if plaintext in edge_log:
                invalid_errors.append("plaintext leaked into Edge error logs")
                break
    finally:
        stop_edge(invalid_edge)

    errors = valid_errors + invalid_errors
    return evidence | {
        "status": "pass" if not errors else "fail",
        "input": ENCRYPTION_INPUT,
        "expected": {
            "valid_key": "encrypted and audited",
            "invalid_key": "no output and no plaintext leak",
        },
        "output": output,
        "invalid_key_response_body": (
            invalid_response.text if invalid_response is not None else None
        ),
        "errors": errors,
        "published_adapters_intact": True,
    }


def run_webhook_fanout_rejection(cli: str, run_dir: Path) -> dict[str, Any]:
    path = REPO / "skills" / "jobs" / "webhook-fan-out" / "pipeline.yaml"
    response, edge, error = run_edge_case(
        path,
        cli,
        run_dir,
        {
            "WEBHOOK_SECRET": "fixture-webhook-secret",
            "RECEIVER_A_HOST": "receiver-a.invalid",
            "RECEIVER_A_TOKEN": "fixture-a",
            "RECEIVER_B_HOST": "receiver-b.invalid",
            "RECEIVER_B_TOKEN": "fixture-b",
            "RECEIVER_C_HOST": "receiver-c.invalid",
            "RECEIVER_C_TOKEN": "fixture-c",
        },
        {
            "port": 8089,
            "path": "/webhook",
            "json": {"event": {"type": "untrusted"}},
            "headers": {"X-Webhook-Signature": "invalid"},
        },
    )
    try:
        errors = []
        if error:
            errors.append(error)
        if response is None:
            errors.append("invalid-signature request was not observed")
        elif response.text.strip():
            errors.append("invalid-signature request produced a response body")
        edge_log = edge.log_file.read_text(errors="replace")
        if "receiver-a.invalid" in edge_log or "receiver-b.invalid" in edge_log:
            errors.append("invalid-signature request reached a fan-out receiver")
        if "receiver-c.invalid" in edge_log:
            errors.append("invalid-signature request reached a fan-out receiver")
        return base_evidence(path) | {
            "check": "invalid webhook signatures are deleted before fan-out",
            "status": "pass" if not errors else "fail",
            "response_body": response.text if response is not None else None,
            "errors": errors,
            "published_adapters_intact": True,
        }
    finally:
        stop_edge(edge)


def execute_recipe(path: Path, cli: str, run_dir: Path) -> dict[str, Any]:
    runners = {
        "encryption-patterns": run_encryption_patterns,
        "secure-slack-pipeline": run_secure_slack,
        "transform-formats": run_transform_formats,
    }
    runner = runners.get(path.parent.name)
    if runner is None:
        return base_evidence(path) | {
            "status": "skipped",
            "reason": unsupported_reason(path),
            "published_adapters_intact": True,
        }
    return runner(path, cli, run_dir)


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
    if not paths:
        print("no recipes selected", file=os.sys.stderr)
        return 1

    run_dir = CONFORMANCE / time.strftime("recipes-%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "schema": "expanso-recipe-execution/2",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "Expanso Edge local; published adapters intact",
        "tools": {
            "expanso_edge": tool_evidence(edge_bin),
            "expanso_cli": tool_evidence(cli),
        },
        "recipes": [],
        "variants": [],
        "security_checks": [],
    }
    for path in paths:
        valid, validation_output = validate_pipeline(path, edge_bin)
        if valid:
            result = execute_recipe(path, cli, run_dir)
        else:
            result = base_evidence(path) | {
                "status": "fail",
                "reason": "published pipeline does not validate",
                "validation_output": validation_output,
            }
        report["recipes"].append(result)
        suffix = (
            ""
            if result["status"] == "pass"
            else f": {result.get('errors') or result.get('reason')}"
        )
        print(f"{result['status'].upper():7} {result['name']}{suffix}")

    if not args.recipes:
        for regression_script in ["test-review-round-two.py", "test-review-round-four.py", "test-review-round-six.py", "test-review-round-seven.py", "test-circuit-failover.py", "test-publication-review.py", "test-time-and-policy.py", "test-backup-and-html.py", "test-auth-html-formats.py", "test-provider-and-cache.py", "test-current-review.py", "test-pages-and-periods.py"]:
            regressions = subprocess.run(
                ["uv", "run", "-s", str(REPO / "scripts" / regression_script)],
                cwd=REPO, check=False,
            )
            report["security_checks"].append({
                "name": regression_script,
                "status": "pass" if regressions.returncode == 0 else "fail",
                "supplemental_evidence": json.loads((CONFORMANCE / "focused-regressions.json").read_text()) if regressions.returncode == 0 else None,
            })
        webhook_check = run_webhook_fanout_rejection(cli, run_dir)
        report["security_checks"].append(webhook_check)
        print(f"{webhook_check['status'].upper():7} webhook-fan-out rejection")

        cloud_path = (
            REPO / "skills" / "transforms" / "json-pretty" / "pipeline-cloud.yaml"
        )
        valid, validation_output = validate_pipeline(cloud_path, edge_bin)
        cloud = base_evidence(cloud_path)
        if valid:
            cloud |= {
                "status": "skipped",
                "reason": unsupported_reason(cloud_path),
                "published_adapters_intact": True,
            }
        else:
            cloud |= {
                "status": "fail",
                "reason": "published pipeline does not validate",
                "validation_output": validation_output,
            }
        report["variants"].append(cloud)
        print(f"{cloud['status'].upper():7} json-pretty cloud: {cloud.get('reason')}")

    rows = report["recipes"] + report["variants"] + report["security_checks"]
    report["totals"] = {
        "recipes": len(report["recipes"]),
        "variants": len(report["variants"]),
        "pass": sum(row["status"] == "pass" for row in rows),
        "fail": sum(row["status"] == "fail" for row in rows),
        "skipped": sum(row["status"] == "skipped" for row in rows),
    }
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["totals"], sort_keys=True))
    return 0 if report["totals"]["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
