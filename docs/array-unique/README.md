# array-unique

Remove duplicate values from arrays.

## Usage

```bash
echo '[1, 2, 2, 3, 3, 3]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "unique": [1, 2, 3],
  "original_count": 6,
  "unique_count": 3,
  "duplicates_removed": 3
}
```
