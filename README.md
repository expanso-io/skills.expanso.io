# Expanso Skills Marketplace

The official marketplace for Expanso skills - pre-built data processing pipelines that work with OpenClaw, Claude, and any MCP-compatible AI assistant.

**172 skills** across **5 categories** - all open source and ready to use.

## What Are Expanso Skills?

Expanso Skills are portable data processing pipelines that:

- **Keep credentials local** - API keys never leave your machine
- **Work offline** - Many skills support local LLM backends (Ollama)
- **Are composable** - Chain skills together for complex workflows
- **Run anywhere** - CLI, MCP server, or Expanso Cloud

Each skill includes:
- `skill.yaml` - Metadata, inputs/outputs, credentials
- `pipeline-cli.yaml` - Standalone CLI pipeline
- `pipeline-mcp.yaml` - MCP server integration
- `test/test.yaml` - Automated tests

## Quick Start

### 1. Install Expanso CLI

```bash
# macOS
brew install expanso-io/tap/expanso

# Linux
curl -fsSL https://get.expanso.io | sh

# Or via Docker
docker pull ghcr.io/expanso-io/expanso:latest
```

### 2. Run a Skill

```bash
# Clone the marketplace
git clone https://github.com/expanso-io/expanso-skills.git
cd expanso-skills

# Run a skill directly
echo '{"text": "Hello world"}' | expanso run skills/transforms/json-pretty/pipeline-cli.yaml

# Or install as MCP server
expanso mcp install skills/ai/text-summarize/pipeline-mcp.yaml
```

### 3. Use with Claude

Add to your `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expanso-skills": {
      "command": "expanso",
      "args": ["mcp", "serve", "--skills-dir", "/path/to/expanso-skills/skills"]
    }
  }
}
```

## Skill Categories

### Workflows (19 skills)
End-to-end automation combining multiple services.

| Skill | Description |
|-------|-------------|
| `morning-briefing` | Daily briefing with calendar, weather, news, tasks |
| `email-triage` | AI-powered email classification and routing |
| `stripe-reports` | Automated Stripe analytics and reports |
| `devops-monitor` | Infrastructure monitoring and alerting |
| `jira-automate` | Jira/Confluence workflow automation |
| `todoist-automate` | Task management automation |
| `seo-pipeline` | SEO analysis and optimization |
| [View all...](skills/workflows/) | |

### AI (23 skills)
AI-powered processing for text, images, audio, and video.

| Skill | Description |
|-------|-------------|
| `text-embed` | Generate embeddings for RAG/semantic search |
| `text-summarize` | Summarize long documents |
| `text-translate` | Multi-language translation |
| `image-analyze` | Vision AI for image understanding |
| `audio-transcribe` | Speech-to-text transcription |
| `meeting-notes` | Transcribe and summarize meetings |
| [View all...](skills/ai/) | |

### Security (14 skills)
Security, compliance, and cryptographic operations.

| Skill | Description |
|-------|-------------|
| `cve-scan` | Scan SBOM for vulnerabilities |
| `pii-detect` | Detect PII in text |
| `pii-redact` | Redact sensitive information |
| `sign-envelope` | Cryptographically sign data |
| `secrets-scan` | Detect leaked secrets |
| `sbom-generate` | Generate software bill of materials |
| [View all...](skills/security/) | |

### Transforms (100 skills)
Data transformation, parsing, and format conversion.

| Skill | Description |
|-------|-------------|
| `json-*` | 10 JSON manipulation skills |
| `array-*` | 15 array operation skills |
| `string-*` | 10 string manipulation skills |
| `text-*` | 12 text processing skills |
| `date-*` | 4 date/time skills |
| `math-*` | 8 mathematical operations |
| [View all...](skills/transforms/) | |

### Utilities (16 skills)
General utilities and helper functions.

| Skill | Description |
|-------|-------------|
| `uuid-generate` | Generate UUIDs |
| `email-validate` | Validate email addresses |
| `mime-type` | Detect file MIME types |
| `image-dimensions` | Get image dimensions |
| `retry-wrapper` | Add retry logic to operations |
| [View all...](skills/utilities/) | |

## Skill Structure

Each skill follows this structure:

