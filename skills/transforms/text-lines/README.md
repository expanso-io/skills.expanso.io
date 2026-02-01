# text-lines

Split text into lines and analyze.

## Usage

```bash
echo "line 1
line 2
line 3" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "lines": ["line 1", "line 2", "line 3"],
  "line_count": 3,
  "non_empty_count": 3,
  "empty_count": 0
}
```
