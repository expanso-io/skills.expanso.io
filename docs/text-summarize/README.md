# text-summarize

> Summarize any text into 3-5 bullet points using an AI model.

**Read before deploying: with the default `openai` backend this skill is not
offline and not local-only.**

- **The input text leaves the host.** The entire input is sent to the OpenAI API
  (`api.openai.com`) on every invocation, subject to OpenAI's data handling terms.
- **`OPENAI_API_KEY` leaves the host, to OpenAI.** It is read from the environment
  of the node that executes the pipeline and sent to OpenAI as the bearer
  credential. It is not sent to Expanso Cloud and is not stored in the pipeline.
- **The key must exist on the executing node.** For a Cloud-scheduled job that is
  the edge node, not the machine you deploy from.
- **Only a self-hosted model avoids this egress** (see
  [Using Ollama](#using-with-ollama-self-hosted-model)).

The authoritative, machine-readable declaration is the `dependencies` block in
[`skill.yaml`](skill.yaml).

**Readiness:** both pipelines pass local validation (`expanso-edge validate`,
v2.1.21). Neither has been confirmed by an end-to-end run on Expanso Cloud.

## Quick Start

`expanso-edge run` starts the node agent; it does not run a pipeline file.
Validate locally, then deploy to your Expanso Cloud control plane:

```bash
# Validate, no control plane needed. Run both; they disagree.
expanso-edge validate pipeline-cli.yaml pipeline-mcp.yaml
expanso-cli job validate pipeline-mcp.yaml --offline

# Deploy. Needs a saved Cloud profile and a connected edge node
# whose environment has OPENAI_API_KEY set.
expanso-cli job deploy pipeline-mcp.yaml

# Deploying only stores the job. Confirm it was scheduled and ran:
expanso-cli job describe text-summarize-mcp
expanso-cli execution list --job-id <job-id>
```

### MCP Mode (HTTP endpoint)

Once `pipeline-mcp.yaml` is running on a node, call it on that node:

```bash
curl -X POST http://<edge-node>:8080/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your long article or document text here..."}'
```

### CLI Mode (stdin)

`pipeline-cli.yaml` reads `stdin`. A Cloud-scheduled job's stdin is not connected
to your terminal, so this variant cannot receive your input once it is scheduled
onto a remote node. For a Cloud-scheduled job, use the MCP variant or change the
input to one the node can reach itself (file, `http_server`, a queue, or object
storage).

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key, set on the executing node. Sent to OpenAI. |
| `PORT` | No | HTTP port for MCP mode (default: 8080) |

*Not required if the pipeline is repointed at a self-hosted Ollama model.

## Example Output

```json
{
  "summary": "• Key insight from the text\n• Another important point\n• Action item or recommendation\n• Supporting detail\n• Conclusion or next steps",
  "metadata": {
    "skill": "text-summarize",
    "mode": "cli",
    "model": "gpt-4o-mini",
    "input_hash": "a1b2c3d4e5f6...",
    "input_length": 2847,
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-31T12:00:00Z"
  }
}
```

## Using with Ollama (Self-Hosted Model)

To keep the input text off third-party APIs, point the pipeline at a model you
host. Edit the pipeline to replace `openai_chat_completion` with `ollama_chat`:

```yaml
# In pipeline-cli.yaml, replace:
- openai_chat_completion:
    api_key: "${OPENAI_API_KEY}"
    model: gpt-4o-mini

# With:
- ollama_chat:
    server_address: "http://localhost:11434"
    model: llama3.2
```

The Ollama server must be reachable from the node that executes the pipeline;
`localhost` means that node. This variant has not been validated or run here.
Make sure Ollama is running there:

```bash
ollama run llama3.2
```

## How It Works

```
┌──────────────────────────── EDGE NODE THAT RUNS THE JOB ─────┐
│                                                              │
│  Input ──▶ Expanso Edge ──▶ Output                           │
│  (stdin    reads OPENAI_API_KEY    (stdout or HTTP response) │
│   or HTTP) from this node's env                              │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS: full input text
                               │ + OPENAI_API_KEY (bearer)
                               ▼
                    ┌─────────────────────┐
                    │ OpenAI API          │
                    │ api.openai.com      │
                    └─────────────────────┘
```

OpenAI receives the full input text, the prompt, and your API key. Expanso Cloud
receives neither the key nor the text; it schedules the job and stores the
pipeline definition.

## Troubleshooting

### "OPENAI_API_KEY not set"

The variable must be set in the environment of the node that executes the
pipeline, not only in the shell you deploy from:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### "text field is required"

For MCP mode, make sure you're sending JSON with a `text` field:

```bash
curl -X POST http://localhost:8080/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text here"}'
```

### Validation Errors

Validate the pipeline files directly, or regenerate the repository-wide report
from the repository root:

```bash
expanso-edge validate pipeline-cli.yaml pipeline-mcp.yaml
uv run -s scripts/validate-skills.py
```

## Cost Estimate

Using OpenAI GPT-4o-mini:
- ~$0.15 per 1M input tokens
- ~$0.60 per 1M output tokens
- Typical summary: ~$0.001 (less than a penny)

Using Ollama: no per-request API cost; you pay for hosting the model.

## Related Skills

- [json-extract](../json-extract/) - Extract structured JSON from text
- [pii-detect](../pii-detect/) - Detect PII in text

---

*Built with [Expanso Edge](https://expanso.io).*
