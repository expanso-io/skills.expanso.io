#!/bin/bash
# Expanso Edge Skill Installer for OpenClaw
# This script makes it ridiculously easy to add expanso-edge to any OpenClaw installation

set -e

echo "🚀 Expanso Edge Skill Installer for OpenClaw"
echo ""

# Detect OpenClaw installation directory
if [ -d "$HOME/.clawdbot" ]; then
    OPENCLAW_DIR="$HOME/.clawdbot"
elif [ -d "/root/.clawdbot" ]; then
    OPENCLAW_DIR="/root/.clawdbot"
else
    echo "⚠️  OpenClaw installation not found at $HOME/.clawdbot or /root/.clawdbot"
    read -p "Enter your OpenClaw directory path: " OPENCLAW_DIR
fi

SKILLS_DIR="${OPENCLAW_DIR}/../clawd/skills"
if [ ! -d "$(dirname "$SKILLS_DIR")" ]; then
    SKILLS_DIR="$HOME/clawd/skills"
fi

echo "📁 OpenClaw directory: $OPENCLAW_DIR"
echo "📁 Skills directory: $SKILLS_DIR"
echo ""

# Create skills directory if it doesn't exist
mkdir -p "$SKILLS_DIR"

# Check if expanso-edge is already installed
if command -v expanso-edge &> /dev/null; then
    echo "✓ expanso-edge is already installed ($(expanso-edge --version 2>&1 | head -1))"
else
    echo "📦 Installing expanso-edge..."
    if curl -fsSL https://get.expanso.io/edge/install.sh | bash; then
        echo "✓ expanso-edge installed successfully"
    else
        echo "❌ Failed to install expanso-edge"
        exit 1
    fi
fi

echo ""

# Download the skill
SKILL_DIR="$SKILLS_DIR/expanso-edge"
echo "📥 Downloading expanso-edge skill..."

if [ -d "$SKILL_DIR" ]; then
    echo "⚠️  Skill already exists at $SKILL_DIR"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    rm -rf "$SKILL_DIR"
fi

mkdir -p "$SKILL_DIR"

# Clone just the skill directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"
git clone --depth 1 --filter=blob:none --sparse https://github.com/expanso-io/expanso-skills.git
cd expanso-skills
git sparse-checkout set openclaw/expanso-edge
cp -r openclaw/expanso-edge/* "$SKILL_DIR/"
cd ~
rm -rf "$TMP_DIR"

echo "✓ Skill downloaded to $SKILL_DIR"
echo ""

# Configure bootstrap credentials
echo "🔑 Configuration"
echo ""

if [ -f "$OPENCLAW_DIR/.env" ]; then
    source "$OPENCLAW_DIR/.env"
fi

if [ -z "$EXPANSO_EDGE_BOOTSTRAP_TOKEN" ]; then
    echo "Enter your Expanso bootstrap token:"
    read -r EXPANSO_EDGE_BOOTSTRAP_TOKEN
    echo "EXPANSO_EDGE_BOOTSTRAP_TOKEN=$EXPANSO_EDGE_BOOTSTRAP_TOKEN" >> "$OPENCLAW_DIR/.env"
fi

if [ -z "$EXPANSO_EDGE_BOOTSTRAP_URL" ]; then
    read -p "Enter bootstrap URL [https://start.cloud.expanso.io]: " EXPANSO_EDGE_BOOTSTRAP_URL
    EXPANSO_EDGE_BOOTSTRAP_URL=${EXPANSO_EDGE_BOOTSTRAP_URL:-https://start.cloud.expanso.io}
    echo "EXPANSO_EDGE_BOOTSTRAP_URL=$EXPANSO_EDGE_BOOTSTRAP_URL" >> "$OPENCLAW_DIR/.env"
fi

echo ""
echo "✓ Configuration saved to $OPENCLAW_DIR/.env"
echo ""

# Start expanso-edge
echo "🚀 Starting expanso-edge..."
export EXPANSO_EDGE_BOOTSTRAP_TOKEN
export EXPANSO_EDGE_BOOTSTRAP_URL

if pgrep -f "expanso-edge" > /dev/null; then
    echo "⚠️  expanso-edge is already running"
else
    nohup expanso-edge > /tmp/expanso-edge.log 2>&1 &
    sleep 2

    if pgrep -f "expanso-edge" > /dev/null; then
        PID=$(pgrep -f "expanso-edge")
        echo "✓ expanso-edge started successfully (PID: $PID)"
        echo "  Logs: /tmp/expanso-edge.log"
    else
        echo "❌ Failed to start expanso-edge"
        echo "  Check logs: tail -f /tmp/expanso-edge.log"
        exit 1
    fi
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Restart OpenClaw: clawdbot gateway restart"
echo "  2. Ask Claude: 'Check the status of expanso-edge'"
echo "  3. View logs: bash $SKILL_DIR/scripts/logs.sh"
echo ""
echo "The expanso-edge daemon is now running and connected to:"
echo "  $EXPANSO_EDGE_BOOTSTRAP_URL"
echo ""
echo "Happy computing! 🎉"
