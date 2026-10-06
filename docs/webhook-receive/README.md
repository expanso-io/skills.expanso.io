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

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-mcp.yaml
expanso-edge validate pipeline-cli.yaml
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
