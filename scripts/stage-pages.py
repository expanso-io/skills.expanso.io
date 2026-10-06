# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Build the flat GitHub Pages publication from authoritative artifacts."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ("catalog.json", "catalog-minimal.json", "validation-report.json", "example-conformance.json")


def stage_observations(repository):
    observations = {}
    reports = list((repository / "execution-reports").glob("*.json*"))
    reports += list((repository / ".conformance").glob("full-*.json"))
    for path in reports:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt") as handle:
            report = json.load(handle)
        for skill in report.get("skills", []):
            sample = next((test for test in skill.get("tests", []) if test.get("status") == "passed" and test.get("stages")), None)
            if sample:
                observations[(skill["name"], report["variant"], skill["pipeline_sha256"])] = {
                    "stages": sample["stages"], "scope": sample["stage_scope"],
                    "date": report["finished_at"], "sample": sample["name"],
                }
    return observations


def explorer_data(directories, observations):
    variants = {}
    for source in directories:
        for path in sorted(source.glob("pipeline*.yaml")):
            job = yaml.safe_load(path.read_text())
            processors = job.get("config", {}).get("pipeline", {}).get("processors", [])
            variant = path.stem.removeprefix("pipeline-")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            evidence = observations.get((source.name, variant, digest), {})
            stages = []
            for index, processor in enumerate(processors):
                stages.append({"label": next(iter(processor)), "config": yaml.safe_dump(processor, sort_keys=False),
                               **(evidence.get("stages", [])[index] if index < len(evidence.get("stages", [])) else {})})
            first = evidence.get("stages", [{}])[0].get("input") if evidence.get("stages") else None
            last = evidence.get("stages", [{}])[-1].get("output") if evidence.get("stages") else None
            stages.insert(0, {"label": "input", "config": yaml.safe_dump(job["config"]["input"], sort_keys=False),
                              **({"input": first, "output": first} if first is not None else {})})
            stages.append({"label": "output", "config": yaml.safe_dump(job["config"]["output"], sort_keys=False),
                           **({"input": last, "output": last} if last is not None else {})})
            variants[path.name] = {"sha256": digest, "stages": stages,
                                   **{key: value for key, value in evidence.items() if key != "stages"}}
    return variants


def published_sources(repository):
    sources = {}
    for directory in sorted((repository / "skills").glob("*/*")):
        if not directory.is_dir():
            continue
        metadata = directory / "skill.yaml"
        skill = yaml.safe_load(metadata.read_text()) if metadata.exists() else {}
        if skill.get("publication", {}).get("status") == "pulled":
            continue
        sources.setdefault(directory.name, []).append(directory)
    return sources


def stage(repository, output):
    sources = published_sources(repository)
    observations = stage_observations(repository)
    skill_names = {path.name for path in (repository / "skills").glob("*/*") if path.is_dir()}
    catalog = json.loads((repository / "catalog.json").read_text())
    if set(catalog["skills"]) - sources.keys():
        raise ValueError("catalog contains unavailable or pulled skills")
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_dir() and (
            child.name == "skill"
            or child.name in skill_names
            or (child / "skill.yaml").exists()
            or any(child.rglob("pipeline*.yaml"))
        ):
            shutil.rmtree(child)
    for name in REPORTS:
        shutil.copyfile(repository / name, output / name)
    for name, directories in sources.items():
        for source in directories:
            for path in source.rglob("*"):
                destination = output / name / path.relative_to(source)
                if path.is_file() and destination.is_file() and path.read_bytes() != destination.read_bytes():
                    raise ValueError(f"conflicting published artifact: {name}/{path.relative_to(source)}")
            shutil.copytree(source, output / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        (output / name / "explorer.json").write_text(json.dumps(explorer_data(directories, observations)))
    spec = importlib.util.spec_from_file_location("seo", ROOT / "scripts/build-seo.py")
    seo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seo)
    seo.generate_sitemap(catalog, output)
    seo.generate_skill_pages(catalog, output)
    print(f"Staged {len(sources)} published skill directories")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    stage(ROOT, args.output)


if __name__ == "__main__":
    main()
