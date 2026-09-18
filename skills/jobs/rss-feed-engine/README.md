# RSS feed engine

Poll an RSS feed, emit one normalized JSON record per item, never emit the same GUID twice (even across restarts).

**Use it when you are asked to build:** An RSS or news feed engine: poll feeds, parse items, deduplicate, store.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21`, on Expanso Cloud (14/14 checks) and on a local-mode node (14/14). The Cloud run was scheduled by label onto one operator-registered node, not a hosted runner, with its dependencies on the same host.

Proved:

- Live NASA (10 items) and BBC Technology (21 items, GMT dates) feeds each matched an independent fetch of the same feed.
- A duplicate GUID was emitted once; a restarted job emitted 0 items it had already seen (file-backed dedupe cache).

Not proved:

- Feeds other than RSS 2.0 (Atom was not tested).

## Components

- inputs: `generate`
- processors: `http`, `xml`, `mapping`, `unarchive`, `dedupe`
- outputs: `file`
- caches: `file`

## Files

- `pipeline.yaml`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
mkdir -p /var/tmp/expanso-rss/state/seen-guids
mkdir -p /var/tmp/expanso-rss/out
```

## Validate, deploy, confirm

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe rss-feed-engine
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
wc -l /var/tmp/expanso-rss/out/rss-items.jsonl
head -1 /var/tmp/expanso-rss/out/rss-items.jsonl
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
