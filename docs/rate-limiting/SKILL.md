---
name: expanso-rate-limiting
description: Rate limit streaming data with backpressure and overflow handling
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
    tags: [expanso, data-routing, rate-limiting, flow-control, recipe]
---

# Rate Limiting

Apply rate limiting to streaming data with configurable limits, backpressure, and overflow handling.

## Category

`data-routing`

## Quick Start

```bash
# Set the output-rate resource count in pipeline.yaml
./run.sh
```

`run.sh` deploys the job; confirm assignment and output separately using
[the execution checks](../../../README.md#confirm-it-actually-ran).
Configure the profile, connected node, and input delivery as described in
[Quick Start](../../../README.md#quick-start) and
[Providing input](../../../README.md#providing-input).
