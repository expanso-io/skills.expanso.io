# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute webhook replay, HTML extraction, fetch failure, and CSV contracts."""
import csv
import hashlib
import hmac
import importlib.util
import io
import json
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


class Page(BaseHTTPRequestHandler):
    status = 200
    html = '<title>Chart</title><h1>Chart</h1><meta name=description content=D><meta name=viewport content=x><img alt=Chart>'

    def do_GET(self):
        self.send_response(self.status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.html.encode())

    def log_message(self, *_):
        pass


def main():
    directory = ROOT / ".conformance" / f"auth-html-formats-{time.time_ns()}"
    directory.mkdir(parents=True)
    secret = "fixture-webhook-secret"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    suite = None
    try:
        suite = reg.Suite(directory, {"WEBHOOK_SECRET": secret})
        raw_body = '{"action":"safe"}'
        signature = "sha256=" + hmac.new(secret.encode(), raw_body.encode(), hashlib.sha256).hexdigest()
        cfg = reg.config("connectors/webhook-receive", "cli")
        wrapped = {"headers": {"X-Hub-Signature-256": signature}, "raw_body": raw_body, "body": {"action": "safe"}}
        result = suite.execute(cfg, wrapped)
        assert result["event"]["body"] == json.loads(raw_body), result
        assert result["metadata"]["signature_status"] == "verified", result
        assert suite.execute(cfg, wrapped | {"body": {"action": "danger"}}) is None
        assert suite.execute(cfg, wrapped | {"raw_body": "{broken"}) is None
        assert suite.execute(cfg, wrapped | {"raw_body": 42}) is None
        assert suite.execute(cfg, wrapped | {"headers": {}}) is None
        assert suite.execute(cfg, "{broken", raw=True) is None
        cfg = reg.config("connectors/webhook-receive", "mcp")
        result = suite.execute(cfg, raw_body, {"X-Hub-Signature-256": signature}, raw=True)
        assert result["metadata"]["signature_status"] == "verified", result
        assert result["event"]["body"] == json.loads(raw_body), result
        broken = "{broken"
        broken_signature = "sha256=" + hmac.new(secret.encode(), broken.encode(), hashlib.sha256).hexdigest()
        assert suite.execute(cfg, broken, {"X-Hub-Signature-256": broken_signature}, raw=True) is None
        assert suite.execute(cfg, raw_body, raw=True) is None
        for variant in ["cli", "mcp"]:
            cfg = reg.config("workflows/seo-pipeline", variant)
            for attrs in [
                '<meta name="description" content="Why 2 > 1"><meta content="width > 0" name="viewport"><img src="x > y" alt="Chart">',
                "<meta content='Why 2 > 1' name='description'><meta name='viewport' content='width > 0'><img src='x > y' alt='Chart'>",
            ]:
                result = suite.execute(cfg, {"html": '<title>Chart</title><h1>Chart</h1>' + attrs})
                assert result["analysis"]["meta_description"] == "Why 2 > 1", result
                assert result["analysis"]["image_count"] == 1, result
                assert result["analysis"]["images_missing_alt"] == 0, result
                assert result["analysis"]["score"] == 100, result
            result = suite.execute(cfg, {"html": '<title>Chart</title><h1>Chart</h1><meta name=description content=D><meta name=viewport content=x><img src="x > y">'})
            assert result["analysis"]["images_missing_alt"] == 1 and result["analysis"]["score"] == 85, result
            for attrs, score, description, viewport, missing_alt in [
                ('<meta name=description content=D><meta name=viewport content=x><img src=x title="Set alt=Chart">', 85, "D", True, 1),
                ("<meta name=description content=D><meta name=viewport content=x><img src=x title='Set alt=Chart'>", 85, "D", True, 1),
                ('<meta title="Set name=description content=D"><meta title="Set name=viewport"><img alt=Chart>', 60, "", False, 0),
                ('<meta name=description title="Set content=D"><meta name=viewport><img alt=Chart>', 75, "", True, 0),
                ('<meta title="Set name=viewport" name=description content=D><meta name=viewport><img title="Set alt=wrong" alt=Chart>', 100, "D", True, 0),
            ]:
                result = suite.execute(cfg, {"html": '<title>Chart</title><h1>Chart</h1>' + attrs})
                analysis = result["analysis"]
                assert analysis["score"] == score and analysis["meta_description"] == description, result
                assert analysis["has_viewport"] is viewport and analysis["images_missing_alt"] == missing_alt, result
            reg.http_transports(cfg["pipeline"], f"http://127.0.0.1:{server.server_port}")
            for status in [503, 200]:
                Page.status = status
                result = suite.execute(cfg, {"url": "https://fixture.invalid"})
                if status == 503:
                    assert result["status"] == "error" and result["error"], result
                    assert "analysis" not in result and "recommendations" not in result, result
                else:
                    assert result["analysis"]["score"] == 100, result
            result = suite.execute(cfg, {"url": "http://fixture.invalid"})
            assert result["status"] == "error" and "analysis" not in result, result
        cfg = reg.config("recipes/transform-formats", "recipe")
        for payload in [{"a": 1}, {"a": 1, "target_format": "caller"}]:
            result = suite.execute(cfg, payload, {"Accept": "text/csv"}, retain_input=True)
            rows = list(csv.DictReader(io.StringIO(result["data"])))
            assert rows == [{key: str(value) for key, value in payload.items()}], result
            assert result["transformation"]["target_format"] == "csv", result
            result = suite.execute(cfg, payload, {"Accept": "application/json"}, retain_input=True)
            assert result["data"] == payload, result
        for payload, expected in [
            ([{"a": 1}, {"a": 2, "b": 3}], [{"a": "1", "b": ""}, {"a": "2", "b": "3"}]),
            ([{}, {"a.b": 3}, {"later": "x"}], [{"a.b": "", "later": ""}, {"a.b": "3", "later": ""}, {"a.b": "", "later": "x"}]),
        ]:
            result = suite.execute(cfg, payload, {"Accept": "text/csv"}, retain_input=True)
            assert list(csv.DictReader(io.StringIO(result["data"]))) == expected, result
        for variant in ["cli", "mcp"]:
            cfg = reg.config("utilities/idempotent-cache", variant)
            request = {"input": {"value": "cached result"}, "ttl_seconds": 3600}
            results = suite.execute(cfg, request, repeat=2)
            assert [result["cached"] for result in results] == [False, True], results
            assert all(result["result"] == request["input"] for result in results), results
            cfg = reg.config("utilities/idempotent-cache", variant)
            cfg["cache_resources"][0]["memory"]["compaction_interval"] = "10ms"
            delay_cache_get(cfg["pipeline"])
            results = suite.execute(cfg, request | {"ttl_seconds": 0.1}, repeat=2)
            assert [result["cached"] for result in results] == [False, False], results
            assert all(result["result"] == request["input"] for result in results), results
        reg.write_evidence()
        print("PASS malformed webhooks discarded; actual HTML attributes; CSV union; cache hits and expiry")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join()


def delay_cache_get(node):
    if isinstance(node, list):
        for child in list(node):
            if isinstance(child, dict) and child.get("cache", {}).get("operator") == "get":
                node.insert(node.index(child), {"sleep": {"duration": "200ms"}})
            delay_cache_get(child)
    elif isinstance(node, dict):
        for child in node.values():
            delay_cache_get(child)


if __name__ == "__main__":
    main()
