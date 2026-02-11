---
name: expanso-encrypt-data
description: Field-level encryption for sensitive data fields
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-security, data-pipeline, recipe]
---

# Encrypt Data

Field-level encryption for sensitive data fields

## Category

`data-security`

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
