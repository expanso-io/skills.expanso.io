# cron-explain

Explain cron expressions in plain English.

## Overview

This skill takes a cron expression and provides a human-readable explanation of when and how often it runs.

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
  "explanation": "This cron job runs at 9:00 AM every weekday (Monday through Friday). It does not run on weekends.",
  "cron": "0 9 * * 1-5",
  "fields": {
    "minute": "0",
    "hour": "9",
    "day_of_month": "*",
    "month": "*",
    "day_of_week": "1-5"
  },
  "metadata": {...}
}
```

## Common Patterns

| Expression | Meaning |
|------------|---------|
| `* * * * *` | Every minute |
| `0 * * * *` | Every hour |
| `0 0 * * *` | Every day at midnight |
| `0 9 * * 1-5` | 9 AM on weekdays |
| `*/15 * * * *` | Every 15 minutes |
| `0 0 1 * *` | First of every month |

## Use Cases

- DevOps documentation
- Scheduled task debugging
- Cron job onboarding
