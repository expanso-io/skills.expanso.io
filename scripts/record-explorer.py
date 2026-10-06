# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Record one illustrative processor execution per variant, not deployment proof.

Only explicit test fixtures are used. Logs observe messages before and after
each top-level processor without changing their bodies. Provider fixtures and
replaced terminal adapters are disclosed in the published record.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCOPE = (
    "Local Expanso Edge processor sample; scheduling selector removed; "
    "input/output adapters replaced by loopback HTTP; OpenAI processors mocked; "
    "environment references use test values; "
    "configured provider responses use test mappings; unconfigured HTTP "
    "providers fail at loopback. Not platform or Cloud execution proof."
)
spec = importlib.util.spec_from_file_location("skill_runner", ROOT / "scripts/test-skills.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def observer(marker):
    return {"log": {"level": "WARN", "message": marker + '${! content().encode("base64") } END'}}


def decode_messages(log, marker):
    messages = []
    for line in log.splitlines():
        if marker not in line:
            continue
        encoded = line.split(marker, 1)[1].split(" END", 1)[0]
        value = base64.b64decode(encoded).decode()
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        messages.append(value)
    return messages


def record(directory, filename, edge, api, work):
    source = directory / filename
    tests = runner.load_yaml(directory / "test/test.yaml") or {}
    cases = tests.get("tests", [])
    case = cases[0] if cases else {"name": "Missing-field negative sample", "input": "{}"}
    sample = case.get("input", "")
    if "input_file" in case:
        path = directory / "test" / case["input_file"]
        if not path.exists():
            path = directory / "test" / tests.get("fixtures_dir", "fixtures") / case["input_file"]
        sample = path.read_text()
    metadata = runner.load_yaml(directory / "skill.yaml")
    inputs = metadata.get("inputs", [])
    payload = runner.build_payload(str(sample), inputs, runner.parse_env_overrides(case.get("env"), inputs))
    job = runner.load_yaml(source)
    job.pop("selector", None)
    processors = job["config"]["pipeline"]["processors"]
    if not processors and "generate" in job["config"].get("input", {}):
        # This pipeline transforms data in its generate input, not in a
        # processor list. Execute that same mapping as the observed stage.
        processors = [{"mapping": job["config"]["input"]["generate"]["mapping"]}]
    names = [next(iter(processor)) for processor in processors]
    if not job["config"]["pipeline"]["processors"]:
        names = ["generate mapping"]
    prefix = f"EXPLORER-{time.time_ns()}-"
    instrumented = []
    for index, processor in enumerate(processors):
        instrumented.extend([observer(f"{prefix}{index}-in "), processor, observer(f"{prefix}{index}-out ")])
    job["config"]["pipeline"]["processors"] = instrumented
    # Unconfigured providers fail at a loopback boundary rather than receiving
    # fixture data or inheriting operator credentials.
    def loopback(node):
        if isinstance(node, list):
            for child in node:
                loopback(child)
        elif isinstance(node, dict):
            for key, child in node.items():
                if key == "http" and isinstance(child, dict) and "url" in child:
                    child.update(url="http://127.0.0.1:9", retries=0, timeout="1s")
                else:
                    loopback(child)
    loopback(job["config"].get("pipeline", {}))
    for resource in job["config"].get("cache_resources", []):
        if "file" in resource:
            resource["file"]["directory"] = str(work / "cache" / resource["label"])
    environment = {key: "fixture" for key in re.findall(r'env\("([A-Z0-9_]+)"\)', source.read_text())}
    environment.update({key: "fixture" for key in re.findall(r'\$\{([A-Z0-9_]+)(?::[^}]*)?\}', source.read_text())})
    environment.update(case.get("env") or {})
    environment["MCP_BEARER_TOKEN"] = runner.HARNESS_MCP_BEARER_TOKEN
    path = work / "observed.yaml"
    path.write_text(yaml.safe_dump(job, sort_keys=False))
    variant = "mcp" if filename == "pipeline-mcp.yaml" else "cli"
    offset = edge.log_file.stat().st_size
    result, _ = runner.execute_test(
        directory.name, path, variant, str(sample), payload, {}, api,
        shutil.which("expanso-cli"), True, work,
        fixture_env=environment, provider_responses=case.get("provider_responses"),
        ai_responses=case.get("ai_responses"), edge_log=edge.log_file,
    )
    log = edge.log_file.read_bytes()[offset:].decode(errors="replace")
    stages = [{"name": name, "input": decode_messages(log, f"{prefix}{index}-in "),
               "output": decode_messages(log, f"{prefix}{index}-out ")}
              for index, name in enumerate(names)]
    if not stages or not stages[0]["input"]:
        raise RuntimeError(f"{directory.name}/{filename}: no recorded execution: {result}")
    record = {
        "schema": "expanso-stage-execution/1",
        "pipeline_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": SCOPE,
        "sample": case.get("name", "sample"),
        "errors": result.get("edge_errors", []),
        "stages": stages,
    }
    destination = directory / filename.replace(".yaml", ".explorer.json")
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Recorded {directory.name}/{filename}: {len(stages)} stages", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="+")
    args = parser.parse_args()
    work = ROOT / ".conformance" / f"explorer-{time.time_ns()}"
    work.mkdir(parents=True)
    api = f"http://127.0.0.1:{runner.find_free_port()}"
    edge = runner.EdgeProcess(api, work / "data", work / "edge.log")
    try:
        edge.start()
        if not runner.wait_for_api(api):
            raise RuntimeError("Edge did not start")
        failures = []
        for index, directory in enumerate(runner.find_skills(args.skills)):
            if index and index % 20 == 0:
                edge.stop()
                edge = runner.EdgeProcess(api, work / f"data-{index}", work / f"edge-{index}.log")
                edge.start()
                if not runner.wait_for_api(api):
                    raise RuntimeError("Edge did not restart")
            metadata = runner.load_yaml(directory / "skill.yaml")
            if metadata.get("publication", {}).get("status") == "pulled":
                continue
            for source in sorted(directory.glob("pipeline*.yaml")):
                try:
                    record(directory, source.name, edge, api, work)
                except (ValueError, RuntimeError) as error:
                    failures.append(str(error))
                    print(f"BLOCKED {error}", flush=True)
        if failures:
            raise RuntimeError(f"{len(failures)} variants lack records")
    finally:
        edge.stop()
        shutil.rmtree(work)


if __name__ == "__main__":
    main()
