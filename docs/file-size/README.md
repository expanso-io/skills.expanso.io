# file-size

Format file sizes in human-readable format.

## Usage

```bash
echo "1048576" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "bytes": 1048576,
  "kb": 1024,
  "mb": 1,
  "formatted": "1 MB"
}
```
