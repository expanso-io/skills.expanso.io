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
echo -e "${GREEN}Binaries installed.${NC}"
echo ""
echo "Verify what you got:"
echo "  expanso-edge version"
echo "  expanso-cli version"
echo ""
echo "Note: these tools take a 'version' subcommand, not a '--version' flag."
echo ""
echo "----------------------------------------------------------------"
echo "Next steps"
echo "----------------------------------------------------------------"
echo ""
echo "Installing the binaries is not enough to run a skill. A skill is a"
echo "job that Expanso Cloud schedules onto an edge node you own, so you"
echo "need a control-plane profile AND at least one connected node."
echo ""
echo "  1. Browse skills:"
echo "     https://skills.expanso.io"
echo ""
echo "  2. Connect the CLI to your Expanso Cloud control plane."
echo "     Get the endpoint and an API key from https://cloud.expanso.io"
echo ""
echo "     expanso-cli profile save my-network \\"
echo "       --endpoint https://YOUR-NETWORK.us2.cloud.expanso.io:9010 \\"
echo "       --api-key exp_ak_YOUR_KEY --select"
echo ""
echo "  3. Connect at least one edge node. Get a bootstrap token from"
echo "     Expanso Cloud, then on the machine that should run the work:"
echo ""
echo "     expanso-edge bootstrap --token YOUR_BOOTSTRAP_TOKEN"
echo "     expanso-edge run"
echo ""
echo "     Confirm the control plane can see it (state must be 'connected'):"
echo "     expanso-cli node list"
echo ""
echo "     With no connected node, a deploy still succeeds but the job is"
echo "     only stored -- the scheduler has nothing to assign it to."
echo ""
echo "  4. Download the skill, then deploy the local file."
echo "     'expanso-cli job deploy' reads a FILE path or '-' for stdin."
echo "     It does NOT fetch an HTTPS URL."
echo ""
echo "     Start with json-pretty's Cloud variant: no credentials, no egress,"
echo "     and it generates its own input so a remote node can run it."
echo ""
echo "     curl -fsSL -O https://skills.expanso.io/json-pretty/pipeline-cloud.yaml"
echo "     expanso-cli job validate pipeline-cloud.yaml --offline"
echo "     expanso-cli job deploy pipeline-cloud.yaml"
echo ""
echo "     Or pipe it straight in:"
echo "     curl -fsSL https://skills.expanso.io/json-pretty/pipeline-cloud.yaml \\"
echo "       | expanso-cli job deploy -"
echo ""
echo "     Downloading first is recommended: you get to read the pipeline,"
echo "     its credential requirements, and where it sends your data."
echo ""
echo "     Most pipeline-cli.yaml files read stdin. A Cloud-scheduled node has"
echo "     no connection to your terminal, so stdin cannot deliver your input"
echo "     there. Use a pipeline-cloud.yaml variant, or an input the node can"
echo "     reach itself (file, http_server, generate, queue, object store)."
echo ""
echo "  5. Confirm it actually ran. A successful deploy is not a run:"
echo ""
echo "     expanso-cli job describe json-pretty-cloud"
echo "     expanso-cli execution list --job-id <job-id>"
echo "     expanso-cli job logs json-pretty-cloud"
echo ""
echo "  6. Or use the Expanso Cloud UI: https://cloud.expanso.io"
echo ""
echo "Before you deploy any skill, check the credentials it needs and the"
echo "data it sends off the host. Only skills with a dependencies block in"
echo "skill.yaml have been audited; for others, inspect the pipeline's"
echo "components. Many skills call a third-party API; those are not offline"
echo "and not local-only."
echo ""
echo "Machine-readable per-skill validation status:"
echo "  https://skills.expanso.io/validation-report.json"
echo "Agent-oriented summary of these contracts:"
echo "  https://skills.expanso.io/llms.txt"
echo ""
