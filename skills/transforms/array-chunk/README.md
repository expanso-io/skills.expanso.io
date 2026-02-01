# array-chunk

Split arrays into smaller chunks.

## Usage

```bash
echo '[1, 2, 3, 4, 5, 6]' | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "original": [1, 2, 3, 4, 5, 6],
  "original_length": 6,
  "chunk_size": 2,
  "chunk_count": 3,
  "valid": true
}
```
