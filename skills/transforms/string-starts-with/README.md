# string-starts-with

Check if a string starts with a given prefix.

## Usage

```bash
echo '{"text": "Hello World", "prefix": "Hello"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "starts_with": true,
  "text": "Hello World",
  "prefix": "Hello"
}
```
