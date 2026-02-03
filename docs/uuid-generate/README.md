# uuid-generate

Generate UUIDs (v4) for unique identifiers.

## Overview

This skill generates cryptographically random UUIDs (version 4). Runs entirely locally with no API calls.

## Usage

### CLI Mode

```bash
# Generate 1 UUID
echo "" | expanso-edge run pipeline-cli.yaml

# Generate 5 UUIDs
COUNT=5 echo "" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Generate 1 UUID
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{}'

# Generate multiple UUIDs
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5}'
```

## Output

### Single UUID

```json
{
  "uuid": "a1b2c3d4-e5f6-4890-abcd-ef1234567890",
  "count": 1,
  "format": "v4",
  "metadata": {
    "skill": "uuid-generate",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Use Cases

- Generate unique identifiers
- Create transaction IDs
- Database record IDs
- API request tracing
