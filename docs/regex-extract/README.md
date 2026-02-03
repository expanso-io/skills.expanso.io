# regex-extract

Extract text matching regex patterns from input.

## Overview

This skill uses regular expressions to find and extract matching text from input. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Extract emails
PATTERN="[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" \
  echo "Contact us at test@example.com or info@company.org" | \
  expanso-edge run pipeline-cli.yaml

# Extract numbers
PATTERN="\\d+" echo "Order #123 with 5 items for $99.99" | \
  expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact test@example.com or info@company.org",
    "pattern": "[a-z]+@[a-z]+\\.[a-z]+"
  }'
```

## Output

```json
{
  "matches": ["test@example.com", "info@company.org"],
  "count": 2,
  "has_match": true,
  "pattern": "[a-z]+@[a-z]+\\.[a-z]+",
  "metadata": {
    "skill": "regex-extract",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Common Patterns

| Pattern | Matches |
|---------|---------|
| `\\d+` | Numbers |
| `[A-Z]{2,}` | Uppercase words |
| `#\\w+` | Hashtags |
| `@\\w+` | Mentions |
| `https?://\\S+` | URLs |

## Use Cases

- Email extraction
- Phone number detection
- URL parsing
- Data mining
- Log parsing
