# json-compact

Compact JSON by removing unnecessary whitespace.

## Usage

```bash
echo '{
  "name": "test",
  "value": 123
}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "compact": "{\"name\":\"test\",\"value\":123}",
  "original_length": 35,
  "compact_length": 27,
  "savings": 8
}
```
