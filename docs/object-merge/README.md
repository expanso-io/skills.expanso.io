# object-merge

Deep merge multiple JSON objects into one.

## Usage

```bash
echo '[{"a": 1}, {"b": 2}, {"c": 3}]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "merged": {"a": 1, "b": 2, "c": 3},
  "count": 3,
  "valid": true,
  "error": ""
}
```
