---
name: expanso-s3-to-postgres
description: Load JSON files from S3 into PostgreSQL with upsert support
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
    tags: [expanso, data-routing, s3, postgres, etl, recipe]
---

# S3 to PostgreSQL

Load JSON files from S3 into PostgreSQL with automatic schema mapping, upserts, and batching.

## Category

`data-routing`

## Quick Start

```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export S3_BUCKET=your-bucket
# Configure POSTGRES_DSN with TLS; see pipeline.yaml
./run.sh
```

`run.sh` deploys the job; confirm assignment and output separately using
[the execution checks](../../../README.md#confirm-it-actually-ran).
Configure the profile, connected node, and input delivery as described in
[Quick Start](../../../README.md#quick-start) and
[Providing input](../../../README.md#providing-input).
