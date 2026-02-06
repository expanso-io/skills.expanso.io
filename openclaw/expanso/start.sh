#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${EXPANSO_BIN_DIR:-$HOME/.expanso/bin}"
LOG_DIR="${EXPANSO_LOG_DIR:-$HOME/.expanso/logs}"
PID_FILE="$HOME/.expanso/expanso-edge.pid"
CONFIG_FILE="$HOME/.expanso/config"

mkdir -p "$LOG_DIR" "$(dirname "$PID_FILE")"

# Parse arguments
TOKEN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --token|-t)
            TOKEN="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get token from various sources
get_token() {
    # Command line argument
    if [[ -n "$TOKEN" ]]; then
        echo "$TOKEN"
        return 0
    fi
    
    # Environment variable
    if [[ -n "${EXPANSO_EDGE_BOOTSTRAP_TOKEN:-}" ]]; then
        echo "$EXPANSO_EDGE_BOOTSTRAP_TOKEN"
        return 0
    fi
    
    # Config file
    if [[ -f "$CONFIG_FILE" ]]; then
        local token=$(grep -E "^EXPANSO_EDGE_BOOTSTRAP_TOKEN=" "$CONFIG_FILE" | cut -d= -f2-)
        if [[ -n "$token" ]]; then
            echo "$token"
            return 0
        fi
    fi
    
    return 1
}

# Check if already running
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️  expanso-edge already running (PID: $PID)"
        echo "   Use ./stop.sh to stop it first"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# Check binary exists
EDGE_BIN="$BIN_DIR/expanso-edge"
if [[ ! -x "$EDGE_BIN" ]]; then
    echo "❌ expanso-edge not found at $EDGE_BIN"
    echo "   Run ./install.sh first"
    exit 1
fi

# Get bootstrap token
BOOTSTRAP_TOKEN=$(get_token) || {
    echo "❌ No bootstrap token found"
    echo ""
    echo "Provide token via:"
    echo "  1. ./start.sh --token YOUR_TOKEN"
    echo "  2. export EXPANSO_EDGE_BOOTSTRAP_TOKEN=YOUR_TOKEN"
    echo "  3. echo 'EXPANSO_EDGE_BOOTSTRAP_TOKEN=YOUR_TOKEN' >> ~/.expanso/config"
    echo ""
    echo "Get your token from https://cloud.expanso.io → Networks → Create/Join"
    exit 1
}

# Start the daemon
LOG_FILE="$LOG_DIR/expanso-edge.log"
echo "🚀 Starting expanso-edge..."
echo "   Log file: $LOG_FILE"

# Run in background
nohup "$EDGE_BIN" run \
    --bootstrap-token "$BOOTSTRAP_TOKEN" \
    >> "$LOG_FILE" 2>&1 &

PID=$!
echo "$PID" > "$PID_FILE"

# Wait a moment and check if it's still running
sleep 2
if kill -0 "$PID" 2>/dev/null; then
    echo "✅ expanso-edge started (PID: $PID)"
    echo ""
    echo "Commands:"
    echo "  ./status.sh  - Check status"
    echo "  ./logs.sh    - View logs"
    echo "  ./stop.sh    - Stop daemon"
else
    echo "❌ expanso-edge failed to start"
    echo "   Check logs: tail -50 $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
