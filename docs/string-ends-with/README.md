# string-ends-with

Check if a string ends with a given suffix.

## Usage

```bash
echo '{"text": "Hello World", "suffix": "World"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "ends_with": true,
  "text": "Hello World",
  "suffix": "World"
}
```
