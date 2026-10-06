#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
"$script_dir/require-expanso-tools.sh"

mode="${1:-check}"
output_dir="${2:-.conformance/nightly}"

case "$mode" in
  check|generate)
    ;;
  *)
    echo "usage: $0 [check|generate] [output-directory]" >&2
    exit 2
    ;;
esac

uv run -s scripts/audit-skills.py
"$script_dir/validate-pipelines.sh"
uv run -s scripts/check-example-conformance.py
uv run -s scripts/check-feature-preservation.py
uv run -s scripts/test-skills.py \
  --variant cli \
  --no-cache \
  --max-reruns 1 \
  --report .conformance/full-cli.json
uv run -s scripts/test-skills.py \
  --variant mcp \
  --no-cache \
  --max-reruns 1 \
  --report .conformance/full-mcp.json
uv run -s scripts/test-negative-inputs.py
uv run -s scripts/test-recipes.py \
  --report .conformance/recipe-execution.json
uv run -s scripts/build-catalog.py --check
uv run -s scripts/build-plugin.py --check

if [[ "$mode" == "check" ]]; then
  uv run -s scripts/validate-skills.py --check
  uv run -s scripts/build-example-conformance.py --check
else
  mkdir -p "$output_dir"
  uv run -s scripts/validate-skills.py \
    --output "$output_dir/validation-report.json"
  uv run -s scripts/build-example-conformance.py \
    --output "$output_dir/example-conformance.json"
fi
