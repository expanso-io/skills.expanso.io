#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -eq 0 ]]; then
  requested=(expanso-edge expanso-cli)
else
  requested=()
  for tool in "$@"; do
    case "$tool" in
      edge|expanso-edge)
        requested+=(expanso-edge)
        ;;
      cli|expanso-cli)
        requested+=(expanso-cli)
        ;;
      *)
        echo "usage: $0 [edge|cli ...]" >&2
        exit 2
        ;;
    esac
  done
fi

for binary in "${requested[@]}"; do
  resolved=$(command -v "$binary" 2>/dev/null || true)
  if [[ -z "$resolved" ]]; then
    echo "$binary is missing from PATH." >&2
    echo "Install the latest $binary release from https://get.expanso.io/ and retry." >&2
    exit 1
  fi
  if ! version=$("$resolved" version 2>&1); then
    echo "$binary on PATH could not report its version: $resolved" >&2
    echo "Install the latest $binary release from https://get.expanso.io/ and retry." >&2
    exit 1
  fi
  [[ -n "$version" ]] || {
    echo "$binary on PATH returned an empty version: $resolved" >&2
    exit 1
  }
  echo "$binary: $version ($resolved)"
done
