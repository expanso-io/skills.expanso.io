# audit-envelope

Wrap any data with audit metadata for compliance, traceability, and tamper detection.

## Overview

This skill creates a cryptographically signed audit envelope around any data. The envelope includes timestamps, trace IDs, actor information, and content hashes for tamper detection. Runs entirely locally.

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
