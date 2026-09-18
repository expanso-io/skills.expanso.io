# Data migration engine

Copy a legacy PostgreSQL table into a new schema in batches, reshaping each row, rejecting invalid rows with a reason, idempotently.

**Use it when you are asked to build:** A data migration engine: move a legacy table into a new schema.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21`, on Expanso Cloud (7/7 checks) and on a local-mode node (7/7). The Cloud run was scheduled by label onto one operator-registered node, not a hosted runner, with its dependencies on the same host.

Proved:

- 1,000 synthetic legacy rows became 994 target rows plus 6 rejects, each with its reason.
- The target matched an independent SQL statement of the transform (expected.sql); a second run changed nothing.

Not proved:

- Change data capture. This is a batch copy; a CDC job (postgres_cdc) did not initialize in testing and is unproven.

## Components

- inputs: `sql_select`
- processors: `mapping`
- outputs: `switch`, `sql_insert`, `file`

## Files

- `expected.sql`
- `legacy.sql`
- `modern.sql`
- `pipeline.yaml`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
# PostgreSQL (tested with 14.23). Seed the sample tables,
# then set the two DSNs in pipeline.yaml to them:
createdb legacy && createdb modern
psql -d legacy -f legacy.sql
psql -d modern -f modern.sql
mkdir -p /var/tmp/expanso-migration/out
```

## Validate, deploy, confirm

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe data-migration
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# 994 rows, and 6 rejects each with a reason:
psql -d modern -Atc 'select count(*) from customers'
wc -l /var/tmp/expanso-migration/out/rejects.jsonl
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
