# image-describe

Generate AI description of an image from URL.

## Usage

```bash
echo '{"image_url": "https://example.com/image.jpg"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "description": "A scenic mountain landscape with snow-capped peaks...",
  "metadata": {"skill": "image-describe"}
}
```

## Requirements

- `OPENAI_API_KEY` environment variable
