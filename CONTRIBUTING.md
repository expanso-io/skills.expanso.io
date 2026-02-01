# Contributing to Expanso Skills

Thank you for your interest in contributing to the Expanso Skills Marketplace! This document provides guidelines for contributing new skills and improving existing ones.

## Getting Started

### Prerequisites

- [Expanso CLI](https://docs.expanso.io/getting-started/installation) installed
- Basic understanding of YAML and data pipelines
- For AI skills: Access to OpenAI API or local Ollama installation

### Development Setup

```bash
# Clone the repository
git clone https://github.com/expanso-io/expanso-skills.git
cd expanso-skills

# Verify installation
expanso version

# Run an existing skill to test setup
echo '{"text": "Hello"}' | expanso run skills/transforms/json-pretty/pipeline-cli.yaml
```

## Creating a New Skill

### 1. Choose the Right Category

| Category | Use For |
|----------|---------|
| `workflows` | Multi-step automations, integrations with external services |
| `ai` | AI/ML processing (text, image, audio, video) |
| `security` | Security, compliance, cryptography |
| `transforms` | Data transformation, parsing, format conversion |
| `utilities` | General helpers, validation, metadata extraction |

### 2. Create from Template

```bash
# Copy the template
cp -r _template skills/[category]/my-skill-name

# Edit the skill definition
$EDITOR skills/[category]/my-skill-name/skill.yaml
```

### 3. Implement skill.yaml

```yaml
name: my-skill-name
version: 1.0.0
description: Clear, concise description of what the skill does

# List all required/optional credentials
credentials:
  - name: API_KEY_NAME
    required: true  # or false if optional
    description: What this credential is for

# Define inputs with types and defaults
inputs:
  - name: input_name
    type: string|integer|boolean|array|object
    required: true
    default: "optional default"
    description: What this input does

# Define outputs
outputs:
  - name: result
    type: string|object|array
    description: What this output contains

# List supported backends
backends:
  - name: openai
    type: remote
    requires: [OPENAI_API_KEY]
  - name: ollama
    type: local
    models: [llama3.2, mistral]
```

### 4. Implement the Pipelines

**pipeline-cli.yaml** - For standalone CLI usage:

```yaml
name: my-skill-cli
type: pipeline

config:
  input:
    stdin:
      codec: all
      max_buffer: 1048576

  pipeline:
    processors:
      - mapping: |
          # Your processing logic
          root.result = content()

  output:
    stdout:
      codec: json_object
```

**pipeline-mcp.yaml** - For MCP server integration:

```yaml
name: my-skill-mcp
type: pipeline

config:
  input:
    http_server:
      address: "0.0.0.0:${PORT:8080}"
      path: /process

  pipeline:
    processors:
      - mapping: |
          # Your processing logic
          root.result = content()

  output:
    sync_response: {}
```

### 5. Add Tests

Create `test/test.yaml`:

```yaml
name: my-skill-tests
tests:
  - name: basic_functionality
    input:
      text: "test input"
    expected:
      result: "expected output"

  - name: handles_empty_input
    input:
      text: ""
    expected:
      result: ""

  - name: handles_special_characters
    input:
      text: "test with 'quotes' and \"double quotes\""
    expected:
      result: "processed correctly"
```

Run tests:

```bash
expanso test skills/[category]/my-skill-name/test/test.yaml
```

### 6. Add Documentation

Create a `README.md` in your skill directory:

```markdown
# my-skill-name

Brief description of what the skill does.

## Usage

### CLI

\`\`\`bash
echo '{"text": "input"}' | expanso run pipeline-cli.yaml
\`\`\`

### MCP

Available as tool `my-skill-name` when running the MCP server.

## Inputs

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| text | string | yes | - | Input text |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| result | string | Processed output |

## Credentials

| Name | Required | Description |
|------|----------|-------------|
| API_KEY | no | Optional API key |

## Examples

### Example 1: Basic usage
...
```

## Skill Guidelines

### Naming Conventions

- Use kebab-case: `text-summarize`, `json-validate`
- Start with the data type or domain: `json-*`, `text-*`, `image-*`
- End with the action: `*-parse`, `*-validate`, `*-convert`

### Best Practices

1. **Single Responsibility**: Each skill should do one thing well
2. **Sensible Defaults**: Always provide reasonable default values
3. **Graceful Errors**: Handle errors gracefully with clear messages
4. **Local First**: Support local backends (Ollama) when possible
5. **Minimal Dependencies**: Avoid unnecessary external dependencies
6. **Comprehensive Tests**: Cover edge cases and error conditions

### Credential Security

- Never embed credentials in pipeline files
- Use environment variable references: `${OPENAI_API_KEY}`
- Mark credentials as `required: false` when local alternatives exist
- Document what each credential is used for

### Output Format

All skills should return structured JSON with:

```json
{
  "result": "...",           // Main output
  "metadata": {              // Optional metadata
    "skill": "skill-name",
    "version": "1.0.0",
    "timestamp": "...",
    "trace_id": "..."
  }
}
```

## Submitting a Pull Request

### Before Submitting

1. Run all tests: `expanso test skills/[category]/my-skill-name/test/test.yaml`
2. Lint YAML files: `yamllint skills/[category]/my-skill-name/`
3. Update the catalog: `uv run -s scripts/build-catalog.py`
4. Ensure documentation is complete

### PR Checklist

- [ ] Skill follows naming conventions
- [ ] `skill.yaml` is complete with all fields
- [ ] Both CLI and MCP pipelines implemented
- [ ] Tests pass
- [ ] README.md included
- [ ] Catalog updated

### PR Description Template

```markdown
## Summary
Brief description of the new skill or changes.

## Skill Details
- **Name**: my-skill-name
- **Category**: transforms
- **Backends**: openai, ollama

## Testing
- [ ] All tests pass
- [ ] Tested with CLI mode
- [ ] Tested with MCP mode

## Related Issues
Fixes #123
```

## Code of Conduct

Please be respectful and constructive in all interactions. We're building this together!

## Questions?

- Open an issue for bugs or feature requests
- Join our [Discord](https://discord.gg/expanso) for discussions
- Email: skills@expanso.io

Thank you for contributing!
