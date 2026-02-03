# date-diff

Calculate difference between two dates.

## Usage

```bash
echo '{"start": "2024-01-01T00:00:00Z", "end": "2024-01-15T00:00:00Z"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "start": "2024-01-01T00:00:00Z",
  "end": "2024-01-15T00:00:00Z",
  "diff_days": 14
}
```
