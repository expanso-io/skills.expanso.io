# http-status

Look up HTTP status code meanings.

## Usage

```bash
echo "404" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "code": 404,
  "message": "Not Found",
  "category": "Client Error"
}
```
