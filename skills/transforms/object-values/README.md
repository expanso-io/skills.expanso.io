# object-values

Extract all values from an object.

## Usage

```bash
echo '{"a": 1, "b": 2, "c": 3}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "keys": ["a", "b", "c"],
  "values": [1, 2, 3],
  "count": 3
}
```
