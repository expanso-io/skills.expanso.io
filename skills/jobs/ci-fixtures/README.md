# CI test fixtures

Generate the same synthetic dataset on every run: every field derived from the record number, single-threaded so the file is byte-identical.

**Use it when you are asked to build:** CI test fixtures: the same synthetic dataset on every run.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21` on a **local-mode node only** (6/6 checks). It has not been run through Cloud.

Proved:

- Two runs wrote byte-identical files of 200 records, all valid against schema.json.
- A typo in the config made expanso-edge validate exit 1, usable as a CI gate.

Not proved:

- Any run through Cloud.
- `restart_policy: never` with this spec; it was added after the run and has not been re-run.

## Components

- inputs: `generate`
- outputs: `file`

## Files

- `pipeline.yaml`
- `schema.json`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
mkdir -p /var/tmp/expanso-fixtures
```

## Validate, deploy, confirm

These commands deploy through your Expanso Cloud profile. This job was proven only on a local-mode node, so a Cloud run of it is untested.

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe ci-fixtures
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# identical on every run:
shasum -a 256 /var/tmp/expanso-fixtures/fixtures.jsonl
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- This spec sets `restart_policy: never` at the top level because its input is bounded. With the default policy a failing bounded job was re-run on Cloud every few seconds and read `running`; with `never` it ended `failed` after one execution. The field was added after this job's run and has not been re-run with this spec.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
