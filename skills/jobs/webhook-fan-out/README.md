# Webhook fan-out

Accept events on one webhook and deliver every event to several endpoints, each retrying independently.

**Use it when you are asked to build:** A webhook fan-out: deliver every event to several endpoints.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21` on a **local-mode node only** (6/6 checks). It has not been run through Cloud.

Proved:

- 10 events in; each of 3 receivers got all 10 exactly once, including one that answered 503 twice.

Not proved:

- Any run through Cloud; real third-party receivers (receivers were local test sinks).

## Components

- inputs: `http_server`
- processors: `mapping`
- outputs: `broker`, `http_client`

## Files

- `events.jsonl`
- `pipeline.yaml`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
# Set the three http_client urls to receivers you control,
# deploy, then post the sample events:
while IFS= read -r ev; do
  curl -s -X POST -H 'Content-Type: application/json' \
    --data "$ev" http://127.0.0.1:8089/webhook
done < events.jsonl
```

## Validate, deploy, confirm

These commands deploy through your Expanso Cloud profile. This job was proven only on a local-mode node, so a Cloud run of it is untested.

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe webhook-fan-out
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# each receiver gets order-001 .. order-010 once
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
