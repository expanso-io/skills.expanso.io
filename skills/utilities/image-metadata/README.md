# image-metadata

Extract metadata from base64-encoded image data.

## Usage

```bash
echo '{"image_base64": "/9j/4AAQSkZ..."}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "format": "jpeg",
  "size_bytes": 15360,
  "size_kb": 15,
  "base64_length": 20480
}
```
