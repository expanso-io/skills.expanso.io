# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Run the current review's executable processor and publication contracts."""
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("focused_regressions", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reg
spec.loader.exec_module(reg)


class StripeFixture(BaseHTTPRequestHandler):
    def respond(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body = {"data": [{"type": "charge", "amount": 1200, "net": 1100, "fee": 100, "currency": "usd"}], "has_more": False}
        if self.path == "/completion":
            body = {"choices": [{"message": {"content": json.dumps({"insights": ["fixture insight"], "quick_wins": ["fixture quick win"]})}}]}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    do_GET = respond
    do_POST = respond

    def log_message(self, *_):
        pass


def completion_transport(node, endpoint):
    if isinstance(node, list):
        for item in node:
            completion_transport(item, endpoint)
    elif isinstance(node, dict):
        if "openai_chat_completion" in node:
            node.clear()
            node["http"] = {"url": endpoint + "/completion", "verb": "POST", "retries": 0}
        else:
            for value in node.values():
                completion_transport(value, endpoint)


def main():
    reg.main()
    directory = ROOT / ".conformance" / f"review-round-two-{time.time_ns()}"
    directory.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), StripeFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    suite = None
    try:
        for key in ["", "short", reg.TOKEN]:
            group = directory / ("missing" if not key else "short" if key == "short" else "valid")
            group.mkdir()
            suite = reg.Suite(group, {"PSEUDONYM_KEY": key, "FORMAT": "spdx", "MCP_BEARER_TOKEN": reg.TOKEN, "STRIPE_API_KEY": "fixture", "STRIPE_API_URL": "https://stripe.example.test"})
            sample = {"email": "private@example.test", "ip_address": "192.0.2.1", "user_name": "Private", "payment_method": {"full_number": "4111111111111111", "expiry": "12/30"}, "location": {"latitude": 10, "longitude": 20, "city": "Fixture"}}
            result = suite.execute(reg.config("recipes/remove-pii", "recipe"), sample)
            if key != reg.TOKEN:
                assert result is None, result
                suite.close()
                suite = None
                continue
            assert all(field not in result for field in ["email", "ip_address", "user_name"]), result
            assert len(result["email_pseudonym"]) == 64, result
            cfg = reg.config("recipes/parse-logs", "recipe")
            for index, case in enumerate(cfg["output"]["switch"]["cases"]):
                destination = "analytics" if index == 0 else "dead_letter"
                case["output"] = {"processors": [{"mapping": f'root = this.assign({{"destination": "{destination}"}})'}], "sync_response": {}}
            for payload, expected in [('{broken', "parse_failed"), ('2026-10-06,ERROR,"billing,worker",failed', "csv"), ('2026-10-06,ERROR,"unclosed,failed', "parse_failed")]:
                result = suite.execute(cfg, payload, retain_output=True)
                assert result["destination"] == ("analytics" if expected == "csv" else "dead_letter"), result
                assert result["format"] == expected, result
                if expected == "csv":
                    assert (result["service"], result["message"]) == ("billing,worker", "failed"), result
            manifest = {"name": "my-app", "version": "1.0", "dependencies": {"@babel/core": "7.0.0"}}
            for variant in ["cli", "mcp"]:
                cfg = reg.config("security/sbom-generate", variant)
                result = suite.execute(cfg, {"packages": manifest, "format": "spdx"} if variant == "mcp" else manifest)
                assert result["sbom"]["name"] == "my-app", result
                packages = result["sbom"]["packages"]
                assert len(packages) == 1 and packages[0]["name"] == "@babel/core", result
                assert re.fullmatch(r"SPDXRef-[A-Za-z0-9.-]+", packages[0]["SPDXID"]), result
                cfg = reg.config("workflows/backup-verify", variant)
                for payload in [{}, {"local_manifest": []}, {"backup_manifest": []}, {"local_manifest": None, "backup_manifest": []}]:
                    result = suite.execute(cfg, payload)
                    assert result["status"]["verified"] is False and result["error"], result
                result = suite.execute(cfg, {"local_manifest": [], "backup_manifest": []})
                assert result["status"]["verified"] is True, result
                cfg = reg.config("workflows/seo-pipeline", variant)
                analyses = []
                for tag in ['<meta name="description" content="Description">', '<meta content="Description" name="description">']:
                    result = suite.execute(cfg, {"html": '<title>Test</title><h1>Test</h1><meta name="viewport" content="width=device-width">' + tag})
                    analyses.append(result["analysis"])
                assert analyses[0] == analyses[1] and analyses[0]["meta_description"] == "Description", analyses
                cfg = reg.config("workflows/stripe-reports", variant)
                reg.http_transports(cfg["pipeline"], endpoint)
                completion_transport(cfg["pipeline"], endpoint)
                for quick in [True, False]:
                    result = suite.execute(cfg, {"include_insights": True, "include_quick_wins": quick}, {"Authorization": f"Bearer {reg.TOKEN}"})
                    assert result["report"]["title"] and result["insights"] == ["fixture insight"], result
                    assert result["quick_wins"] == (["fixture quick win"] if quick else []), result
            suite.close()
            suite = None
        reg.write_evidence()
        subprocess.run(["uv", "run", "-s", "scripts/build-catalog.py"], cwd=ROOT, check=True)
        subprocess.run(["uv", "run", "-s", "scripts/build-example-conformance.py", "--from-ledger"], cwd=ROOT, check=True)
        catalog = json.loads((ROOT / "catalog.json").read_text())
        assert not {"auto-coder", "site-migrate"}.intersection(catalog["skills"])
        table = json.loads((ROOT / "example-conformance.json").read_text())
        assert len(table["pulled_examples"]) == 4 and all(row["reason"] for row in table["pulled_examples"])
        assert len(table["skipped_reasons"]) == 28 and all(row["reason"] for row in table["skipped_reasons"])
        assert all(row["criteria"]["structure"]["status"] == "pass" for row in table["examples"] if row["status"] != "pulled")
        builder_spec = importlib.util.spec_from_file_location("ledger_builder", ROOT / "scripts/build-example-conformance.py")
        builder = importlib.util.module_from_spec(builder_spec)
        builder_spec.loader.exec_module(builder)
        stripe_path = ROOT / "skills/workflows/stripe-reports/pipeline-cli.yaml"
        fixtures = {
            builder.REPORTS["cli"]: {"skills": [{"category": "workflows", "name": "stripe-reports", "pipeline_sha256": builder.sha256(stripe_path), "status": "failed", "reason": "fixture failure"}]},
            builder.REPORTS["mcp"]: {}, builder.REPORTS["recipes"]: {},
        }
        load_json = builder.load_json
        builder.load_json = lambda path: fixtures[path] if path in fixtures else load_json(path)
        failed_table = builder.build_table(table)
        failed_stripe = next(row for row in failed_table["examples"] if row["pipeline"] == str(stripe_path.relative_to(ROOT)))
        assert failed_stripe["status"] == "failing", failed_stripe
        print(f"PASS {len(reg.EVIDENCE)} executable cases; 4 pulled variants; 28 concrete skip reasons")
        return 0
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
