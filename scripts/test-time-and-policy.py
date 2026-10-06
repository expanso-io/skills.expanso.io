# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise event-time endpoints, hourly Gmail cutoffs, and spaced grants."""
import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("regressions", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reg
spec.loader.exec_module(reg)


class Gmail(BaseHTTPRequestHandler):
    queries = []

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path.endswith("/messages"):
            query = parse_qs(url.query)["q"][0]
            self.queries.append(query)
            cutoff = int(next(term.split(":", 1)[1] for term in query.split() if term.startswith("after:")))
            records = [("recent", time.time() - 1800), ("old", time.time() - 86400)]
            body = {"messages": [{"id": name} for name, timestamp in records if timestamp > cutoff]}
        else:
            body = {"id": url.path.rsplit("/", 1)[1], "snippet": "fixture", "payload": {"headers": []}}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *_):
        pass


def main():
    directory = ROOT / ".conformance" / f"time-and-policy-{time.time_ns()}"
    directory.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Gmail)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    suite = None
    try:
        for index, policy in enumerate(["marketing-bot : slack-read : read", " * : slack-read : read "]):
            group = directory / str(index)
            group.mkdir()
            suite = reg.Suite(group, {
                "ACCESS_POLICY": policy, "EXPANSO_API_KEYS": "fixture-key:marketing-bot",
                "GMAIL_API_URL": f"http://127.0.0.1:{server.server_port}", "GMAIL_TOKEN": "fixture-token",
            })
            for variant in ["cli", "mcp"]:
                result = suite.execute(reg.config("security/access-gate", variant),
                    {"agent": "marketing-bot", "resource": "slack-read", "action": "read"})
                assert result["allowed"] is True, result
            cfg = reg.config("recipes/secure-slack-pipeline", "recipe")
            cfg["pipeline"]["processors"] = cfg["pipeline"]["processors"][:4] + [
                {"catch": [{"mapping": 'root = {"error": error()}'}]}
            ]
            result = suite.execute(cfg, {"channel": "C123", "limit": 1},
                                  headers={"X-Expanso-Api-Key": "fixture-key"})
            assert result == {"channel": "C123", "limit": 1}, result
            if index == 0:
                for variant in ["cli", "mcp"]:
                    cfg = reg.config("workflows/email-triage", variant)
                    init = next(p["try"] for p in cfg["pipeline"]["processors"] if "try" in p)
                    switch = next(p for p in init if "switch" in p)
                    cfg["pipeline"]["processors"] = [{"try": [init[0], switch]}]
                    for hours in [1, 1.5, 6]:
                        Gmail.queries.clear()
                        before = time.time()
                        result = suite.execute(cfg, {"provider": "gmail", "since_hours": hours})
                        after = time.time()
                        assert [email["id"] for email in result["emails"]] == ["recent"], result
                        assert len(Gmail.queries) == 1, Gmail.queries
                        query = Gmail.queries[0].split()
                        assert query[0] == "label:INBOX", query
                        cutoff = int(query[1].removeprefix("after:"))
                        assert before - hours * 3600 - 1 <= cutoff <= after - hours * 3600, query
                cfg = reg.config("recipes/aggregate-time-windows", "recipe")
                cfg.pop("buffer")
                processors = cfg["pipeline"]["processors"]
                invalid = suite.execute(
                    {
                        "_source_pipeline": cfg["_source_pipeline"],
                        "pipeline": {"processors": processors[:2]},
                    },
                    {
                        "sensor_id": "a",
                        "location": "room",
                        "timestamp": "2026-10-06T12:03:00Z",
                        "temperature": "bad",
                    },
                )
                assert invalid is None, invalid
                cfg["pipeline"]["processors"] = [
                    {"unarchive": {"format": "json_array"}},
                    {"mapping": 'root = this\nmeta window_end_timestamp = "2026-10-06T12:05:00Z"'},
                    processors[-2],
                    processors[-1],
                    {"archive": {"format": "json_array"}},
                ]
                invalid = suite.execute(cfg, [
                    {"sensor_id": "a", "location": "room", "aggregation_level": "sensor",
                     "group_key": "a", "timestamp": "2026-10-06T12:03:00Z", "temperature": "bad"},
                ])
                assert invalid in (None, []), invalid
                for timestamps in [
                    ["2026-10-06T12:03:20Z", "2026-10-06T12:03:00Z"],
                    ["2026-10-06T12:03:00.200Z", "2026-10-06T13:03:00.100+01:00"],
                ]:
                    for level, key in [("sensor", "a"), ("location", "room")]:
                        result = suite.execute(cfg, [
                            {"sensor_id": "a", "location": "room", "aggregation_level": level, "group_key": key,
                             "timestamp": timestamps[0], "temperature": 20},
                            {"sensor_id": "a", "location": "room", "aggregation_level": level, "group_key": key,
                             "timestamp": timestamps[1], "temperature": 10},
                        ])
                        assert len(result) == 1 and result[0]["aggregation_level"] == level, result
                        assert all(row["temperature_change"] == 10 and row["temperature_trend"] == "increasing"
                                   and row["event_count"] == 2 and row["temperature_avg"] == 15 for row in result), result
            suite.close()
            suite = None
        reg.write_evidence()
        print(f"PASS {len(reg.EVIDENCE)} event-time, Gmail cutoff, and spaced-policy cases")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
