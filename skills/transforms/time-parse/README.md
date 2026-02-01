# time-parse

Parse time string into components.

## Usage

```bash
echo "14:30:45" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "hour": 14,
  "minute": 30,
  "second": 45,
  "total_seconds": 52245,
  "original": "14:30:45"
}
```
