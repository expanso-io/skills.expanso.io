#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${EXPANSO_BIN_DIR:-$HOME/.expanso/bin}"
FORCE="${1:-}"

mkdir -p "$BIN_DIR"

echo "🔧 Installing Expanso components..."
echo "   Binary directory: $BIN_DIR"

# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) echo "❌ Unsupported architecture: $ARCH"; exit 1 ;;
esac

PLATFORM="${OS}_${ARCH}"
echo "   Platform: $PLATFORM"

# Install expanso-edge
install_edge() {
    if [[ -x "$BIN_DIR/expanso-edge" ]] && [[ "$FORCE" != "--force" ]]; then
        echo "✅ expanso-edge already installed"
        return 0
    fi
    
    echo "⬇️  Installing expanso-edge..."
    
    # Try official installer first
    if curl -fsSL https://get.expanso.io/edge/install.sh -o /tmp/install-edge.sh 2>/dev/null; then
        if EXPANSO_INSTALL_DIR="$BIN_DIR" bash /tmp/install-edge.sh 2>/dev/null; then
            echo "✅ expanso-edge installed via official script"
            return 0
        fi
    fi
    
    # Fallback: direct download
    echo "   Official installer failed, trying direct download..."
    EDGE_URL="https://github.com/expanso-io/expanso/releases/latest/download/expanso-edge_${PLATFORM}"
    if curl -fsSL "$EDGE_URL" -o "$BIN_DIR/expanso-edge" 2>/dev/null; then
        chmod +x "$BIN_DIR/expanso-edge"
        echo "✅ expanso-edge installed via direct download"
        return 0
    fi
    
    echo "❌ Failed to install expanso-edge"
    echo "   Please install manually from https://docs.expanso.io/getting-started/installation/"
    return 1
}

# Install expanso-cli
install_cli() {
    if [[ -x "$BIN_DIR/expanso-cli" ]] && [[ "$FORCE" != "--force" ]]; then
        echo "✅ expanso-cli already installed"
        return 0
    fi
    
    echo "⬇️  Installing expanso-cli..."
    
    # Try official installer first
    if curl -fsSL https://get.expanso.io/cli/install.sh -o /tmp/install-cli.sh 2>/dev/null; then
        if EXPANSO_INSTALL_DIR="$BIN_DIR" bash /tmp/install-cli.sh 2>/dev/null; then
            echo "✅ expanso-cli installed via official script"
            return 0
        fi
    fi
    
    # Fallback: direct download
    echo "   Official installer failed, trying direct download..."
    CLI_URL="https://github.com/expanso-io/expanso/releases/latest/download/expanso-cli_${PLATFORM}"
    if curl -fsSL "$CLI_URL" -o "$BIN_DIR/expanso-cli" 2>/dev/null; then
        chmod +x "$BIN_DIR/expanso-cli"
        echo "✅ expanso-cli installed via direct download"
        return 0
    fi
    
    echo "❌ Failed to install expanso-cli"
    echo "   Please install manually from https://docs.expanso.io/getting-started/installation/"
    return 1
}

# Add to PATH if not already
setup_path() {
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo ""
        echo "📝 Add to your shell profile:"
        echo "   export PATH=\"\$PATH:$BIN_DIR\""
    fi
}

# Run installation
install_edge
install_cli
setup_path

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Get a bootstrap token from https://cloud.expanso.io"
echo "  2. Run: ./start.sh --token YOUR_TOKEN"
echo "  3. Deploy pipelines from the cloud dashboard"
