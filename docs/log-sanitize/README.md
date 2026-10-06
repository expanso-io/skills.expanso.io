# log-sanitize

Sanitize log entries by removing sensitive data patterns like passwords, tokens, and API keys.

## Overview

This skill runs **entirely locally** without any API calls. It uses pattern matching to detect and redact common secret patterns in log files.

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
  "sanitized": "user=admin password=***REDACTED*** token=***REDACTED***",
  "redactions": 27,
  "metadata": {
    "skill": "log-sanitize",
    "mode": "cli",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Patterns Detected

| Pattern | Example | Replacement |
|---------|---------|-------------|
| Passwords | `password=secret` | `password=***REDACTED***` |
| API Keys | `api_key=sk-123` | `api_key=***REDACTED***` |
| Tokens | `token=abc123` | `token=***REDACTED***` |
| Bearer Auth | `Bearer eyJ...` | `Bearer ***REDACTED***` |
| AWS Keys | `AKIAIOSFODNN7` | `***AWS_KEY_REDACTED***` |
| JWT Tokens | `eyJ...eyJ...` | `***JWT_REDACTED***` |
| Secrets | `secret=xyz` | `secret=***REDACTED***` |

## Use Cases

- Pre-processing logs before sending to log aggregators
- Sanitizing logs before sharing with support
- Compliance with security policies
- Preparing logs for public documentation
