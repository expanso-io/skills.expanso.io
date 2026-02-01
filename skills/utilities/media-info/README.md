# media-info

Get comprehensive media file information.

## Usage

```bash
echo '{"filename": "video.mp4", "size_bytes": 10485760}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "filename": "video.mp4",
  "extension": "mp4",
  "type": "video",
  "size_bytes": 10485760,
  "size_mb": 10,
  "is_media": true
}
```
