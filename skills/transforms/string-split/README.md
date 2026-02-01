# string-split

Split strings by various delimiters.

## Usage

```bash
echo "a, b, c, d" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "by_comma": ["a", "b", "c", "d"],
  "by_space": ["a,", "b,", "c,", "d"],
  "comma_count": 4
}
```
