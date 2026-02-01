# timestamp-parse

Parse and format timestamps between different formats.

## Overview

This skill parses timestamps from various formats and outputs them in multiple formats (ISO 8601, Unix, date parts). Runs entirely locally.

## Usage

### CLI Mode

```bash
# Get current time in all formats
echo "" | expanso-edge run pipeline-cli.yaml

# Parse ISO timestamp
echo "2024-01-15T10:30:00Z" | expanso-edge run pipeline-cli.yaml

# Parse date only
echo "2024-01-15" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Get current time
curl -X POST http://localhost:8080/parse \
  -H "Content-Type: application/json" \
  -d '{}'

# Parse specific timestamp
curl -X POST http://localhost:8080/parse \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2024-01-15T10:30:00Z"}'
```

## Output

```json
{
  "iso": "2024-01-15T10:30:00Z",
  "date": "2024-01-15",
  "time": "10:30:00",
  "unix": 1705315800,
  "unix_ms": 1705315800000,
  "day_of_week": "Monday",
  "metadata": {
    "skill": "timestamp-parse",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Supported Input Formats

- ISO 8601: `2024-01-15T10:30:00Z`
- Date only: `2024-01-15`
- Empty: Returns current time

## Use Cases

- Time zone conversions
- Log timestamp normalization
- API date formatting
- Data processing pipelines
