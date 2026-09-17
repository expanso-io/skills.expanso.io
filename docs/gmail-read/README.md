# gmail-read

Read emails from Gmail through Expanso Edge. Your OAuth tokens stay on your machine — AI agents get clean email data without access to your credentials.

## Why Use This Instead of Direct Gmail API Access?

When an AI agent connects directly to Gmail, it gets your OAuth token — and with it, full access to your inbox. With Expanso Edge:

- **Credentials stay local** — Your `GMAIL_ACCESS_TOKEN` never leaves your machine
- **Data isolation** — Compose with `pii-redact` to strip personal info before the agent sees it
- **Scoped access** — Use `data-fence` to limit which email fields the agent can read
- **Audit trail** — Every access is logged with trace IDs
- **Query filtering** — Same Gmail search syntax you already know

## Quick Start

```bash
# Install Expanso Edge
curl -fsSL https://get.expanso.io/edge/install.sh | bash

# Read unread emails
echo '{"query":"is:unread","limit":10}' | \
  GMAIL_ACCESS_TOKEN=ya29... expanso-edge run pipeline-cli.yaml

# Search for specific emails
echo '{"query":"from:boss@company.com subject:Q1 review"}' | \
  GMAIL_ACCESS_TOKEN=ya29... expanso-edge run pipeline-cli.yaml
```

## Inputs

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | no | `is:unread` | Gmail search query (same syntax as Gmail search bar) |
| `label` | string | no | `INBOX` | Gmail label to read from |
| `limit` | integer | no | 20 | Max emails to retrieve (1-100) |
| `include_body` | boolean | no | true | Include email body content |

## Outputs

```json
{
  "emails": [
    {
      "id": "18d1234abcd",
      "fetch_url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/18d1234abcd"
    }
  ],
  "metadata": {
    "skill": "gmail-read",
    "query": "is:unread",
    "trace_id": "abc123...",
    "email_count": 10,
    "timestamp": "2026-02-23T..."
  }
}
```

## Composable Security

Chain with security skills for safe agent access:

```
access-gate → gmail-read → pii-redact → data-fence → audit-log
```

## Credentials

| Name | Required | Description |
|------|----------|-------------|
| `GMAIL_ACCESS_TOKEN` | Yes | Gmail OAuth2 access token |
| `GMAIL_REFRESH_TOKEN` | No | For automatic token refresh |
| `GMAIL_CLIENT_ID` | No | OAuth2 client ID |
| `GMAIL_CLIENT_SECRET` | No | OAuth2 client secret |
| `GMAIL_API_URL` | No | Override API URL (for testing) |

### Getting a Gmail Access Token

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the Gmail API
3. Create OAuth2 credentials (Desktop app type)
4. Use the OAuth2 flow to get an access token with `gmail.readonly` scope

## Framework Compatibility

| Framework | Integration |
|-----------|------------|
| **OpenClaw** | Available as an Expanso skill in the marketplace |
| **LangChain** | Use as a LangChain Tool via MCP endpoint |
| **CrewAI** | Use as a CrewAI Tool via MCP endpoint |
| **Claude MCP** | Direct MCP server integration |
| **OpenAI Agents** | Function calling via MCP endpoint |
