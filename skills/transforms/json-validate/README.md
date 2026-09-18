# json-validate

Validate JSON syntax and structure with detailed error reporting.

## Overview

This skill validates JSON content locally without any API calls. It parses the JSON and returns whether it's valid, any error messages, and statistics about the structure.

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

### Valid JSON

```json
{
  "valid": true,
  "error": null,
  "parsed": {
    "key": "value",
    "array": [1, 2, 3]
  },
  "stats": {
    "type": "object",
    "length": 35
  },
  "metadata": {
    "skill": "json-validate",
    "mode": "cli",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Invalid JSON

```json
{
  "valid": false,
  "error": "Invalid JSON syntax",
  "parsed": null,
  "stats": null,
  "metadata": { ... }
}
```

## Use Cases

- Validating API responses
- Pre-commit hooks for JSON files
- CI/CD pipeline validation
- Data ingestion validation
