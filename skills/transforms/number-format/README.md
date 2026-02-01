# number-format

Format numbers with various display options.

## Usage

```bash
echo "1234567.89" | expanso-edge run pipeline-cli.yaml
FORMAT=currency echo "99.5" | expanso-edge run pipeline-cli.yaml
FORMAT=percent echo "0.756" | expanso-edge run pipeline-cli.yaml
```

## Formats

- `standard`: 1234567.89
- `currency`: $99.50
- `percent`: 75.6%
- `scientific`: 1.23e+06
