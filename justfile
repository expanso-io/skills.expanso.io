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
    uv run -s scripts/skill-lookup.py {{ ARGS }}

# List all skills by category
list-skills:
    uv run -s scripts/skill-lookup.py list

# Search skills
search QUERY:
    uv run -s scripts/skill-lookup.py search {{ QUERY }}

# Run skill tests (pass through args)
test-skills *ARGS:
    uv run -s scripts/test-skills.py {{ ARGS }}

# Stage the Pages publication for local testing
prep-docs:
    uv run -s scripts/stage-pages.py

# Full local dev setup
dev: prep-docs serve
