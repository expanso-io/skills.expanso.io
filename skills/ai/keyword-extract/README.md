# keyword-extract

Extract keywords and key phrases from text.

## Overview

This skill extracts important keywords, multi-word phrases, and main topics from text. Useful for SEO, content tagging, and search indexing.

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
  "keywords": [
    {"word": "machine", "relevance": 0.95},
    {"word": "learning", "relevance": 0.92},
    {"word": "AI", "relevance": 0.88}
  ],
  "phrases": [
    "machine learning",
    "artificial intelligence",
    "neural networks"
  ],
  "topics": [
    "Technology",
    "Artificial Intelligence"
  ],
  "keyword_count": 3,
  "metadata": {...}
}
```

## Use Cases

- SEO keyword research
- Content tagging
- Document indexing
- Topic modeling
- Article summarization
