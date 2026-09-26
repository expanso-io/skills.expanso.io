---
name: build-expanso-pipeline
description: Write or adapt an Expanso pipeline job spec (YAML with type pipeline and a config block of input, Bloblang mapping processors and output). Use when the user asks to create, write, modify or convert an Expanso pipeline or job, write Bloblang for Expanso, move processing to the edge, filter, parse, dedupe, route or fan out data with Expanso, or turn a stdin skill into one a Cloud-scheduled node can run.
---

# Build an Expanso pipeline

An Expanso pipeline is a **job spec**: a YAML file you submit to the Expanso
Cloud control plane, which schedules it onto one of the user's edge nodes. The
node runs it next to the data. Design for that: filter, reduce and redact on the
node, and send only what the destination needs.

## Before you write anything

1. Check for an existing job or recipe with the `find-expanso-skill` skill. A
   proven job adapted beats a new file.
2. Pin down, asking only for what you can't infer:
   - **Source**: where the data is, as seen *from the node* (a path on the
     node, a port the node listens on, a broker, a URL the node can reach).
   - **Shape**: one example record.
   - **Destination**: where results go, and in what format.
   - **Bounded or streaming**: a file or batch that ends, or a stream that
     doesn't.
   - **Which node**: the label that picks it (for example
     `pipeline_role: logs`).

## Write the spec

Start from `assets/pipeline-template.yaml`. The required shape is in
`references/job-spec.md`. Rules that are easy to miss:

- Top level: `name`, `type: pipeline`, and a `config:` block holding `input`,
  `pipeline.processors` and `output`. Add `selector.match_labels` to pin the
  job to intended nodes, with **underscores, not hyphens, in label keys**.
- **Bounded input** (a file read once, `generate` with a `count`, a
  `sql_select`): set top-level `restart_policy: never`. Otherwise a failing
  bounded job is restarted every few seconds and keeps reading `running`.
- **No `stdin` input for a Cloud-scheduled job.** The remote node has no
  connection to anyone's terminal. Use `file`, `http_server`, `generate`,
  `mqtt`, `kafka`, an object store or a SQL input.
- **`stdout` output: write `stdout: {}`.** Do not add `codec: json_object`; it
  passed both validators and was then rejected at runtime in testing.
- **Credentials**: never write a secret into the file. Reference an environment
  variable that is set **on the node that runs the job**, not on the machine
  that deploys it, and tell the user which variable to set where.
- Prefer components that have been run end to end. `references/components.md`
  lists them with working snippets taken from the proven jobs.

## Write the Bloblang

Mappings are Bloblang. Follow `references/bloblang.md`. The errors the strict
validator reports most often in this catalog are:

- A variable read without its `$`: after `let line = ...`, write `$line`, not
  `line` (a bare name is a field path).
- `let` or `meta` inside an `if`/`else`/`match` used as an **expression**
  (`root = if ... { let x = ... }`). Hoist the `let` above the expression.
- Wrong argument counts: `filter`, `map_each`, `or`, `merge`, `re_find_all`
  each take **one** argument; `filter`/`map_each` take a lambda
  (`x -> x > 10`).
- `this.items[0]` style dynamic indexing: use `this.items.index(0)`.
- Methods that don't exist at v2.1.21, such as `ts_add`,
  `format_timestamp_iso8601`, `parse_timestamp_iso8601`. Only use methods you
  have seen validate; check <https://docs.expanso.io/guides/bloblang/methods>.

## Hand it over

1. Save the file (default `pipeline.yaml`) and put a header comment on it:
   what it does, which values to edit, which env vars must be set on the node,
   and what leaves the host.
2. Validate it with the `validate-expanso-pipeline` skill. Do not report the
   pipeline as done until `expanso-edge validate` passes, and if the CLIs are
   not installed, say plainly that it is unvalidated.
3. Tell the user, in one short list: what leaves the node and to where,
   which env vars to set on the node, and that it has not been executed yet.
   Offer the `deploy-expanso-job` skill to run it.

Never claim a pipeline "works" or "is production ready" on validation alone.
Validation is not execution.
