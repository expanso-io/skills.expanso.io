#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Testing pipeline syntax..."

# Job-spec recipes nest input/output under `config:`; plain pipelines keep
# them at the root. Parse the YAML so both layouts are checked the same way.
python3 - "$SCRIPT_DIR/pipeline.yaml" <<'PY'
import sys

import yaml

with open(sys.argv[1]) as f:
    doc = yaml.safe_load(f)
print("✓ YAML syntax valid")

body = doc.get("config", doc) if isinstance(doc, dict) else None
missing = [k for k in ("input", "output") if not isinstance(body, dict) or not body.get(k)]
if missing:
    print(f"✗ Missing required sections: {', '.join(missing)}")
    sys.exit(1)
print("✓ Required sections present (input, output)")
PY

echo "All tests passed!"
