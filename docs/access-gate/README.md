# access-gate

Permission check gateway for AI agent access to connectors and data sources. Chain before any connector skill to enforce access control. Runs entirely locally — no external API calls.

## The Problem

When AI agents have direct access to your connectors (Slack, Gmail, databases), there's no access control. Any agent can read any channel, any inbox, any table. The `access-gate` skill adds a composable permission layer.

## How It Works

```
Agent Request → access-gate → [connector] → data-fence → audit-log
                    ↓
              Check policy:
              - Is this agent allowed?
              - Can it access this resource?
              - Is this action permitted?
                    ↓
              ALLOW → pass through to connector
              DENY  → block with reason
```

## Quick Start

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
```

## Policy Format

Set via the `ACCESS_POLICY` environment variable:

```bash
# Single rule: agent:resource:action
ACCESS_POLICY="marketing-bot:slack-read:read"

# Multiple rules (comma-separated)
ACCESS_POLICY="marketing-bot:slack-read:read,data-analyst:postgres-query:read,*:webhook-receive:*"

# Default policy (when no rules match)
ACCESS_DEFAULT="deny"  # or "allow"
```

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `agent` | string | yes | — | Agent or user identifier |
| `resource` | string | yes | — | Resource being accessed |
| `action` | string | no | `read` | Action: read, write, delete |

## Outputs

```json
{
  "allowed": true,
  "reason": "Matched policy rule for agent=marketing-bot resource=slack-read",
  "agent": "marketing-bot",
  "resource": "slack-read",
  "action": "read",
  "passthrough": {"channel": "C01234567"},
  "metadata": {
    "skill": "access-gate",
    "trace_id": "abc123...",
    "timestamp": "2026-02-23T..."
  }
}
```

## Composable Security Chain

Each skill in this chain is a separate job, and `expanso-edge run` cannot pipe one pipeline into the next, so this chain has no verified run form.
