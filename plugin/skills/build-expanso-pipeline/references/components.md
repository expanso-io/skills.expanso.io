# Components with working snippets

Every snippet here is taken from a job that ran end to end on expanso-edge
v2.1.21 (`skills/jobs/` in the Expanso Skills repository), or from a published
file that passes `expanso-edge validate` where marked *validates only*. Prefer
these over components you have not seen run. For anything else, check
<https://docs.expanso.io> and let `expanso-edge validate` confirm the fields.

## Inputs

**`generate`**: synthetic or timer-driven messages. A bounded poll, or a
standing poller when `count` is removed and `interval` set (for example `5m`).

```yaml
input:
  generate:
    count: 1
    interval: 1s
    mapping: root = {}
```

**`file`**: read files on the node. Wrap in `broker` with `batching` to read a
bounded file as one batch.

```yaml
input:
  broker:
    inputs:
      - file:
          paths: ["/var/log/app/access.log"]
          scanner:
            lines: {}
    batching:
      count: 100000
      period: 2s
```

**`http_server`**: accept POSTs on the node.

```yaml
input:
  http_server:
    address: "127.0.0.1:8088"
    path: /events
    allowed_verbs: [POST]
```

**`mqtt`**: subscribe to a broker. The topic is in `@mqtt_topic`.

```yaml
input:
  mqtt:
    urls: ["tcp://127.0.0.1:1883"]
    topics: ["plant/+/+/telemetry"]
    client_id: "sensor-telemetry"
    qos: 1
```

**`sql_select`**: read a table once (a batch copy, not change data capture;
`postgres_cdc` did not initialize in testing).

```yaml
input:
  sql_select:
    driver: postgres
    dsn: "postgres://USER:PASS@SRC_HOST:5432/SRC_DB"
    table: customers
    columns: [cust_no, full_name, email]
    suffix: ORDER BY cust_no
```

**`kafka`** *(validates only; never run end to end)*:

```yaml
input:
  kafka:
    addresses: ["${KAFKA_BROKERS:localhost:9092}"]
    topics: ["${INPUT_TOPIC:events}"]
    consumer_group: my-group
```

## Processors

**`mapping`**: Bloblang transform; see `bloblang.md`.

**`http`**: fetch per message. Guard the result before parsing, so a fetch
error is reported as a fetch error:

```yaml
- http:
    url: "https://www.nasa.gov/news-release/feed/"
    verb: GET
    retries: 3
- mapping: |
    root = if errored() {
      throw("feed fetch failed: " + error().or("unknown"))
    } else { content() }
```

**`xml`**: `operator: to_json`.

**`unarchive`**: split one JSON array message into one message per element.

```yaml
- unarchive:
    format: json_array
```

**`dedupe`**: drop repeats by key. Needs a named cache; a `file` cache survives
restarts, a `memory` cache does not.

```yaml
- dedupe:
    cache: seen_events
    key: '${! json("id") }'
# at config level:
cache_resources:
  - label: seen_events
    memory: {}
  # or: file: { directory: "/var/tmp/app/state/seen" }
```

**`switch`** (processor): a **list** of cases; a case without `check` is the
default.

```yaml
- switch:
    - check: this.status >= 400
      processors:
        - mapping: 'root = this.merge({"kind": "error"})'
    - processors:
        - group_by_value:
            value: '${! json("minute") } ${! json("path") }'
        - archive:
            format: json_array
```

**`try` / `catch`** *(validates only)*: each takes a list of processors
directly. `catch` is its own processor, not a field inside a `switch` case.

```yaml
- try:
    - mapping: root = this
- catch:
    - mapping: |
        root = this
        root._error = @error
```

**`branch`** and **`ollama_embeddings`**, **`qdrant`**: used by the RAG job;
read its `pipeline.yaml` at <https://skills.expanso.io/rag-embed-retrieve/>
before using them. The native `qdrant` **output** could not map ids at v2.1.21
and reported success with 0 points; write to Qdrant's REST API with
`http_client` instead.

LLM components (`openai_chat_completion` and similar) require a `tools` field
at v2.1.21; `tools: []` satisfies the validator. They send the credential and
the data to the provider.

## Outputs

**`file`**: one JSON document per line.

```yaml
output:
  file:
    path: "/var/tmp/app/out/result.jsonl"
    codec: lines
```

**`stdout`**: write `stdout: {}`. Do not add `codec: json_object`.

**`http_client`**: POST with retries.

```yaml
output:
  http_client:
    url: "https://RECEIVER_HOST/notify"
    verb: POST
    headers: {Content-Type: application/json}
    retries: 5
    retry_period: 200ms
    max_in_flight: 1
```

**`broker`** with `pattern: fan_out`: deliver every message to every output.

```yaml
output:
  broker:
    pattern: fan_out
    outputs:
      - http_client: { url: "https://A/notify", verb: POST }
      - http_client: { url: "https://B/notify", verb: POST }
```

**`switch`** (output): an **object** with `cases`, unlike the processor form.
`continue: true` also passes the message to later cases.

```yaml
output:
  switch:
    cases:
      - check: errored()
        output:
          file: { path: "/var/tmp/app/rejects.jsonl", codec: lines }
        processors:
          - mapping: 'root = {"error": error(), "raw": content().string()}'
      - check: this.alert
        continue: true
        output:
          file: { path: "/var/tmp/app/alerts.jsonl", codec: lines }
      - output:
          file: { path: "/var/tmp/app/all.jsonl", codec: lines }
```

**`sql_insert`**:

```yaml
sql_insert:
  driver: postgres
  dsn: "postgres://USER:PASS@DST_HOST:5432/DST_DB"
  table: customers
  columns: [id, email]
  args_mapping: root = [this.id, this.email]
  suffix: ON CONFLICT (id) DO NOTHING
  max_in_flight: 4
  batching:
    count: 100
    period: 1s
```

## Not available

- **Iceberg, Delta, Hudi or any lakehouse table output** does not exist.
  Writing Parquet to object storage is not a table commit. Say so rather than
  approximating it.
- Unknown fields the strict validator rejected on specific components in this
  catalog include `max_retries`, `backoff`, `compression`, `storage_class`,
  `time_partitioning`, and `processors` inside a `broker` output. Check the
  component's docs page before adding a field.
