# base64-codec

Encode and decode Base64 content locally.

## Overview

This skill encodes text to Base64 or decodes Base64 back to text. Runs entirely locally with no API calls.

## Usage

### CLI Mode

```bash
# Encode text to Base64
echo "Hello World" | expanso-edge run pipeline-cli.yaml

# Decode Base64 to text
MODE=decode echo "SGVsbG8gV29ybGQ=" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Encode
curl -X POST http://localhost:8080/codec \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello World", "mode": "encode"}'

# Decode
curl -X POST http://localhost:8080/codec \
  -H "Content-Type: application/json" \
  -d '{"text": "SGVsbG8gV29ybGQ=", "mode": "decode"}'
```

## Output

### Encode

```json
{
  "result": "SGVsbG8gV29ybGQ=",
  "mode": "encode",
  "metadata": {
    "skill": "base64-codec",
    "operation": "encode",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Decode

```json
{
  "result": "Hello World",
  "mode": "decode",
  "metadata": { ... }
}
```

## Use Cases

- Encoding credentials for config files
- Decoding JWT payload sections
- Processing base64-encoded images
- API request/response handling
