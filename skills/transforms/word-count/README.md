# word-count

Count words, characters, sentences, and paragraphs in text.

## Overview

This skill provides comprehensive text statistics including word count, character count, sentence count, paragraph count, and estimated reading time. Runs entirely locally.

## Usage

### CLI Mode

```bash
# Count words in text
echo "Hello world. This is a test." | expanso-edge run pipeline-cli.yaml

# Count words in a file
cat document.txt | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
# Start server
PORT=8080 expanso-edge run pipeline-mcp.yaml &

# Make request
curl -X POST http://localhost:8080/count \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world. This is a test sentence."}'
```

## Output

```json
{
  "words": 7,
  "characters": 38,
  "characters_no_spaces": 32,
  "sentences": 2,
  "paragraphs": 1,
  "reading_time_minutes": 1,
  "metadata": {
    "skill": "word-count",
    "trace_id": "...",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Use Cases

- Document statistics
- Content length validation
- Reading time estimation
- Text analysis preprocessing
