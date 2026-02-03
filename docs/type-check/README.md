# type-check

Check the type of JSON values.

## Usage

```bash
echo '[1, 2, 3]' | expanso-edge run pipeline-cli.yaml
echo '{"key": "value"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "type": "array",
  "is_array": true,
  "is_object": false,
  "is_string": false
}
```
