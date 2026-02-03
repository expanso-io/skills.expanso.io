# line-numbers

Add line numbers to text.

## Usage

```bash
echo "First line
Second line
Third line" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "numbered": "1: First line\n2: Second line\n3: Third line",
  "line_count": 3,
  "empty_lines": 0
}
```
