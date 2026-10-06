# code-explain

> Explain code in plain English with step-by-step breakdown.

This skill takes any code snippet and produces a clear, human-readable explanation. Perfect for:
- Code review assistance
- Learning new codebases
- Documentation generation
- Onboarding new team members

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
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `LANGUAGE` | No | auto-detect | Programming language hint |
| `DETAIL_LEVEL` | No | normal | brief, normal, or detailed |
| `PORT` | No | 8080 | HTTP port for MCP mode |

*Not required if using Ollama backend.

## Detail Levels

| Level | Description |
|-------|-------------|
| `brief` | 2-3 sentence summary |
| `normal` | Step-by-step breakdown with key concepts |
| `detailed` | Line-by-line explanation with examples and pitfalls |

## Example Output

### Input
```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

### Output (normal detail)
```json
{
  "explanation": "This function implements binary search, an efficient algorithm for finding an element in a sorted array.\n\n**How it works:**\n1. Initialize two pointers: `left` at the start, `right` at the end\n2. Calculate the middle index\n3. If the middle element matches the target, return its index\n4. If the target is larger, search the right half\n5. If the target is smaller, search the left half\n6. Repeat until found or the search space is exhausted\n\n**Key insight:** Each iteration eliminates half the remaining elements, giving O(log n) time complexity.\n\n**Returns:** The index of the target if found, otherwise -1.",
  "metadata": {
    "skill": "code-explain",
    "mode": "cli",
    "model": "gpt-4o-mini",
    "input_hash": "abc123...",
    "input_length": 342,
    "trace_id": "550e8400-...",
    "language": "python",
    "detail_level": "normal",
    "timestamp": "2026-01-31T12:00:00Z"
  }
}
```

## Using with Ollama

For complete privacy, use Ollama with CodeLlama:

```yaml
# Replace in pipeline-cli.yaml:
- ollama_chat:
    server_address: "http://localhost:11434"
    model: codellama
```

Run Ollama:
```bash
ollama run codellama
```

## Use Cases

- **Code Review**: Get quick explanations of unfamiliar code
- **Documentation**: Generate README explanations from code
- **Learning**: Understand complex algorithms step-by-step
- **Debugging**: Clarify what code is supposed to do vs what it does

## Related Skills

- [text-summarize](../text-summarize/) - Summarize text
- [text-analyze](../text-analyze/) - Analyze text for sentiment/entities

---

*Built with [Expanso Edge](https://expanso.io).*
