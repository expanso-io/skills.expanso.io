---
name: expanso-enrich-export
description: Enrich logs with metadata and export to storage
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, log-processing, data-pipeline, recipe]
---

# Enrich and Export

Enrich logs with metadata and export to storage

## Category

`log-processing`

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
