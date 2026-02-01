# array-join

Join array elements with various separators.

## Usage

```bash
echo '["a", "b", "c"]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "by_comma": "a, b, c",
  "by_space": "a b c",
  "by_pipe": "a | b | c",
  "count": 3
}
```
