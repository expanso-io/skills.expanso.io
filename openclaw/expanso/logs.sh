#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${EXPANSO_LOG_DIR:-$HOME/.expanso/logs}"
LOG_FILE="$LOG_DIR/expanso-edge.log"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "⚠️  No log file found at $LOG_FILE"
    echo "   Has expanso-edge been started?"
    exit 1
fi

# Parse arguments
FOLLOW=false
LINES=50

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        *)
            LINES="$1"
            shift
            ;;
    esac
done

if [[ "$FOLLOW" == "true" ]]; then
    echo "📋 Following $LOG_FILE (Ctrl+C to stop)"
    echo "───────────────────────────────────────"
    tail -f "$LOG_FILE"
else
    echo "📋 Last $LINES lines from $LOG_FILE"
    echo "───────────────────────────────────────"
    tail -n "$LINES" "$LOG_FILE"
fi
