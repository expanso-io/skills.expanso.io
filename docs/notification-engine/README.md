# Notification engine

Receive events on a webhook, drop duplicates, keep the severities someone must act on, and POST a formatted message with retries.

**Use it when you are asked to build:** A notification engine: send a message when an event matters.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21`, on Expanso Cloud (7/7 checks) and on a local-mode node (7/7). The Cloud run was scheduled by label onto one operator-registered node, not a hosted runner, with its dependencies on the same host.

Proved:

- 8 events in; exactly the 3 critical/high ones delivered, a duplicate delivered once.
- Two 503 responses from the receiver were retried until they succeeded.

Not proved:

- Delivery into Slack, email or any real person. The receiver was a local test sink; the {"text": ...} body matches the Slack incoming-webhook shape, but Slack was not called.

## Components

- inputs: `http_server`
- processors: `dedupe`, `mapping`
- outputs: `http_client`
- caches: `memory`

## Files

- `events.jsonl`
- `pipeline.yaml`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
# Set the http_client url to a receiver you control,
# deploy, then send the sample events:
while IFS= read -r ev; do
  curl -s -X POST -H 'Content-Type: application/json' \
    --data "$ev" http://127.0.0.1:8088/events
done < events.jsonl
```

## Validate, deploy, confirm

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe notification-engine
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# the receiver gets 3 messages: evt-001, evt-003, evt-006
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
