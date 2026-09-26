# Expanso job spec structure

Verified against `expanso-edge` and `expanso-cli` v2.1.21. A job spec is YAML:

```yaml
name: log-reduction            # job name; used by `job describe`/`job logs`
type: pipeline                 # required
restart_policy: never          # bounded inputs only (see below)
selector:                      # optional; pins the job to labelled nodes
  match_labels:
    pipeline_role: logs        # underscores in keys, never hyphens
config:                        # required: the pipeline itself
  input: { ... }               # exactly one input (use `broker` to combine)
  pipeline:
    threads: 1                 # optional; 1 keeps output order stable
    processors: [ ... ]        # applied in order to every message
  output: { ... }              # exactly one output (use `broker`/`switch`)
  cache_resources:             # optional; named caches for `dedupe` etc.
    - label: seen
      memory: {}
```

Optional top-level fields seen in published specs: `description`,
`namespace`, `priority`, `labels` (free-form metadata, not the selector).

## Fields that decide whether it runs

- **`type: pipeline` and `config:`** must both be present. A bare pipeline
  (`input`/`pipeline`/`output` at the top level) is not a job spec.
- **`selector.match_labels`**: without it the scheduler may place the job on any
  connected node. A hyphenated label key (for example `pipeline-role`) made the
  pipeline fail to build on the node. Use `pipeline_role`.
- **`restart_policy: never`** for a bounded input. With the default policy a
  failing bounded job was re-run on Cloud every few seconds and stayed
  `running`; with `never` it ended `failed` after one execution. Leave it out
  for a standing (streaming or polling) job, so a transient failure restarts it.

## Where things resolve

Every path, host, port and environment variable in the spec is resolved **on
the node that executes the job**, not on the machine that ran
`expanso-cli job deploy`.

- `file` paths are paths on the node.
- `http_server.address` is a port on the node. `127.0.0.1` accepts only
  local connections; `0.0.0.0` accepts connections from the network.
- `${VAR}` / `${VAR:default}` in a field and `env("VAR")` in Bloblang read the
  node's environment. A variable exported in the deployer's shell does nothing
  for a remote node.

## Variants in the published catalog

| File | Input | Use |
|---|---|---|
| `pipeline.yaml` | varies | jobs and recipes |
| `pipeline-cli.yaml` | `stdin` | only where the pipeline runs attached to a process you control; not for a Cloud-scheduled node |
| `pipeline-mcp.yaml` | `http_server` with `sync_response` output | request/response endpoint served by a node; endpoint operation is unverified |
| `pipeline-cloud.yaml` | `generate` | `json-pretty` only; the credential-free first run |
