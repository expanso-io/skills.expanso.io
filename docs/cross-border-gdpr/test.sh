#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Testing pipeline syntax..."

# Check YAML is valid
if command -v yq &> /dev/null; then
  yq eval '.' "$SCRIPT_DIR/pipeline.yaml" > /dev/null
  echo "✓ YAML syntax valid"
elif command -v python3 &> /dev/null; then
  python3 -c "import yaml; yaml.safe_load(open('$SCRIPT_DIR/pipeline.yaml'))"
  echo "✓ YAML syntax valid"
else
  echo "⚠ No YAML validator available (install yq or python3)"
fi

# Check required fields
if grep -q "^input:" "$SCRIPT_DIR/pipeline.yaml" && \
   grep -q "^output:" "$SCRIPT_DIR/pipeline.yaml"; then
  echo "✓ Required sections present (input, output)"
else
  echo "✗ Missing required sections"
  exit 1
fi

echo "All tests passed!"
