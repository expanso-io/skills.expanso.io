---
name: expanso
description: Connect your OpenClaw to Expanso Cloud. Install expanso-edge + expanso-cli, run data pipelines locally with cloud visibility, control, and traceability.
homepage: https://expanso.io
emoji: "⚡"
version: 1.0.0
author: Expanso
---

# Expanso for OpenClaw

Run enterprise data pipelines locally while maintaining cloud visibility and control.

## What This Skill Does

- **Installs** both `expanso-edge` daemon and `expanso-cli`
- **Connects** to your Expanso Cloud account
- **Runs** pipelines deployed from the cloud
- **Reports** metrics and status back to cloud

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/expanso-io/expanso-skills/main/openclaw/expanso/install.sh | bash
```

## Setup

### 1. Create Expanso Cloud Account

Go to [cloud.expanso.io](https://cloud.expanso.io) and create a free account.

### 2. Get Bootstrap Token

1. Create a network in Expanso Cloud
2. Click "Add Node"
3. Copy the bootstrap token

### 3. Start the Daemon

```bash
./start.sh --token YOUR_BOOTSTRAP_TOKEN
```

## Natural Language Commands

After installation, just ask OpenClaw:

- "What's my Expanso status?"
- "Start Expanso"
- "Stop Expanso"
- "Show Expanso logs"
- "List my Expanso networks"

## Shell Scripts

| Script | Purpose |
|--------|---------|
| `./install.sh` | Install edge + CLI binaries |
| `./start.sh --token TOKEN` | Start edge daemon |
| `./stop.sh` | Stop daemon |
| `./status.sh` | Check everything |
| `./logs.sh [-f]` | View logs |
| `./uninstall.sh` | Remove binaries |
| `./test.sh` | Run test suite |

## Architecture

```
┌─────────────────┐
│  Expanso Cloud  │ ◄── Build & deploy pipelines here
│ cloud.expanso.io│
└────────┬────────┘
         │ Bootstrap token
         ▼
┌─────────────────┐
│  expanso-edge   │ ◄── Daemon runs on your machine
│   (daemon)      │     Executes pipelines locally
└────────┬────────┘
         │
┌────────┴────────┐
│  expanso-cli    │ ◄── Optional: CI/CD, automation
│   (optional)    │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   Your Data     │ ◄── Never leaves your machine
└─────────────────┘
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `EXPANSO_EDGE_BOOTSTRAP_TOKEN` | Yes | Token from Expanso Cloud |
| `EXPANSO_BIN_DIR` | No | Binary location (default: ~/.expanso/bin) |
| `EXPANSO_LOG_DIR` | No | Log location (default: ~/.expanso/logs) |

## Configuration File

Store your token in `~/.expanso/config`:
```bash
EXPANSO_EDGE_BOOTSTRAP_TOKEN=your-token-here
```

## Troubleshooting

### "Not connected to cloud"
```bash
./status.sh           # Check status
./logs.sh | grep error # Look for errors
```

### "Binary not found"
```bash
./install.sh --force  # Reinstall binaries
```

### "Daemon won't start"
```bash
./stop.sh             # Ensure it's stopped
./start.sh --token YOUR_TOKEN  # Start with token
./logs.sh             # Check logs
```

## Resources

- [Expanso Documentation](https://docs.expanso.io)
- [Expanso Cloud](https://cloud.expanso.io)
- [Pipeline Examples](https://examples.expanso.io)
