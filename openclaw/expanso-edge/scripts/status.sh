#!/bin/bash
# Check expanso-edge daemon status

echo "=== Expanso Edge Status ==="
echo ""

# Check if expanso-edge process is running
if pgrep -f "expanso-edge" > /dev/null; then
    PID=$(pgrep -f "expanso-edge")
    echo "✓ expanso-edge is RUNNING"
    echo "  PID: $PID"

    # Get process info
    if [ -f "/proc/$PID/cmdline" ]; then
        echo "  Command: $(cat /proc/$PID/cmdline | tr '\0' ' ')"
    fi

    # Get uptime
    if [ -f "/proc/$PID/stat" ]; then
        START_TIME=$(awk '{print $22}' /proc/$PID/stat)
        UPTIME=$(awk '{print int($1)}' /proc/uptime)
        BOOT_TIME=$(grep btime /proc/stat | awk '{print $2}')
        SECONDS=$((UPTIME - (START_TIME / 100)))
        echo "  Uptime: ${SECONDS}s"
    fi
else
    echo "✗ expanso-edge is NOT RUNNING"
    exit 1
fi

echo ""
echo "Environment:"
echo "  Bootstrap URL: ${EXPANSO_EDGE_BOOTSTRAP_URL:-not set}"
echo "  Bootstrap Token: ${EXPANSO_EDGE_BOOTSTRAP_TOKEN:+[set]}${EXPANSO_EDGE_BOOTSTRAP_TOKEN:-not set}"
