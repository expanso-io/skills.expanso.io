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

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
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

Each skill in this chain is a separate job, and `expanso-edge run` cannot pipe one pipeline into the next, so this chain has no verified run form.
