# image-caption

Generate accessible alt text and captions for images.

## Usage

```bash
echo '{"image_url": "https://example.com/image.jpg"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "alt_text": "A golden retriever running on a beach",
  "caption": "Dog playing at sunset",
  "metadata": {"skill": "image-caption"}
}
```

## Requirements

- `OPENAI_API_KEY` environment variable
