# regex-extract

Extract text matching regex patterns from input.

## Overview

This skill uses regular expressions to find and extract matching text from input. Runs entirely locally.

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
