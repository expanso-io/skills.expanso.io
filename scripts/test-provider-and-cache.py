# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute scanner failures, cache validation, Jira ADF, and Stripe scales."""
import importlib.util
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("regressions", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reg
spec.loader.exec_module(reg)


class Provider(BaseHTTPRequestHandler):
    mode = "clean"
    calls = []

    def respond(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request = json.loads(raw) if raw else None
        self.calls.append((self.path, request))
        status = 200
        if self.path == "/openai/v1/chat/completions":
            if self.mode == "disconnect":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if self.mode == "unauthorized":
                status = 401
                body = {"error": {"message": "fixture credential rejected", "type": "authentication_error", "code": "invalid_api_key"}}
            else:
                result = {"findings": [], "summary": "Fixture clean result"}
                if self.mode == "finding":
                    result["findings"] = [{"type": "email", "value": "fixture@example.test", "severity": "high", "confidence": 1}]
                content = "not JSON" if self.mode == "invalid" else json.dumps(result)
                body = {"id": "fixture", "object": "chat.completion", "created": 1, "model": "gpt-4o-mini", "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]}
        elif self.path == "/jira":
            fields = request["fields"]
            description = fields.get("description")
            valid = description is None or (
                description["type"] == "doc" and description["version"] == 1
                and all(paragraph["type"] == "paragraph" and all(
                    node["type"] == "text" and isinstance(node["text"], str) and len(node["text"]) > 0
                    for node in paragraph.get("content", [])
                ) for paragraph in description["content"])
            )
            status = 201 if valid else 400
            body = {"id": "1", "key": "TEST-1", "self": "https://jira.example.test/rest/api/3/issue/1"} if valid else {"errorMessages": ["empty ADF text node"]}
        else:
            assert self.path == "/stripe", self.path
            body = {"has_more": False, "data": [
                {"id": currency, "type": "charge", "currency": currency, "amount": 500, "net": 400, "fee": 100}
                for currency in ["isk", "ugx", "mga", "usd", "jpy", "bhd"]
            ]}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    do_POST = respond
    do_GET = respond

    def log_message(self, *_):
        pass


def openai_endpoint(node, endpoint):
    if isinstance(node, list):
        for child in node:
            openai_endpoint(child, endpoint)
    elif isinstance(node, dict):
        if "openai_chat_completion" in node:
            node["openai_chat_completion"].update(server_address=endpoint + "/openai/v1", api_key="fixture-no-metered-key")
        for child in node.values():
            openai_endpoint(child, endpoint)


def main():
    directory = ROOT / ".conformance" / f"provider-and-cache-{time.time_ns()}"
    directory.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    suite = None
    try:
        suite = reg.Suite(directory, {"MCP_BEARER_TOKEN": reg.TOKEN, "JIRA_URL": "https://jira.example.test", "JIRA_EMAIL": "fixture@example.test", "JIRA_API_TOKEN": "fixture", "STRIPE_API_KEY": "fixture"})
        headers = {"Authorization": f"Bearer {reg.TOKEN}"}
        for variant in ["cli", "mcp"]:
            for skill, flag in [("pii-detect", "has_pii"), ("secrets-scan", "has_secrets")]:
                cfg = reg.config("security/" + skill, variant)
                openai_endpoint(cfg["pipeline"], endpoint)
                for mode in ["unauthorized", "disconnect", "invalid", "clean", "finding"]:
                    Provider.mode = mode
                    Provider.calls.clear()
                    result = suite.execute(cfg, "fixture text" if variant == "cli" else {"text": "fixture text"}, raw=variant == "cli")
                    assert Provider.calls and all(path == "/openai/v1/chat/completions" for path, _ in Provider.calls), Provider.calls
                    if mode in ["unauthorized", "disconnect", "invalid"]:
                        assert result["status"] == "error" and result["error"], result
                        assert flag not in result and "findings" not in result, result
                    else:
                        assert result[flag] is (mode == "finding"), result
                        assert len(result["findings"]) == int(mode == "finding"), result
            cfg = reg.config("utilities/idempotent-cache", variant)
            for request in [{}, {"ttl_seconds": 3600}, {"input": None}]:
                result = suite.execute(cfg, request)
                assert result["status"] == "error" and "input field is required" in result["error"], result
                assert "cached" not in result and "result" not in result, result
            request = {"input": {"value": "fixture"}}
            results = suite.execute(cfg, request, repeat=2)
            assert [result["cached"] for result in results] == [False, True], results
            assert all(result["result"] == request["input"] for result in results), results
            cfg = reg.config("workflows/jira-automate", variant)
            reg.http_transports(cfg["pipeline"], endpoint + "/jira")
            for extra in [{}, {"description": ""}, {"description": "Details"}]:
                Provider.calls.clear()
                result = suite.execute(cfg, {"action": "create", "project": "TEST", "summary": "x"} | extra, headers)
                assert result["result"]["issue"]["key"] == "TEST-1", result
                assert len(Provider.calls) == 1, Provider.calls
                content = Provider.calls[0][1]["fields"]["description"]["content"][0]["content"]
                assert content == ([{"type": "text", "text": "Details"}] if extra.get("description") else []), content
            cfg = reg.config("workflows/stripe-reports", variant)
            reg.http_transports(cfg["pipeline"], endpoint + "/stripe")
            result = suite.execute(cfg, {"include_insights": False, "include_quick_wins": False}, headers)
            totals = {row["currency"]: row for row in result["metrics"]["revenue_by_currency"]}
            for currency, exponent, units in [("ISK", 2, 5), ("UGX", 2, 5), ("MGA", 0, 500), ("USD", 2, 5), ("JPY", 0, 500), ("BHD", 3, 0.5)]:
                assert totals[currency]["minor_unit_exponent"] == exponent, result
                assert totals[currency]["gross_minor"] / 10 ** exponent == units, result
        reg.write_evidence()
        print("PASS real OpenAI processor failures and results; cache validation; Jira ADF; Stripe scales")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
