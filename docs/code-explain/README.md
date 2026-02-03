# code-explain

> Explain code in plain English with step-by-step breakdown.

This skill takes any code snippet and produces a clear, human-readable explanation. Perfect for:
- Code review assistance
- Learning new codebases
- Documentation generation
- Onboarding new team members

## Quick Start

### CLI Mode

```bash
export OPENAI_API_KEY=sk-...

# Explain a code file
cat mycode.py | expanso-edge run pipeline-cli.yaml

# With language hint (improves accuracy)
cat mycode.rs | LANGUAGE=rust expanso-edge run pipeline-cli.yaml

# Brief explanation
cat mycode.js | DETAIL_LEVEL=brief expanso-edge run pipeline-cli.yaml

# Detailed explanation with line-by-line breakdown
cat mycode.go | DETAIL_LEVEL=detailed expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &

curl -X POST http://localhost:8080/explain \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def factorial(n):\n  return 1 if n <= 1 else n * factorial(n-1)",
    "language": "python",
    "detail_level": "normal"
  }'
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

*Built with [Expanso Edge](https://expanso.io) - Your keys, your machine.*
