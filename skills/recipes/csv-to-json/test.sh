#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -c "import yaml; yaml.safe_load(open('$SCRIPT_DIR/pipeline.yaml'))" && echo "✓ YAML valid"
echo "All tests passed!"
