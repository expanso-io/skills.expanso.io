#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE="$SCRIPT_DIR/pipeline.yaml"

for tool in expanso-edge expanso-cli; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Error: $tool is required. Install it from https://get.expanso.io." >&2
    exit 1
  fi
done

echo "Validating $PIPELINE with Expanso Edge..."
expanso-edge validate "$PIPELINE"

echo "Deploying $PIPELINE through Expanso Cloud..."
expanso-cli job deploy "$PIPELINE" "$@"

echo "Deployment accepted. Confirm assignment and execution separately:"
echo "  expanso-cli job describe <job-id>"
echo "  expanso-cli execution list --job-id <job-id>"
