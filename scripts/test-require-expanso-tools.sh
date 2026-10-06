#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
checker="$repo_root/scripts/require-expanso-tools.sh"
test_root=$(mktemp -d)

cleanup() {
  rm -rf "$test_root"
}
trap cleanup EXIT INT TERM

make_binary() {
  local destination="$1"
  local version="$2"

  printf '%s\n' \
    '#!/usr/bin/env bash' \
    "printf '%s\\n' '$version'" > "$destination"
  chmod 0755 "$destination"
}

tool_dir="$test_root/tools"
empty_dir="$test_root/empty"
mkdir -p "$tool_dir" "$empty_dir"
make_binary "$tool_dir/expanso-edge" "v9.9.9"
make_binary "$tool_dir/expanso-cli" "Expanso CLI version v9.9.9"

output=$(PATH="$tool_dir:/usr/bin:/bin" "$checker")
grep -q "expanso-edge: v9.9.9 ($tool_dir/expanso-edge)" <<< "$output"
grep -q "expanso-cli: Expanso CLI version v9.9.9 ($tool_dir/expanso-cli)" \
  <<< "$output"
echo "PASS uses Expanso tools already on PATH"

error_file="$test_root/missing-edge"
if PATH="$empty_dir:/usr/bin:/bin" "$checker" edge \
  > /dev/null 2> "$error_file"; then
  echo "checker unexpectedly accepted a missing expanso-edge" >&2
  exit 1
fi
grep -q "expanso-edge is missing from PATH" "$error_file"
grep -q "Install the latest expanso-edge release" "$error_file"
echo "PASS missing Edge fails with latest-install guidance"

error_file="$test_root/missing-cli"
if PATH="$empty_dir:/usr/bin:/bin" "$checker" cli \
  > /dev/null 2> "$error_file"; then
  echo "checker unexpectedly accepted a missing expanso-cli" >&2
  exit 1
fi
grep -q "expanso-cli is missing from PATH" "$error_file"
grep -q "Install the latest expanso-cli release" "$error_file"
echo "PASS missing CLI fails with latest-install guidance"
