# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise the unchanged published slug MCP adapter at its configured PORT."""
import importlib.util
import re
import shutil
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("recipes", ROOT / "scripts/test-recipes.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def main():
    count = 0
    for path in (ROOT / "skills").glob("*/*/pipeline-mcp.yaml"):
        metadata = yaml.safe_load((path.parent / "skill.yaml").read_text())
        if metadata.get("publication", {}).get("status") == "pulled":
            continue
        config = yaml.safe_load(path.read_text())["config"]
        adapter = config["input"]["http_server"]
        assert re.fullmatch(r"[^:]+:\$\{PORT(?::[^}]+)?\}", adapter["address"]), str(path)
        count += 1
    print(f"Published MCP listener configurations: {count}")
    work = ROOT / ".conformance/mcp-listener"
    work.mkdir(parents=True, exist_ok=True)
    port = runner.free_port()
    api = f"http://127.0.0.1:{runner.free_port()}"
    edge = runner.Edge(api, work / "data", work / "edge.log", ROOT, {"PORT": str(port)})
    try:
        edge.start()
        cli = shutil.which("expanso-cli")
        assert runner.wait_for_api(cli, api), "Edge API did not start"
        path = ROOT / "skills/transforms/slug-generate/pipeline-mcp.yaml"
        deployed, job_name, details = runner.deploy(path, cli, api)
        assert deployed, details
        ready, reason = runner.wait_for_execution_running(
            cli, job_name, api, timeout=45
        )
        assert ready, reason
        assert runner.wait_for_port(port, timeout=15), "Published MCP listener did not bind PORT"
        response = requests.post(f"http://127.0.0.1:{port}/slugify", json={"text": "Hello World!"}, timeout=10)
        assert response.status_code == 200, response.text
        assert response.json()["slug"] == "hello-world", response.text
        print("Intact published MCP adapter: hello-world")
    finally:
        edge.stop()
        assert not runner.wait_for_port(port, timeout=0.2), "Owned listener survived shutdown"
        shutil.rmtree(work)


if __name__ == "__main__":
    main()
