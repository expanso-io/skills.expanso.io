# markdown-format

Format text as Markdown elements (headings, lists, code blocks, links).

## Overview

This skill wraps text in various Markdown formatting elements. Runs entirely locally.

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

## Format Options

| Format | Input | Output |
|--------|-------|--------|
| `heading` | "Title" (level=2) | `## Title` |
| `h1`, `h2`, `h3` | "Title" | `# Title`, etc. |
| `bold` | "text" | `**text**` |
| `italic` | "text" | `_text_` |
| `code` | "code" (lang=py) | ````python\ncode\n```` |
| `inline-code` | "var" | `` `var` `` |
| `quote` | "text" | `> text` |
| `list` | "a\nb\nc" | `- a\n- b\n- c` |
| `numbered` | "a\nb\nc" | `1. a\n2. b\n3. c` |
| `link` | "text" (url=...) | `[text](url)` |

## Use Cases

- Document generation
- README formatting
- Note taking
- Content management
