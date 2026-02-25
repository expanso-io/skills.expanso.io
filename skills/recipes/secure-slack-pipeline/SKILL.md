# Secure Slack Pipeline

A complete security-composed Slack reader pipeline demonstrating all Expanso Edge security stages in a single pipeline.

## Architecture

```
Request → Auth Verify → Input Validate → Access Gate → Slack API →
          Error Check → PII Redact → Data Fence → Envelope → Audit Log
```

All stages run **inside a single Expanso pipeline** — no shell piping, no external orchestration.

## Security Stages

| Stage | What It Does |
|-------|-------------|
| **Auth Verify** | Validates API key, derives agent identity from credential |
| **Input Validate** | Rejects malformed channel IDs, caps limit range |
| **Access Gate** | Deny-by-default permission check against ACCESS_POLICY |
| **Error Check** | Verifies Slack API returned ok: true |
| **PII Redact** | Strips emails, phone numbers, SSNs from message text |
| **Data Fence** | Limits fields to id, text, timestamp only |
| **Canonical Envelope** | Standard output shape (source, resource, schema_version, data) |
| **Audit Log** | Structured log of agent, resource, count, trace_id |

## Usage

```bash
# Set up credentials and policy
export SLACK_BOT_TOKEN=xoxb-...
export EXPANSO_API_KEYS="key123:marketing-bot,key456:data-analyst"
export ACCESS_POLICY="marketing-bot:slack-read:read,data-analyst:slack-read:read"

# Start the pipeline
expanso-edge run pipeline.yaml

# Call it (from your agent or curl)
curl -X POST http://localhost:4195/secure-slack-read \
  -H "X-Expanso-Api-Key: key123" \
  -H "Content-Type: application/json" \
  -d '{"channel":"C01234567","limit":10}'
```

## Output

```json
{
  "source": "slack",
  "resource": "conversations.history",
  "schema_version": "1.0",
  "trace_id": "abc123...",
  "agent": "marketing-bot",
  "data": [
    {"id": "1234.5678", "text": "Meeting with [EMAIL] at 3pm", "timestamp": "1234.5678"}
  ],
  "count": 1,
  "sensitivity": "redacted"
}
```

Note: PII has been redacted (email replaced with `[EMAIL]`), and only allowed fields (id, text, timestamp) are exposed.

## Why This Matters

Traditional integrations give AI agents raw credentials and unrestricted data access. This pipeline ensures:

- **Agent identity is verified** — not trusted from the payload
- **Permissions are enforced** — deny-by-default, explicit policy required
- **Sensitive data is stripped** — before the agent ever sees it
- **Every access is logged** — with agent identity and trace ID
- **Credentials stay local** — SLACK_BOT_TOKEN never leaves the edge node
