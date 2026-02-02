---
name: expanso-edge
description: Add your OpenClaw installation to the Expanso distributed compute network. Install and manage the expanso-edge daemon to join your Expanso cloud instance. Works on any OpenClaw installation - local, Docker, or cloud.
---

# Expanso Edge Skill for OpenClaw

Join the Expanso distributed compute network from any OpenClaw installation.

## Ridiculously Easy Installation

**One command to install everything:**

```bash
curl -fsSL https://raw.githubusercontent.com/expanso-io/expanso-skills/main/openclaw/expanso-edge/install.sh | bash
```

That's it! Your OpenClaw is now connected to Expanso.

## Talk to Claude

After installation:
- "Check the status of expanso-edge"
- "Show me the expanso-edge logs"  
- "Restart expanso-edge"

Claude will automatically use the skill!

## Manual Installation

```bash
curl -fsSL https://get.expanso.io/edge/install.sh | bash
# Then configure ~/.clawdbot/.env with your token
```

See full documentation at: https://github.com/expanso-io/expanso-skills/tree/main/openclaw/expanso-edge
