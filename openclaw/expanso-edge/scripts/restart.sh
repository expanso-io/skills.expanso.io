#!/bin/bash
# Restart expanso-edge daemon

echo "=== Restarting Expanso Edge ==="
echo ""

# Check if already running
if pgrep -f "expanso-edge" > /dev/null; then
    OLD_PID=$(pgrep -f "expanso-edge")
    echo "Stopping existing process (PID: $OLD_PID)..."
    kill $OLD_PID
    sleep 2

    # Force kill if still running
    if pgrep -f "expanso-edge" > /dev/null; then
        echo "Force killing..."
        kill -9 $OLD_PID
        sleep 1
    fi
fi

# Start expanso-edge
if [ -z "$EXPANSO_EDGE_BOOTSTRAP_TOKEN" ]; then
    echo "✗ ERROR: EXPANSO_EDGE_BOOTSTRAP_TOKEN not set"
    exit 1
fi

echo "Starting expanso-edge..."
export EXPANSO_EDGE_BOOTSTRAP_TOKEN
export EXPANSO_EDGE_BOOTSTRAP_URL

expanso-edge &
NEW_PID=$!

sleep 2

# Verify it started
if pgrep -f "expanso-edge" > /dev/null; then
    echo "✓ expanso-edge restarted successfully (PID: $NEW_PID)"
else
    echo "✗ Failed to start expanso-edge"
    exit 1
fi
