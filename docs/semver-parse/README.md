# semver-parse

Parse semantic version strings.

## Usage

```bash
echo "v1.2.3-beta" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "version": "1.2.3-beta",
  "major": 1,
  "minor": 2,
  "patch": 3,
  "prerelease": "beta",
  "valid": true
}
```
