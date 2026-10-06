# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Record standalone explorer samples on Edge with explicit adapter/provider fixtures.

These traces demonstrate stage data flow, not intact deployments or platform proof.
Only disposable copies are modified; the reports bind to the published bytes.
"""
import gzip
import hashlib
import hmac
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("harness", ROOT / "scripts/test-skills.py")
harness = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = harness
spec.loader.exec_module(harness)

DOCUMENT = "# Battery guide\n\nCharge the sensor before deployment."
VECTOR = [0.25, 0.5, 0.75]
SAMPLES = {
    "jobs/ci-fixtures/pipeline.yaml": ({"id": "fixture-1"}, {"id": "fixture-1"}),
    "jobs/data-migration-engine/pipeline.yaml": (
        {"cust_no": 1, "full_name": "Tester, Ada", "email": "ADA@example.test",
         "balance_cents": -5, "signup": "10/06/2026", "status_code": "A"},
        {"balance": "-0.05", "email": "ada@example.test"}),
    "jobs/log-reduction/pipeline.yaml": (
        '127.0.0.1 - - [06/Oct/2026:12:00:00 +0000] "GET /api HTTP/1.1" 500 12 "-" "fixture" 0.25',
        {"kind": "error", "status": 500, "latency_ms": 250}),
    "jobs/notification-engine/pipeline.yaml": (
        {"id": "fixture-1", "severity": "high", "source": "sensor", "message": "Temperature", "ts": "2026-10-06T12:00:00Z"},
        {"event_id": "fixture-1", "severity": "high"}),
    "jobs/rag-embed-retrieve/pipeline.yaml": ({}, {"points": [{"vector": VECTOR}]}),
    "jobs/rag-embed-retrieve/pipeline-query.yaml": (
        {"question": "When should I charge the sensor?", "expected_doc": "guide.md"},
        {"hits": [{"doc": "guide.md", "text": "Charge the sensor before deployment."}]}),
    "jobs/rss-feed-engine/pipeline.yaml": ({}, {"guid": "fixture-1", "title": "Fixture news"}),
    "jobs/sensor-telemetry-mqtt/pipeline.yaml": (
        {"seq": 1, "ts": "2026-10-06T12:00:00Z", "temp_f": 212, "pressure_kpa": 101},
        {"line": "line1", "sensor": "sensor1", "temp_c": 100, "alert": True}),
    "jobs/webhook-fan-out/pipeline.yaml": ({"event": "fixture"}, {"event": "fixture"}),
    "recipes/csv-to-json/pipeline.yaml": ({"count": "12", "active": "true"}, {"count": 12, "active": True}),
    "transforms/json-pretty/pipeline-cloud.yaml": ({"sample": {"hello": "expanso"}, "seq": 1}, {"valid": True, "seq": 1}),
}


def provider_fixture(component, config):
    if component == "http":
        url = config["url"]
        if "nasa.gov" in url:
            return '<rss><channel><item><guid>fixture-1</guid><title>Fixture news</title><link>https://example.test/news</link><category>test</category><description>Fixture</description><pubDate>Tue, 06 Oct 2026 12:00:00 +0000</pubDate></item></channel></rss>'
        if "index.json" in url:
            return {"documents": ["https://example.test/guide.md"]}
        if url == '${! meta("source_uri") }':
            return DOCUMENT
        raise ValueError(f"No stage fixture for HTTP URL: {url}")
    if component == "ollama_embeddings":
        return VECTOR
    if component == "qdrant":
        return [{"id": {"uuid": "00000000-0000-0000-0000-000000000001"}, "score": 1,
                 "payload": {"source_uri": {"stringValue": "https://example.test/guide.md"},
                             "doc": {"stringValue": "guide.md"}, "chunk_id": {"stringValue": "guide.md#0"},
                             "chunk_index": {"integerValue": "0"},
                             "text": {"stringValue": "Charge the sensor before deployment."}}}]
    raise ValueError(component)


def replace_providers(value, replaced):
    if isinstance(value, list):
        for item in value:
            replace_providers(item, replaced)
    elif isinstance(value, dict):
        for component in ("http", "ollama_embeddings", "qdrant"):
            if component in value:
                response = provider_fixture(component, value[component])
                value.clear()
                value["mapping"] = "root = " + json.dumps(response)
                replaced.add(component)
                return
        for item in value.values():
            replace_providers(item, replaced)


def main():
    reports = {}
    conformance = ROOT / ".conformance"
    conformance.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=conformance, prefix="standalone-stages-") as directory:
        work = Path(directory)
        edge = harness.EdgeProcess(f"http://127.0.0.1:{harness.find_free_port()}", work / "data", work / "edge.log",
                                   env={"WEBHOOK_SECRET": "fixture-webhook-secret"})
        try:
            edge.start()
            assert harness.wait_for_api(edge.api_url), "Edge API unavailable"
            for relative, (sample, expected) in SAMPLES.items():
                source = ROOT / "skills" / relative
                job = yaml.safe_load(source.read_text())
                job.pop("selector", None)
                job.pop("restart_policy", None)
                config = job["config"]
                processors = config.setdefault("pipeline", {}).setdefault("processors", [])
                replaced = set()
                replace_providers(processors, replaced)
                for cache in config.get("cache_resources", []):
                    if "file" in cache:
                        (work / "cache").mkdir(exist_ok=True)
                        cache["file"]["directory"] = str(work / "cache")
                setup = "root = content()\n"
                if source.parent.name == "sensor-telemetry-mqtt":
                    setup += 'meta mqtt_topic = "plant/line1/sensor1/telemetry"\n'
                if source.parent.parent.name == "recipes":
                    setup += 'meta path = "fixture.csv"\n'
                if source.parent.name == "webhook-fan-out":
                    signature = hmac.new(b"fixture-webhook-secret", json.dumps(sample).encode(), hashlib.sha256).hexdigest()
                    setup += f'meta "X-Webhook-Signature" = "{signature}"\n'
                processors.insert(0, {"mapping": setup})
                copy = work / source.parent.name / source.name
                copy.parent.mkdir(exist_ok=True)
                copy.write_text(yaml.safe_dump(job, sort_keys=False))
                result, _ = harness.execute_test(
                    source.parent.name, copy, "cli", json.dumps(sample) if not isinstance(sample, str) else sample,
                    sample if isinstance(sample, dict) else {}, {}, edge.api_url, shutil.which("expanso-cli"),
                    False, work, expected_output=expected, edge_log=edge.log_file,
                )
                assert result["status"] == "passed", (relative, result)
                observed = result.pop("stages")
                assert all("input" in stage and "output" in stage for stage in observed), relative
                result["stages"] = observed[1:]
                result["adapter_values"] = {"input": observed[0]["output"], "output": observed[-1]["output"]}
                result["stage_scope"] = (
                    "Observed Edge stage boundaries with disposable sample input/output adapters and metadata. "
                    + ("Provider fixtures: " + ", ".join(sorted(replaced)) + ". " if replaced else "")
                    + "This is stage-flow evidence, not an intact platform deployment."
                )
                result["published_adapters_intact"] = False
                result["published_processors_intact"] = not replaced
                result["name"] = "Standalone stage sample"
                variant = source.stem.removeprefix("pipeline-")
                report = reports.setdefault(variant, {"variant": variant, "skills": []})
                report["skills"].append({"name": source.parent.name,
                                         "pipeline_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                         "tests": [result]})
                print(f"PASS {relative}: {len(observed) - 1} recorded processor stages")
        finally:
            edge.stop()
    for variant, report in reports.items():
        report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with gzip.GzipFile(filename=str(ROOT / "execution-reports" / f"explorer-{variant}.json.gz"), mode="wb", mtime=0) as output:
            output.write(json.dumps(report).encode())


if __name__ == "__main__":
    main()
