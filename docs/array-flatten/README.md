# array-flatten

Flatten nested arrays into a single level.

## Usage

```bash
echo '[[1, 2], [3, [4, 5]]]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "flat": [1, 2, 3, 4, 5],
  "flat_length": 5,
  "valid": true
}
```
