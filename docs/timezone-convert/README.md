# timezone-convert

Convert timestamp to different timezone.

## Usage

```bash
echo '{"timestamp": "2024-01-15T12:00:00Z", "timezone": "America/New_York"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original": "2024-01-15T12:00:00Z",
  "timezone": "America/New_York",
  "converted": "2024-01-15T07:00:00-05:00"
}
```
