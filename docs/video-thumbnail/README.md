# video-thumbnail

Generate thumbnail timestamp information for videos.

## Usage

```bash
echo '{"video_url": "https://example.com/video.mp4", "timestamp": 30}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "video_url": "https://example.com/video.mp4",
  "timestamp_seconds": 30,
  "thumbnail_time": "0:00:30",
  "suggested_filename": "thumbnail_30s.jpg"
}
```
