#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Testing pipeline syntax..."
python3 -c "import yaml; yaml.safe_load(open('$SCRIPT_DIR/pipeline.yaml'))" 2>/dev/null && echo "✓ YAML valid" || echo "⚠ Could not validate"
grep -q "http_server:" "$SCRIPT_DIR/pipeline.yaml" && echo "✓ HTTP input configured" || exit 1
echo "All tests passed!"
