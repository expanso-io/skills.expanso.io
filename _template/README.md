# {{SKILL_NAME}}

> {{DESCRIPTION}}

## Why Expanso Edge?

This skill runs on **Expanso Edge**, which means:

- **Your API keys stay local** - `${OPENAI_API_KEY}` is resolved on your machine, never transmitted
- **Validated pipelines** - Every skill passes `expanso-cli job validate` before publication
- **Full audit trail** - Every invocation is logged with input hash and trace ID
- **Backend flexibility** - Use OpenAI, Ollama, or other backends without code changes

## Quick Start

### CLI Mode (for shell scripting)

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Run the skill
echo "Your input text here" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode (for OpenClaw integration)

```bash
# Start the skill server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Call from another process (or OpenClaw MCP)
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Your input text here"}'
```

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `PORT` | No | HTTP port for MCP mode (default: 8080) |

*Not required if using Ollama backend locally.

## Using with Ollama (Local, No API Key)

For complete privacy, use Ollama instead of OpenAI:

```bash
# Make sure Ollama is running with a model
ollama run llama3.2

# Modify the pipeline to use ollama_chat instead of openai_chat_completion
# (See pipeline-cli.yaml comments for details)
```

## Output Format

```json
{
  "result": "The processed output...",
  "metadata": {
    "skill": "{{SKILL_NAME}}",
    "mode": "cli",
    "model": "gpt-4o-mini",
    "input_hash": "a1b2c3d4...",
    "input_length": 42,
    "trace_id": "uuid-v4...",
    "timestamp": "2026-01-31T12:00:00Z"
  }
}
```

## Troubleshooting

### "OPENAI_API_KEY not set"

Make sure you've exported the environment variable:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### Validation Errors

Run the validation script to check your pipeline:

```bash
expanso-cli job validate pipeline-cli.yaml --offline
```

## Related Skills

- [text-summarize](../text-summarize/) - Summarize any text
- [json-extract](../json-extract/) - Extract structured JSON from text
- [pii-detect](../pii-detect/) - Detect PII in text

---

*Built with [Expanso Edge](https://expanso.io) - Your keys, your machine.*
