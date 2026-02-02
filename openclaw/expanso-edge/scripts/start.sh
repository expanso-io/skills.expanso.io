#!/bin/bash
# Start expanso-edge daemon with bootstrap configuration

echo "=== Starting Expanso Edge ==="
echo ""

# Load environment variables
if [ -f "$HOME/.clawdbot/.env" ]; then
    source "$HOME/.clawdbot/.env"
elif [ -f "/root/.clawdbot/.env" ]; then
    source "/root/.clawdbot/.env"
fi

# Check if already running
if pgrep -f "expanso-edge" > /dev/null; then
    PID=$(pgrep -f "expanso-edge")
    echo "⚠️  expanso-edge is already running (PID: $PID)"
    echo ""
    echo "To restart, run: bash $(dirname $0)/restart.sh"
    exit 0
fi

# Validate configuration
if [ -z "$EXPANSO_EDGE_BOOTSTRAP_TOKEN" ]; then
    echo "❌ EXPANSO_EDGE_BOOTSTRAP_TOKEN not set"
    echo ""
    echo "Set it in one of these ways:"
    echo "  1. Add to ~/.clawdbot/.env:"
    echo "     echo 'EXPANSO_EDGE_BOOTSTRAP_TOKEN=your-token' >> ~/.clawdbot/.env"
    echo ""
    echo "  2. Export as environment variable:"
    echo "     export EXPANSO_EDGE_BOOTSTRAP_TOKEN=your-token"
    echo ""
    exit 1
fi

# Set default bootstrap URL if not provided
EXPANSO_EDGE_BOOTSTRAP_URL=${EXPANSO_EDGE_BOOTSTRAP_URL:-https://start.cloud.expanso.io}

# Start the daemon
echo "Starting expanso-edge..."
echo "  Bootstrap URL: $EXPANSO_EDGE_BOOTSTRAP_URL"
echo "  Token: ${EXPANSO_EDGE_BOOTSTRAP_TOKEN:0:20}..."
echo ""

export EXPANSO_EDGE_BOOTSTRAP_TOKEN
export EXPANSO_EDGE_BOOTSTRAP_URL

# Start in background with log file
LOG_FILE="/tmp/expanso-edge.log"
nohup expanso-edge > "$LOG_FILE" 2>&1 &
PID=$!

sleep 2

# Verify it started
if pgrep -f "expanso-edge" > /dev/null; then
    echo "✓ expanso-edge started successfully"
    echo "  PID: $PID"
    echo "  Logs: $LOG_FILE"
    echo ""
    echo "View logs: tail -f $LOG_FILE"
else
    echo "❌ Failed to start expanso-edge"
    echo ""
    echo "Check logs: cat $LOG_FILE"
    exit 1
fi
