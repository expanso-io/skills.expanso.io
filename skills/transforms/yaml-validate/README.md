# yaml-validate

Validate YAML syntax and structure with detailed error reporting.

## Overview

This skill validates YAML content locally without any API calls. It parses the YAML and returns whether it's valid, any error messages, and the parsed structure as JSON.

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

### Valid YAML

```json
{
  "valid": true,
  "error": null,
  "parsed": {
    "key": "value",
    "list": ["item1", "item2"]
  },
  "metadata": {
    "skill": "yaml-validate",
    "mode": "cli",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Invalid YAML

```json
{
  "valid": false,
  "error": "Invalid YAML syntax",
  "parsed": null,
  "metadata": { ... }
}
```

## Use Cases

- Validating configuration files before deployment
- CI/CD pipeline validation steps
- Pre-commit hooks for YAML files
- API input validation
