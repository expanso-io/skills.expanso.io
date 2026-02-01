# mime-type

Look up MIME types by file extension.

## Usage

```bash
echo "json" | expanso-edge run pipeline-cli.yaml
echo ".png" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "extension": "json",
  "mime": "application/json",
  "category": "application"
}
```
