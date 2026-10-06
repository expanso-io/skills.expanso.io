# grammar-check

Check text for grammar, spelling, and style issues with automatic corrections.

## Overview

This skill analyzes text for errors and provides corrections along with explanations of each issue found.

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
