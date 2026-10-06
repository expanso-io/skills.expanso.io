# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise primary, secondary, and failed enrichment paths on Expanso Edge."""
import importlib.util
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


class Provider(BaseHTTPRequestHandler):
    calls = []
    statuses = {}

    def do_GET(self):
        tier = self.path.split("/")[1]
        self.calls.append(tier)
        self.send_response(self.statuses[tier])
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"provider": tier, "event_id": "evt-1"}).encode())

    def log_message(self, *_):
        pass


def main():
    directory = ROOT / ".conformance" / f"circuit-failover-{time.time_ns()}"
    directory.mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    suite = None
    try:
        suite = reg.Suite(directory, {"PRIMARY_API_TOKEN": "fixture", "SECONDARY_API_TOKEN": "fixture"})
        cfg = reg.config("recipes/circuit-breakers", "recipe")
        processors = cfg["pipeline"]["processors"]
        primary = processors[1]["try"][0]["http"]
        secondary = processors[2]["catch"][1]["try"][0]["http"]
        for tier, transport in [("primary", primary), ("secondary", secondary)]:
            transport.update(url=f"http://127.0.0.1:{server.server_port}/{tier}/enrich/${{!this.event_id}}", retries=0)
        for statuses, source, calls in [
            ({"primary": 200, "secondary": 200}, "primary_api", ["primary"]),
            ({"primary": 500, "secondary": 200}, "secondary_api", ["primary", "secondary"]),
            ({"primary": 500, "secondary": 500}, "none", ["primary", "secondary"]),
        ]:
            Provider.statuses = statuses
            Provider.calls = []
            result = suite.execute(cfg, {"event_id": "evt-1"})
            assert Provider.calls == calls, Provider.calls
            assert result["enrichment_source"] == source, result
            assert result["processed_at"], result
            if source == "none":
                assert result["enrichment"] is None and result["enrichment_failed"] is True, result
            else:
                assert result["enrichment"]["provider"] == calls[-1], result
        reg.write_evidence()
        print("PASS primary success, secondary failover, and both-provider failure")
    finally:
        if suite:
            suite.close()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
