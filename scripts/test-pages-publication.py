# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Check the byte contract of staged Pages downloads over HTTP."""
import importlib.util
import hashlib
import json
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


staging = module("staging", "stage-pages.py")
serving = module("serving", "serve-site.py")


class QuietHandler(serving.SiteHandler):
    def log_message(self, *_):
        pass


def check_explorer_values(name, explorer):
    assert explorer, (name, "no explorer variants")
    for variant, recording in explorer.items():
        assert recording["stages"], (name, variant, "no stages")
        for index, stage in enumerate(recording["stages"]):
            missing = {"input", "output"} - stage.keys()
            assert not missing, (name, variant, index, "missing stage values", missing)


def check_publication(output):
    serving.DOCS = output
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    count = 0
    try:
        for name in staging.REPORTS:
            with urlopen(f"{endpoint}/{name}") as response:
                assert response.read() == (ROOT / name).read_bytes(), name
        sources = staging.published_sources(ROOT)
        for name, directories in sources.items():
            expected = {p.relative_to(source) for source in directories for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
            expected.add(Path("explorer.json"))
            actual = {p.relative_to(output / name) for p in (output / name).rglob("*") if p.is_file()}
            assert actual == expected, (name, actual ^ expected)
            with urlopen(f"{endpoint}/{name}/explorer.json") as response:
                explorer = json.load(response)
            check_explorer_values(name, explorer)
            for pipeline in (pipeline for source in directories for pipeline in source.glob("pipeline*.yaml")):
                with urlopen(f"{endpoint}/{name}/{pipeline.name}") as response:
                    assert response.read() == pipeline.read_bytes(), pipeline
                count += 1
        for metadata in (ROOT / "skills").glob("*/*/skill.yaml"):
            if yaml.safe_load(metadata.read_text()).get("publication", {}).get("status") != "pulled":
                continue
            name = metadata.parent.name
            assert not (output / name).exists(), name
            assert not (output / "skill" / name).exists(), name
            for pipeline in metadata.parent.glob("pipeline*.yaml"):
                try:
                    urlopen(f"{endpoint}/{name}/{pipeline.name}")
                except HTTPError as exc:
                    assert exc.code == 404, exc
                else:
                    raise AssertionError(f"pulled download still published: {name}")
        for page in (output / "skill").glob("*/index.html"):
            with urlopen(f"{endpoint}/skill/{page.parent.name}/") as response:
                assert response.read() == page.read_bytes(), page
        ledger = json.loads((output / "example-conformance.json").read_text())
        for row in ledger["examples"]:
            source = ROOT / row["pipeline"]
            assert row["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest(), row["pipeline"]
            if row["status"] != "pulled":
                with urlopen(f"{endpoint}/{source.parent.name}/{source.name}") as response:
                    assert row["sha256"] == hashlib.sha256(response.read()).hexdigest(), row["pipeline"]
        pages = {p.name for p in (output / "skill").iterdir()}
        published_names = {Path(row["pipeline"]).parent.name for row in ledger["examples"] if row["status"] != "pulled"}
        assert pages == published_names, ("published pages missing", published_names - pages, "extra pages", pages - published_names)
        assert pages == set(json.loads((output / "catalog.json").read_text())["skills"]), pages
        print(f"PASS {count} published pipeline downloads; pulled downloads return 404")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def check_staged_server(output):
    serving.DOCS = output
    report = output / "catalog.json"
    catalog = json.loads(report.read_text())
    catalog["generated"] = "staged publication fixture"
    report.write_text(json.dumps(catalog))
    pipeline = output / "slug-generate" / "pipeline-cli.yaml"
    pipeline.write_bytes(pipeline.read_bytes() + b"\n")
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        for path in (report, pipeline):
            with urlopen(f"http://127.0.0.1:{server.server_port}/{path.relative_to(output)}") as response:
                assert response.read() == path.read_bytes(), path
        print("PASS server returns staged bytes when source artifacts differ")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def main():
    check_publication(ROOT / "docs")
    (ROOT / ".conformance").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / ".conformance", prefix="pages-publication-") as directory:
        output = Path(directory)
        stale = output / "retry-wrapper"
        stale.mkdir()
        (stale / "obsolete.json").write_text("stale withdrawn download")
        nested = output / "slug-generate" / "slug-generate"
        nested.mkdir(parents=True)
        (nested / "pipeline-cli.yaml").write_text("stale nested download")
        (output / "keep.css").write_text("static asset")
        staging.stage(ROOT, output)
        check_publication(output)
        (output / "slug-generate" / "obsolete.yaml").write_text("stale file")
        staging.stage(ROOT, output)
        check_publication(output)
        assert (output / "keep.css").read_text() == "static asset"
        check_staged_server(output)


if __name__ == "__main__":
    main()
