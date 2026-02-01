# array-filter

Filter array elements, removing null and empty values.

## Usage

```bash
echo '[1, null, 2, "", 3]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "filtered": [1, 2, 3],
  "original_count": 5,
  "filtered_count": 3,
  "removed_count": 2
}
```
