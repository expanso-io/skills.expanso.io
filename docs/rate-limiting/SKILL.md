---
name: expanso-rate-limiting
description: Rate limit streaming data with backpressure and overflow handling
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-routing, rate-limiting, flow-control, recipe]
---

# Rate Limiting

Apply rate limiting to streaming data with configurable limits, backpressure, and overflow handling.

## Category

`data-routing`

## Quick Start

```bash
export RATE_LIMIT=1000  # messages per second
./run.sh
```
