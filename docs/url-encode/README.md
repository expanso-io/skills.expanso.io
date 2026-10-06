# url-encode

URL encode and decode text for safe URL parameters.

## Overview

This skill encodes text for safe use in URLs or decodes URL-encoded text back to plain text. Runs entirely locally with no API calls.

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

### Encode

```json
{
  "result": "Hello%20World%21%20Special%20chars%3A%20%26%3D%3F",
  "mode": "encode",
  "metadata": {
    "skill": "url-encode",
    "operation": "encode",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Decode

```json
{
  "result": "Hello World! Special chars: &=?",
  "mode": "decode",
  "metadata": { ... }
}
```

## Characters Encoded

| Character | Encoded |
|-----------|---------|
| Space | `%20` |
| `!` | `%21` |
| `&` | `%26` |
| `=` | `%3D` |
| `?` | `%3F` |
| `#` | `%23` |

## Use Cases

- Building safe query strings
- Processing user input for URLs
- Decoding URL parameters
- API request preparation
