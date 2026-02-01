# jwt-decode

Decode JWT tokens to view header and payload (does not verify signature).

## Usage

```bash
# Pass any JWT token (header.payload.signature format)
echo "<your-jwt-token>" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "header": {"alg": "HS256"},
  "payload": {"sub": "1234"},
  "signature": "sig",
  "valid_format": true
}
```

**Note**: This decodes only. Use a proper library for verification.
