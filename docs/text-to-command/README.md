# text-to-command

> Convert natural language instructions to CLI commands.

Turn plain English into executable shell commands. Perfect for:
- CLI command recall
- Automation scripting
- DevOps assistance
- Learning shell syntax

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

*Built with [Expanso Edge](https://expanso.io).*
