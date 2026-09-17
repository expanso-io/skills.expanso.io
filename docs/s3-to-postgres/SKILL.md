---
name: expanso-s3-to-postgres
description: Load JSON files from S3 into PostgreSQL with upsert support
metadata:
  openclaw:
    requires:
      bins: [expanso]
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
export POSTGRES_DSN=postgres://user:pass@localhost:5432/db
./run.sh
```
