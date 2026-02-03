# html-strip

Strip HTML tags from text, leaving only plain text content.

## Overview

This skill removes all HTML tags, scripts, styles, and comments from HTML content. It also decodes common HTML entities. Runs entirely locally.

## Usage

### CLI Mode

```bash
echo "<p>Hello <b>World</b>!</p>" | expanso-edge run pipeline-cli.yaml
# Output: "Hello World!"

cat webpage.html | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &
curl -X POST http://localhost:8080/strip \
  -H "Content-Type: application/json" \
  -d '{"html": "<div><h1>Title</h1><p>Content</p></div>"}'
```

## Output

```json
{
  "text": "Title Content",
  "original_length": 42,
  "text_length": 13,
  "reduction_percent": 69,
  "metadata": {...}
}
```

## Features

- Removes script and style blocks
- Strips HTML comments
- Removes all HTML tags
- Decodes HTML entities (&amp; &lt; etc.)
- Normalizes whitespace

## Use Cases

- Web scraping text extraction
- Email content cleaning
- Document conversion
- Search indexing
