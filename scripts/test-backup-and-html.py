# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Exercise backup object-key isolation and quoted/unquoted HTML analysis."""
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("regressions", ROOT / "scripts/test-review-regressions.py")
reg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reg
spec.loader.exec_module(reg)


def main():
    directory = ROOT / ".conformance" / f"backup-and-html-{time.time_ns()}"
    directory.mkdir(parents=True)
    suite = reg.Suite(directory, {"DB_HOST": "fixture", "DB_NAME": "fixture"})
    try:
        cfg = reg.config("recipes/nightly-backup", "recipe")
        table_inputs = cfg["input"]["sequence"]["inputs"]
        cfg["pipeline"]["processors"] = [
            {"unarchive": {"format": "json_array"}},
            {"switch": [
                {"check": 'this._table == "' + table_input["sql_select"]["table"] + '"',
                 "processors": table_input["processors"]}
                for table_input in table_inputs
            ]},
        ] + cfg["pipeline"]["processors"]
        for case in cfg["output"]["switch"]["cases"]:
            path = case["output"]["gcp_cloud_storage"]["path"]
            case["output"] = {"file": {"path": str(directory / "objects") + "/" + path, "codec": "lines"}}
        payload = [{"_table": table, "id": row} for table in ["inventory", "orders", "order_items"] for row in [1, 2]]
        suite.execute(cfg, payload, retain_output=True, decode_json=False)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            files = list((directory / "objects").rglob("*.jsonl"))
            if len(files) == 6:
                break
            time.sleep(0.05)
        assert len(files) == 6, files
        records = [json.loads(path.read_text()) for path in files]
        assert {(row["_table"], row["id"]) for row in records} == {(row["_table"], row["id"]) for row in payload}, records
        assert len({row["_backup_metadata"]["row_id"] for row in records}) == 6, records
        assert all(row["_checksum"] for row in records), records
        for variant in ["cli", "mcp"]:
            for attrs in [
                '<meta name=description content=D><meta name=viewport content=width=device-width><img src=x alt=Chart>',
                '<meta name = description content = D><meta name = viewport content=width=device-width><img src=x alt = Chart>',
                '<meta name="description" content="Description with spaces"><meta name="viewport" content="width=device-width"><img src="x" alt="Chart">',
                "<meta name='description' content='Description with spaces'><meta name='viewport' content='width=device-width'><img src='x' alt=''>",
            ]:
                result = suite.execute(reg.config("workflows/seo-pipeline", variant), {"html": '<title>Chart</title><h1>Chart</h1>' + attrs})
                analysis = result["analysis"]
                assert analysis["score"] == 100 and analysis["has_viewport"] is True, result
                assert analysis["images_missing_alt"] == 0 and analysis["meta_description"] in ["D", "Description with spaces"], result
                assert result["recommendations"] == [], result
            for attribute, expected in [
                ('content="Bob\'s complete guide"', "Bob's complete guide"),
                ("content='A \"complete\" guide'", 'A "complete" guide'),
            ]:
                result = suite.execute(reg.config("workflows/seo-pipeline", variant),
                                       {"html": '<title>Chart</title><h1>Chart</h1><meta name="description" ' + attribute + '><meta name=viewport content=x><img src=x alt=Chart>'})
                assert result["analysis"]["meta_description"] == expected, result
                assert result["analysis"]["score"] == 100, result
            result = suite.execute(reg.config("workflows/seo-pipeline", variant),
                                   {"html": '<title>Chart</title><h1>Chart</h1><meta name=description-other content=D><meta name=viewport-other content=x><img src=x alt=>'})
            assert result["analysis"]["score"] == 45, result
        reg.write_evidence()
        print("PASS six backup rows survive in distinct objects; fourteen HTML attribute cases")
    finally:
        suite.close()


if __name__ == "__main__":
    main()
