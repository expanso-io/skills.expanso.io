# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## Layout

`skills/<category>/<name>/` is authoritative. `docs/<name>/` is a **flat published
mirror that CI regenerates** — `.github/workflows/pages.yml` copies root
`catalog.json`, `catalog-minimal.json`, `validation-report.json` and every
`skills/*/*/` directory into `docs/` at deploy time. Edit `skills/`; committed
`docs/` copies are build artifacts and can be stale without that being a live
defect. GitHub Pages publishes `docs/`.

Catalogs are built by `scripts/build-catalog.py` (default source `skills/`).

## Expanso CLI contract (verified against v2.1.21)

Get these wrong and the published instructions become unrunnable. They have been
wrong here before.

- `expanso-cli job deploy FILE` reads a **local path**, or `-` for stdin. It does
  **not** fetch an HTTPS URL — that fails with `failed to read job specification
  file`. Download first, or pipe.
- `expanso-edge run` starts the **node agent**; its `--config`/`-c` flag takes
  agent configuration files. There is no `expanso-edge run <pipeline>` form.
- `expanso-edge validate FILE...` is the local pipeline validator (`-` for stdin).
- Both binaries use a `version` **subcommand**; there is no `--version` flag.
- `expanso-cli execution list --job-id`; `--job` is rejected despite appearing in
  the CLI's own help text.
- The two validators answer different questions, and the difference is load
  bearing. `expanso-cli job validate --offline` checks JOB SPEC structure and is
  what CI gates on; `expanso-edge validate` checks the inner PIPELINE CONFIG and
  catches unknown component fields, bloblang arity and type errors. Many files
  are accepted by the first and rejected by the second, so a green CI run is not
  evidence of semantic validity. `validation-report.json` records both, as
  `job_spec_accepted` and `validates`. Run both.
- A successful deploy only **stores** the job. Assignment and execution follow
  asynchronously and can still fail; confirm with `job describe` /
  `execution list --job-id`. Passing validation is not execution evidence.

## Job skills (`skills/jobs/`)

Complete user jobs (RSS engine, migration, notifications, RAG, ...), each run
end to end. Their `skill.yaml` carries a `proof` block (where it ran, what was
and was not proved) that `build-catalog.py` publishes only for skills with a
`job` field. The job specs have the same structure as the proven runs; only
the values in each header comment differ (exception: the RSS fetch-error
guard, newer than its Cloud run). Do not add a job here without a run
record, and keep `proof.status` honest (`executed-local-only` is not Cloud).

## Skills run on Cloud-scheduled nodes

A `stdin` input cannot receive an operator's terminal input once the job is
scheduled onto a remote node. Use `file`, `http_server`, `generate`, a queue or
object storage. `skills/transforms/json-pretty/pipeline-cloud.yaml` is the
credential-free first-run example.

Credentials resolve in the environment of the **node that executes** the pipeline,
not the machine that ran the deploy.

## Claims must be per-skill

"Works offline" and "keeps credentials local" are false site-wide: a skill calling
a third-party API transmits its credential and data to that provider. Record real
requirements in the skill's `dependencies` block (see
`skills/ai/text-summarize/skill.yaml`).

## Validation gates

`scripts/validate-pipelines.sh` is the CI gate. It is fail-closed: a missing
validator or an empty file list fails rather than skipping. Every recipe
`pipeline.yaml` must be a full job spec (`type: pipeline` plus a `config:` block).

Per-skill validation status: `uv run -s scripts/validate-skills.py` writes
`validation-report.json` (`--check` fails on drift). Readiness vocabulary caps at
`validated-not-executed`; nothing is `verified-executed` without a dated Cloud run
record.

Python runs through `uv`.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
