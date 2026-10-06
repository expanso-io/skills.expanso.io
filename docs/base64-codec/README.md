# base64-codec

Encode and decode Base64 content locally.

## Overview

This skill encodes text to Base64 or decodes Base64 back to text. Runs entirely locally with no API calls.

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
  "result": "SGVsbG8gV29ybGQ=",
  "mode": "encode",
  "metadata": {
    "skill": "base64-codec",
    "operation": "encode",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Decode

```json
{
  "result": "Hello World",
  "mode": "decode",
  "metadata": { ... }
}
```

## Use Cases

- Encoding credentials for config files
- Decoding JWT payload sections
- Processing base64-encoded images
- API request/response handling
