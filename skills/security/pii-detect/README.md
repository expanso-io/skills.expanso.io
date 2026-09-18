# pii-detect

> Detect personally identifiable information (PII) in text.

Scan text for sensitive personal data before processing, logging, or sharing. Essential for:
- GDPR/CCPA compliance
- Log sanitization before storage
- Data loss prevention (DLP)
- Privacy-aware data pipelines

## Quick Start

### CLI Mode

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)). `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine.

```bash
expanso-edge validate pipeline-cli.yaml
```

### MCP Mode

```bash
expanso-edge validate pipeline-mcp.yaml
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `PII_TYPES` | No | all | Comma-separated types to detect |
| `PORT` | No | 8080 | HTTP port for MCP mode |

## PII Types

| Type | Description | Examples |
|------|-------------|----------|
| `email` | Email addresses | john@example.com |
| `phone` | Phone numbers | 555-123-4567, +1 (555) 123-4567 |
| `ssn` | Social Security Numbers | 123-45-6789 |
| `credit_card` | Credit card numbers | 4111-1111-1111-1111 |
| `name` | Person names | John Smith, Jane Doe |
| `address` | Physical addresses | 123 Main St, New York, NY |
| `dob` | Dates of birth | 01/15/1990, January 15, 1990 |
| `ip_address` | IP addresses | 192.168.1.1, 10.0.0.1 |

## Example Output

### Input
```
Customer Support Ticket #12345

From: John Smith <john.smith@example.com>
Phone: (555) 123-4567
SSN: 123-45-6789

Please update my address to 123 Main Street, Boston, MA 02101.
My date of birth is March 15, 1985.
```

### Output
```json
{
  "findings": [
    {"type": "name", "value": "John Smith", "start": 35, "end": 45, "confidence": 0.95},
    {"type": "email", "value": "john.smith@example.com", "start": 47, "end": 69, "confidence": 1.0},
    {"type": "phone", "value": "(555) 123-4567", "start": 78, "end": 92, "confidence": 1.0},
    {"type": "ssn", "value": "123-45-6789", "start": 99, "end": 110, "confidence": 1.0},
    {"type": "address", "value": "123 Main Street, Boston, MA 02101", "start": 140, "end": 173, "confidence": 0.9},
    {"type": "dob", "value": "March 15, 1985", "start": 200, "end": 214, "confidence": 0.95}
  ],
  "has_pii": true,
  "summary": "Found 6 PII items: 1 name, 1 email, 1 phone, 1 SSN, 1 address, 1 DOB",
  "metadata": {
    "skill": "pii-detect",
    "input_hash": "abc123...",
    "trace_id": "550e8400-...",
    "findings_count": 6
  }
}
```

## Use Cases

### Pre-Logging Check
```bash
expanso-edge validate pipeline-cli.yaml
```

### Compliance Scanning
```bash
expanso-edge validate pipeline-cli.yaml
```

### Pipeline Integration
```yaml
# Use in a larger Expanso pipeline
pipeline:
  processors:
    - subprocess:
        name: pii-check
        command: ["expanso-edge", "run", "skills/pii-detect/pipeline-cli.yaml"]
    - switch:
        - check: this.has_pii == true
          processors:
            - log:
                level: WARN
                message: "PII detected - routing to secure storage"
```

## Related Skills

- [pii-redact](../pii-redact/) - Redact detected PII from text
- [secrets-scan](../secrets-scan/) - Detect hardcoded secrets
- [log-sanitize](../log-sanitize/) - Sanitize logs before storage

---

*Built with [Expanso Edge](https://expanso.io).*
