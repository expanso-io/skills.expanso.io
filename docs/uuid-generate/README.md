# uuid-generate

Generate UUIDs (v4) for unique identifiers.

## Overview

This skill generates cryptographically random UUIDs (version 4). Runs entirely locally with no API calls.

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

### Single UUID

```json
{
  "uuid": "a1b2c3d4-e5f6-4890-abcd-ef1234567890",
  "count": 1,
  "format": "v4",
  "metadata": {
    "skill": "uuid-generate",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Use Cases

- Generate unique identifiers
- Create transaction IDs
- Database record IDs
- API request tracing
