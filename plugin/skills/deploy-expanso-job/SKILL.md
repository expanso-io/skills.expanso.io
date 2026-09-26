---
name: deploy-expanso-job
description: Install the Expanso CLIs, connect to Expanso Cloud, register an edge node, deploy a pipeline job with expanso-cli and confirm it actually executed. Use when the user asks to deploy, run, submit, schedule or ship an Expanso pipeline or job, set up expanso-cli or expanso-edge, connect a node to Expanso Cloud, or check whether a deployed job ran.
---

# Deploy an Expanso job and prove it ran

A successful `expanso-cli job deploy` only means the control plane **stored**
the job. Assignment to a node and execution happen afterwards, asynchronously,
and can still fail. You are not done until you have checked the execution and
the output.

Run commands only with the user's go-ahead: deploying changes what their nodes
do.

## Step 1: tools

```bash
expanso-cli version
expanso-edge version
```

If missing, the installers download from `get.expanso.io`. Pipe to `bash`,
not `sh`:

```bash
curl -fsSL https://get.expanso.io/cli/install.sh | bash    # expanso-cli: job management
curl -fsSL https://get.expanso.io/edge/install.sh | bash   # expanso-edge: the node agent and local validator
```

## Step 2: control plane and node

Skip what `expanso-cli node list` shows is already set up.

```bash
# Endpoint and API key come from https://cloud.expanso.io
expanso-cli profile save my-network \
  --endpoint https://YOUR-NETWORK.us2.cloud.expanso.io:9010 \
  --api-key YOUR_API_KEY --select

# On the machine that should run the work:
expanso-edge bootstrap --token YOUR_BOOTSTRAP_TOKEN
expanso-edge run

# The node must show as connected before anything can be scheduled
expanso-cli node list
```

Ask the user to paste their own endpoint, API key and bootstrap token into the
terminal themselves; don't ask for them in chat. The first five nodes are free.

`expanso-edge run` starts the **node agent**. It does not run a pipeline file:
there is no `expanso-edge run pipeline.yaml` form, and its `--config`/`-c` flag
takes agent configuration. Pipelines reach a node only through the control
plane.

If the job has a `selector`, the node needs matching labels. Use underscores in
label keys.

## Step 3: validate, then deploy

Validate first with the `validate-expanso-pipeline` skill. Then:

```bash
expanso-cli job deploy pipeline.yaml --dry-run   # preview, submits nothing
expanso-cli job deploy pipeline.yaml
```

`job deploy` reads a **local path**, or `-` for stdin. It does **not** fetch a
URL (that fails with `failed to read job specification file`). For a catalog
file, download it first or pipe it:

```bash
curl -fsSL -O https://skills.expanso.io/json-pretty/pipeline-cloud.yaml
expanso-cli job deploy pipeline-cloud.yaml
# or
curl -fsSL https://skills.expanso.io/<name>/pipeline.yaml | expanso-cli job deploy -
```

For a first run with no credentials and nothing leaving the host, use
`json-pretty/pipeline-cloud.yaml` (job name `json-pretty-cloud`).

## Step 4: confirm it ran

```bash
expanso-cli job describe <job-name>              # job state
expanso-cli execution list --job-id <job-id>     # per-node executions
expanso-cli job logs <job-name>                  # logs
```

The flag is `--job-id`. `--job` and `--job-name` are rejected, even though
`--job` appears in the CLI's own help text. Get the job id from `job describe`.

Read the state:

- `completed`: a bounded job finished. Now check the output (Step 5).
- `running`: fine for a standing job. For a bounded job, check
  `execution list`: many executions in a short time means it is failing and
  being restarted; add `restart_policy: never`.
- `degraded` or `failed`: switch to the `debug-expanso-job` skill.
- No execution at all: no connected node matches the selector.

## Step 5: check the output at the destination

A job can complete and still write nothing. Count what arrived where the job
writes: `wc -l` on an output file on the node, a row count in the target
table, the receiver's log. Compare with what went in.

## Credentials and data

Credentials and paths resolve on the **node that executes the job**. Exporting
a variable in the shell that runs `job deploy` does nothing for a remote node;
set it in the node agent's environment. Before deploying anything that calls a
third-party API, remind the user that the pipeline will send that provider its
credential and the data it processes.

## Report

Say what you ran and what you saw: the job state, the execution count and
result, and the output count at the destination. If you stopped at deploy, say
"deployed, execution not yet confirmed", not "deployed successfully".
