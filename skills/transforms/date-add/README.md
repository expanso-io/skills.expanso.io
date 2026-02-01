# date-add

Add days to a date.

## Usage

```bash
echo '{"date": "2024-01-15T00:00:00Z", "days": 7}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original": "2024-01-15T00:00:00Z",
  "days_added": 7,
  "result": "2024-01-22T00:00:00Z"
}
```
