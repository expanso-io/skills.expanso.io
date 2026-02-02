# OpenClaw Skills

OpenClaw-compatible skills for AI assistants. These skills are shell scripts and tools that Claude can call directly from chat conversations.

## What Are OpenClaw Skills?

OpenClaw skills are different from Expanso Edge pipeline skills:
- **OpenClaw Skills** = Shell scripts, tools, and utilities that Claude can invoke
- **Expanso Edge Skills** = YAML-based data processing pipelines

## Skill Structure

Each OpenClaw skill follows this structure:

```
skill-name/
├── SKILL.md                 # Skill metadata and documentation
└── scripts/                 # Executable scripts
    ├── tool1.sh
    ├── tool2.sh
    └── ...
```

### SKILL.md Format

```markdown
---
name: skill-name
description: What the skill does
---

# Skill Name

Documentation, usage examples, prerequisites, etc.
```

## Using Skills in OpenClaw Deployments

### Option 1: Clone During Build (Recommended)

Add to your Dockerfile:

```dockerfile
# Clone expanso-skills and copy OpenClaw skills
RUN git clone https://github.com/expanso-io/expanso-skills.git /tmp/expanso-skills \
    && cp -r /tmp/expanso-skills/openclaw/* /root/clawd/skills/ \
    && rm -rf /tmp/expanso-skills
```

### Option 2: Git Submodule

```bash
# In your OpenClaw deployment repo
git submodule add https://github.com/expanso-io/expanso-skills.git skills-marketplace
```

Then in Dockerfile:
```dockerfile
COPY skills-marketplace/openclaw/* /root/clawd/skills/
```

### Option 3: Direct Copy

```bash
# Clone the repo
git clone https://github.com/expanso-io/expanso-skills.git

# Copy skills to your deployment
cp -r expanso-skills/openclaw/* ./skills/
```

## Available OpenClaw Skills

### System & Infrastructure

| Skill | Description |
|-------|-------------|
| `expanso-edge` | Monitor and control expanso-edge daemon |

## Creating New OpenClaw Skills

1. **Create skill directory:**
   ```bash
   mkdir -p openclaw/my-skill/scripts
   ```

2. **Add SKILL.md:**
   ```markdown
   ---
   name: my-skill
   description: Brief description
   ---

   # My Skill

   Documentation here...
   ```

3. **Add scripts:**
   ```bash
   #!/bin/bash
   # openclaw/my-skill/scripts/tool.sh
   echo "Hello from my skill!"
   ```

4. **Make executable:**
   ```bash
   chmod +x openclaw/my-skill/scripts/*.sh
   ```

5. **Test locally:**
   ```bash
   bash openclaw/my-skill/scripts/tool.sh
   ```

6. **Submit PR** to this repo!

## Integration Examples

### Cloudflare Workers Sandbox

See [moltworker](https://github.com/cloudflare/moltworker) for a complete example of OpenClaw running in Cloudflare Sandbox with custom skills.

### Local Development

```bash
# Clone skills
git clone https://github.com/expanso-io/expanso-skills.git

# Copy to OpenClaw skills directory
cp -r expanso-skills/openclaw/* ~/.clawdbot/skills/

# Restart OpenClaw
clawdbot gateway restart
```

## Contributing

Have an OpenClaw skill to share? We'd love to add it!

1. Fork this repo
2. Add your skill to `openclaw/your-skill-name/`
3. Follow the structure above
4. Submit a PR

## Support

- **OpenClaw Docs:** https://docs.openclaw.ai/
- **Expanso Skills Issues:** https://github.com/expanso-io/expanso-skills/issues
- **OpenClaw Issues:** https://github.com/openclaw/openclaw/issues
