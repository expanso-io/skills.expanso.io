# audio-duration

Format audio duration from seconds to HH:MM:SS.

## Usage

```bash
echo '{"seconds": 3661}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "seconds": 3661,
  "minutes": 61.02,
  "formatted": "01:01:01",
  "short": "01:01:01"
}
```
