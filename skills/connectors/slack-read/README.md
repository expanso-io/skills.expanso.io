# slack-read

Read messages from Slack channels and DMs through Expanso Edge. Your Slack bot token stays on your machine — AI agents get clean message data without access to your credentials.

## Why Use This Instead of Direct Slack API Access?

When an AI agent connects directly to Slack, it gets your bot token. With Expanso Edge:

- **Credentials stay local** — Your `SLACK_BOT_TOKEN` never leaves your machine
- **Data isolation** — Compose with `pii-redact` to strip sensitive data before the agent sees it
- **Audit trail** — Every access is logged with trace IDs
- **Rate limiting** — Prevent agents from hammering the Slack API
- **Field filtering** — Use `data-fence` to limit which message fields the agent can see

## Quick Start

```bash
# Install Expanso Edge
curl -fsSL https://get.expanso.io/edge/install.sh | bash

# Read messages from a channel
echo '{"channel":"C01234567"}' | \
  SLACK_BOT_TOKEN=xoxb-your-token expanso-edge run pipeline-cli.yaml
```

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `channel` | string | yes | — | Slack channel ID (e.g., C01234567) |
| `limit` | integer | no | 20 | Max messages to retrieve (1-100) |
| `query` | string | no | — | Filter messages containing this text |
| `since_hours` | integer | no | 24 | Retrieve messages from last N hours |

## Outputs

```json
{
  "messages": [
    {
      "id": "1234567890.123456",
      "user": "U01234567",
      "text": "The deploy finished successfully",
      "timestamp": "1234567890.123456",
      "thread_ts": null,
      "reactions": [{"name": "white_check_mark", "count": 2}]
    }
  ],
  "metadata": {
    "skill": "slack-read",
    "channel": "C01234567",
    "trace_id": "abc123...",
    "message_count": 15,
    "timestamp": "2026-02-23T..."
  }
}
```

## Composable Security

Chain with security skills for safe agent access:

```
access-gate → slack-read → pii-redact → data-fence → audit-log
```

Example pipeline composition:
```bash
# Agent requests Slack messages → gate checks permission →
# read messages → redact PII → filter to allowed fields → log access
echo '{"channel":"C01234567","agent":"marketing-bot"}' | \
  expanso-edge run access-gate.yaml | \
  expanso-edge run pipeline-cli.yaml | \
  expanso-edge run pii-redact.yaml | \
  expanso-edge run data-fence.yaml
```

## Credentials

| Name | Required | Description |
|------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack Bot User OAuth Token (`xoxb-...`) |
| `SLACK_CHANNEL_ID` | No | Default channel ID |
| `SLACK_API_URL` | No | Override API URL (for testing or Slack Enterprise Grid) |

### Getting a Slack Bot Token

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under **OAuth & Permissions**, add the `channels:history` scope
3. Install the app to your workspace
4. Copy the **Bot User OAuth Token** (`xoxb-...`)

## Framework Compatibility

| Framework | Integration |
|-----------|------------|
| **OpenClaw** | Available as an Expanso skill in the marketplace |
| **LangChain** | Use as a LangChain Tool via MCP endpoint |
| **CrewAI** | Use as a CrewAI Tool via MCP endpoint |
| **Claude MCP** | Direct MCP server integration |
| **OpenAI Agents** | Function calling via MCP endpoint |
