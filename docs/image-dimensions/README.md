# image-dimensions

Calculate image properties from dimensions.

## Usage

```bash
echo '{"width": 1920, "height": 1080}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "width": 1920,
  "height": 1080,
  "megapixels": 2.07,
  "aspect_ratio": "16:9",
  "orientation": "landscape"
}
```
