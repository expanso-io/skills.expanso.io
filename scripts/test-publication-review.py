# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise publication dependencies, literal CSV keys, and public options."""
import argparse
import csv
import importlib.util
import io
import shlex
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("regressions", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reg
spec.loader.exec_module(reg)


def workflow_contract():
    pages = yaml.load((ROOT / ".github/workflows/pages.yml").read_text(), Loader=yaml.BaseLoader)
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = pages["jobs"]
    needs = jobs["deploy"]["needs"]
    needs = [needs] if isinstance(needs, str) else needs
    assert "conformance" in needs
    assert jobs["conformance"]["uses"] == "./.github/workflows/ci.yml"
    assert "workflow_call" in ci["on"]
    assert "if" not in jobs["deploy"]
    commands = [shlex.split(line) for step in ci["jobs"]["conformance"]["steps"]
                for line in step.get("run", "").replace("\\\n", " ").splitlines()]
    for variant in ["cli", "mcp"]:
        assert ["uv", "run", "-s", "scripts/test-skills.py", "--variant", variant,
                "--no-cache", "--max-reruns", "1", "--report", f".conformance/full-{variant}.json"] in commands
    assert ["uv", "run", "-s", "scripts/test-recipes.py", "--report", ".conformance/recipe-execution.json"] in commands
    assert ["npm", "run", "test:site"] in commands
    for job in [jobs["deploy"], ci["jobs"]["conformance"]]:
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        assert "ref" not in checkout.get("with", {})
    print("PASS Pages requires reusable execution and browser conformance at caller SHA", flush=True)


def artifact_scan(base):
    workflow = yaml.safe_load((ROOT / ".github/workflows/ai-check.yml").read_text())
    for step in workflow["jobs"]["check"]["steps"]:
        if "run" not in step:
            continue
        prefix = ''
        if "BASE_SHA" in step.get("env", {}):
            prefix = 'git() { if [ "$1" = diff ]; then shift; shift; command git diff "$BASE_SHA" "$@"; else command git "$@"; fi; }; export HEAD_SHA=HEAD;\n' + "export BASE_SHA=" + shlex.quote(base) + ";\n"
        subprocess.run(["bash", "-e", "-o", "pipefail", "-c", prefix + step["run"]], cwd=ROOT, check=True)


def main():
    workflow_contract()
    directory = ROOT / ".conformance" / f"publication-review-{time.time_ns()}"
    directory.mkdir(parents=True)
    suite = reg.Suite(directory, {"PLACEHOLDER": "[HIDDEN]", "ACCESS_POLICY": "*:slack-read:read", "EXPANSO_API_KEYS": "fixture-key:marketing-bot"})
    try:
        result = suite.execute(reg.config("recipes/transform-formats", "recipe"),
                               {"a.b": 1, "quoted,key": 'a"b'}, headers={"Accept": "text/csv"}, decode_json=False)
        rows = list(csv.DictReader(io.StringIO(result)))
        assert rows[0]["a.b"] == "1" and rows[0]["quoted,key"] == 'a"b', result
        for variant in ["cli", "mcp"]:
            for spacing in ["", " = ", "\t=\n"]:
                equals = spacing or "="
                html = f'<title>Chart</title><meta name="description" content="Summary"><h1>Chart</h1><img src="x" alt{equals}"Chart"><meta name{equals}"viewport" content="width=device-width">'
                cfg = reg.config("workflows/seo-pipeline", variant)
                payload = {"html": html}
                result = suite.execute(cfg, payload)
                assert result["analysis"]["score"] == 100, result
                assert result["analysis"]["images_missing_alt"] == 0, result
                assert result["analysis"]["has_viewport"] is True, result
                assert result["recommendations"] == [], result
            cfg = reg.config("security/pii-redact", variant)
            processors = cfg["pipeline"]["processors"]
            processors[2] = {"mapping": '''meta delivered_prompt = this.messages.0.content
root = {"choices": [{"message": {"content": "{\\"redacted_text\\":\\"[HIDDEN]\\",\\"redaction_count\\":1,\\"redacted_types\\":[\\"email\\"]}"}}]}'''}
            processors.append({"mapping": 'root = this\nroot.delivered_prompt = meta("delivered_prompt")'})
            payload = "Contact john@example.test" if variant == "cli" else {"text": "Contact john@example.test", "placeholder": "[HIDDEN]"}
            result = suite.execute(cfg, payload, raw=variant == "cli")
            assert "'[HIDDEN]'" in result["delivered_prompt"], result
            assert result.get("metadata", {}).get("placeholder") == "[HIDDEN]", result
            assert "redaction_mask" not in result["metadata"], result
            assert result["redacted_text"] == "[HIDDEN]", result
        cfg = reg.config("recipes/secure-slack-pipeline", "recipe")
        cfg["pipeline"]["processors"] = cfg["pipeline"]["processors"][:4] + [
            {"catch": [{"mapping": 'root = {"error": error()}'}]}
        ]
        result = suite.execute(cfg, {"channel": "C123", "limit": 1},
                               headers={"X-Expanso-Api-Key": "fixture-key"})
        assert result == {"channel": "C123", "limit": 1}, result
        reg.write_evidence()
        print(f"PASS {len(reg.EVIDENCE)} focused processor cases", flush=True)
    finally:
        suite.close()
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-base")
    args = parser.parse_args()
    if args.scan_base:
        artifact_scan(args.scan_base)


if __name__ == "__main__":
    main()
