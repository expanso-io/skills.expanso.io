#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for expanso CLI
if ! command -v expanso &> /dev/null; then
  echo "Error: expanso CLI not found. Install with: clawhub install expanso"
  exit 1
fi

# Run the pipeline
echo "Running pipeline..."
expanso run -c "$SCRIPT_DIR/pipeline.yaml" "$@"
