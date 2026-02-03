# text-to-command

> Convert natural language instructions to CLI commands.

Turn plain English into executable shell commands. Perfect for:
- CLI command recall
- Automation scripting
- DevOps assistance
- Learning shell syntax

## Quick Start

### CLI Mode

```bash
export OPENAI_API_KEY=sk-...

# Basic usage
echo "find all python files modified today" | expanso-edge run pipeline-cli.yaml

# With shell context
echo "compress this folder" | SHELL_TYPE=bash expanso-edge run pipeline-cli.yaml

# PowerShell
echo "list running processes" | SHELL_TYPE=powershell expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &

curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "find all files larger than 100MB",
    "shell": "bash"
  }'
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `SHELL_TYPE` | No | bash | Target shell |
| `CONTEXT` | No | - | Additional context |
| `PORT` | No | 8080 | HTTP port for MCP mode |

## Supported Shells

| Shell | Value |
|-------|-------|
| Bash | `bash` |
| Zsh | `zsh` |
| Fish | `fish` |
| PowerShell | `powershell` |
| Windows CMD | `cmd` |

## Example Output

### Input
```
find all python files larger than 1MB modified in the last week
```

### Output
```json
{
  "command": "find . -name '*.py' -size +1M -mtime -7",
  "explanation": "Recursively finds Python files (.py) larger than 1MB that were modified within the last 7 days",
  "shell": "bash",
  "metadata": {
    "skill": "text-to-command",
    "trace_id": "550e8400-..."
  }
}
```

## More Examples

| Instruction | Generated Command |
|-------------|-------------------|
| "count lines in all js files" | `find . -name '*.js' -exec wc -l {} + \| tail -1` |
| "show disk usage sorted by size" | `du -sh * \| sort -h` |
| "kill process on port 3000" | `lsof -ti:3000 \| xargs kill` |
| "download this URL" | `curl -O <url>` |
| "extract tar.gz file" | `tar -xzf file.tar.gz` |

## Safety

The skill:
- Prefers non-destructive commands when ambiguous
- Warns about potentially dangerous operations
- Never generates `rm -rf /` or similar without explicit request
- Explains what each command does

## Related Skills

- [code-explain](../code-explain/) - Explain code
- [nl-to-sql](../nl-to-sql/) - Natural language to SQL

---

*Built with [Expanso Edge](https://expanso.io) - Your keys, your machine.*
