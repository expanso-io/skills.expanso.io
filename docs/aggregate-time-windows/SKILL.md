---
name: expanso-aggregate-time-windows
description: Time-window aggregations for metrics and analytics
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-transformation, data-pipeline, recipe]
---

# Aggregate Time Windows

Time-window aggregations for metrics and analytics

## Category

`data-transformation`

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
