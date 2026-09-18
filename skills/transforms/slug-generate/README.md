# slug-generate

Generate URL-safe slugs from text.

## Overview

This skill converts text to URL-safe slugs by lowercasing, replacing spaces with hyphens, and removing special characters. Runs entirely locally.

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
