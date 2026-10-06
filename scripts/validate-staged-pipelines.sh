#!/usr/bin/env bash
set -euo pipefail

pipeline_paths=()
while IFS= read -r -d '' path; do
  case "$path" in
    skills/*/*/pipeline.yaml|skills/*/*/pipeline-cli.yaml|\
    skills/*/*/pipeline-mcp.yaml|skills/*/*/pipeline-cloud.yaml|\
    skills/*/*/pipeline-query.yaml)
      pipeline_paths+=("$path")
      ;;
  esac
done < <(
  git diff --cached --name-only --diff-filter=ACMR -z -- skills
)

if [[ "${#pipeline_paths[@]}" -eq 0 ]]; then
  echo "No staged pipeline YAML to validate."
  exit 0
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
"$script_dir/require-expanso-tools.sh" edge
failed=0

for path in "${pipeline_paths[@]}"; do
  echo "Validating staged $path"
  if ! git show ":$path" | expanso-edge validate -; then
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "One or more staged pipelines failed expanso-edge validation." >&2
  exit 1
fi

echo "Validated ${#pipeline_paths[@]} staged pipeline file(s) with expanso-edge."
