# whitespace-normalize

Normalize whitespace in text (collapse multiple spaces, trim lines).

## Usage

```bash
echo "Hello    world   with   spaces" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "normalized": "Hello world with spaces",
  "original_length": 31,
  "normalized_length": 23,
  "chars_removed": 8
}
```
