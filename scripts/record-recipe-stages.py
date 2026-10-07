# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Record recipe stage flow on Edge using disposable transport fixtures."""
import argparse
import copy
import hashlib
import hmac
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stage_recipe_runner", ROOT / "scripts/test-recipes.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
KEY = "fixture-pseudonym-key-at-least-32-characters"
ENCRYPTION = runner.ENCRYPTION_INPUT | {"address": runner.ENCRYPTION_INPUT["billing_address"]}
EVENT = {"event_id": "fixture-1", "event_type": "payment", "severity": "ERROR", "data": {"value": 1}}
SAMPLES = {
    "aggregate-time-windows": ({"sensor_id": "sensor-1", "location": "plant-1", "temperature": 20, "timestamp": "2026-10-06T12:00:00Z"}, {"event_count": 1, "temperature_avg": 20}),
    "circuit-breakers": ({"event_id": "fixture-1"}, {"enrichment_source": "primary_api"}),
    "content-routing": (EVENT, {"event_family": "payment"}),
    "content-splitting": ({"items": [{"id": "item-1"}]}, {"id": "item-1"}),
    "cross-border-gdpr": ({"customer_id": "customer-1", "customer_name": "Fixture", "customer_email": "fixture@example.test", "customer_dob": "1980-01-01", "customer_address": "Fixture street", "iban": "DE123456", "ip_address": "192.0.2.1", "transaction_amount": 25, "transaction_timestamp": "2026-10-06T12:00:00Z"}, {"email_domain": "example.test", "amount_bucket": "10-50", "_transfer_controls": {"named_fields_check_passed": True}}),
    "csv-to-json": ({"count": "12", "active": "true"}, {"count": 12, "active": True}),
    "db2-to-bigquery": ({"TRANSACTION_ID": "txn-1", "CUSTOMER_ID": "customer-1", "AMOUNT": 20, "CURRENCY": "EUR", "USD_RATE": 1.1, "ACCOUNT_NUMBER": "123456789012", "MERCHANT_CATEGORY_CODE": "5411", "TRANSACTION_DATE": "2026-10-06", "TRANSACTION_TYPE": "purchase", "MERCHANT_NAME": "Fixture", "SOURCE_SYSTEM": "fixture", "CREATED_AT": "2026-10-06T12:00:00Z"}, {"transaction_id": "txn-1", "amount_usd": 22, "transaction_category": "GROCERY"}),
    "dead-letter-queue": (EVENT, {"status": "success"}),
    "deduplicate-events": (EVENT, {"is_duplicate": False}),
    "encrypt-data": (ENCRYPTION, {"encryption_metadata": {"encrypted": True}}),
    "encryption-patterns": (ENCRYPTION, {"processing_metadata": {"encryption_status": "success"}}),
    "enforce-schema": (EVENT | {"timestamp": "2026-10-06T12:00:00Z"}, {"validation": {"status": "passed"}}),
    "enrich-export": ({"message": "Fixture", "service": "test", "level": "ERROR"}, {"event": {"application": {"message": "Fixture"}}}),
    "fan-out-kafka": (EVENT, EVENT),
    "fan-out-pattern": ({"sensor_id": "sensor-1"}, {"sensor_id": "sensor-1"}),
    "fan-out-s3": (EVENT, EVENT),
    "filter-severity": ({"level": "ERROR", "message": "Fixture"}, {"level": "ERROR", "filter_metadata": {"passed_filter": True}}),
    "http-webhook-ingestion": ({"event": {"type": "fixture"}}, {"_event_type": "fixture"}),
    "kafka-to-s3": (EVENT, {"_kafka_topic": "fixture-events"}),
    "nightly-backup": ({"id": "row-1", "value": 20}, {"id": "row-1"}),
    "normalize-timestamps": ({"timestamp": "2026-10-06T12:00:00Z"}, {"timestamp": "2026-10-06T12:00:00Z", "quality_score": 1}),
    "parse-logs": ({"level": "ERROR", "message": "Fixture"}, {"format": "json", "level": "ERROR"}),
    "priority-queues": (EVENT | {"customer_tier": "enterprise"}, {"priority_queue": "critical"}),
    "production-log-pipeline": ({"level": "ERROR", "message": "Fixture", "service": "test"}, {"priority": "high"}),
    "rate-limiting": (EVENT, EVENT),
    "remove-pii": ({"email": "fixture@example.test", "ip_address": "192.0.2.1", "user_name": "Fixture", "payment_method": {"full_number": "4111111111111111", "expiry": "12/30", "type": "visa"}, "location": {"city": "Berlin", "latitude": 52.5, "longitude": 13.4}}, {"email_domain": "example.test", "payment_method": {"type": "visa"}}),
    "s3-to-postgres": ({"id": "row-1", "value": 20}, {"id": "row-1", "source_key": "fixture.jsonl"}),
    "secure-slack-pipeline": ({"channel": "C123", "limit": 1}, {"count": 1, "data": [{"id": "1728136800.000001", "text": "Contact [EMAIL]", "timestamp": "1728136800.000001"}]}),
    "smart-buffering": (EVENT | {"category": "important"}, {"priority_tier": 1}),
    "transform-formats": ({"a": 1}, {"data": '"a"\n"1"', "transformation": {"target_format": "csv"}}),
    "seo-pipeline": ({"html": '<div title="<img src=x><meta name=viewport><meta name=description content=Fake><h1>Fake</h1><a>Fake</a><title>Fake</title>"></div><title>Chart</title><meta name="description" content="Summary"><h1>Chart</h1><img alt="Chart"><meta name="viewport">'}, {"analysis": {"score": 100, "title": "Chart", "meta_description": "Summary", "image_count": 1, "images_missing_alt": 0, "h1_count": 1, "link_count": 0}}),
    "stripe-reports": ({"period": "today", "include_insights": False}, {"metrics": {"revenue_by_currency": [{"gross_minor": 1200, "refunds_minor": 200, "net_minor": 970, "fees_minor": 30, "currency": "USD", "minor_unit_exponent": 2}]}}),
}


