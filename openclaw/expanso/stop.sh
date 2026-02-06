#!/usr/bin/env bash
set -euo pipefail

PID_FILE="$HOME/.expanso/expanso-edge.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "⚠️  No PID file found - expanso-edge may not be running"
    
    # Try to find it anyway
    PID=$(pgrep -f "expanso-edge run" || true)
    if [[ -n "$PID" ]]; then
        echo "   Found running process: $PID"
        echo -n "   Stop it? [y/N] "
        read -r confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            kill "$PID"
            echo "✅ expanso-edge stopped"
        fi
    else
        echo "   No running expanso-edge process found"
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "🛑 Stopping expanso-edge (PID: $PID)..."
    kill "$PID"
    
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "   Forcing shutdown..."
        kill -9 "$PID" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    echo "✅ expanso-edge stopped"
else
    echo "⚠️  Process $PID not running (stale PID file)"
    rm -f "$PID_FILE"
fi
