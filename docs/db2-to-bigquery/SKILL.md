---
name: expanso-db2-to-bigquery
description: Migrate financial transactions from DB2 to BigQuery
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, enterprise-migration, data-pipeline, recipe]
---

# DB2 to BigQuery

Migrate financial transactions from DB2 to BigQuery

## Category

`enterprise-migration`

## Quick Start

```bash
# Run the pipeline with sample data
./run.sh

# Or run directly with Expanso CLI
expanso run -c pipeline.yaml
```

## Pipeline

The `pipeline.yaml` contains the complete Expanso configuration.

## Requirements

- Expanso Edge installed (`clawhub install expanso`)
- Required credentials configured (see pipeline.yaml for env vars)

## Testing

```bash
./test.sh
```

## Related

- [Expanso Documentation](https://docs.expanso.io)
- [More Examples](https://examples.expanso.io)
