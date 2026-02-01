# audio-transcribe

Transcribe audio content using AI.

## Usage

```bash
echo '{"audio_url": "https://example.com/audio.mp3", "description": "A podcast about technology"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "transcript": "Welcome to the technology podcast...",
  "metadata": {"skill": "audio-transcribe"}
}
```

## Requirements

- `OPENAI_API_KEY` environment variable
