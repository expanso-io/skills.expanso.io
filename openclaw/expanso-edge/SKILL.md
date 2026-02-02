---
name: expanso-edge
description: Interact with the expanso-edge daemon running in the container. Check status, view logs, manage edge compute tasks, and interact with the Expanso network. The expanso-edge daemon connects to the Expanso distributed compute platform.
---

# Expanso Edge

Control and monitor the expanso-edge daemon running in the Cloudflare Sandbox container.

## Prerequisites

- `EXPANSO_EDGE_BOOTSTRAP_TOKEN` environment variable set
- `EXPANSO_EDGE_BOOTSTRAP_URL` environment variable set
- expanso-edge daemon running in the container

## Quick Start

### Check Status
```bash
bash /root/clawd/skills/expanso-edge/scripts/status.sh
```

### View Logs
```bash
bash /root/clawd/skills/expanso-edge/scripts/logs.sh
```

### Get Edge Info
```bash
bash /root/clawd/skills/expanso-edge/scripts/info.sh
```

## Available Commands

| Command | Purpose |
|---------|---------|
| status.sh | Check if expanso-edge is running and get PID |
| logs.sh | View recent expanso-edge logs |
| info.sh | Get edge node information and configuration |
| restart.sh | Restart the expanso-edge daemon |

## Environment Variables

- `EXPANSO_EDGE_BOOTSTRAP_TOKEN` - Authentication token for Expanso network
- `EXPANSO_EDGE_BOOTSTRAP_URL` - Bootstrap server URL (default: https://start.cloud.expanso.io)

## Troubleshooting

- **Daemon not running**: Check logs with `logs.sh` and verify environment variables are set
- **Connection issues**: Verify `EXPANSO_EDGE_BOOTSTRAP_URL` is accessible
- **Authentication errors**: Check that `EXPANSO_EDGE_BOOTSTRAP_TOKEN` is valid

## Integration with OpenClaw

The expanso-edge daemon runs automatically when the container starts. Use these scripts to:
- Monitor edge compute status
- Debug connectivity issues
- Restart the daemon if needed
- Get information about the edge node
