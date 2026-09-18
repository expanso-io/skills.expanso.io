# video-generate

Generate short videos from text prompts using Replicate AI.

## Quick Start

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
```

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `REPLICATE_API_TOKEN` | Yes | API token from [replicate.com](https://replicate.com) |

## Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Text description of the video to generate |

## Output

```json
{
  "video_url": "https://replicate.delivery/...",
  "status": "succeeded",
  "metadata": {
    "skill": "video-generate",
    "model": "minimax/video-01",
    "prediction_id": "abc123",
    "trace_id": "550e8400-e29b-41d4-...",
    "started_at": "2026-02-02T20:00:00Z",
    "completed_at": "2026-02-02T20:01:30Z"
  }
}
```

## How It Works

This skill uses the [minimax/video-01](https://replicate.com/minimax/video-01) model on Replicate:

1. Submit your text prompt to the Replicate API
2. Poll for completion (videos typically take 30-120 seconds)
3. Return the generated video URL

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Your Prompt │────▶│ Expanso Edge │────▶│ Replicate AI │
└─────────────┘     └──────────────┘     └──────────────┘
                           │                    │
                           │◀───── Poll ────────│
                           │                    │
                    ┌──────▼──────┐       ┌─────▼─────┐
                    │ Video URL   │◀──────│ Generated │
                    │ (returned)  │       │   Video   │
                    └─────────────┘       └───────────┘
```

## Cost Estimate

Replicate charges based on compute time. For minimax/video-01:
- ~$0.05-0.10 per video generation
- Prices vary by video length and complexity

Check [replicate.com/pricing](https://replicate.com/pricing) for current rates.

## Tips

- **Be specific**: "A golden retriever running through a wheat field at sunset" works better than "a dog"
- **Include style**: Add words like "cinematic", "slow motion", "aerial view"
- **Keep it short**: Model generates ~5 second clips

## Troubleshooting

### "Invalid API token"

Make sure `REPLICATE_API_TOKEN` is set and starts with `r8_`:

```bash
echo $REPLICATE_API_TOKEN
# Should print: r8_xxxxx...
```

### Video generation times out

The skill polls for up to 3 minutes. Some complex prompts may take longer. Check the prediction status at replicate.com.

### "Prompt field is required"

Make sure you're sending valid JSON with a `prompt` field:

```bash
expanso-edge validate pipeline-cli.yaml
```

## Related Skills

- [text-to-image](../text-to-image/) - Generate still images from text
- [image-analyze](../image-analyze/) - Analyze images with AI
