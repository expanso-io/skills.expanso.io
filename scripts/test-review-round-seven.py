# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute record preservation, deduplication, routing, OSV, and slug contracts."""
import importlib.util
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("round_six", ROOT / "scripts/test-review-round-six.py")
round_six = importlib.util.module_from_spec(spec)
spec.loader.exec_module(round_six)
reg = round_six.reg


class OSV(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        self.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"vulns": []}')

    def log_message(self, *_):
        pass


def fail_openai(node):
    if isinstance(node, list):
        for child in node:
            fail_openai(child)
    elif isinstance(node, dict):
        if any(str(key).startswith("openai_") for key in node):
            node.clear()
            node["mapping"] = 'root = throw("provider fixture failure")'
            return
        for child in node.values():
            fail_openai(child)


def main():
    directory = ROOT / ".conformance" / f"review-round-seven-{time.time_ns()}"
    directory.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), OSV)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    suite = None
    try:
        suite = reg.Suite(
            directory,
            {
                "SEPARATOR": ".",
                "MCP_BEARER_TOKEN": reg.TOKEN,
                "FIELD_ENCRYPTION_KEY_HEX": "00" * 32,
                "FIELD_MAC_KEY": reg.TOKEN,
                "VERIFY_KEY": "",
            },
        )
        for variant in ("cli", "mcp"):
            payload = {"match_fields": ["sku", "name"], "catalogs": [
                {"name": "first", "items": [{"sku": "A", "name": "widget", "price": 1}, {"sku": "A", "name": "widget", "price": 2}]},
                {"name": "second", "items": [{"sku": "B", "name": "other", "price": 3}]},
            ]}
            result = suite.execute(reg.config("workflows/catalog-reconcile", variant), payload)
            assert result["matches"] == [] and result["conflicts"] == [], result
            assert sorted(row["record"]["price"] for row in result["unmatched"]) == [1, 2, 3], result
            assert result["summary"]["unmatched"] == result["summary"]["total_processed"] == 3, result
            assert [row["source"] for row in result["unmatched"]].count("first") == 2, result

            cfg = reg.config("security/cve-scan", variant)
            reg.http_transports(cfg, f"http://127.0.0.1:{server.server_port}")
            for purl, versioned in [("pkg:npm/lodash", False), ("pkg:npm/%40scope/lodash", False), ("pkg:npm/lodash@4.17.20", True)]:
                sbom = {"components": [{"name": "lodash", "version": "4.17.20", "purl": purl}]}
                OSV.requests.clear()
                result = suite.execute(cfg, sbom if variant == "cli" else {"sbom": sbom})
                assert len(OSV.requests) == 1, OSV.requests
                expected = {"package": {"purl": purl}}
                if not versioned:
                    expected["version"] = "4.17.20"
                assert OSV.requests[0] == expected, OSV.requests
                assert result["vulnerabilities"] == [], result

            separators = ["."] if variant == "cli" else [".", "+", "[", "$", "\\", "--"]
            for separator in separators:
                result = suite.execute(reg.config("transforms/slug-generate", variant), "Hello World" if variant == "cli" else {"text": f"{separator}Hello{separator}{separator} World{separator}", "separator": separator})
                assert result["slug"] == f"hello{separator}world", result

        cfg = round_six.routed(reg.config("recipes/deduplicate-events", "recipe"), ["unique", "duplicate"])
        payload = {"event_id": "new", "timestamp": "malformed", "message": "original", "error": "business event error"}
        results = suite.execute(cfg, payload, retain_output=True, repeat=2)
        assert [row["is_duplicate"] for row in results] == [False, True], results
        assert [row["destination"] for row in results] == ["unique", "duplicate"], results
        assert all(row["message"] == "original" for row in results), results
        for invalid in [{"timestamp": "malformed"}, {"event_id": "new", "timestamp": "malformed", "dedup_strategy": "composite"}]:
            result = suite.execute(cfg, invalid, retain_output=True)
            assert result["error"] and result["is_duplicate"] is None, result
            assert result["dedup_result"]["is_duplicate"] is None, result
        cfg = round_six.routed(reg.config("recipes/content-splitting", "recipe"), ["processed", "dead_letter"])
        for item, destination in [({}, "dead_letter"), ({"id": 1}, "processed"), ("invalid", "dead_letter")]:
            result = suite.execute(cfg, {"items": [item]}, retain_output=True)
            assert result["destination"] == destination, result
            if destination == "dead_letter":
                assert result["invalid"] and result["original"] == item, result
        for recipe, payload in [
            (
                "encrypt-data",
                {
                    "payment": {"card_number": "4111111111111111"},
                    "customer": {"email": "private@example.test"},
                    "address": {"zip": {"invalid": True}},
                },
            ),
            (
                "encryption-patterns",
                {
                    "payment": {"card_number": "4111111111111111"},
                    "customer": {"email": "private@example.test"},
                    "billing_address": {"zip": {"invalid": True}},
                },
            ),
        ]:
            result = suite.execute(reg.config("recipes/" + recipe, "recipe"), payload)
            assert result is None, (recipe, result)
        for skill in ["ai/audio-transcribe", "workflows/voice-admin"]:
            for variant in ["cli", "mcp"]:
                headers = (
                    {"Authorization": f"Bearer {reg.TOKEN}"}
                    if variant == "mcp"
                    else None
                )
                cfg = reg.config(skill, variant)
                fail_openai(cfg["pipeline"])
                result = suite.execute(cfg, {}, headers=headers)
                assert result["status"] == "error" and result["error"], result
                assert not {
                    "transcript",
                    "actions",
                    "execution_status",
                }.intersection(result), result
        envelope = {
            "payload": {"data": "fixture"},
            "hash": "0" * 64,
            "signature": "0" * 64,
            "algorithm": "hmac-sha256",
        }
        for variant in ["cli", "mcp"]:
            headers = (
                {"Authorization": f"Bearer {reg.TOKEN}"}
                if variant == "mcp"
                else None
            )
            payload = envelope if variant == "cli" else {"envelope": envelope}
            result = suite.execute(
                reg.config("security/verify-signature", variant),
                payload,
                headers=headers,
            )
            assert result["valid"] is False and result["error"], result
            assert result.get("payload") is None, result
        reg.write_evidence()
        print(f"PASS {len(reg.EVIDENCE)} behavioral cases across eight changed pipeline variants")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
