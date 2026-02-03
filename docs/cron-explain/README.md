# cron-explain

Explain cron expressions in plain English.

## Overview

This skill takes a cron expression and provides a human-readable explanation of when and how often it runs.

## Usage

### CLI Mode

```bash
export OPENAI_API_KEY=sk-...

echo "0 9 * * 1-5" | expanso-edge run pipeline-cli.yaml
echo "*/15 * * * *" | expanso-edge run pipeline-cli.yaml
echo "0 0 1 * *" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &
curl -X POST http://localhost:8080/explain \
  -H "Content-Type: application/json" \
  -d '{"cron": "0 9 * * 1-5"}'
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
