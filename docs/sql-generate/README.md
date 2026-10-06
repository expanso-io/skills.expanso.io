# sql-generate

Generate SQL queries from natural language descriptions.

## Overview

This skill converts plain English descriptions into valid SQL queries. Supports multiple SQL dialects and can use table schema for context.

## Usage

### CLI Mode

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)). `pipeline-mcp.yaml` serves HTTP on the node that executes it, not on your machine.

```bash
expanso-edge validate pipeline-cli.yaml
```

### MCP Mode

```bash
expanso-edge validate pipeline-mcp.yaml
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
