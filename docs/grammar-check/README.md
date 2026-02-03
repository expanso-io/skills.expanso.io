# grammar-check

Check text for grammar, spelling, and style issues with automatic corrections.

## Overview

This skill analyzes text for errors and provides corrections along with explanations of each issue found.

## Usage

### CLI Mode

```bash
export OPENAI_API_KEY=sk-...

echo "Their going to the store tommorow" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &
curl -X POST http://localhost:8080/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Their going to the store tommorow"}'
```

## Output

```json
{
  "corrected": "They're going to the store tomorrow",
  "issues": [
    {
      "original": "Their",
      "correction": "They're",
      "type": "grammar"
    },
    {
      "original": "tommorow",
      "correction": "tomorrow",
      "type": "spelling"
    }
  ],
  "issue_count": 2,
  "has_issues": true,
  "metadata": {...}
}
```

## Issue Types

- **spelling**: Misspelled words
- **grammar**: Grammatical errors (verb tense, subject-verb agreement, etc.)
- **style**: Stylistic improvements (passive voice, wordiness, etc.)

## Use Cases

- Document proofreading
- Email checking
- Content editing
- Student writing feedback
