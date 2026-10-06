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
    stripe_data = []

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
            body = {"issues": [], "id": "42", "key": "TEST-42", "self": "https://jira.example.test/42"}
        elif path == "/todoist":
            body = {"results": [], "id": "42", "content": "fixture task"}
        elif path == "/stripe":
            body = {"data": self.stripe_data, "has_more": False}
        else:
            body = {"value": []}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    do_GET = respond
    do_POST = respond
    do_PUT = respond

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
        for skill, action in [("jira-automate", "create"), ("todoist-automate", "create"), ("todoist-automate", "update")]:
            cfg = reg.config("workflows/" + skill, variant)
            reg.http_transports(cfg["pipeline"], endpoint + ("/jira" if skill == "jira-automate" else "/todoist"))
            for status in [401, 200]:
                Provider.status = status
                Provider.calls.clear()
                result = suite.execute(cfg, {"action": action, "project": "TEST", "summary": "fixture", "content": "fixture", "task_id": "42"}, auth)
                assert len(Provider.calls) == 1, Provider.calls
                if status == 401:
                    assert result["status"] == "error" and result["error"], result
                    assert "result" not in result and "tasks" not in result and "issues" not in result, result
                else:
                    assert result["result"], result
        cfg = reg.config("workflows/stripe-reports", variant)
        reg.http_transports(cfg["pipeline"], endpoint + "/stripe")
        round_two.completion_transport(cfg["pipeline"], endpoint)
        for status in [401, 200]:
            Provider.status = status
            Provider.calls.clear()
            result = suite.execute(cfg, {"include_insights": status == 401}, auth)
            assert Provider.calls == ["/stripe"], Provider.calls
            if status == 401:
                assert result["status"] == "error" and result["error"], result
                assert "report" not in result and "metrics" not in result, result
            else:
                assert result["metrics"]["transactions"]["total"] == 0, result
        transactions = [{"type": "charge", "currency": "usd", "amount": 1200, "net": 1100, "fee": 100}, {"type": "charge", "currency": "jpy", "amount": 5000, "net": 4900, "fee": 100}]
        for data in [transactions, list(reversed(transactions))]:
            Provider.stripe_data = data
            result = suite.execute(cfg, {"include_insights": False}, auth)
            totals = result["metrics"]["revenue_by_currency"]
            assert [total["currency"] for total in totals] == ["JPY", "USD"], result
            assert [total["gross_minor"] for total in totals] == [5000, 1200], result
        Provider.stripe_data = []
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


def db2_cases(suite, valid_key):
    sample = {"TRANSACTION_ID": "42", "CUSTOMER_ID": "customer", "ACCOUNT_NUMBER": "123456789012", "TRANSACTION_DATE": "2026-10-06T12:00:00Z", "AMOUNT": 10, "CURRENCY": "USD", "USD_RATE": 1, "MERCHANT_CATEGORY_CODE": "5411"}
    cfg = reg.config("recipes/db2-to-bigquery", "recipe")
    for payload in [sample, sample | {"TRANSACTION_DATE": "2026-10-06"}, sample | {"USD_RATE": None}]:
        result = suite.execute(cfg, payload)
        if valid_key and payload == sample:
            assert result["account_number_masked"] == "****-****-9012", result
            assert len(result["account_number_pseudonym"]) == 64 and "ACCOUNT_NUMBER" not in result, result
        else:
            assert result is None, result


def main():
    before = (ROOT / "example-conformance.json").read_bytes()
    directory = ROOT / ".conformance" / f"review-round-four-{time.time_ns()}"
    directory.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    suite = None
    try:
        suite = reg.Suite(directory, {"MCP_BEARER_TOKEN": reg.TOKEN, "JIRA_URL": "https://jira.example.test", "JIRA_EMAIL": "fixture", "JIRA_API_TOKEN": "fixture", "TODOIST_API_URL": "https://todoist.example.test", "TODOIST_TOKEN": "fixture", "GMAIL_API_URL": "https://gmail.example.test", "GMAIL_TOKEN": "fixture", "OUTLOOK_API_URL": "https://outlook.example.test", "OUTLOOK_TOKEN": "fixture", "STRIPE_API_KEY": "fixture", "ACCOUNT_PSEUDONYM_KEY": reg.TOKEN})
        run_cases(suite, f"http://127.0.0.1:{server.server_port}")
        db2_cases(suite, True)
        suite.close()
        suite = None
        missing = directory / "missing-account-key"
        missing.mkdir()
        suite = reg.Suite(missing, {"ACCOUNT_PSEUDONYM_KEY": ""})
        db2_cases(suite, False)
        reg.write_evidence()
        spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build-example-conformance.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        cli_report = builder.REPORTS["cli"]
        builder.REPORTS["cli"] = directory / "missing-complete-cli.json"
        try:
            builder.build_table()
        except RuntimeError as exc:
            assert "required report is missing" in str(exc), exc
        else:
            raise AssertionError("missing complete execution report was accepted")
        builder.REPORTS["cli"] = cli_report
        load_json = builder.load_json
        builder.load_json = lambda path: {} if path in builder.REPORTS.values() else load_json(path)
        table = builder.build_table()
        for row in table["examples"]:
            assert row["sha256"] == hashlib.sha256((ROOT / row["pipeline"]).read_bytes()).hexdigest(), row
        video = next(row for row in table["examples"] if row["pipeline"] == "skills/ai/video-generate/pipeline-mcp.yaml")
        assert video["criteria"]["runs"]["status"] == "failing", video
        ledger = json.loads(before)
        for row in ledger["examples"]:
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
