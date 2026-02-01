# sql-generate

Generate SQL queries from natural language descriptions.

## Overview

This skill converts plain English descriptions into valid SQL queries. Supports multiple SQL dialects and can use table schema for context.

## Usage

### CLI Mode

```bash
export OPENAI_API_KEY=sk-...

echo "Get all users who signed up last month" | expanso-edge run pipeline-cli.yaml

# Specify dialect
DIALECT=mysql echo "Count orders by status" | expanso-edge run pipeline-cli.yaml

# With schema context
SCHEMA="users(id, name, email, created_at)" \
  echo "Find users with gmail addresses" | expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Get all users who signed up last month",
    "dialect": "postgresql",
    "schema": "users(id, name, email, created_at)"
  }'
```

## Output

```json
{
  "sql": "SELECT u.id, u.name, u.email\nFROM users u\nWHERE u.created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')\n  AND u.created_at < DATE_TRUNC('month', CURRENT_DATE);",
  "explanation": "Selects users whose created_at falls within last month using PostgreSQL date functions",
  "dialect": "postgresql",
  "metadata": {...}
}
```

## Supported Dialects

- `postgresql` (default)
- `mysql`
- `sqlite`
- `mssql`

## Use Cases

- Quick query generation
- Learning SQL
- Data exploration
- Report building
