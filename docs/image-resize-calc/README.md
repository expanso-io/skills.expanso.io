# image-resize-calc

Calculate new dimensions for resizing while maintaining aspect ratio.

## Usage

```bash
echo '{"width": 1920, "height": 1080, "max_width": 800, "max_height": 600}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original_width": 1920,
  "original_height": 1080,
  "new_width": 800,
  "new_height": 450,
  "aspect_ratio": 1.78,
  "scale_factor": 0.42
}
```
