# string-pad

Pad strings to specified length with zeros.

## Usage

```bash
echo "42" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "left": "0000000042",
  "right": "4200000000",
  "original": "42",
  "original_length": 2,
  "target_length": 10
}
```
