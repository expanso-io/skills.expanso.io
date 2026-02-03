# text-stats

Calculate detailed text statistics.

## Usage

```bash
echo "Hello world. This is a test." | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "characters": 29,
  "characters_no_spaces": 24,
  "words": 6,
  "lines": 1,
  "sentences": 2,
  "avg_word_length": 4,
  "reading_time_minutes": 1
}
```
