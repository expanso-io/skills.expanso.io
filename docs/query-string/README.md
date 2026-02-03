# query-string

Parse URL query strings into structured data.

## Usage

```bash
echo "name=test&page=1&sort=asc" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "raw": "name=test&page=1&sort=asc",
  "param_count": 3,
  "pairs": ["name=test", "page=1", "sort=asc"],
  "has_encoded": false
}
```
