# json-merge

Merge multiple JSON objects into one.

## Usage

```bash
echo '[{"a": 1}, {"b": 2}]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "merged": {"a": 1, "b": 2},
  "object_count": 2,
  "valid": true
}
```
