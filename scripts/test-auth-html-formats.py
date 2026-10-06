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
        reg.write_evidence()
        print("PASS webhook replay mismatch rejected; quote-aware SEO and fetch errors; CSV payload preservation")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
