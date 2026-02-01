# date-format

Parse and format dates in various formats.

## Usage

```bash
echo "2024-01-15" | expanso-edge run pipeline-cli.yaml
echo "now" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "iso": "2024-01-15T00:00:00Z",
  "date": "2024-01-15",
  "time": "00:00:00",
  "unix": 1705276800,
  "day_of_week": "Monday"
}
```
