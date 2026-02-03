#!/usr/bin/env bash
# Expanso Tools Installer
# Usage: curl -fsSL https://skills.expanso.io/install.sh | bash
#
# Installs:
# - Expanso Edge (local pipeline runtime)
# - Expanso CLI (deploy to Expanso Cloud)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}==>${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}Expanso Tools Installer${NC}"
echo ""

# Install Expanso Edge
if command -v expanso-edge &> /dev/null; then
    success "Expanso Edge already installed"
else
    info "Installing Expanso Edge..."
    if curl -fsSL https://get.expanso.io/edge/install.sh | bash; then
        success "Expanso Edge installed"
    else
        warn "Could not install automatically"
        echo "    Manual install: https://docs.expanso.io/edge/install"
    fi
fi

# Install Expanso CLI
if command -v expanso-cli &> /dev/null; then
    success "Expanso CLI already installed"
else
    info "Installing Expanso CLI..."
    if curl -fsSL https://get.expanso.io/cli/install.sh | sh; then
        success "Expanso CLI installed"
    else
        warn "Could not install automatically"
        echo "    Manual install: https://docs.expanso.io/cli/install"
    fi
fi

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Browse skills: https://skills.expanso.io"
echo ""
echo "  2. Deploy a skill:"
echo "     export EXPANSO_CLI_ENDPOINT=\"https://your-instance.us1.cloud.expanso.io\""
echo "     expanso-cli job deploy https://skills.expanso.io/text-summarize/pipeline-cli.yaml"
echo ""
echo "  3. Or use Expanso Cloud UI: https://cloud.expanso.io"
echo ""
