# boolean-parse

Parse various boolean representations (yes/no, true/false, 1/0, on/off).

## Usage

```bash
echo "yes" | expanso-edge run pipeline-cli.yaml
echo "0" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "input": "yes",
  "boolean": true,
  "is_truthy": true,
  "is_falsy": false,
  "is_valid": true
}
```
