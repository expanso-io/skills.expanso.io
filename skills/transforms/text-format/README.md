# text-format

Transform text case: uppercase, lowercase, title case, sentence case.

## Overview

This skill transforms text between different case formats. Runs entirely locally with no API calls.

## Usage

### CLI Mode

```bash
# Lowercase (default)
echo "HELLO WORLD" | expanso-edge run pipeline-cli.yaml

# Uppercase
FORMAT=upper echo "hello world" | expanso-edge run pipeline-cli.yaml

# Title Case
FORMAT=title echo "hello world" | expanso-edge run pipeline-cli.yaml

# Sentence case
FORMAT=sentence echo "hello world. this is a test." | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/format \
  -H "Content-Type: application/json" \
  -d '{"text": "hello world", "format": "upper"}'
```

## Format Options

| Format | Input | Output |
|--------|-------|--------|
| `lower` | "Hello World" | "hello world" |
| `upper` | "Hello World" | "HELLO WORLD" |
| `title` | "hello world" | "Hello World" |
| `sentence` | "hello world" | "Hello world" |

## Use Cases

- Text normalization
- Display formatting
- Data cleaning
- User input processing
