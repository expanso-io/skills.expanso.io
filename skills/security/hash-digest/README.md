# hash-digest

> Compute cryptographic hash (SHA256, SHA512, MD5, XXHash64) of any input.

Pure local processing - no external API calls, no credentials needed. Perfect for:
- Content integrity verification
- Deduplication keys
- Audit trail fingerprints
- Cache keys

## Quick Start

### CLI Mode

```bash
# SHA256 (default)
echo "Hello, World!" | expanso-edge run pipeline-cli.yaml

# SHA512
echo "Hello, World!" | ALGORITHM=sha512 expanso-edge run pipeline-cli.yaml

# MD5 (legacy compatibility)
echo "Hello, World!" | ALGORITHM=md5 expanso-edge run pipeline-cli.yaml

# XXHash64 (fast, non-cryptographic)
echo "Hello, World!" | ALGORITHM=xxhash64 expanso-edge run pipeline-cli.yaml

# Hash a file
cat large_file.bin | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &

curl -X POST http://localhost:8080/hash \
  -H "Content-Type: application/json" \
  -d '{"data": "Hello, World!", "algorithm": "sha256"}'
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
# Generate hash for dedup key
cat document.pdf | ALGORITHM=xxhash64 expanso-edge run pipeline-cli.yaml | jq -r '.hash'
```

### Audit Trail
```bash
# Hash input before processing for audit
INPUT_HASH=$(echo "$DATA" | expanso-edge run pipeline-cli.yaml | jq -r '.hash')
echo "Processing data with hash: $INPUT_HASH"
```

### File Integrity
```bash
# Verify file hasn't changed
EXPECTED="dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
ACTUAL=$(cat file.txt | expanso-edge run pipeline-cli.yaml | jq -r '.hash')
[ "$EXPECTED" = "$ACTUAL" ] && echo "OK" || echo "MISMATCH"
```

## No Credentials Required

This skill runs entirely locally with no external API calls. Your data never leaves your machine.

## Related Skills

- [sign-envelope](../sign-envelope/) - Cryptographically sign data
- [verify-signature](../verify-signature/) - Verify signatures
- [audit-envelope](../audit-envelope/) - Wrap output with audit metadata

---

*Built with [Expanso Edge](https://expanso.io) - Your keys, your machine.*
