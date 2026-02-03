# string-contains

Check if string contains substring.

## Usage

```bash
echo '{"text": "Hello World", "search": "World"}' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "contains": true,
  "contains_case_insensitive": true,
  "starts_with": false,
  "ends_with": true
}
```
