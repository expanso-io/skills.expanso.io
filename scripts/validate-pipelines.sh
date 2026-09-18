#!/usr/bin/env bash
# Validate every published pipeline job spec with the Expanso CLI.
#
# This is the repository-owned command that CI runs. It lives here, rather than
# inline in .github/workflows/ci.yml, so the exact gate can be reproduced
# locally before pushing:
#
#     ./scripts/validate-pipelines.sh
#
# It is fail-closed on purpose. If expanso-cli cannot be installed or run, the
# gate FAILS rather than passing by skipping: a green check that silently
# validated nothing is worse than a red one. CI previously skipped this step for
# exactly that reason (its installer URL 404'd), so no pipeline was ever checked.
set -euo pipefail

SKILLS_DIR="${1:-skills}"

if ! command -v expanso-cli >/dev/null 2>&1; then
  echo "Installing expanso-cli..."
  # Authoritative route, matching README.md and docs/install.sh.
  # Pipe to bash, not sh: the installer is a bash script and fails under
  # dash (/bin/sh on Debian/Ubuntu) with a syntax error at its first array.
  curl -fsSL https://get.expanso.io/cli/install.sh | bash
  export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
fi

if ! command -v expanso-cli >/dev/null 2>&1; then
  echo "expanso-cli is required to validate pipelines and could not be installed." >&2
  echo "Refusing to report success without running the validator." >&2
  exit 1
fi

echo "expanso-cli version: $(expanso-cli version 2>&1 | head -1)"
echo "Validating pipeline job specs under ${SKILLS_DIR}/ ..."

# NOTE ON SCOPE. This gate checks JOB SPEC structure only, with
# `expanso-cli job validate --offline`. It does NOT check that a pipeline's
# inner component configuration is valid: `expanso-edge validate` is stricter
# and still rejects several recipes for real component-config errors (unknown
# fields, bloblang arity, numeric fields written as env interpolations).
# Passing this gate therefore means "accepted as a job spec", NOT "the pipeline
# is semantically correct". Do not read a green run as the latter.

files=()
while IFS= read -r f; do
  files+=("$f")
done < <(find "$SKILLS_DIR" -name "pipeline*.yaml" -type f | sort)

if [ "${#files[@]}" -eq 0 ]; then
  echo "No pipeline*.yaml files found under ${SKILLS_DIR}/." >&2
  echo "Refusing to report success without validating anything." >&2
  exit 1
fi

errors=0
validated=0
for pipeline in "${files[@]}"; do
  # Capture this validator's OWN exit status directly. Do not pipe it into
  # another command: with `set -o pipefail` the pipeline's status would be the
  # last command's, and under `set -e` a failing validator would abort the
  # script before the error could be counted or reported.
  set +e
  output="$(expanso-cli job validate "$pipeline" --offline 2>&1)"
  status=$?
  set -e

  if [ "$status" -eq 0 ]; then
    validated=$((validated + 1))
  else
    errors=$((errors + 1))
    echo "FAIL ($status) $pipeline"
    printf '%s\n' "$output" | sed 's/^/     /'
  fi
done

echo "Validated ${validated} of ${#files[@]} pipeline files, ${errors} failing."
if [ "$errors" -gt 0 ]; then
  exit 1
fi
