# Log reduction

Parse access logs, drop health-check noise, keep every 4xx/5xx as its own event and roll up successes per minute, route and status.

**Use it when you are asked to build:** Log reduction: cut log volume but keep every error.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21` on a **local-mode node only** (5/5 checks). It has not been run through Cloud.

Proved:

- 5,000 synthetic lines became 330 events: all 250 errors kept individually and 80 per-minute rollups matching an independent recount.
- 92.7% fewer bytes on that synthetic log only; not a benchmark for real logs.

Not proved:

- Any run through Cloud; streaming (unbounded) logs. The whole bounded file is read as one batch.

## Components

- inputs: `broker`, `file`
- processors: `mapping`, `switch`, `group_by_value`, `archive`
- outputs: `file`

## Files

- `make_log.py`
- `pipeline.yaml`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
# The sample log (or point the file input at a real one):
uv run python make_log.py /var/log/app/access.log
mkdir -p /var/tmp/expanso-logs/out
```

## Validate, deploy, confirm

These commands deploy through your Expanso Cloud profile. This job was proven only on a local-mode node, so a Cloud run of it is untested.

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe log-reduction
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# 330 lines for the sample log:
wc -l /var/tmp/expanso-logs/out/reduced.jsonl
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
