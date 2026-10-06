#!/usr/bin/env bash
set -euo pipefail

base_sha="${1:-}"

if [[ -z "$base_sha" || "$base_sha" =~ ^0+$ ]]; then
  base_sha="HEAD^"
fi

merge_base=$(git merge-base "$base_sha" HEAD)
relevant='^(skills/|scripts/|tests/|package(-lock)?\.json$|playwright\.config\.js$|catalog(-minimal)?\.json$|validation-report\.json$|example-conformance\.json$|negative-input-classification\.json$|review-regression-evidence\.json$|\.github/|\.pre-commit-config\.yaml$|docs/(index\.html|css/|js/)|README\.md$|CONTRIBUTING\.md$|justfile$)'

if git diff --name-only "$merge_base" HEAD | grep -Eq "$relevant"; then
  echo "run=true" >> "$GITHUB_OUTPUT"
  echo "Conformance inputs changed since $merge_base."
else
  echo "run=false" >> "$GITHUB_OUTPUT"
  echo "No published example or conformance input changed since $merge_base."
fi
