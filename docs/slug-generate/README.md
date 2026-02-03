# slug-generate

Generate URL-safe slugs from text.

## Overview

This skill converts text to URL-safe slugs by lowercasing, replacing spaces with hyphens, and removing special characters. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Generate slug
echo "Hello World! This is a Test" | expanso-edge run pipeline-cli.yaml
# Output: hello-world-this-is-a-test

# Custom separator
SEPARATOR=_ echo "Hello World" | expanso-edge run pipeline-cli.yaml
# Output: hello_world
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/slugify \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello World! This is a Test"}'
```

## Output

```json
{
  "slug": "hello-world-this-is-a-test",
  "original": "Hello World! This is a Test",
  "separator": "-",
  "metadata": {
    "skill": "slug-generate",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Examples

| Input | Output |
|-------|--------|
| "Hello World!" | "hello-world" |
| "My Blog Post #1" | "my-blog-post-1" |
| "  Spaces  Everywhere  " | "spaces-everywhere" |
| "Café & Restaurant" | "caf-restaurant" |

## Use Cases

- URL path generation
- File naming
- Database keys
- SEO-friendly URLs
