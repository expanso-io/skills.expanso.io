# hash-digest

> Compute cryptographic hash (SHA256, SHA512, MD5, XXHash64) of any input.

Pure local processing - no external API calls, no credentials needed. Perfect for:
- Content integrity verification
- Deduplication keys
- Audit trail fingerprints
- Cache keys

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
| `ALGORITHM` | No | sha256 | Hash algorithm |
| `PORT` | No | 8080 | HTTP port for MCP mode |

## Algorithms

| Algorithm | Output Size | Speed | Use Case |
|-----------|-------------|-------|----------|
| `sha256` | 64 chars | Medium | Default, security-sensitive |
| `sha512` | 128 chars | Medium | Higher security |
| `md5` | 32 chars | Fast | Legacy, non-security |
| `xxhash64` | 16 chars | Very Fast | Dedup, cache keys |

## Example Output

### Input
```
Hello, World!
```

### Output (SHA256)
```json
{
  "hash": "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f",
  "algorithm": "sha256",
  "input_length": 14,
  "metadata": {
    "skill": "hash-digest",
    "mode": "cli",
    "trace_id": "550e8400-...",
    "timestamp": "2026-01-31T12:00:00Z"
  }
}
```

## Use Cases

### Content Deduplication
```bash
expanso-edge validate pipeline-cli.yaml
```

### Audit Trail
```bash
expanso-edge validate pipeline-cli.yaml
```

### File Integrity
```bash
expanso-edge validate pipeline-cli.yaml
```

## No Credentials Required

This skill runs entirely locally with no external API calls. Your data never leaves your machine.

## Related Skills

- [sign-envelope](../sign-envelope/) - Cryptographically sign data
- [verify-signature](../verify-signature/) - Verify signatures
- [audit-envelope](../audit-envelope/) - Wrap output with audit metadata

---

*Built with [Expanso Edge](https://expanso.io).*