class Provider(BaseHTTPRequestHandler):
    def do_GET(self):
        body = {"ok": True, "messages": [{"ts": "1728136800.000001", "text": "Contact fixture@example.test"}]}
        if self.path == "/stripe":
            body = {"has_more": False, "data": [
                {"type": "payment", "amount": 1200, "fee": 30, "net": 1170, "currency": "usd", "status": "available"},
                {"type": "payment_refund", "amount": -200, "fee": 0, "net": -200, "currency": "usd", "status": "available"},
            ]}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


def redirect_http(node, endpoint):
    if isinstance(node, list):
        for item in node:
            redirect_http(item, endpoint)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "http" and isinstance(value, dict) and "url" in value:
                value["url"] = endpoint + ("/stripe" if 'stripe_url' in value["url"] else "")
            else:
                redirect_http(value, endpoint)


def assert_subset(expected, actual):
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert key in actual, (key, actual)
            assert_subset(value, actual[key])
    else:
        assert actual == expected, (expected, actual)


def record(paths, directory):
    directory.mkdir(parents=True, exist_ok=True)
    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=provider.serve_forever)
    thread.start()
    endpoint = f"http://127.0.0.1:{provider.server_port}"
    cli = shutil.which("expanso-cli")
    assert cli, "expanso-cli required"
    edge = runner.Edge(f"http://127.0.0.1:{runner.free_port()}", directory / "data", directory / "edge.log", directory,
                       runner.VALID_ENCRYPTION_ENV | {"PSEUDONYM_KEY": KEY, "ACCOUNT_PSEUDONYM_KEY": KEY, "TRANSFER_POLICY_ID": "fixture-policy", "WEBHOOK_SECRET": KEY, "EXPANSO_API_KEYS": "fixture-key:fixture-agent", "ACCESS_POLICY": "fixture-agent:slack-read:read", "SLACK_BOT_TOKEN": "fixture-token", "SLACK_API_URL": endpoint, "S3_BUCKET": "fixture-bucket", "PRIMARY_API_TOKEN": "fixture-token", "SECONDARY_API_TOKEN": "fixture-token", "STRIPE_API_KEY": "fixture-token", "OPENAI_API_KEY": "unused-fixture-token", "MCP_BEARER_TOKEN": KEY})
    rows = []
    try:
        edge.start()
        assert runner.wait_for_api(cli, edge.api_url), "Edge unavailable"
        for index, path in enumerate(paths):
            sample, expected = SAMPLES[path.parent.name]
            body = json.dumps(sample)
            config = copy.deepcopy(yaml.safe_load(path.read_text())["config"])
            config.pop("http", None)
            config.pop("buffer", None)
            port = runner.free_port()
            config["input"] = {"http_server": {"address": f"127.0.0.1:{port}", "path": "/test", "allowed_verbs": ["POST"], "timeout": "15s"}}
            config["output"] = {"sync_response": {}}
            processors = config.setdefault("pipeline", {}).setdefault("processors", [])
            redirect_http(processors, endpoint)
            setup = 'root = content()\nmeta kafka_topic = "fixture-events"\nmeta kafka_partition = "0"\nmeta kafka_offset = "1"\nmeta s3_key = "fixture.jsonl"\nmeta path = "fixture.csv"\nmeta window_end_timestamp = "2026-10-06T12:00:00Z"\nmeta "X-Expanso-Api-Key" = "fixture-key"\nmeta Accept = "text/csv"\n'
            signature = hmac.new(KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
            setup += f'meta "X-Webhook-Signature" = "{signature}"\n'
            setup += f'meta Authorization = "Bearer {KEY}"\n'
            probes = [{"mapping": setup}]
            for stage, processor in enumerate(processors):
                probes += [{"log": {"level": "WARN", "message": f"RECIPE_STAGE_{stage}_input ${{! content().string().quote() }}"}}, processor,
                           {"log": {"level": "WARN", "message": f"RECIPE_STAGE_{stage}_output ${{! content().string().quote() }}"}}]
            config["pipeline"]["processors"] = probes
            name = f"recipe-stages-{index}-{time.time_ns()}"
            copy_path = directory / f"{name}.yaml"
            copy_path.write_text(yaml.safe_dump({"name": name, "type": "pipeline", "config": config}, sort_keys=False))
            offset = edge.log_file.stat().st_size
            ok, _, detail = runner.deploy(copy_path, cli, edge.api_url)
            assert ok, (path, detail)
            try:
                ready, detail = runner.wait_for_execution_running(cli, name, edge.api_url)
                assert ready, (path, detail)
                assert runner.wait_for_port(port), path
                response = requests.post(f"http://127.0.0.1:{port}/test", data=body, headers={"Content-Type": "application/json"}, timeout=20)
                response.raise_for_status()
                if response.headers.get("Content-Type", "").startswith("multipart/"):
                    message = BytesParser(policy=default).parsebytes(
                        ("Content-Type: " + response.headers["Content-Type"] + "\r\n\r\n").encode() + response.content
                    )
                    output = [json.loads(part.get_payload(decode=True)) for part in message.iter_parts()]
                else:
                    output = response.json()
                if path.parent.name == "aggregate-time-windows":
                    for item in output:
                        assert_subset(expected, item)
                else:
                    assert_subset(expected, output)
                time.sleep(0.1)
                with edge.log_file.open("rb") as log:
                    log.seek(offset)
                    logs = log.read().decode()
                assert " ERR " not in logs, (path, logs)
                observed = [{} for _ in processors]
                for match in re.finditer(r'RECIPE_STAGE_(\d+)_(input|output) ("(?:[^"\\]|\\.)*")', logs):
                    value = json.loads(match[3])
                    try:
                        value = json.loads(value)
                    except ValueError:
                        pass
                    observed[int(match[1])].setdefault(match[2], []).append(value)
                for stage in observed:
                    assert {"input", "output"} <= stage.keys(), (path, stage)
                    for side in stage:
                        if len(stage[side]) == 1:
                            stage[side] = stage[side][0]
                rows.append({"pipeline": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "stages": observed, "adapter_values": {"input": sample, "output": output},
                             "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sample": "Recipe fixture sample",
                             "scope": "Observed Edge processor stage flow with fixture input/output transports and metadata, including fixture window_end_timestamp instead of waiting for source windows; source buffers are omitted. Circuit-breakers, Slack, and Stripe HTTP use loopback providers. External source/sink deployment is not proved."})
                (directory / "recordings.json").write_text(json.dumps({"stage_traces": rows}, indent=2) + "\n")
                print(f"PASS {path.parent.name}: {len(observed)} recorded stages", flush=True)
            finally:
                subprocess.run([cli, "job", "delete", name, "--endpoint", edge.api_url, "--force"], input="y\n", capture_output=True, text=True)
    finally:
        edge.stop()
        provider.shutdown()
        provider.server_close()
        thread.join()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=".conformance/recipe-stage-execution.json")
    args = parser.parse_args()
    paths = sorted((ROOT / "skills/recipes").glob("*/pipeline.yaml"))
    rows = record(paths, ROOT / ".conformance" / f"recipe-stages-{time.time_ns()}")
    (ROOT / args.report).write_text(json.dumps({"stage_traces": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
