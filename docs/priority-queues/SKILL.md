---
name: expanso-priority-queues
description: Priority-based message routing to different queues
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-routing, data-pipeline, recipe]
---

# Priority Queues

Priority-based message routing to different queues

## Category

`data-routing`

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
