# object-pick

Pick specific keys from an object.

## Usage

```bash
echo '{"object": {"a": 1, "b": 2, "c": 3}, "keys": ["a", "c"]}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original_keys": ["a", "b", "c"],
  "picked_keys": ["a", "c"],
  "picked_count": 2,
  "omitted_count": 1
}
```
