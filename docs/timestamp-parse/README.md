# timestamp-parse

Parse and format timestamps between different formats.

## Overview

This skill parses timestamps from various formats and outputs them in multiple formats (ISO 8601, Unix, date parts). Runs entirely locally.

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
  "iso": "2024-01-15T10:30:00Z",
  "date": "2024-01-15",
  "time": "10:30:00",
  "unix": 1705315800,
  "unix_ms": 1705315800000,
  "day_of_week": "Monday",
  "metadata": {
    "skill": "timestamp-parse",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Supported Input Formats

- ISO 8601: `2024-01-15T10:30:00Z`
- Date only: `2024-01-15`
- Empty: Returns current time

## Use Cases

- Time zone conversions
- Log timestamp normalization
- API date formatting
- Data processing pipelines
