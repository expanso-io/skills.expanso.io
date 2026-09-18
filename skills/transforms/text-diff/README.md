# text-diff

Compare two texts and identify differences with similarity scoring.

## Overview

This skill compares two text inputs and provides metrics about their differences, including length changes, word counts, similarity scores, and content hashes. Runs entirely locally.

## Usage

### CLI Mode

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)). `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine.

```bash
expanso-edge validate pipeline-cli.yaml
```

### MCP Mode

```bash
expanso-edge validate pipeline-mcp.yaml
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
