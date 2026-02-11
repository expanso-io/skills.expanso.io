---
name: expanso-http-webhook-ingestion
description: Ingest webhooks via HTTP and forward to Kafka with validation
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-routing, http, kafka, webhook, recipe]
---

# HTTP Webhook Ingestion

Accept HTTP webhooks and forward to Kafka with request validation, authentication, and rate limiting.

## Category

`data-routing`

## Quick Start

```bash
export KAFKA_BROKERS=localhost:9092
./run.sh
# Send a webhook: curl -X POST http://localhost:8080/webhook -d '{"event":"test"}'
```

## Requirements

- Expanso Edge installed (`clawhub install expanso`)
- Kafka broker for output
