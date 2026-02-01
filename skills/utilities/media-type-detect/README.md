# media-type-detect

Detect media type from filename extension.

## Usage

```bash
echo '{"filename": "photo.jpg"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "filename": "photo.jpg",
  "extension": "jpg",
  "media_type": "image/jpeg",
  "category": "image"
}
```
