# array-length

Get length of arrays, objects (key count), or strings.

## Usage

```bash
echo '[1, 2, 3, 4, 5]' | expanso-edge run pipeline-cli.yaml
echo '{"a": 1, "b": 2}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "type": "array",
  "length": 5,
  "is_empty": false
}
```
