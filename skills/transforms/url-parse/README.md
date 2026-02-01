# url-parse

Parse URL components into structured data.

## Usage

```bash
echo "https://example.com:8080/path?query=1" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "protocol": "https",
  "host": "example.com",
  "port": "8080",
  "path": "/path",
  "query": "query=1",
  "valid": true
}
```
