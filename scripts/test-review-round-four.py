# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute provider failure, matching, digest, and ledger contracts."""
import hashlib
import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("round_two", ROOT / "scripts/test-review-round-two.py")
round_two = importlib.util.module_from_spec(spec)
spec.loader.exec_module(round_two)
reg = round_two.reg


class Provider(BaseHTTPRequestHandler):
    status = 200
    ids = []
    failed_id = None
    calls = []

    def respond(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        path = urlsplit(self.path).path
        self.calls.append(path)
        status = self.status
        body = {}
        if path == "/completion":
            status = 200
            body = {"choices": [{"message": {"content": "[]"}}]}
        elif path == "/users/me/messages":
            body = {"messages": [{"id": value} for value in self.ids]}
        elif path.startswith("/users/me/messages/"):
            ident = path.rsplit("/", 1)[-1]
            status = 401 if ident == self.failed_id else 200
            body = {"id": ident, "snippet": "fixture", "payload": {"headers": []}}
        elif path == "/jira":
            body = {"issues": []}
        elif path == "/todoist":
            body = {"results": []}
        else:
            body = {"value": []}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    do_GET = respond
    do_POST = respond

    def log_message(self, *_):
        pass


def email_transports(node, endpoint):
    if isinstance(node, list):
        for child in node:
            email_transports(child, endpoint)
    elif isinstance(node, dict):
        if "http" in node:
            node["http"]["url"] = '${! this.url.replace_all("https://gmail.example.test", "' + endpoint + '").replace_all("https://outlook.example.test", "' + endpoint + '") }'
            node["http"]["retries"] = 0
        else:
            for child in node.values():
                email_transports(child, endpoint)


def run_cases(suite, endpoint):
    auth = {"Authorization": f"Bearer {reg.TOKEN}"}
    for variant in ["cli", "mcp"]:
        for skill, action, field in [("jira-automate", "search", "issues"), ("todoist-automate", "list", "tasks")]:
            cfg = reg.config("workflows/" + skill, variant)
            reg.http_transports(cfg["pipeline"], endpoint + ("/jira" if skill == "jira-automate" else "/todoist"))
            for status in [401, 200]:
                Provider.status = status
                Provider.calls.clear()
                result = suite.execute(cfg, {"action": action, "project": "TEST"}, auth)
                assert len(Provider.calls) == 1, Provider.calls
                if status == 401:
                    assert result["status"] == "error" and result["error"], result
                    assert field not in result and "result" not in result, result
                else:
                    assert result[field] == [], result
        cfg = reg.config("workflows/email-triage", variant)
        email_transports(cfg["pipeline"], endpoint)
        round_two.completion_transport(cfg["pipeline"], endpoint)
        for provider, status, ids, failed in [("gmail", 401, [], None), ("outlook", 401, [], None), ("gmail", 200, ["good", "bad"], "bad"), ("gmail", 200, [], None), ("outlook", 200, [], None)]:
            Provider.status, Provider.ids, Provider.failed_id = status, ids, failed
            Provider.calls.clear()
            result = suite.execute(cfg, {"provider": provider}, auth)
            if status != 200 or failed:
                assert result["status"] == "error" and result["error"], result
                assert "emails" not in result and "summary" not in result, result
                assert "/completion" not in Provider.calls, Provider.calls
            else:
                assert result["emails"] == [] and result["summary"]["processed"] == 0, result
        cfg = reg.config("workflows/catalog-reconcile", variant)
        for items, matched, unmatched in [([{"sku": "A|B", "name": "C"}, {"sku": "A", "name": "B|C"}], 0, 2), ([{"sku": "a.b", "name": "C"}, {"sku": "A.B", "name": "c"}], 1, 0)]:
            result = suite.execute(cfg, {"match_fields": ["sku", "name"], "catalogs": [{"name": "left", "items": [items[0]]}, {"name": "right", "items": [items[1]]}]})
            assert result["summary"]["matched"] == matched and result["summary"]["unmatched"] == unmatched, result
            if matched:
                assert len(result["matches"][0]["records"]) == 2, result
        for fields in [[], ["sku", "name"]]:
            result = suite.execute(cfg, {"match_fields": fields, "catalogs": [{"name": "left", "items": [{}]}, {"name": "right", "items": [{}]}]})
            assert "matches" not in result and "summary" not in result, result
        cfg = reg.config("workflows/backup-verify", variant)
        for digest, verified in [("AB" * 32, True), ("AC" * 32, False)]:
            result = suite.execute(cfg, {"local_manifest": [{"path": "a.b", "size": 2, "sha256": "ab" * 32}], "backup_manifest": [{"path": "a.b", "size": 2, "sha256": digest}]})
            assert result["status"]["verified"] is verified, result


def main():
    before = (ROOT / "example-conformance.json").read_bytes()
    directory = ROOT / ".conformance" / f"review-round-four-{time.time_ns()}"
    directory.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    suite = None
    try:
        suite = reg.Suite(directory, {"MCP_BEARER_TOKEN": reg.TOKEN, "JIRA_URL": "https://jira.example.test", "JIRA_EMAIL": "fixture", "JIRA_API_TOKEN": "fixture", "TODOIST_API_URL": "https://todoist.example.test", "TODOIST_TOKEN": "fixture", "GMAIL_API_URL": "https://gmail.example.test", "GMAIL_TOKEN": "fixture", "OUTLOOK_API_URL": "https://outlook.example.test", "OUTLOOK_TOKEN": "fixture"})
        run_cases(suite, f"http://127.0.0.1:{server.server_port}")
        reg.write_evidence()
        spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build-example-conformance.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.load_execution_report = lambda path: {}
        table = builder.build_table()
        for row in table["examples"]:
            assert row["sha256"] == hashlib.sha256((ROOT / row["pipeline"]).read_bytes()).hexdigest(), row
        video = next(row for row in table["examples"] if row["pipeline"] == "skills/ai/video-generate/pipeline-mcp.yaml")
        assert video["criteria"]["runs"]["status"] == "failing", video
        ledger = json.loads(before)
        for row in ledger["examples"]:
            assert row["sha256"] == hashlib.sha256((ROOT / row["pipeline"]).read_bytes()).hexdigest(), row
            assert row["criteria"]["runs"].get("method") != "expanso-edge focused processor regression", row
        assert (ROOT / "example-conformance.json").read_bytes() == before
        print(f"PASS {len(reg.EVIDENCE)} executable cases; current-byte ledger contracts")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
