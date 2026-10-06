---
name: expanso-priority-queues
description: Priority-based message routing to different queues
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
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
./run.sh
```

## Pipeline

The `pipeline.yaml` contains the complete Expanso configuration.

## Requirements

- Expanso Edge and CLI v2.1.21 or newer installed
- Required credentials configured (see pipeline.yaml for env vars)

## Testing

```bash
./test.sh
```

## Related

- [Expanso Documentation](https://docs.expanso.io)
- [More Examples](https://examples.expanso.io)
