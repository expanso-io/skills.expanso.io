# array-map

Transform array elements to strings.

## Usage

```bash
echo '[1, true, null]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "mapped": ["1", "true", "null"],
  "count": 3
}
```
