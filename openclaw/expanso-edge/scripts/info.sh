#!/bin/bash
# Get expanso-edge information

echo "=== Expanso Edge Information ==="
echo ""

# Check version
if command -v expanso-edge &> /dev/null; then
    echo "Version:"
    expanso-edge --version 2>&1 || echo "  (version command not available)"
    echo ""
fi

# Show configuration
echo "Configuration:"
echo "  Bootstrap URL: $EXPANSO_EDGE_BOOTSTRAP_URL"
echo "  Token Status: ${EXPANSO_EDGE_BOOTSTRAP_TOKEN:+Configured}${EXPANSO_EDGE_BOOTSTRAP_TOKEN:-Not configured}"
echo ""

# Check process status
if pgrep -f "expanso-edge" > /dev/null; then
    PID=$(pgrep -f "expanso-edge")
    echo "Process Status:"
    echo "  PID: $PID"
    echo "  Memory: $(ps -p $PID -o rss= | awk '{printf "%.2f MB\n", $1/1024}')"
    echo "  CPU: $(ps -p $PID -o %cpu=)%"
else
    echo "Process Status: Not running"
fi

echo ""
echo "Container Info:"
echo "  Hostname: $(hostname)"
echo "  Container IP: $(hostname -i 2>/dev/null || echo 'N/A')"
