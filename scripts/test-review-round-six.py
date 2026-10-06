# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute withdrawal receipts and recipe routing contracts."""
import hashlib
import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reg", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reg)
WITHDRAWALS = {
    "utilities/retry-wrapper": {"command": "false"},
    "utilities/determinism-test": {"input": "fixture", "runs": 10, "pipeline": "missing"},
    "workflows/terminal-services": {"service": "slack", "action": "send"},
    "workflows/multi-platform-chat": {"message": "fixture", "platform": "all"},
    "workflows/marketing-auto": {"action": "campaign", "topic": "fixture"},
    "workflows/health-integrate": {},
    "security/jwt-verify": {"token": "eyJhbGciOiJub25lIn0=.eyJleHAiOjQxMDI0NDQ4MDB9.invalid"},
    "security/policy-check": {"config": {"secret": "fixture"}, "policy": {"deny": [{"path": "secret", "condition": "exists"}]}},
    "utilities/openapi-validate": {"spec": {"openapi": "3.0.0"}, "request": {"invalid": True}},
}


def routed(cfg, labels):
    for case, label in zip(cfg["output"]["switch"]["cases"], labels):
        case["output"] = {"processors": [{"mapping": 'root = this.assign({"destination": "' + label + '"})'}], "sync_response": {}}
    return cfg


def main():
    directory = ROOT / ".conformance" / f"review-round-six-{time.time_ns()}"
    directory.mkdir()
    suite = reg.Suite(directory, {})
    artifacts = ["catalog.json", "catalog-minimal.json", "example-conformance.json"]
    before = {name: (ROOT / name).read_bytes() for name in artifacts}
    try:
        for skill, payload in WITHDRAWALS.items():
            for variant in ["cli", "mcp"]:
                result = suite.execute(reg.config(skill, variant), payload)
                assert result["status"] == "unsupported" and result["publication"] == "pulled" and result["reason"], result
                assert set(result) == {"status", "publication", "skill", "reason"}, result
        cfg = routed(reg.config("recipes/parse-logs", "recipe"), ["analytics", "dead_letter"])
        access = '192.0.2.1 - alice [06/Oct/2026:12:00:00 +0000] "GET /billing HTTP/1.1" 200 123'
        syslog = '<34>Oct  6 12:00:00 host service[123]: billing failed'
        result = suite.execute(cfg, access, retain_output=True)
        assert result["destination"] == "analytics" and result["format"] == "access_log", result
        assert (result["method"], result["path"], result["status"], result["bytes"]) == ("GET", "/billing", 200, 123), result
        result = suite.execute(cfg, syslog, retain_output=True)
        assert result["destination"] == "analytics" and result["message"] == "billing failed", result
        assert result["hostname"] == "host" and result["program"] == "service", result
        cfg = routed(reg.config("recipes/deduplicate-events", "recipe"), ["unique", "duplicate"])
        payload = {"event_id": "event-42", "message": "original payload", "timestamp": "2026-10-06T12:00:00Z"}
        results = suite.execute(cfg, payload, retain_output=True, repeat=2)
        assert [row["destination"] for row in results] == ["unique", "duplicate"], results
        assert [row["is_duplicate"] for row in results] == [False, True], results
        for row in results:
            assert row["event_id"] == payload["event_id"] and row["message"] == payload["message"], row
        cfg = routed(reg.config("recipes/content-splitting", "recipe"), ["processed", "dead_letter"])
        result = suite.execute(cfg, {"items": [{"id": 1}]}, retain_output=True)
        assert result["id"] == 1 and result["destination"] == "processed", result
        result = suite.execute(cfg, {"items": ["invalid"]}, retain_output=True)
        assert result["destination"] == "dead_letter" and result["invalid"], result
        for skill in WITHDRAWALS:
            name = skill.split("/")[-1]
            assert name not in json.loads(before["catalog.json"])["skills"], name
            assert all(name not in group["skills"] for group in json.loads(before["catalog-minimal.json"])["categories"].values()), name
        reg.write_evidence()
        assert before == {name: (ROOT / name).read_bytes() for name in artifacts}, "tests changed committed publication artifacts"
        print(f"PASS {len(reg.EVIDENCE)} behavioral cases; nine withdrawal and three routing contracts")
    finally:
        suite.close()


if __name__ == "__main__":
    main()
