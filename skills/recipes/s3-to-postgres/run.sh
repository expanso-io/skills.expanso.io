#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
expanso run -c "$SCRIPT_DIR/pipeline.yaml" "$@"
