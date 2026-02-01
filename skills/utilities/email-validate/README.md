# email-validate

Validate email address format and extract user/domain parts.

## Overview

This skill validates email format using regex and extracts the user and domain components. Runs entirely locally.

## Usage

### CLI Mode

```bash
echo "user@example.com" | expanso-edge run pipeline-cli.yaml
echo "invalid-email" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

## Output

```json
{
  "valid": true,
  "email": "user@example.com",
  "user": "user",
  "domain": "example.com",
  "metadata": {
    "skill": "email-validate",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Use Cases

- Form validation
- Data cleaning
- User registration
- Contact list processing
