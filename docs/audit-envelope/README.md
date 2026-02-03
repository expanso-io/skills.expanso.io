# audit-envelope

Wrap any data with audit metadata for compliance, traceability, and tamper detection.

## Overview

This skill creates a cryptographically signed audit envelope around any data. The envelope includes timestamps, trace IDs, actor information, and content hashes for tamper detection. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Wrap JSON data
echo '{"action": "user.login", "ip": "192.168.1.1"}' | \
  expanso-edge run pipeline-cli.yaml

# With custom source and actor
SOURCE=auth-service ACTOR=user-123 \
  echo '{"action": "payment", "amount": 100}' | \
  expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/wrap \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"action": "user.login"},
    "source": "auth-service",
    "actor": "user-123"
  }'
```

## Output

```json
{
  "envelope": {
    "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "source": "auth-service",
    "actor": "user-123",
    "payload": {
      "action": "user.login"
    },
    "payload_hash": "abc123...",
    "payload_size": 25,
    "version": "1.0"
  },
  "signature": "def456...",
  "metadata": {
    "skill": "audit-envelope",
    "trace_id": "a1b2c3d4..."
  }
}
```

## Envelope Fields

| Field | Description |
|-------|-------------|
| `trace_id` | Unique UUID for this envelope |
| `timestamp` | ISO 8601 creation timestamp |
| `source` | System that created the envelope |
| `actor` | User/system that initiated the action |
| `payload` | Original data |
| `payload_hash` | SHA-256 hash of payload |
| `payload_size` | Size of payload in bytes |
| `signature` | HMAC signature for tamper detection |

## Use Cases

- Audit logging for compliance (SOX, HIPAA, PCI)
- Event sourcing with tamper detection
- API request/response logging
- Change tracking in databases
