#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v expanso &> /dev/null; then
  echo "Error: expanso CLI not found. Install with: clawhub install expanso"
  exit 1
fi
echo "Starting webhook server on :8080..."
expanso run -c "$SCRIPT_DIR/pipeline.yaml" "$@"
