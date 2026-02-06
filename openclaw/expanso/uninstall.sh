#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${EXPANSO_BIN_DIR:-$HOME/.expanso/bin}"

echo "🗑️  Uninstalling Expanso..."

# Stop daemon if running
"$SKILL_DIR/stop.sh" 2>/dev/null || true

# Remove binaries
if [[ -f "$BIN_DIR/expanso-edge" ]]; then
    rm -f "$BIN_DIR/expanso-edge"
    echo "   Removed expanso-edge"
fi

if [[ -f "$BIN_DIR/expanso-cli" ]]; then
    rm -f "$BIN_DIR/expanso-cli"
    echo "   Removed expanso-cli"
fi

# Ask about config/logs
echo ""
echo -n "Remove configuration and logs? [y/N] "
read -r confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.expanso"
    echo "   Removed ~/.expanso"
fi

echo ""
echo "✅ Uninstall complete"
