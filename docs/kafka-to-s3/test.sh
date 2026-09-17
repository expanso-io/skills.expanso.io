#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Testing pipeline syntax..."
if command -v python3 &> /dev/null; then
  python3 -c "import yaml; yaml.safe_load(open('$SCRIPT_DIR/pipeline.yaml'))"
  echo "✓ YAML syntax valid"
fi
if grep -q "^input:" "$SCRIPT_DIR/pipeline.yaml" && grep -q "^output:" "$SCRIPT_DIR/pipeline.yaml"; then
  echo "✓ Required sections present"
else
  echo "✗ Missing required sections"
  exit 1
fi
echo "All tests passed!"
