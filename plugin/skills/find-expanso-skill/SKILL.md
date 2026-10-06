---
name: find-expanso-skill
description: Find an existing Expanso job or pipeline recipe before writing one from scratch, and report honestly how far it has been proven. Use when the user asks to build a data pipeline, ETL job, log reduction, webhook fan-out, notification, RSS ingestion, RAG embedding, database migration, MQTT telemetry or similar with Expanso, asks "is there an Expanso skill for X", or browses skills.expanso.io.
---

# Find an Expanso skill

The Expanso Skills catalog at <https://skills.expanso.io> holds about 200
published pipelines. They are **not** equally trustworthy. Always check a
candidate's proof level before recommending it, and say that level to the user.

## Step 1: check the proven jobs first

Eight complete jobs were run end to end and their output counted at the
destination. Read `references/proven-jobs.md` and match the request against
them before looking anywhere else. If one fits, recommend it, say where it was
proven (Cloud and local, or local only), and list its "not proved" items.

## Step 2: search the catalog

If no proven job fits, search the catalog:

- `https://skills.expanso.io/catalog.json`: every skill, keyed by name, with
  `description`, `category`, `inputs`, `outputs`, `credentials`, `backends`,
  `tags`, and a `dependencies` block for audited skills.
- `https://skills.expanso.io/catalog-minimal.json`: names by category only.

Fetch with whatever tool is available (web fetch, or `curl -fsSL` in a shell).
Match on name, description and tags. Categories: `jobs`, `recipes`, `ai`,
`connectors`, `security`, `transforms`, `utilities`, `workflows`.

## Step 3: check readiness for each candidate

Fetch `https://skills.expanso.io/validation-report.json` and look the skill up
under `skills.<name>` (recipes whose name collides with another skill appear as
`recipes/<name>`). Report:

| `readiness` | What to tell the user |
|---|---|
| `validated-not-executed` | Every variant passes the strict validator. See the [readiness contract](../../../README.md#catalog-api) for execution proof limits. |
| `invalid-does-not-validate` | At least one variant is **rejected** by `expanso-edge validate`. Show the `variants.<v>.error` text. Do not deploy as is; fix it first with the `validate-expanso-pipeline` skill. |
| `verified-executed` | Reserved. No skill currently holds it. Never claim it. |

`job_spec_accepted: true` only means the file is a well-formed job spec. It is
**not** evidence that the pipeline is valid. Do not present it as such.

Check `https://skills.expanso.io/example-conformance.json` and any dated skill
proof for execution evidence and its scope.

## Step 4: pick the right file

A skill directory is published at `https://skills.expanso.io/<name>/`.

- Jobs and recipes: `pipeline.yaml`.
- Other skills: `pipeline-cli.yaml` (reads `stdin`), `pipeline-mcp.yaml`
  (`http_server` in, `sync_response` out), and for `json-pretty` only,
  `pipeline-cloud.yaml`.

A `stdin` input cannot receive anything once the job runs on a remote node.
For a Cloud-scheduled job, recommend the `-mcp` variant or rewrite the input
(`file`, `http_server`, `generate`, a queue or object store). The
`build-expanso-pipeline` skill covers that rewrite.

## Step 5: state what leaves the host

For each recommendation, say which services the pipeline talks to. If the
catalog entry has a `dependencies` block, quote `third_party_apis`,
`credentials_transmitted` and `data_leaving_host`. Otherwise read the
pipeline's components: any third-party API component (for example
`openai_chat_completion`, an `http` call to a SaaS API) sends its credential and
the data to that provider. Never describe a skill as "offline" or "keeps
credentials local" unless its `dependencies.offline_capable` is `true`.

## Output

Give a short ranked list: skill name, one line on what it does, proof level,
what it sends where, and the file to start from. If nothing fits, say so and
offer to write one with the `build-expanso-pipeline` skill.
