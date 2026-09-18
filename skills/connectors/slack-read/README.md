# slack-read

Read messages from Slack channels and DMs through Expanso Edge. Your Slack bot token stays with the edge node that runs the pipeline — AI agents get clean message data without access to your credentials. The token and your requests are still sent to the Slack API (`slack.com`), which is how the skill reads messages.

## Why Use This Instead of Direct Slack API Access?

When an AI agent connects directly to Slack, it gets your bot token. With Expanso Edge:

- **The agent never holds the token** — `SLACK_BOT_TOKEN` is read from the executing node's environment and sent only to Slack as the API credential; it is not given to the agent or sent to Expanso Cloud
- **Data isolation** — Compose with `pii-redact` to strip sensitive data before the agent sees it
- **Audit trail** — Every access is logged with trace IDs
- **Rate limiting** — Prevent agents from hammering the Slack API
- **Field filtering** — Use `data-fence` to limit which message fields the agent can see

## Quick Start

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
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
Each skill in this chain is a separate job, and `expanso-edge run` cannot pipe one pipeline into the next, so this chain has no verified run form.

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
