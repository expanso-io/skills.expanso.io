# yaml-validate

Validate YAML syntax and structure with detailed error reporting.

## Overview

This skill validates YAML content locally without any API calls. It parses the YAML and returns whether it's valid, any error messages, and the parsed structure as JSON.

## Usage

### CLI Mode

```bash
# Validate YAML string
echo "key: value" | expanso-edge run pipeline-cli.yaml

# Validate YAML file
cat config.yaml | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"yaml": "key: value\nlist:\n  - item1\n  - item2"}'
```

## Output

### Valid YAML

```json
{
  "valid": true,
  "error": null,
  "parsed": {
    "key": "value",
    "list": ["item1", "item2"]
  },
  "metadata": {
    "skill": "yaml-validate",
    "mode": "cli",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Invalid YAML

```json
{
  "valid": false,
  "error": "Invalid YAML syntax",
  "parsed": null,
  "metadata": { ... }
}
```

## Use Cases

- Validating configuration files before deployment
- CI/CD pipeline validation steps
- Pre-commit hooks for YAML files
- API input validation
