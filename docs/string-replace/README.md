# string-replace

Replace all occurrences of a substring.

## Usage

```bash
echo '{"text": "hello world", "search": "world", "replace": "there"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original": "hello world",
  "result": "hello there",
  "search": "world",
  "replace": "there"
}
```
