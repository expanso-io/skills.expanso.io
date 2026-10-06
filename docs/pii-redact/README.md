# pii-redact

Redact personally identifiable information (PII) from text, replacing it with configurable placeholders.

## Overview

This skill uses AI to detect and redact PII from text. Unlike `pii-detect` which only identifies PII, this skill **transforms** the text by replacing sensitive information with placeholders.

## Usage

### CLI Mode

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)). `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine.

```bash
expanso-edge validate pipeline-cli.yaml
```

### MCP Mode

```bash
expanso-edge validate pipeline-mcp.yaml
```

## Output

```json
{
  "redacted_text": "Contact [REDACTED] at [REDACTED] or [REDACTED]",
  "redaction_count": 3,
  "redacted_types": ["name", "email", "phone"],
  "metadata": {
    "skill": "pii-redact",
    "mode": "cli",
    "model": "gpt-4o-mini",
    "placeholder": "[REDACTED]",
    "trace_id": "abc123...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## PII Types Detected

- Names (first, last, full)
- Email addresses
- Phone numbers
- Social Security Numbers
- Street addresses
- Credit card numbers
- IP addresses
- Dates of birth
- Government IDs

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PLACEHOLDER` | `[REDACTED]` | Text to replace PII with |
| `OPENAI_API_KEY` | - | Required for OpenAI backend |

## Use Cases

- Log sanitization before storage
- Data anonymization for analytics
- Compliance with GDPR/CCPA
- Preparing data for public sharing
