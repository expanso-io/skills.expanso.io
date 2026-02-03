# text-indent

Indent text blocks with spaces.

## Usage

```bash
echo "line1
line2" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "indented_2": "  line1\n  line2",
  "indented_4": "    line1\n    line2",
  "line_count": 2
}
```
