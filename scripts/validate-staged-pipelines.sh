#!/usr/bin/env bash
set -euo pipefail

if ! command -v expanso-edge >/dev/null 2>&1; then
  echo "expanso-edge is required to validate staged pipelines." >&2
  exit 1
fi

count=0
failed=0

while IFS= read -r -d '' path; do
  case "$path" in
    skills/*/*/pipeline.yaml|skills/*/*/pipeline-cli.yaml|\
    skills/*/*/pipeline-mcp.yaml|skills/*/*/pipeline-cloud.yaml|\
    skills/*/*/pipeline-query.yaml)
      count=$((count + 1))
      echo "Validating staged $path"
      if ! git show ":$path" | expanso-edge validate -; then
        failed=1
      fi
      ;;
  esac
done < <(
  git diff --cached --name-only --diff-filter=ACMR -z -- skills
)

if [[ "$count" -eq 0 ]]; then
  echo "No staged pipeline YAML to validate."
  exit 0
fi

if [[ "$failed" -ne 0 ]]; then
  echo "One or more staged pipelines failed expanso-edge validation." >&2
  exit 1
fi

echo "Validated $count staged pipeline file(s) with expanso-edge."
