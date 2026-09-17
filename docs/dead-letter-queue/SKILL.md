---
name: expanso-dead-letter-queue
description: Handle failed messages with dead-letter queue pattern and retry logic
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-routing, dlq, error-handling, recipe]
---

# Dead Letter Queue

Route failed messages to a dead-letter queue with error metadata, automatic retries, and alerting.

## Category

`data-routing`

## Quick Start

```bash
export KAFKA_BROKERS=localhost:9092
./run.sh
```

## Features

- Automatic retry with exponential backoff
- Error categorization
- Metadata enrichment for debugging
- DLQ topic for manual investigation
