# json-diff

Compare two JSON objects and find differences.

## Usage

```bash
echo '{"a": {"x": 1}, "b": {"x": 1, "y": 2}}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "a_key_count": 1,
  "b_key_count": 2,
  "only_in_a": [],
  "only_in_b": ["y"],
  "equal": false
}
```
