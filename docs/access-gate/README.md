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

```bash
# Install Expanso Edge
curl -fsSL https://get.expanso.io/edge/install.sh | bash

# Default deny (no policy configured)
echo '{"agent":"unknown-bot","resource":"slack-read"}' | \
  expanso-edge run pipeline-cli.yaml
# → {"allowed": false, "reason": "No policy rules configured, default=deny"}

# Allow specific agent
echo '{"agent":"marketing-bot","resource":"slack-read"}' | \
  ACCESS_POLICY="marketing-bot:slack-read:read" \
  expanso-edge run pipeline-cli.yaml
# → {"allowed": true, "reason": "Matched policy rule..."}

# Wildcard rules
echo '{"agent":"any-agent","resource":"webhook-receive"}' | \
  ACCESS_POLICY="*:webhook-receive:read" \
  expanso-edge run pipeline-cli.yaml
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

```bash
# Full security chain:
# 1. Check permission
# 2. Read Slack messages
# 3. Redact PII
# 4. Filter allowed fields
# 5. Log access
echo '{"agent":"marketing-bot","resource":"slack-read","channel":"C01234567"}' | \
  ACCESS_POLICY="marketing-bot:slack-read:read" \
  expanso-edge run access-gate.yaml | \
  SLACK_BOT_TOKEN=xoxb-... expanso-edge run slack-read.yaml | \
  expanso-edge run pii-redact.yaml | \
  expanso-edge run data-fence.yaml
```
