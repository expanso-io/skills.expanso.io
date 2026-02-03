# text-truncate

Truncate text to specified length with optional suffix.

## Overview

This skill truncates text to a maximum length, optionally appending a suffix (like "...") when text is cut. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Truncate to 100 chars (default)
echo "This is a long text..." | expanso-edge run pipeline-cli.yaml

# Truncate to 20 chars
LENGTH=20 echo "This is a very long text that will be truncated" | \
  expanso-edge run pipeline-cli.yaml

# Custom suffix
LENGTH=20 SUFFIX="[more]" echo "This is a very long text" | \
  expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/truncate \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a very long text", "length": 15, "suffix": "..."}'
```

## Output

```json
{
  "result": "This is a v...",
  "truncated": true,
  "original_length": 24,
  "final_length": 15,
  "metadata": {
    "skill": "text-truncate",
    "max_length": 15,
    "suffix": "...",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Use Cases

- Preview text generation
- Tweet/post character limits
- Database field constraints
- UI display truncation
