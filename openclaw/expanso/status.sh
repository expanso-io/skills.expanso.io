#!/usr/bin/env bash
set -euo pipefail

BIN_DIR="${EXPANSO_BIN_DIR:-$HOME/.expanso/bin}"
PID_FILE="$HOME/.expanso/expanso-edge.pid"

echo "═══════════════════════════════════════"
echo "  Expanso Status"
echo "═══════════════════════════════════════"

# Check binaries
echo ""
echo "📦 Binaries:"
if [[ -x "$BIN_DIR/expanso-edge" ]]; then
    VERSION=$("$BIN_DIR/expanso-edge" version 2>/dev/null | head -1 || echo "unknown")
    echo "   ✅ expanso-edge: $VERSION"
else
    echo "   ❌ expanso-edge: not installed"
fi

if [[ -x "$BIN_DIR/expanso-cli" ]]; then
    VERSION=$("$BIN_DIR/expanso-cli" version 2>/dev/null | head -1 || echo "unknown")
    echo "   ✅ expanso-cli: $VERSION"
else
    echo "   ❌ expanso-cli: not installed"
fi

# Check daemon
echo ""
echo "🔄 Daemon:"
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        UPTIME=$(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ' || echo "unknown")
        echo "   ✅ Running (PID: $PID, uptime: $UPTIME)"
    else
        echo "   ❌ Not running (stale PID file)"
    fi
else
    # Check for process without PID file
    PID=$(pgrep -f "expanso-edge run" || true)
    if [[ -n "$PID" ]]; then
        echo "   ⚠️  Running without PID file (PID: $PID)"
    else
        echo "   ⏹️  Not running"
    fi
fi

# Check token
echo ""
echo "🔑 Configuration:"
if [[ -n "${EXPANSO_EDGE_BOOTSTRAP_TOKEN:-}" ]]; then
    echo "   ✅ Token: set via environment"
elif [[ -f "$HOME/.expanso/config" ]] && grep -q "EXPANSO_EDGE_BOOTSTRAP_TOKEN" "$HOME/.expanso/config"; then
    echo "   ✅ Token: set via config file"
else
    echo "   ❌ Token: not configured"
fi

# Cloud connectivity
echo ""
echo "☁️  Cloud:"
if curl -s --connect-timeout 5 https://cloud.expanso.io/health >/dev/null 2>&1; then
    echo "   ✅ cloud.expanso.io reachable"
else
    echo "   ❌ cloud.expanso.io not reachable"
fi

echo ""
