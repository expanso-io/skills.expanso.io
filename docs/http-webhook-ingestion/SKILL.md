---
name: expanso-http-webhook-ingestion
description: Ingest webhooks via HTTP and forward to Kafka with validation
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
    tags: [expanso, data-routing, http, kafka, webhook, recipe]
---

# HTTP Webhook Ingestion

Accept HTTP webhooks and forward to Kafka with request validation, authentication, and rate limiting.

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

Send requests to `/webhook` on the executing node. The signature mapping in
[pipeline.yaml](pipeline.yaml) defines the required request header and digest.

## Requirements

- Expanso Edge and CLI v2.1.21 or newer installed
- Kafka broker for output
