# env-parse

Parse .env file format and analyze contents.

## Usage

```bash
echo "KEY=value
DB_HOST=localhost" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "line_count": 2,
  "variable_count": 2,
  "has_comments": false
}
```
