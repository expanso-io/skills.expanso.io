#!/bin/bash
# View expanso-edge logs

echo "=== Expanso Edge Logs ==="
echo ""

# Check if running
if ! pgrep -f "expanso-edge" > /dev/null; then
    echo "✗ expanso-edge is not running"
    exit 1
fi

# Try to find log files in common locations
LOG_LOCATIONS=(
    "/var/log/expanso-edge.log"
    "/tmp/expanso-edge.log"
    "$HOME/.expanso/edge.log"
    "/root/.expanso/edge.log"
)

FOUND_LOG=false
for LOG in "${LOG_LOCATIONS[@]}"; do
    if [ -f "$LOG" ]; then
        echo "Found log: $LOG"
        echo "---"
        tail -n 50 "$LOG"
        FOUND_LOG=true
        break
    fi
done

if [ "$FOUND_LOG" = false ]; then
    echo "No log files found in common locations"
    echo "Process is running but logs not captured"
    echo ""
    echo "Tip: Restart the worker to capture logs properly"
fi
