# url-encode

URL encode and decode text for safe URL parameters.

## Overview

This skill encodes text for safe use in URLs or decodes URL-encoded text back to plain text. Runs entirely locally with no API calls.

## Usage

### CLI Mode

```bash
# Encode text for URL
echo "Hello World! Special chars: &=?" | expanso-edge run pipeline-cli.yaml

# Decode URL-encoded text
MODE=decode echo "Hello%20World%21" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Encode
curl -X POST http://localhost:8080/encode \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello World!", "mode": "encode"}'

# Decode
curl -X POST http://localhost:8080/encode \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello%20World%21", "mode": "decode"}'
```

## Output

### Encode

```json
{
  "result": "Hello%20World%21%20Special%20chars%3A%20%26%3D%3F",
  "mode": "encode",
  "metadata": {
    "skill": "url-encode",
    "operation": "encode",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Decode

```json
{
  "result": "Hello World! Special chars: &=?",
  "mode": "decode",
  "metadata": { ... }
}
```

## Characters Encoded

| Character | Encoded |
|-----------|---------|
| Space | `%20` |
| `!` | `%21` |
| `&` | `%26` |
| `=` | `%3D` |
| `?` | `%3F` |
| `#` | `%23` |

## Use Cases

- Building safe query strings
- Processing user input for URLs
- Decoding URL parameters
- API request preparation
