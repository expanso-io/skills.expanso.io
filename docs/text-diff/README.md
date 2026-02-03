# text-diff

Compare two texts and identify differences with similarity scoring.

## Overview

This skill compares two text inputs and provides metrics about their differences, including length changes, word counts, similarity scores, and content hashes. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Compare two texts via JSON
echo '{"original": "Hello World", "modified": "Hello Universe"}' | \
  expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/diff \
  -H "Content-Type: application/json" \
  -d '{
    "original": "The quick brown fox jumps over the lazy dog",
    "modified": "The quick red fox jumps over the lazy cat"
  }'
```

## Output

```json
{
  "identical": false,
  "changes": {
    "original_length": 11,
    "modified_length": 14,
    "length_delta": 3,
    "original_words": 2,
    "modified_words": 2
  },
  "similarity": 0.785,
  "hashes": {
    "original": "abc123...",
    "modified": "def456..."
  },
  "metadata": {
    "skill": "text-diff",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Output Fields

| Field | Description |
|-------|-------------|
| `identical` | Boolean: are texts exactly the same? |
| `changes.length_delta` | Character count difference |
| `changes.original_words` | Word count in original |
| `changes.modified_words` | Word count in modified |
| `similarity` | Score from 0 (different) to 1 (identical) |
| `hashes` | SHA-256 hashes for both texts |

## Use Cases

- Version comparison
- Document change tracking
- Content deduplication
- Plagiarism detection (basic)
