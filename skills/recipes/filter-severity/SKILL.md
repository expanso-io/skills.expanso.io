---
name: expanso-filter-severity
description: Filter log messages by severity level
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, log-processing, data-pipeline, recipe]
---

# Filter by Severity

Filter log messages by severity level

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
