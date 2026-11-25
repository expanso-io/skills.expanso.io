#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
checker="$repo_root/scripts/check-no-auto-open.py"
fixtures="$repo_root/scripts/tests/check-no-auto-open"

if uv run -s "$checker" "$fixtures/bad"; then
    echo "Expected unsafe fixture to fail" >&2
    exit 1
fi

uv run -s "$checker" "$fixtures/good"
echo "Auto-open checker test passed."
