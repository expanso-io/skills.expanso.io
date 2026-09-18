# Expanso Skills Marketplace

The official marketplace for Expanso skills: complete jobs for the data work
you are asked to build, plus single-purpose pipeline skills, for OpenClaw,
Claude and any MCP-compatible AI assistant. All open source; the live count
per category is in [`catalog.json`](catalog.json).

## If you are asked to build...

These eight jobs were each run end to end on 2026-09-18 with
`expanso-edge` v2.1.21 and their output counted at the destination. Each
lives in [`skills/jobs/`](skills/jobs/) with its job spec, a README with
dependency setup and output checks, the sample inputs used, and a
`skill.yaml` `proof` block recording where it ran and what was not proved.
The dated, sanitized run record with the Cloud job and execution ids is
[`skills/jobs/PROOF-2026-09-18.md`](skills/jobs/PROOF-2026-09-18.md).

| Job | Proven | Directory |
|---|---|---|
| RSS feed engine | Cloud + local; live NASA and BBC feeds; fetch-error guard local only | [`rss-feed-engine`](skills/jobs/rss-feed-engine/) |
| Data migration engine (batch) | Cloud + local | [`data-migration-engine`](skills/jobs/data-migration-engine/) |
| Notification engine | Cloud + local, to a local test receiver only | [`notification-engine`](skills/jobs/notification-engine/) |
| RAG: fetch, chunk, embed, store, search | Cloud + local; Ollama + Qdrant; URL-based chunk id local only | [`rag-embed-retrieve`](skills/jobs/rag-embed-retrieve/) |
| Webhook fan-out | Local only | [`webhook-fan-out`](skills/jobs/webhook-fan-out/) |
| Log reduction | Local only | [`log-reduction`](skills/jobs/log-reduction/) |
| Sensor telemetry over MQTT | Local only; synthetic publisher | [`sensor-telemetry-mqtt`](skills/jobs/sensor-telemetry-mqtt/) |
| CI test fixtures | Local only | [`ci-fixtures`](skills/jobs/ci-fixtures/) |

"Cloud" means submitted to an Expanso Cloud workspace and executed by one
operator-registered node chosen by label, with the job's dependencies on
that host; it is not a hosted runner. "Local" means a local-mode node only.
Each job spec has the same structure as the job that ran; only the values
listed in its header comment differ, and long mappings are rewrapped. Three
changes are newer than the runs and were not re-run on Cloud: the RSS
fetch-error guard and the RAG URL-based chunk id (each validated on a
local-mode node only), and `restart_policy: never` on the bounded jobs.
Not proven, and not published as working jobs:
live X (Twitter) ingestion, change data capture, delivery into Slack or
email, and the native `qdrant` output (the RAG job writes through Qdrant's
REST API instead). The first five nodes are free.

