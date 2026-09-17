---
name: expanso-csv-to-json
description: Convert CSV files to JSON with schema inference and validation
metadata:
  openclaw:
    requires:
      bins: [expanso]
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
