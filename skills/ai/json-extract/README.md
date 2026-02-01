# json-extract

> Extract structured JSON from natural language text while keeping your API keys local.

This skill demonstrates structured output extraction with Expanso + OpenClaw:

- **Your API keys stay local** - `${OPENAI_API_KEY}` is resolved on your machine
- **Flexible field extraction** - Specify exactly what fields to extract
- **Schema validation ready** - Output can be validated against JSON Schema
- **Full audit trail** - Every invocation is logged with input hash and trace ID

## Quick Start

### CLI Mode (for shell scripting)

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Extract from stdin (uses default fields)
echo "John Smith, 35 years old, lives in NYC" | \
  expanso-edge run pipeline-cli.yaml

# With custom fields
echo "Contact: jane@example.com, Phone: 555-1234" | \
  EXTRACT_FIELDS="email,phone" expanso-edge run pipeline-cli.yaml
```

### MCP Mode (for OpenClaw integration)

```bash
# Start the skill server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Call from curl (or OpenClaw MCP)
curl -X POST http://localhost:8080/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "John Smith, 35 years old, lives in NYC"}'

# With custom fields
curl -X POST http://localhost:8080/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact: jane@example.com", "fields": ["email", "phone"]}'
```

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `EXTRACT_FIELDS` | No | Comma-separated fields to extract (CLI mode) |
| `PORT` | No | HTTP port for MCP mode (default: 8080) |

*Not required if using Ollama backend locally.

## Default Fields

When no fields are specified, the skill extracts these common fields:

- `name` - Person or entity names
- `email` - Email addresses
- `phone` - Phone numbers
- `address` - Physical addresses
- `date` - Dates and times
- `amount` - Monetary amounts
- `company` - Company/organization names

## Example Output

### Input
```
Meeting with John Smith from Acme Corp on January 15th, 2026.
Contact: john.smith@acme.com, Phone: (555) 123-4567.
Budget approved: $50,000.
```

### Output
```json
{
  "extracted": {
    "name": "John Smith",
    "company": "Acme Corp",
    "date": "January 15th, 2026",
    "email": "john.smith@acme.com",
    "phone": "(555) 123-4567",
    "amount": "$50,000"
  },
  "raw_response": "{...}",
  "metadata": {
    "skill": "json-extract",
    "mode": "cli",
    "model": "gpt-4o-mini",
    "input_hash": "a1b2c3d4e5f6...",
    "input_length": 142,
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "fields_requested": "default",
    "timestamp": "2026-01-31T12:00:00Z"
  }
}
```

## Custom Field Extraction

You can request specific fields for your use case:

```bash
# Extract only contact info
echo "..." | EXTRACT_FIELDS="email,phone,address" expanso-edge run pipeline-cli.yaml

# Extract financial data
echo "..." | EXTRACT_FIELDS="amount,currency,account_number,date" expanso-edge run pipeline-cli.yaml

# Extract product info
echo "..." | EXTRACT_FIELDS="product_name,sku,price,quantity" expanso-edge run pipeline-cli.yaml
```

## Using with Ollama (Local, No API Key)

For complete privacy, you can use Ollama instead of OpenAI. Edit the pipeline to replace `openai_chat_completion` with `ollama_chat`:

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

Make sure Ollama is running:

```bash
ollama run llama3.2
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR MACHINE                                 │
│                                                                 │
│  ┌───────────────┐     ┌─────────────────┐     ┌─────────────┐  │
│  │ Unstructured  │────▶│ Expanso Edge    │────▶│ Structured  │  │
│  │ Text Input    │     │                 │     │ JSON Output │  │
│  │               │     │ ${OPENAI_API_KEY}│     │             │  │
│  └───────────────┘     │ resolved HERE   │     └─────────────┘  │
│                        └────────┬────────┘                      │
│                                 │                               │
│                        ┌────────▼────────┐                      │
│                        │ Local Vault     │                      │
│                        │ (env vars)      │                      │
│                        └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ API call with key
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OPENAI API                                   │
│                                                                 │
│  Receives: text + field list                                    │
│  Does NOT receive: who you are, where the key came from        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### "OPENAI_API_KEY not set"

Make sure you've exported the environment variable:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### "text field is required"

For MCP mode, make sure you're sending JSON with a `text` field:

```bash
curl -X POST http://localhost:8080/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text here"}'
```

### Invalid JSON Response

The LLM occasionally returns malformed JSON. The skill will return an empty `extracted` object in this case. Check `raw_response` for the actual model output.

### Validation Errors

Run the validation script:

```bash
uv run -s scripts/validate-skills.py json-extract
```

## Cost Estimate

Using OpenAI GPT-4o-mini:
- ~$0.15 per 1M input tokens
- ~$0.60 per 1M output tokens
- Typical extraction: ~$0.001 (less than a penny)

Using Ollama: **Free** (runs locally)

## Use Cases

- **Contact parsing** - Extract names, emails, phones from business cards or emails
- **Invoice processing** - Pull amounts, dates, vendor info from invoices
- **Lead enrichment** - Extract company info from LinkedIn profiles
- **Form filling** - Parse unstructured text into form fields
- **Log analysis** - Extract timestamps, error codes, IPs from logs

## Related Skills

- [text-summarize](../text-summarize/) - Summarize text into bullet points
- [pii-detect](../pii-detect/) - Detect PII in text

---

*Built with [Expanso Edge](https://expanso.io) - Your keys, your machine.*