> **Readiness:** these skills are published pipeline definitions. Except where a
> skill's own README states otherwise, they have **not** been confirmed by an
> end-to-end run on current Expanso Cloud. See
> [Pipeline shape & readiness](#pipeline-shape--readiness) and
> [Known issues](#known-issues) before depending on one.

## What Are Expanso Skills?

Expanso Skills are portable data processing pipeline definitions. A skill is a
*job spec*: you submit it to your Expanso Cloud control plane, and the scheduler
assigns it to an edge node you own and control.

What that means in practice:

- **Your infrastructure runs the work** - pipelines execute on your own edge
  nodes, not on Expanso's servers.
- **Credentials resolve on the node that runs the pipeline** - they are read from
  that node's environment and are not embedded in the pipeline definition.
  **This is not the same as "credentials never leave your machine".** A skill that
  calls a third-party API (OpenAI, Slack, Gmail, ...) transmits its credential to
  *that provider*, along with whatever data you send it. Only skills whose
  `skill.yaml` has a `dependencies` block (`text-summarize` and the eight jobs) have been
  audited for what leaves the host; for any other skill, check its pipeline's
  components rather than relying on its README.
- **Some skills run without network egress; many do not.** Only skills whose
  components are entirely local are offline-capable. Any skill listing a
  third-party API component is **not** offline. Check the skill, not this page.
- **Are composable** - chain skills together for complex workflows.

Each skill includes:
- `skill.yaml` - Metadata, inputs/outputs, credentials
- `pipeline-cli.yaml` - Standalone CLI pipeline
- `pipeline-mcp.yaml` - MCP server integration
- `test/test.yaml` - Automated tests

## Quick Start

### 1. Install Expanso

```bash
# Install Expanso Edge (the node agent)
curl -fsSL https://get.expanso.io/edge/install.sh | bash
expanso-edge version

# Install Expanso CLI (for job management)
curl -fsSL https://get.expanso.io/cli/install.sh | bash
expanso-cli version
```

Both tools take a `version` **subcommand**. There is no `--version` flag.

### 2. Connect to Expanso Cloud

Skills run as Cloud-scheduled jobs, so the binaries alone are not enough. You
need a control-plane profile and at least one connected node.

```bash
# Endpoint and API key come from https://cloud.expanso.io
expanso-cli profile save my-network \
  --endpoint https://YOUR-NETWORK.us2.cloud.expanso.io:9010 \
  --api-key exp_ak_YOUR_KEY --select

# On the machine that should run the work:
expanso-edge bootstrap --token YOUR_BOOTSTRAP_TOKEN
expanso-edge run

# The node must show up as connected before anything can be scheduled
expanso-cli node list
```

### 3. Validate and deploy a skill

Start with `json-pretty`'s **Cloud variant**. It needs no credentials, sends
nothing off the host, and generates its own bounded input, so a remote node can
run it with no further setup.

```bash
# Clone the marketplace
git clone https://github.com/expanso-io/skills.expanso.io.git
cd skills.expanso.io

# Validate locally, no control plane needed
expanso-edge validate skills/transforms/json-pretty/pipeline-cloud.yaml
expanso-cli job validate skills/transforms/json-pretty/pipeline-cloud.yaml --offline

# Submit to your control plane; the scheduler assigns it to a matching node
expanso-cli job deploy skills/transforms/json-pretty/pipeline-cloud.yaml

# Confirm it actually ran
expanso-cli job describe json-pretty-cloud
expanso-cli job logs json-pretty-cloud
```

Or straight from the marketplace, without cloning:

```bash
curl -fsSL -O https://skills.expanso.io/json-pretty/pipeline-cloud.yaml
expanso-cli job deploy pipeline-cloud.yaml
```

Validation and deployment both passing does **not** mean the pipeline ran. See
[Confirm it actually ran](#confirm-it-actually-ran).

**Why `pipeline-cloud.yaml` and not `pipeline-cli.yaml`?** The `-cli` variant
reads `stdin`, which a Cloud-scheduled node cannot receive from your terminal.
See [Providing input](#providing-input).

### 4. Use with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "expanso-pipelines": {
      "command": "npx",
      "args": ["@expanso/mcp-pipelines"]
    }
  }
}
```

This MCP server provides tools to validate, create, and deploy Expanso pipelines directly from Claude.

## Skill Categories

### Jobs (8 skills)
Complete jobs, each run end to end. See [If you are asked to build...](#if-you-are-asked-to-build).

### Workflows (19 skills)
End-to-end automation combining multiple services.

| Skill | Description |
|-------|-------------|
| `morning-briefing` | Daily briefing with calendar, weather, news, tasks |
| `email-triage` | AI-powered email classification and routing |
| `stripe-reports` | Automated Stripe analytics and reports |
| `devops-monitor` | Infrastructure monitoring and alerting |
| `jira-automate` | Jira/Confluence workflow automation |
| `todoist-automate` | Task management automation |
| `seo-pipeline` | SEO analysis and optimization |
| [View all...](skills/workflows/) | |

### AI (23 skills)
AI-powered processing for text, images, audio, and video.

| Skill | Description |
|-------|-------------|
| `text-embed` | Generate embeddings for RAG/semantic search |
| `text-summarize` | Summarize long documents |
| `text-translate` | Multi-language translation |
| `image-analyze` | Vision AI for image understanding |
| `audio-transcribe` | Speech-to-text transcription |
| `meeting-notes` | Transcribe and summarize meetings |
| [View all...](skills/ai/) | |

### Connectors (3 skills)
Integration connectors for SaaS services and messaging platforms.

| Skill | Description |
|-------|-------------|
| `slack-read` | Read Slack channel messages via the Slack Web API |
| `gmail-read` | Read Gmail messages via the Gmail API |
| `webhook-receive` | Receive and verify webhook events from any service |

### Security (16 skills)
Security, compliance, and cryptographic operations.

| Skill | Description |
|-------|-------------|
| `cve-scan` | Scan SBOM for vulnerabilities |
| `pii-detect` | Detect PII in text |
| `pii-redact` | Redact sensitive information |
| `sign-envelope` | Cryptographically sign data |
| `secrets-scan` | Detect leaked secrets |
| `sbom-generate` | Generate software bill of materials |
| `access-gate` | Deny-by-default permission gateway for agent access |
| `data-fence` | Field-level filtering to limit agent data exposure |
| [View all...](skills/security/) | |

### Transforms (100 skills)
Data transformation, parsing, and format conversion.

| Skill | Description |
|-------|-------------|
| `json-*` | 10 JSON manipulation skills |
| `array-*` | 15 array operation skills |
| `string-*` | 10 string manipulation skills |
| `text-*` | 12 text processing skills |
| `date-*` | 4 date/time skills |
| `math-*` | 8 mathematical operations |
| [View all...](skills/transforms/) | |

### Utilities (16 skills)
General utilities and helper functions.

| Skill | Description |
|-------|-------------|
| `uuid-generate` | Generate UUIDs |
| `email-validate` | Validate email addresses |
| `mime-type` | Detect file MIME types |
| `image-dimensions` | Get image dimensions |
| `retry-wrapper` | Add retry logic to operations |
| [View all...](skills/utilities/) | |

## Skill Structure

Each skill follows this structure:

```
skill-name/
├── skill.yaml          # Skill metadata
├── pipeline-cli.yaml   # CLI pipeline definition
├── pipeline-mcp.yaml   # MCP server pipeline
├── README.md           # Documentation
└── test/
    ├── test.yaml       # Test definitions
    └── fixtures/       # Test data
```

### skill.yaml

```yaml
name: text-summarize
version: 1.0.0
description: Summarize long documents using AI

credentials:
  - name: OPENAI_API_KEY
    required: false  # Not required if using Ollama
    description: OpenAI API key

inputs:
  - name: text
    type: string
    required: true
    description: Text to summarize
  - name: max_length
    type: integer
    default: 100
    description: Maximum summary length

outputs:
  - name: summary
    type: string
    description: Summarized text

backends:
  - name: openai
    type: remote
    requires: [OPENAI_API_KEY]
  - name: ollama
    type: local
    models: [llama3.2, mistral]
```

## Using Skills

### What `expanso-edge` actually does

This matters, because earlier versions of this README got it wrong:

- `expanso-edge run` starts the **node agent**. It connects to your control plane,
  registers the node, and executes jobs the scheduler assigns to it.
  Its `--config` / `-c` flag takes **agent configuration files**. Passing a
  pipeline to it does *not* run that pipeline.
- `expanso-edge validate FILE...` validates pipeline configs locally, offline.
  It reads stdin when given `-` or no file.
- `expanso-cli job deploy FILE` submits a job spec to the control plane.

There is no supported `expanso-edge run <pipeline>` form. Execution goes through
the control plane.

### Validate locally

```bash
# Validate one or more pipeline configs, no control plane required
expanso-edge validate skills/ai/text-summarize/pipeline-cli.yaml

# Validate from stdin
cat skills/ai/text-summarize/pipeline-cli.yaml | expanso-edge validate -

# Validate the job spec client-side
expanso-cli job validate skills/ai/text-summarize/pipeline-cli.yaml --offline
```

Local validation checks pipeline syntax, structure and component types. It does
**not** run the orchestrator's submission validation, and it does not prove the
pipeline will execute. See [Known issues](#known-issues).

### Deploy to Expanso Cloud

```bash
# Submit; the scheduler assigns it to nodes matching the job's selector
expanso-cli job deploy skills/ai/text-summarize/pipeline-cli.yaml

# Preview without submitting
expanso-cli job deploy skills/ai/text-summarize/pipeline-cli.yaml --dry-run

# Deploy straight from the marketplace over stdin
curl -fsSL https://skills.expanso.io/text-summarize/pipeline-cli.yaml \
  | expanso-cli job deploy -
```

`expanso-cli job deploy` takes a **local file path**, or `-` for stdin. It does
not fetch an HTTPS URL: passing one fails with
`failed to read job specification file`. Download first, or pipe via stdin.

### Confirm it actually ran

A successful deploy means the control plane **stored** the job. Assignment and
execution happen afterwards, asynchronously, and can still fail.

```bash
expanso-cli job describe <job-name>              # job state
expanso-cli execution list --job-id <job-id>     # per-node executions
expanso-cli job logs <job-name>                  # realtime logs
```

A job whose state is `degraded` has been assigned but is failing at runtime.
Note the flag is `--job-id`; `--job-name` and `--job` are not accepted.

### Providing input

Many skills in this repository declare a `stdin` input. **A `stdin` input cannot
receive your terminal's input once the job is scheduled onto a remote node** --
the node's process has no connection to your shell. `stdin` skills are usable
only where the pipeline runs attached to a process you control.

For a Cloud-scheduled job, use an input the node can reach on its own, for
example `file` (a path on the node), `http_server`, `generate`, or a message
queue or object-store input. See [Known issues](#known-issues).

### MCP Mode

Skills with `pipeline-mcp.yaml` are shaped as HTTP endpoints, using an
`http_server` input and a `sync_response` output. They are intended to be served
by a node running that pipeline.

The MCP endpoint's advertised address and its operational status have **not**
been verified for this release. Treat `pipeline-mcp.yaml` as a definition, not a
running service.

## Testing

### Run the Skill Test Harness

```bash
uv run -s scripts/test-skills.py --report /tmp/test-report.json
```

The harness defaults to:
- Reusing cached passing results when inputs and pipelines are unchanged
- Rerunning failed tests up to 3 total attempts

### Test a New Expanso CLI/Edge Cut

If you have a locally built or pre-release binary, point the harness at it:

```bash
EXPANSO_CLI_BIN=/path/to/expanso-cli \
EXPANSO_EDGE_BIN=/path/to/expanso-edge \
uv run -s scripts/test-skills.py --report /tmp/test-report.json
```

Useful flags:
- `--no-cache` to force a full run
- `--no-rerun-failed` to disable retries
- `--max-reruns 3` to change attempts per test

## Credential Management

Credentials are referenced by environment variable from the pipeline definition
and are never embedded in it:

```bash
export OPENAI_API_KEY=sk-...
export SLACK_WEBHOOK=https://hooks.slack.com/...
```

Two things this does **not** mean:

- **It is not "credentials never leave your machine".** A skill that calls a
  third-party API sends its credential to *that provider*. `text-summarize`
  authenticates to the OpenAI API with `OPENAI_API_KEY`; `slack-read` authenticates
  to Slack; `gmail-read` authenticates to Google. What is true is that the
  credential is not sent to *Expanso Cloud* and is not stored in the pipeline file.
- **The variable must exist on whichever node runs the pipeline**, not on the
  machine you ran `expanso-cli job deploy` from. For a Cloud-scheduled job that is
  the edge node's environment. Exporting it in your own shell does not make it
  available to a remote node.

Each skill's `skill.yaml` lists the credentials it references. Only skills with a
`dependencies` block in `skill.yaml` (`text-summarize` and the jobs) have been audited
for what leaves the host, and the catalog publishes that block. For any other
skill, check the pipeline's components: any third-party API component sends its
credential and your data to that provider.

## Pipeline shape & readiness

Every row is at its true label. **No row is `verified-executed`.** A row may only
be promoted by a dated run record on current Expanso Cloud carrying pinned
versions, control-plane identifiers, and a downstream receipt. Component
availability alone does not promote a row: it establishes that the component
exists, not that the shape runs.

Component availability below was confirmed on 2026-09-17 against the Expanso MCP
documentation server's `list_components` (236 components) and cross-checked
against live `docs.expanso.io` component pages.

| # | Pipeline shape | Readiness | Components | Notes |
|---|---|---|---|---|
| 1 | `stdin` -> mapping -> `stdout` | `drafted-unverified` | present, Stable | `stdin` has no input path on a Cloud-scheduled node |
| 2 | `http_server` -> mapping -> `sync_response` (MCP) | `drafted-unverified` | present, Stable | endpoint operation unverified |
| 3 | Kafka source -> mapping -> sink | `drafted-unverified` | `kafka`, `kafka_franz` present, Stable | never run end to end |
| 4 | input -> mapping -> Kafka sink | `drafted-unverified` | `kafka` output present, Stable | never run end to end |
| 5 | input -> mapping -> Postgres sink | `drafted-unverified` | `sql_insert`, `sql_raw` present, Stable | never run end to end |
| 6 | input -> mapping -> Iceberg sink | **`not-supported`** | **no Iceberg component exists** | see below |
| 7 | input -> mapping -> object-store sink | `drafted-unverified` | `aws_s3` present, Stable | never run end to end |
| 8 | sensor / industrial telemetry -> mapping -> sink | `drafted-unverified` | `mqtt` input present, Stable | never run end to end |

**Row 6 is `not-supported`, not `drafted-unverified`.** A case-insensitive search
of the full component listing for `iceberg`, `delta`, `lakehouse` and `hudi`
returns no match, and `docs.expanso.io/components/outputs/iceberg/` returns 404.
`parquet_encode` exists, but writing Parquet into an object store is not an
Iceberg table commit: no catalog registration, no snapshot, no manifest write.
`drafted-unverified` would imply the shape might work as written; the evidence
contradicts that. This is a demotion on evidence.

Component presence was established against a documentation component listing. It
does **not** establish behavior in a Cloud-managed execution context, which is
unproven for every row.

## Known issues

Open items affecting published skills, recorded rather than silently patched.

### Two validators, two different questions

This distinction matters more than any count, so it is stated first:

| Command | Question it answers | Used by |
|---|---|---|
| `expanso-cli job validate --offline` | Is this a well-formed **job spec**? | the repository CI gate |
| `expanso-edge validate` | Is the inner **pipeline config** valid? | `validation-report.json` |

The first does **not** check component configuration. A pipeline can be accepted
as a job spec and still be rejected by the strict validator for unknown
component fields, bloblang arity errors or wrong value types. In
`validation-report.json` those two answers are recorded separately, as
`job_spec_accepted` and `validates`; a substantial number of skills are
`job_spec_accepted: true` **and** `validates: false`.

**A green CI run therefore does not mean the catalog is semantically valid.** It
means every file was accepted as a job spec.

### Some skills have a pipeline the local validator rejects

Settled, offline evidence: `expanso-edge validate` at **v2.1.21** rejects at
least one published pipeline variant (`pipeline-cli.yaml`, `pipeline-mcp.yaml`,
`pipeline-cloud.yaml`, or a recipe's `pipeline.yaml`) of a number of skills.
Every variant is validated separately. A skill is labelled `invalid-does-not-validate` in
[`validation-report.json`](https://skills.expanso.io/validation-report.json)
if **any** of its variants is rejected, and is **excluded from any "ready"
promotion**.

**The report is the only source for which skills and how many.** Counts and the
affected list are deliberately not repeated here, because prose copies go stale
silently while the report is drift-checked:

```bash
uv run -s scripts/validate-skills.py           # regenerate
uv run -s scripts/validate-skills.py --check   # fails if the report is stale
```

For the cli/mcp skills, two causes account for nearly all of them:

- **`Missing required field 'tools'` in `openai_chat_completion`.** The
  component schema at v2.1.21 requires a `tools` field. Adding `tools: []` (no
  tool calling) was verified to satisfy the validator. This repair has been
  applied **only** to both pipelines of the promoted `text-summarize` skill; the
  rest are left untouched and labelled, so the fix can be applied deliberately
  rather than swept across the catalog.
- **Bloblang mapping syntax errors**, plus one file
  (`email-triage/pipeline-cli.yaml`) that is not valid YAML at all.

Some skills have both causes, one per variant.

Recipes (`skills/recipes/*/pipeline.yaml`) fail for different reasons, mostly
component-configuration errors:

- **Unknown component fields**, such as `max_retries`, `batching`, `backoff`,
  `compression`, `storage_class` or `time_partitioning`.
- **Unknown processors**: `try`, `catch` and `json_documents` are not
  components at v2.1.21.
- **Wrong value types**, where a string (often an env interpolation) is given
  for a numeric field such as a rate limit `count` or `batching.count`.
- **Bloblang errors**, including `let` inside an expression-position
  `if`/`else`/`match` body and wrong method arity.

### `codec: json_object` on `stdout` outputs

All 177 published skills carry it. In **exploratory** testing against Expanso
Cloud v2.1.21 it was rejected at runtime with
`codec was not recognised: json_object`, while both validators passed and the
deploy succeeded; removing the key (`stdout: {}`) ran correctly in the same
test. **This has not been confirmed on an intended test workspace, so the catalog
has not been changed.** Newly authored files here use `stdout: {}`. If a job
reaches `degraded` state, suspect its output codec.

### Validation is not execution

A pipeline can pass both validators, be accepted by the control plane, and still
fail when a node runs it. The `codec` issue above is exactly that. Always check
`job describe` and `execution list --job-id`.

### `stdin` inputs on Cloud-scheduled jobs

See [Providing input](#providing-input). Skills whose only input is `stdin` have
no delivery path on a remote node.

### MCP endpoint status

`pipeline-mcp.yaml` files are definitions. Their advertised endpoint and its
operational status are unverified for this release.

### Catalog freshness

`catalog.json` carries a `generated` timestamp of 2026-02-24. Its **contents were
checked and are accurate**: 177 skills, exactly matching the skills on disk, with
no additions or omissions. The timestamp is stale metadata, not stale data.


## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding a New Skill

1. Use the template:
   ```bash
   cp -r _template skills/category/my-new-skill
   ```

2. Update `skill.yaml` with your skill metadata

3. Implement the pipeline in `pipeline-cli.yaml` and `pipeline-mcp.yaml`

4. Add tests in `test/test.yaml`

5. Submit a PR!

### Skill Guidelines

- Keep skills focused and single-purpose
- Support both remote (OpenAI) and local (Ollama) backends when possible
- Include comprehensive tests
- Document all inputs, outputs, and credentials
- Follow naming conventions: `category-action` (e.g., `text-summarize`, `json-validate`)

## Catalog API

The marketplace provides a JSON catalog for programmatic access:

```bash
# Full catalog with all metadata
curl https://skills.expanso.io/catalog.json

# Minimal catalog (just names and categories)
curl https://skills.expanso.io/catalog-minimal.json

# Per-skill validation status and readiness labels
curl https://skills.expanso.io/validation-report.json

# Agent-oriented summary of the invocation and dependency contracts
curl https://skills.expanso.io/llms.txt
```

### Validation report

`validation-report.json` is generated by `scripts/validate-skills.py` and records
what the **local validator** says about every published pipeline, with the tool
version it was produced against:

```bash
uv run -s scripts/validate-skills.py           # regenerate
uv run -s scripts/validate-skills.py --check   # fail if results drifted
```

Its `readiness` vocabulary caps at `validated-not-executed`. Nothing reaches
`verified-executed` without a dated Expanso Cloud run record. The report itself
carries the current totals and the validator version they were produced against;
they are not duplicated in this prose -- see [Known issues](#known-issues).

### Catalog Structure

```json
{
  "version": "1.0.0",
  "total_skills": 177,
  "categories": {
    "ai": {
      "description": "AI-powered skills...",
      "skill_count": 23,
      "tags": ["ai", "ml", "llm"]
    }
  },
  "skills": {
    "text-summarize": {
      "name": "text-summarize",
      "version": "1.0.0",
      "description": "Summarize long documents",
      "category": "ai",
      "credentials": [...],
      "inputs": [...],
      "outputs": [...],
      "backends": ["openai", "ollama"],
      "tags": ["ai", "local", "openai", "remote", "text"],
      "dependencies": {"offline_capable": false, "...": "..."}
    }
  }
}
```

`dependencies` is copied verbatim from `skill.yaml` and is present only for
audited skills. The `offline` tag is set only when a skill declares
`dependencies.offline_capable: true`, or declares only local backends.

## Related Resources

- [Expanso Documentation](https://docs.expanso.io)
- [Pipeline Schema](https://docs.expanso.io/schemas/pipeline.schema.json)
- [OpenClaw Integration](https://expanso.io/expanso-hearts-openclaw/)
- [Expanso Cloud](https://cloud.expanso.io)

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with love by [Expanso](https://expanso.io)
