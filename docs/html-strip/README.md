# html-strip

Strip HTML tags from text, leaving only plain text content.

## Overview

This skill removes all HTML tags, scripts, styles, and comments from HTML content. It also decodes common HTML entities. Runs entirely locally.

## Usage

### CLI Mode

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)). `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine.

```bash
expanso-edge validate pipeline-cli.yaml
```

### MCP Mode

```bash
expanso-edge validate pipeline-mcp.yaml
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
