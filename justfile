# Expanso Skills Marketplace

# Default recipe
default:
    @just --list

# Serve the website locally with hot reload
serve:
    npx live-server docs --port=8080

# Build the catalog from skills
build-catalog:
    uv run -s scripts/build-catalog.py

# Look up skills
lookup *ARGS:
    uv run -s scripts/skill-lookup.py {{ARGS}}

# List all skills by category
list-skills:
    uv run -s scripts/skill-lookup.py list

# Search skills
search QUERY:
    uv run -s scripts/skill-lookup.py search {{QUERY}}

# Run skill tests (pass through args)
test-skills *ARGS:
    uv run -s scripts/test-skills.py {{ARGS}}

# Copy catalog and skills to docs (for local testing)
# Uses flat structure: docs/<skill-name>/
prep-docs:
    #!/usr/bin/env bash
    set -euo pipefail
    cp catalog.json docs/
    cp catalog-minimal.json docs/
    echo "Copying skills with flat structure..."
    for dir in skills/*/*/; do
        name=$(basename "$dir")
        cp -r "$dir" "docs/$name" 2>/dev/null || true
    done
    echo "Done. Skills at docs/<name>/"

# Full local dev setup
dev: prep-docs serve
