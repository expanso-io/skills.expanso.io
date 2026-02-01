# text-wrap

Wrap text at specified line width.

## Usage

```bash
echo "This is a long line of text that should be wrapped" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "wrapped": "This is a long line...",
  "original_length": 52,
  "word_count": 10,
  "estimated_lines": 1,
  "width": 80
}
```
