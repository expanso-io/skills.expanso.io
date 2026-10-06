# gmail-read

Read message metadata and snippets from Gmail through Expanso Edge. Your OAuth tokens stay with the edge node that runs the pipeline — AI agents get clean email data without access to your credentials. The tokens and your requests are still sent to the Gmail API (Google), which is how the skill reads mail.

## Why Use This Instead of Direct Gmail API Access?

When an AI agent connects directly to Gmail, it gets your OAuth token — and with it, full access to your inbox. With Expanso Edge:

- **The agent never holds the token** — `GMAIL_ACCESS_TOKEN` is read from the executing node's environment and sent only to Google as the API credential; it is not given to the agent or sent to Expanso Cloud
- **Data isolation** — Compose with `pii-redact` to strip personal info before the agent sees it
- **Scoped access** — Use `data-fence` to limit which email fields the agent can read
- **Audit trail** — Every access is logged with trace IDs
- **Query filtering** — Same Gmail search syntax you already know

## Quick Start

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
```

## Inputs and outputs

See [skill.yaml](skill.yaml) for declared inputs and credentials. The final
mapping in [pipeline-cli.yaml](pipeline-cli.yaml) and
[pipeline-mcp.yaml](pipeline-mcp.yaml) defines the response envelope.

## Composable Security

Chain with security skills for safe agent access:

```
access-gate → gmail-read → pii-redact → data-fence → audit-log
```

## Credentials

Credential requirements are declared in [skill.yaml](skill.yaml). Credentials
resolve on the executing node; see
[the credential contract](../../../README.md#what-are-expanso-skills).

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
