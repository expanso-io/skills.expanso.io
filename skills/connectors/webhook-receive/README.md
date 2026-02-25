# webhook-receive

Receive and process webhook events from any service through Expanso Edge. Universal connector that works with GitHub, Stripe, Slack, Jira, and any service that sends webhooks.

## Why Use This Instead of Direct Webhook Endpoints?

When an AI agent receives webhooks directly, it gets raw event data including potentially sensitive information. With Expanso Edge:

- **Data isolation** — Webhook payloads are processed locally before reaching the agent
- **Signature verification** — Validate HMAC signatures to prevent spoofing
- **Composable security** — Chain with `pii-redact`, `data-fence`, and `audit-log`
- **No cloud dependency** — Webhooks arrive at your edge node, not a third-party server
- **Replay support** — CLI mode lets you replay and test webhook payloads

## Quick Start

```bash
# Install Expanso Edge
curl -fsSL https://get.expanso.io/edge/install.sh | bash

# Start webhook listener (MCP mode)
expanso-edge run pipeline-mcp.yaml
# Webhooks arrive at http://localhost:4195/webhook

# Test with a sample payload (CLI mode)
echo '{"action":"opened","pull_request":{"title":"Add feature"}}' | \
  expanso-edge run pipeline-cli.yaml
```

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | no | `/webhook` | HTTP path to listen on (MCP mode) |
| `verify_signature` | boolean | no | false | Verify HMAC signature |
| `signature_header` | string | no | `X-Hub-Signature-256` | Header containing signature |

## Outputs

```json
{
  "event": {
    "type": "push",
    "body": {"ref": "refs/heads/main", "commits": [...]},
    "received_at": "2026-02-23T..."
  },
  "metadata": {
    "skill": "webhook-receive",
    "event_type": "push",
    "trace_id": "abc123...",
    "timestamp": "2026-02-23T..."
  }
}
```

## Composable Security

Chain with security skills for safe webhook processing:

```
webhook-receive → sign-envelope → policy-check → data-fence → audit-log
```

## Supported Webhook Sources

| Service | Event Header | Example Events |
|---------|-------------|----------------|
| **GitHub** | `X-GitHub-Event` | push, pull_request, issues |
| **Stripe** | `X-Stripe-Event` | invoice.paid, charge.failed |
| **Slack** | `X-Slack-Signature` | message, reaction_added |
| **Jira** | `X-Atlassian-Webhook` | issue_created, sprint_started |
| **Generic** | `X-Event-Type` | Any custom webhook |

## Credentials

| Name | Required | Description |
|------|----------|-------------|
| `WEBHOOK_SECRET` | No | Shared secret for HMAC signature verification |
| `WEBHOOK_ALLOWED_IPS` | No | Comma-separated allowed source IPs |
| `WEBHOOK_SIGNATURE_HEADER` | No | Override signature header name |

## Framework Compatibility

| Framework | Integration |
|-----------|------------|
| **OpenClaw** | Available as an Expanso skill in the marketplace |
| **LangChain** | Use as a LangChain Tool via MCP endpoint |
| **CrewAI** | Use as a CrewAI Tool via MCP endpoint |
| **Claude MCP** | Direct MCP server integration |
| **OpenAI Agents** | Function calling via MCP endpoint |
