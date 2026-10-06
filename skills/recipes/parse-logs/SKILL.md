---
name: expanso-parse-logs
description: Parse and classify log entries with severity extraction
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
    tags: [expanso, data-transformation, data-pipeline, recipe]
---

# Parse Logs

Parse and classify log entries with severity extraction

## Category

`data-transformation`

## Quick Start

```bash
# Validate and submit the job to Expanso Cloud
./run.sh
```

`run.sh` deploys the job; confirm assignment and output separately using
[the execution checks](../../../README.md#confirm-it-actually-ran).
Configure the profile, connected node, and input delivery as described in
[Quick Start](../../../README.md#quick-start) and
[Providing input](../../../README.md#providing-input).

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
