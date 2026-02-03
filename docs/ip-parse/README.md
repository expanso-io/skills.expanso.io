# ip-parse

Parse and validate IP addresses.

## Usage

```bash
echo "192.168.1.1" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "ip": "192.168.1.1",
  "valid": true,
  "version": 4,
  "is_private": true,
  "is_loopback": false
}
```
