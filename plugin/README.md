# Expanso Skills Claude Code Plugin

This plugin adds the `/expanso-skill` slash command to Claude Code, providing easy access to the Expanso Skills Marketplace.

## Installation

### Option 1: Add to CLAUDE.md (Recommended)

Add the following to your project's `CLAUDE.md` or `~/.claude/CLAUDE.md`:

```markdown
## Expanso Skills

When the user uses `/expanso-skill`, load and follow the instructions from:
https://raw.githubusercontent.com/expanso-io/expanso-skills/main/plugin/expanso-skill.md

Skills catalog is available at:
https://raw.githubusercontent.com/expanso-io/expanso-skills/main/catalog.json
```

### Option 2: Copy Plugin File

Copy `expanso-skill.md` to your `~/.aiskills/` directory:

```bash
curl -o ~/.aiskills/expanso-skill.md \
  https://raw.githubusercontent.com/expanso-io/expanso-skills/main/plugin/expanso-skill.md
```

## Usage

Once installed, use the `/expanso-skill` command in Claude Code:

```
/expanso-skill list ai          # List AI skills
/expanso-skill show text-embed  # Show skill details
/expanso-skill search json      # Search for skills
/expanso-skill invoke pii-redact --cli  # Generate invocation code
```

## Available Subcommands

| Command | Description |
|---------|-------------|
| `list [category]` | List skills by category (ai, security, transforms, utilities, workflows) |
| `show <skill>` | Display full details for a skill |
| `search <query>` | Search skills by name or description |
| `invoke <skill> [--cli\|--mcp]` | Generate invocation code |

## Skill Categories

| Category | Count | Description |
|----------|-------|-------------|
| ai | 23 | AI-powered text, image, audio, video processing |
| security | 14 | Security, compliance, cryptography |
| transforms | 100 | Data transformation and format conversion |
| utilities | 16 | General utilities and helpers |
| workflows | 19 | Multi-step automation workflows |

## Related

- [Expanso Skills Marketplace](https://github.com/expanso-io/expanso-skills)
- [Expanso Documentation](https://docs.expanso.io)
- [OpenClaw Integration](https://expanso.io/expanso-hearts-openclaw/)
