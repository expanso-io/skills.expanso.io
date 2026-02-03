# markdown-format

Format text as Markdown elements (headings, lists, code blocks, links).

## Overview

This skill wraps text in various Markdown formatting elements. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Create heading
FORMAT=heading LEVEL=2 echo "My Section" | expanso-edge run pipeline-cli.yaml
# Output: ## My Section

# Create code block
FORMAT=code LANG=python echo "print('hello')" | expanso-edge run pipeline-cli.yaml
# Output: ```python\nprint('hello')\n```

# Create list
FORMAT=list echo -e "Item 1\nItem 2\nItem 3" | expanso-edge run pipeline-cli.yaml
# Output: - Item 1\n- Item 2\n- Item 3

# Create link
FORMAT=link URL="https://example.com" echo "Click here" | expanso-edge run pipeline-cli.yaml
# Output: [Click here](https://example.com)
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Create formatted Markdown
curl -X POST http://localhost:8080/format \
  -H "Content-Type: application/json" \
  -d '{"text": "My Title", "format": "heading", "level": 2}'
```

## Format Options

| Format | Input | Output |
|--------|-------|--------|
| `heading` | "Title" (level=2) | `## Title` |
| `h1`, `h2`, `h3` | "Title" | `# Title`, etc. |
| `bold` | "text" | `**text**` |
| `italic` | "text" | `_text_` |
| `code` | "code" (lang=py) | ````python\ncode\n```` |
| `inline-code` | "var" | `` `var` `` |
| `quote` | "text" | `> text` |
| `list` | "a\nb\nc" | `- a\n- b\n- c` |
| `numbered` | "a\nb\nc" | `1. a\n2. b\n3. c` |
| `link` | "text" (url=...) | `[text](url)` |

## Use Cases

- Document generation
- README formatting
- Note taking
- Content management