```
skill-name/
├── skill.yaml          # Skill metadata
├── pipeline-cli.yaml   # CLI pipeline definition
├── pipeline-mcp.yaml   # MCP server pipeline
├── README.md           # Documentation
└── test/
    ├── test.yaml       # Test definitions
    └── fixtures/       # Test data
```

### skill.yaml

```yaml
name: text-summarize
version: 1.0.0
description: Summarize long documents using AI

credentials:
  - name: OPENAI_API_KEY
    required: false  # Not required if using Ollama
    description: OpenAI API key

inputs:
  - name: text
    type: string
    required: true
    description: Text to summarize
  - name: max_length
    type: integer
    default: 100
    description: Maximum summary length

outputs:
  - name: summary
    type: string
    description: Summarized text

backends:
  - name: openai
    type: remote
    requires: [OPENAI_API_KEY]
  - name: ollama
    type: local
    models: [llama3.2, mistral]
```

## Using Skills

### CLI Mode

```bash
# Pipe input
echo "Long text to summarize..." | expanso run skills/ai/text-summarize/pipeline-cli.yaml

# With parameters
expanso run skills/ai/text-summarize/pipeline-cli.yaml \
  --input.text "Your text here" \
  --input.max_length 50

# Using local backend (Ollama)
EXPANSO_BACKEND=ollama expanso run skills/ai/text-summarize/pipeline-cli.yaml
```

### MCP Mode

```bash
# Start MCP server for a single skill
expanso mcp serve skills/ai/text-summarize/pipeline-mcp.yaml

# Start MCP server for all skills
expanso mcp serve --skills-dir skills/

# With specific port
expanso mcp serve --port 8080 skills/
```

### Programmatic Usage

```python
from expanso import Pipeline

# Load and run a skill
pipeline = Pipeline.load("skills/ai/text-summarize/pipeline-cli.yaml")
result = pipeline.run({"text": "Long document...", "max_length": 100})
print(result["summary"])
```

## Credential Management

Expanso keeps credentials secure:

```bash
# Set credentials (stored locally, never transmitted)
expanso credentials set OPENAI_API_KEY sk-...
expanso credentials set SLACK_WEBHOOK https://hooks.slack.com/...

# List configured credentials
expanso credentials list

# Credentials are injected at runtime, never embedded in pipelines
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding a New Skill

1. Use the template:
   ```bash
   cp -r _template skills/category/my-new-skill
   ```

2. Update `skill.yaml` with your skill metadata

3. Implement the pipeline in `pipeline-cli.yaml` and `pipeline-mcp.yaml`

4. Add tests in `test/test.yaml`

5. Submit a PR!

### Skill Guidelines

- Keep skills focused and single-purpose
- Support both remote (OpenAI) and local (Ollama) backends when possible
- Include comprehensive tests
- Document all inputs, outputs, and credentials
- Follow naming conventions: `category-action` (e.g., `text-summarize`, `json-validate`)

## Catalog API

The marketplace provides a JSON catalog for programmatic access:

```bash
# Full catalog with all metadata
curl https://raw.githubusercontent.com/expanso-io/expanso-skills/main/catalog.json

# Minimal catalog (just names and categories)
curl https://raw.githubusercontent.com/expanso-io/expanso-skills/main/catalog-minimal.json
```

### Catalog Structure

```json
{
  "version": "1.0.0",
  "total_skills": 172,
  "categories": {
    "ai": {
      "description": "AI-powered skills...",
      "skill_count": 23,
      "tags": ["ai", "ml", "llm"]
    }
  },
  "skills": {
    "text-summarize": {
      "name": "text-summarize",
      "version": "1.0.0",
      "description": "Summarize long documents",
      "category": "ai",
      "credentials": [...],
      "inputs": [...],
      "outputs": [...],
      "backends": ["openai", "ollama"],
      "tags": ["ai", "text", "openai", "local"]
    }
  }
}
```

## Related Resources

- [Expanso Documentation](https://docs.expanso.io)
- [Pipeline Schema](https://docs.expanso.io/schemas/pipeline.schema.json)
- [OpenClaw Integration](https://expanso.io/expanso-hearts-openclaw/)
- [Expanso Cloud](https://cloud.expanso.io)

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with love by [Expanso](https://expanso.io)
