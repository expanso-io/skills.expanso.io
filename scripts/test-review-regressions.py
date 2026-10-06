# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute focused processor and resource regressions on local Expanso Edge.

External boundaries use a loopback HTTP fixture; published processor graphs
are unchanged except HTTP transport destinations and retry timing. Selected
subgraphs are unit contracts, not end-to-end platform execution proof.
"""
from __future__ import annotations

import copy
import importlib.util
import hashlib
import json
import shutil
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("recipe_runner", ROOT / "scripts/test-recipes.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
EVIDENCE = []
TOKEN = "regression-bearer-token-at-least-32-characters"
AUTH_SKILLS = [
    "ai/audio-transcribe", "ai/video-generate", "connectors/gmail-read",
    "connectors/slack-read", "workflows/stripe-reports", "workflows/voice-admin",
    "workflows/jira-automate", "workflows/todoist-automate", "workflows/email-triage",
]


class Provider(BaseHTTPRequestHandler):
    calls = []
    status = 200

    def reply(self):
        size = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(size)
        self.__class__.calls.append(self.path)
        body = {"vulns": []}
        if "/mailFolders/" in self.path:
            query = parse_qs(urlsplit(self.path).query)
            cutoff = query.get("$filter", [""])[0]
            now = datetime.now(timezone.utc)
            dates = [("old", now - timedelta(days=7)), ("recent", now - timedelta(minutes=10))]
            minimum = datetime.fromisoformat(cutoff.removeprefix("receivedDateTime ge ").replace("Z", "+00:00")) if cutoff else now - timedelta(days=30)
            body = {"value": [{"id": name, "receivedDateTime": date.isoformat(), "subject": name} for name, date in dates if date >= minimum]}
        data = json.dumps(body).encode()
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if self.status != 204:
            self.wfile.write(data)

    do_GET = reply
    do_POST = reply
    do_PUT = reply

    def log_message(self, *_):
        pass


def config(skill, variant="cli"):
    path = ROOT / "skills" / skill / f"pipeline-{variant}.yaml"
    if variant == "recipe":
        path = ROOT / "skills" / skill / "pipeline.yaml"
    return yaml.safe_load(path.read_text())["config"] | {"_source_pipeline": str(path.relative_to(ROOT))}


def http_transports(node, endpoint):
    if isinstance(node, list):
        for child in node:
            http_transports(child, endpoint)
    elif isinstance(node, dict):
        for key, child in node.items():
            if key == "http" and isinstance(child, dict) and "url" in child:
                child.update(url=endpoint, retries=0)
            else:
                http_transports(child, endpoint)


class Suite:
    def __init__(self, directory, env):
        self.directory = directory
        self.api = f"http://127.0.0.1:{runner.free_port()}"
        self.edge = runner.Edge(self.api, directory / "data", directory / "edge.log", directory, env)
        self.edge.start()
        if not runner.wait_for_api(CLI, self.api):
            self.edge.stop()
            raise RuntimeError("Edge did not start")
        self.count = 0

    def close(self):
        self.edge.stop()

    def execute(
        self,
        cfg,
        payload,
        headers=None,
        retain_input=False,
        retain_output=False,
        repeat=1,
        raw=False,
        decode_json=True,
    ):
        self.count += 1
        cfg = copy.deepcopy(cfg)
        source = cfg.pop("_source_pipeline", None)
        cfg.pop("http", None)
        port = runner.free_port()
        inbound = cfg.get("input", {}).get("http_server", {}) if retain_input else {}
        inbound.update(address=f"127.0.0.1:{port}", path="/test", timeout="10s", allowed_verbs=["POST"])
        inbound.pop("cert_file", None)
        inbound.pop("key_file", None)
        cfg["input"] = {"http_server": inbound}
        if not retain_output:
            cfg["output"] = {"sync_response": {}}
        name = f"regression-{self.count}"
        path = self.directory / f"{name}.yaml"
        path.write_text(yaml.safe_dump({"name": name, "type": "pipeline", "config": cfg}, sort_keys=False))
        ok, _, output = runner.deploy(path, CLI, self.api)
        assert ok, output
        try:
            ready, reason = runner.wait_for_execution_running(
                CLI, name, self.api, timeout=45
            )
            assert ready, reason
            assert runner.wait_for_port(port), path.read_text()
            results = []
            for _ in range(repeat):
                request_headers = dict(headers or {})
                if raw:
                    request_headers.setdefault("Content-Type", "text/plain")
                    response = requests.post(
                        f"http://127.0.0.1:{port}/test",
                        data=payload,
                        headers=request_headers,
                        timeout=15,
                    )
                else:
                    response = requests.post(
                        f"http://127.0.0.1:{port}/test",
                        json=payload,
                        headers=request_headers,
                        timeout=15,
                    )
                result = (response.json() if decode_json else response.text) if response.content else None
                if source:
                    EVIDENCE.append({
                        "pipeline": source,
                        "sha256": hashlib.sha256((ROOT / source).read_bytes()).hexdigest(),
                        "input": payload, "output": result,
                        "job": str(path.relative_to(ROOT)),
                        "scope": "processor regression with loopback input/output and provider fixtures",
                    })
                results.append(result)
            return results if repeat > 1 else results[0]
        finally:
            runner.delete_job(CLI, name, self.api)


def main():
    directory = ROOT / ".conformance" / f"review-regressions-{time.time_ns()}"
    directory.mkdir(parents=True)
    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{provider.server_port}"
    rows = []
    suite = None
    try:
        for token in ["", "short", TOKEN]:
            group = directory / ("missing" if not token else "short" if token == "short" else "valid")
            group.mkdir()
            suite = Suite(group, {
                "MCP_BEARER_TOKEN": token, "PSEUDONYM_KEY": TOKEN,
                "TRANSFER_POLICY_ID": "fixture", "JIRA_URL": "https://jira.example.test",
                "JIRA_EMAIL": "fixture@example.test", "JIRA_API_TOKEN": "fixture",
                "TODOIST_TOKEN": "fixture", "OUTLOOK_TOKEN": "fixture",
                "OUTLOOK_API_URL": endpoint,
            })
            for skill in AUTH_SKILLS:
                guard = config(skill, "mcp")["pipeline"]["processors"][0]
                cfg = {"_source_pipeline": f"skills/{skill}/pipeline-mcp.yaml", "pipeline": {"processors": [guard, {"http": {"url": endpoint, "verb": "POST", "retries": 0}}]}}
                for supplied in ([None, token] if token != TOKEN else [None, "wrong", TOKEN]):
                    Provider.calls.clear()
                    suite.execute(cfg, {"action": "create", "content": "x"}, {"Authorization": f"Bearer {supplied}"} if supplied is not None else {})
                    assert len(Provider.calls) == int(token == TOKEN and supplied == TOKEN), (skill, token, supplied, Provider.calls)
                rows.append(f"auth:{skill}:{group.name}")
            print(f"PASS authentication: {group.name} (9 pipelines)", flush=True)
            if token != TOKEN:
                suite.close()
                suite = None
                continue
            for skill, action, request in [
                ("jira-automate", "update", {"action": "update", "issue_key": "TEST-1", "summary": "updated"}),
                ("todoist-automate", "complete", {"action": "complete", "task_id": "123"}),
            ]:
                for variant in ["cli", "mcp"]:
                    cfg = config("workflows/" + skill, variant)
                    switch = next(p["switch"] for p in cfg["pipeline"]["processors"] if "switch" in p)
                    branch = next(b for b in switch if b.get("check") == f'this.action == "{action}"')
                    cfg["pipeline"]["processors"] = branch["processors"]
                    http_transports(cfg["pipeline"], endpoint)
                    for status in [400, 204]:
                        Provider.status = status
                        result = suite.execute(cfg, request)
                        if status == 400:
                            assert result["status"] == "error" and result["error"], result
                            assert "result" not in result, result
                        else:
                            receipt = result["result"].get("issue", result["result"])
                            assert receipt.get("updated" if action == "update" else "completed") is True, result
                    rows.append(f"receipt:{skill}:{variant}")
            Provider.status = 200
            cfg = config("recipes/cross-border-gdpr", "recipe")
            sample = {"customer_id": "123", "customer_name": "Private", "customer_email": "private@example.test", "customer_dob": "1990-01-01", "customer_address": "Private", "iban": "DE123", "ip_address": "192.0.2.1", "transaction_amount": 12, "transaction_timestamp": "2026-10-06T12:00:00Z"}
            result = suite.execute(cfg, sample)
            assert result["_transfer_controls"]["named_fields_check_passed"] is True, result
            assert not set(sample).intersection(result).intersection({"customer_id", "customer_name", "customer_email", "customer_dob", "customer_address", "iban", "ip_address"}), result
            assert suite.execute(cfg, sample | {"customer_dob": "invalid"}) is None
            rows.append("gdpr:valid-and-transform-failure")
            for recipe in ["smart-buffering", "production-log-pipeline"]:
                result = suite.execute(config("recipes/" + recipe, "recipe"), {"message": "server error", "level": "ERROR", "category": "important"}, retain_input=True)
                assert result, recipe
                rows.append(f"rate-limit:{recipe}")
            result = suite.execute(config("recipes/filter-severity", "recipe"), "database connection failed")
            assert result["level"] == "ERROR", result
            rows.append("severity:inferred-error")
            for variant in ["cli", "mcp"]:
                cfg = config("workflows/email-triage", variant)
                processors = cfg["pipeline"]["processors"]
                if variant == "mcp":
                    processors = processors[1:]
                processors = next(p["try"] for p in processors if "try" in p)
                switch = next(p for p in processors if "switch" in p)
                cfg["pipeline"]["processors"] = [{"try": [processors[0], switch]}]
                result = suite.execute(cfg, {"provider": "outlook", "since_hours": 1})
                assert [email["id"] for email in result["emails"]] == ["recent"], (result, Provider.calls)
                rows.append(f"outlook:{variant}")
                cfg = config("security/cve-scan", variant)
                http_transports(cfg["pipeline"], endpoint)
                for invalid, valid in [(100, 1), (1, 101)]:
                    payload = {"components": [{"name": f"invalid-{n}"} for n in range(invalid)] + [{"name": f"valid-{n}", "version": "1.0", "ecosystem": "PyPI"} for n in range(valid)]}
                    result = suite.execute(cfg, {"sbom": payload} if variant == "mcp" else payload)
                    assert result["scanned_packages"] == min(valid, 100), result
                    assert len(result["skipped_packages"]) == invalid + max(valid - 100, 0), result
                    assert [p["name"] for p in result["skipped_packages"] if p["name"].startswith("valid-")] == (["valid-100"] if valid > 100 else []), result
                rows.append(f"cve:{variant}")
            suite.close()
            suite = None
        group = directory / "gdpr-missing-key"
        group.mkdir()
        suite = Suite(group, {"PSEUDONYM_KEY": "", "TRANSFER_POLICY_ID": "fixture"})
        assert suite.execute(config("recipes/cross-border-gdpr", "recipe"), sample) is None
        rows.append("gdpr:missing-key")
        print(f"PASS {len(rows)} regression contracts on Expanso Edge")
        (directory / "report.json").write_text(json.dumps({"passed": rows}, indent=2) + "\n")
        write_evidence()
        return 0
    finally:
        if suite:
            suite.close()
        provider.shutdown()
        provider.server_close()
        thread.join(timeout=5)


def write_evidence():
    (ROOT / ".conformance" / "focused-regressions.json").write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(),
        "engine": runner.tool_evidence(shutil.which("expanso-edge")),
        "status": "pass", "cases": EVIDENCE,
    }, indent=2) + "\n")


CLI = shutil.which("expanso-cli")
if __name__ == "__main__":
    if not CLI:
        raise SystemExit("expanso-cli is required")
    raise SystemExit(main())
