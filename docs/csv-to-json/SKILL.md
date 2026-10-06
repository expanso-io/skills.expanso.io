---
name: expanso-csv-to-json
description: Convert CSV files to JSON with schema inference and validation
metadata:
  openclaw:
    requires:
      bins: [expanso-edge, expanso-cli]
    tags: [expanso, data-transformation, csv, json, recipe]
---

# CSV to JSON

Convert CSV files to JSON format with automatic schema inference, type coercion, and header mapping.

## Category

`data-transformation`

## Quick Start

```bash
export INPUT_DIR=/path/to/csv/files
export OUTPUT_DIR=/path/to/json/output
./run.sh
```

`run.sh` deploys the job; confirm assignment and output separately using
[the execution checks](../../../README.md#confirm-it-actually-ran).
Configure the profile, connected node, and input delivery as described in
[Quick Start](../../../README.md#quick-start) and
[Providing input](../../../README.md#providing-input).
