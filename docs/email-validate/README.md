# email-validate

Validate email address format and extract user/domain parts.

## Overview

This skill validates email format using regex and extracts the user and domain components. Runs entirely locally.

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
  "valid": true,
  "email": "user@example.com",
  "user": "user",
  "domain": "example.com",
  "metadata": {
    "skill": "email-validate",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Use Cases

- Form validation
- Data cleaning
- User registration
- Contact list processing
