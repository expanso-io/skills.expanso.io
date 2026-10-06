---
name: expanso-dead-letter-queue
description: Handle failed messages with dead-letter queue pattern and retry logic
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
    tags: [expanso, data-routing, dlq, error-handling, recipe]
---

# Dead Letter Queue

Route failed messages to a dead-letter queue with error metadata, automatic retries, and alerting.

## Category

`data-routing`

## Quick Start

```bash
# Configure Kafka TLS/SASL on the executing node; see pipeline.yaml
./run.sh
```

`run.sh` deploys the job; confirm assignment and output separately using
[the execution checks](../../../README.md#confirm-it-actually-ran).
Configure the profile, connected node, and input delivery as described in
[Quick Start](../../../README.md#quick-start) and
[Providing input](../../../README.md#providing-input).

## Features

- Automatic retry with exponential backoff
- Error categorization
- Metadata enrichment for debugging
- DLQ topic for manual investigation
