# path-parse

Parse file paths into components.

## Usage

```bash
echo "/home/user/docs/file.txt" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "dirname": "/home/user/docs",
  "filename": "file.txt",
  "basename": "file",
  "extension": ".txt",
  "is_absolute": true,
  "depth": 4
}
```
