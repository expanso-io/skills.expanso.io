# object-keys

Extract keys and values from JSON objects.

## Usage

```bash
echo '{"name": "test", "value": 123}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "keys": ["name", "value"],
  "values": ["test", 123],
  "count": 2,
  "valid": true
}
```
