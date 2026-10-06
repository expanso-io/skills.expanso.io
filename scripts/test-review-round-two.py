# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Run the current review's executable processor and publication contracts."""
import importlib.util
import hashlib
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("focused_regressions", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reg
spec.loader.exec_module(reg)


class StripeFixture(BaseHTTPRequestHandler):
    gmail_list_status = 200
    gmail_failed_id = None
    gmail_ids = []
    gmail_calls = []
    def respond(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body = {"data": [{"type": "charge", "amount": 1200, "net": 1100, "fee": 100, "currency": "usd"}], "has_more": False}
        if self.path == "/completion":
            body = {"choices": [{"message": {"content": json.dumps({"insights": ["fixture insight"], "quick_wins": ["fixture quick win"]})}}]}
        status = 200
        path = urlsplit(self.path).path
        if path.startswith("/users/me/messages"):
            self.__class__.gmail_calls.append(path)
            if path == "/users/me/messages":
                status = self.gmail_list_status
                body = {"messages": [{"id": ident} for ident in self.gmail_ids], "resultSizeEstimate": len(self.gmail_ids)}
            else:
                ident = path.rsplit("/", 1)[-1]
                status = 401 if ident == self.gmail_failed_id else 200
                body = {"id": ident, "snippet": "fixture message", "payload": {"headers": [{"name": "Subject", "value": "Fixture subject"}]}}
            if status != 200:
                body = {"error": {"code": status, "message": "fixture unauthorized"}}
        self.send_response(status)
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


def gmail_transports(node, endpoint):
    if isinstance(node, list):
        for child in node:
            gmail_transports(child, endpoint)
    elif isinstance(node, dict):
        for key, child in node.items():
            if key == "http" and isinstance(child, dict) and "url" in child:
                child["url"] = '${! (if this.url != null { this.url } else { meta("list_url") }).replace_all("https://gmail.example.test", "' + endpoint + '") }'
                child["retries"] = 0
            else:
                gmail_transports(child, endpoint)


def main():
    artifacts = ["catalog.json", "catalog-minimal.json", "example-conformance.json", "review-regression-evidence.json"]
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in artifacts}
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
            suite = reg.Suite(group, {"PSEUDONYM_KEY": key, "LOG_PSEUDONYM_KEY": key, "GMAIL_API_URL": "https://gmail.example.test", "GMAIL_ACCESS_TOKEN": "fixture", "FORMAT": "spdx", "MCP_BEARER_TOKEN": reg.TOKEN, "STRIPE_API_KEY": "fixture", "STRIPE_API_URL": "https://stripe.example.test"})
            sample = {"email": "private@example.test", "ip_address": "192.0.2.1", "user_name": "Private", "payment_method": {"full_number": "4111111111111111", "expiry": "12/30"}, "location": {"latitude": 10, "longitude": 20, "city": "Fixture"}}
            result = suite.execute(reg.config("recipes/remove-pii", "recipe"), sample)
            production = suite.execute(reg.config("recipes/production-log-pipeline", "recipe"), {"message": "server error", "level": "ERROR", "source_ip": "192.0.2.1"}, retain_input=True)
            if key != reg.TOKEN:
                assert production is None, production
                assert result is None, result
                suite.close()
                suite = None
                continue
            assert re.fullmatch(r"[0-9a-f]{64}", production["source_ip"]), production
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
            manifest = {"name": "my-app", "version": "1.0", "dependencies": {"@babel/core": "7.0.0", "@a/b-c": "1.0", "@a-b/c": "1.0"}, "devDependencies": {"@a/b-c": "1.0"}}
            for variant in ["cli", "mcp"]:
                cfg = reg.config("security/sbom-generate", variant)
                result = suite.execute(cfg, {"packages": manifest, "format": "spdx"} if variant == "mcp" else manifest)
                assert result["sbom"]["name"] == "my-app", result
                packages = result["sbom"]["packages"]
                assert len(packages) == 4 and len({package["SPDXID"] for package in packages}) == 4, result
                assert all(re.fullmatch(r"SPDXRef-[A-Za-z0-9.-]+", package["SPDXID"]) for package in packages), result
                cfg = reg.config("connectors/gmail-read", variant)
                gmail_transports(cfg["pipeline"], endpoint)
                for list_status, failed_id, ids in [(401, None, ["good"]), (200, "bad", ["good", "bad"]), (200, None, []), (200, None, ["good", "other"])]:
                    StripeFixture.gmail_list_status = list_status
                    StripeFixture.gmail_failed_id = failed_id
                    StripeFixture.gmail_ids = ids
                    StripeFixture.gmail_calls.clear()
                    result = suite.execute(cfg, {"limit": 20}, {"Authorization": f"Bearer {reg.TOKEN}"})
                    if list_status != 200 or failed_id:
                        assert result["status"] == "error" and result["error"], result
                        assert "data" not in result and "count" not in result, result
                    else:
                        assert result["count"] == len(ids), result
                        assert sorted(email["id"] for email in result["data"]) == sorted(ids), result
                    assert len(StripeFixture.gmail_calls) == (1 if list_status != 200 else 1 + len(ids)), StripeFixture.gmail_calls
                cfg = reg.config("workflows/devops-monitor", variant)
                for conclusion, health, count in [("failure", "degraded", 1), ("success", "healthy", 0)]:
                    result = suite.execute(cfg, {"workflows": [{"status": "completed", "conclusion": conclusion, "id": 42}]})
                    assert result["status"]["overall_health"] == health and result["status"]["issue_count"] == count, result
                    if count:
                        assert result["issues"][0]["source_id"] == 42, result
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
        catalog_spec = importlib.util.spec_from_file_location("catalog_builder", ROOT / "scripts/build-catalog.py")
        catalog_builder = importlib.util.module_from_spec(catalog_spec)
        catalog_spec.loader.exec_module(catalog_builder)
        catalog, _ = catalog_builder.build_catalog(ROOT / "skills", "categorized")
        assert not {"auto-coder", "site-migrate"}.intersection(catalog["skills"])
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
        failed_table = builder.build_table()
        failed_stripe = next(row for row in failed_table["examples"] if row["pipeline"] == str(stripe_path.relative_to(ROOT)))
        assert failed_stripe["status"] == "failing", failed_stripe
        assert len(failed_table["pulled_examples"]) == 4
        gmail = next(row for row in failed_table["examples"] if row["pipeline"] == "skills/connectors/gmail-read/pipeline-cli.yaml")
        assert gmail["status"] == "failing" and gmail["criteria"]["runs"]["status"] == "failing", gmail
        assert gmail["criteria"]["runs"]["processor_regression"]["status"] == "pass", gmail
        recipe = ROOT / "skills/recipes/production-log-pipeline/pipeline.yaml"
        cloud = ROOT / "skills/transforms/json-pretty/pipeline-cloud.yaml"
        for status in ["fail", "failed", "pass", "skipped"]:
            fixtures[builder.REPORTS["recipes"]] = {"recipes": [{"pipeline": str(recipe.relative_to(ROOT)), "sha256": builder.sha256(recipe), "status": status}], "variants": [{"pipeline": str(cloud.relative_to(ROOT)), "sha256": builder.sha256(cloud), "status": "skipped"}]}
            model = builder.build_table()
            row = next(row for row in model["examples"] if row["pipeline"] == str(recipe.relative_to(ROOT)))
            expected = "failing" if status in {"fail", "failed"} else status
            assert row["criteria"]["runs"]["status"] == expected, row
            assert row["status"] in ({"pass", "fixed"} if expected == "pass" else {expected}), row
            cloud_row = next(row for row in model["examples"] if row["pipeline"] == str(cloud.relative_to(ROOT)))
            assert cloud_row["criteria"]["runs"]["reason"] == builder.load_json(ROOT / "scripts/integration-skip-reasons.json")[str(cloud.relative_to(ROOT))], cloud_row
        after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in artifacts}
        assert after == before, "committed public artifacts changed during testing"
        print(f"PASS {len(reg.EVIDENCE)} executable cases; publication and failed-report contracts")
        return 0
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
