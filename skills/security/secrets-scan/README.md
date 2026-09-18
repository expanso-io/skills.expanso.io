# secrets-scan

> Detect hardcoded secrets (API keys, tokens, passwords) in text or code.

Scan code, configs, and logs for accidentally committed credentials. Essential for:
- Pre-commit hooks
- CI/CD pipelines
- Code review automation
- Security audits

## Quick Start

### CLI Mode

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)). `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine.

```bash
expanso-edge validate pipeline-cli.yaml
```

### MCP Mode

```bash
expanso-edge validate pipeline-mcp.yaml
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `SECRET_TYPES` | No | all | Comma-separated secret types |
| `PORT` | No | 8080 | HTTP port for MCP mode |

## Secret Types

| Type | Examples |
|------|----------|
| `api_key` | sk-xxx, AKIA..., api_key=... |
| `token` | ghp_xxx, Bearer xxx |
| `password` | password=xxx, pwd:xxx |
| `private_key` | -----BEGIN RSA PRIVATE KEY----- |
| `aws_key` | aws-xxx, aws_secret_access_key |
| `github_token` | ghp_xxx, gho_xxx |
| `slack_token` | slack-xxx |
| `openai_key` | sk-xxx |

## Example Output

### Input
```javascript
const config = {
  apiKey: "sk-proj-abc123def456ghi789",
  database: {
    password: "supersecret123!"
  },
  aws: {
    accessKeyId: "YOUR_AWS_ACCESS_KEY_ID",
    secretAccessKey: "YOUR_AWS_SECRET_KEY"
  }
};
```

### Output
```json
{
  "findings": [
    {
      "type": "openai_key",
      "value": "sk-p...789",
      "line": 2,
      "severity": "high",
      "context": "OpenAI API key in apiKey field"
    },
    {
      "type": "password",
      "value": "supe...123!",
      "line": 4,
      "severity": "high",
      "context": "Database password"
    },
    {
      "type": "aws_key",
      "value": "YOUR...ID",
      "line": 7,
      "severity": "high",
      "context": "AWS Access Key ID"
    },
    {
      "type": "aws_key",
      "value": "YOUR...KEY",
      "line": 8,
      "severity": "high",
      "context": "AWS Secret Access Key"
    }
  ],
  "has_secrets": true,
  "summary": "Found 4 high-severity secrets: 1 OpenAI key, 1 password, 2 AWS credentials"
}
```

## Pre-Commit Integration

There is no verified pre-commit form. The skill runs as a Cloud-scheduled job,
and `pipeline-cli.yaml` reads `stdin`, which that job cannot receive from a
local `git diff`.

## False Positive Handling

The scanner automatically ignores:
- Placeholder values: `your-api-key-here`, `xxx`, `<token>`
- Environment references: `${API_KEY}`, `$SECRET`
- Example values from documentation
- Test fixtures with obvious fake data

## Related Skills

- [pii-detect](../pii-detect/) - Detect personally identifiable information
- [log-sanitize](../log-sanitize/) - Sanitize logs before storage
- [policy-check](../policy-check/) - Check configuration against policies

---

*Built with [Expanso Edge](https://expanso.io).*
