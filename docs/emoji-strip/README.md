# emoji-strip

Remove emojis from text.

## Usage

```bash
echo "Hello World! 🌍🎉" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original": "Hello World! 🌍🎉",
  "clean": "Hello World!",
  "original_length": 16,
  "clean_length": 12,
  "removed_count": 4
}
```
