---
name: expanso-kafka-to-s3
description: Stream Kafka topics to S3 with partitioning and batching
metadata:
  openclaw:
    requires:
      bins: [expanso]
    tags: [expanso, data-routing, kafka, s3, recipe]
---

# Kafka to S3

Stream data from Kafka topics to S3 buckets with intelligent partitioning, batching, and compression.

## Category

`data-routing`

## Quick Start

```bash
# Configure environment
export KAFKA_BROKERS=localhost:9092
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export S3_BUCKET=your-bucket

# Run the pipeline
./run.sh
```

## Pipeline

The `pipeline.yaml` streams from Kafka to S3 with:
- Consumer group management
- Time-based partitioning (hourly/daily)
- Gzip compression
- Batching for efficient S3 writes

## Requirements

- Expanso Edge installed (`clawhub install expanso`)
- Kafka broker access
- AWS credentials with S3 write permissions

## Related

- [Expanso Documentation](https://docs.expanso.io)
- [More Examples](https://examples.expanso.io)
