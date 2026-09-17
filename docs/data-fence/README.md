# data-fence

Filter data to only allowed fields and rows before passing to AI agents. Composable security skill that ensures agents only see the data they need. Runs entirely locally — no external API calls.

## The Problem

When an AI agent reads from Slack, Gmail, or a database, it gets everything — including fields it doesn't need (and shouldn't see). The `data-fence` skill adds a composable data filtering layer.

## How It Works

```
[connector output] → data-fence → [agent sees only allowed fields]

Before:  {"id": 1, "name": "John", "ssn": "123-45-6789", "salary": 150000}
After:   {"id": 1, "name": "John"}
```

## Quick Start

```bash
# Install Expanso Edge
curl -fsSL https://get.expanso.io/edge/install.sh | bash

# Allowlist mode — keep only these fields
echo '{"data":[{"id":1,"name":"John","ssn":"123-45-6789"}],"allowed_fields":["id","name"]}' | \
  expanso-edge run pipeline-cli.yaml

# Blocklist mode — remove these fields
echo '{"data":[{"id":1,"name":"John","ssn":"123-45-6789"}],"blocked_fields":["ssn"]}' | \
  expanso-edge run pipeline-cli.yaml

# Via environment variable
echo '{"data":[{"id":1,"name":"John","ssn":"123-45-6789"}]}' | \
  FENCE_ALLOWED_FIELDS="id,name" expanso-edge run pipeline-cli.yaml
```

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `data` | any | yes | — | Data to filter (object or array) |
| `allowed_fields` | array | no | — | Fields to keep (allowlist) |
| `blocked_fields` | array | no | — | Fields to remove (blocklist) |
| `max_rows` | integer | no | 100 | Maximum rows to return |

## Outputs

```json
{
  "data": [{"id": 1, "name": "John"}],
  "metadata": {
    "skill": "data-fence",
    "original_row_count": 50,
    "filtered_row_count": 50,
    "rows_removed": 0,
    "allowed_fields": ["id", "name"],
    "trace_id": "abc123...",
    "timestamp": "2026-02-23T..."
  }
}
```

## Environment Variables

| Name | Description |
|------|-------------|
| `FENCE_ALLOWED_FIELDS` | Comma-separated allowlist (e.g., `id,name,text`) |
| `FENCE_BLOCKED_FIELDS` | Comma-separated blocklist (e.g., `ssn,email,phone`) |
| `FENCE_MAX_ROWS` | Maximum rows to return (default: 100) |

## Composable Security Chain

```bash
# Full chain: gate → read → redact PII → fence fields → log
echo '{"agent":"marketing-bot","resource":"slack-read","channel":"C01234567"}' | \
  ACCESS_POLICY="marketing-bot:slack-read:read" \
  expanso-edge run access-gate.yaml | \
  SLACK_BOT_TOKEN=xoxb-... expanso-edge run slack-read.yaml | \
  expanso-edge run pii-redact.yaml | \
  FENCE_ALLOWED_FIELDS="id,text,timestamp" \
  expanso-edge run data-fence.yaml
```
