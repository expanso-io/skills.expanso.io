#!/usr/bin/env bash
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "═══════════════════════════════════════"
echo "  Expanso Skill Test Suite"
echo "═══════════════════════════════════════"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local name="$1"
    local cmd="$2"
    
    echo -n "Testing: $name... "
    if eval "$cmd" >/dev/null 2>&1; then
        echo "✅ PASS"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Test 1: Scripts exist and are executable
run_test "install.sh exists" "[[ -x '$SKILL_DIR/install.sh' ]]"
run_test "start.sh exists" "[[ -x '$SKILL_DIR/start.sh' ]]"
run_test "stop.sh exists" "[[ -x '$SKILL_DIR/stop.sh' ]]"
run_test "status.sh exists" "[[ -x '$SKILL_DIR/status.sh' ]]"
run_test "logs.sh exists" "[[ -x '$SKILL_DIR/logs.sh' ]]"
run_test "uninstall.sh exists" "[[ -x '$SKILL_DIR/uninstall.sh' ]]"
run_test "SKILL.md exists" "[[ -f '$SKILL_DIR/SKILL.md' ]]"

# Test 2: status.sh runs without error
run_test "status.sh runs" "'$SKILL_DIR/status.sh'"

# Test 3: Check for curl (required for install)
run_test "curl available" "command -v curl"

echo ""
echo "═══════════════════════════════════════"
echo "  Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "═══════════════════════════════════════"

if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
fi
