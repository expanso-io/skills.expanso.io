---
name: debug-expanso-job
description: Diagnose an Expanso job that is degraded, failed, stuck running, never scheduled, or completed without output. Use when the user reports an Expanso pipeline or job not working, a degraded job state, repeated executions, missing output, a codec error, or asks why their Expanso job did not run.
---

# Debug an Expanso job

Work from evidence. Collect the state first, form one hypothesis, change one
thing, redeploy, and check again. Show the user your reasoning as you go.

## Step 1: collect

```bash
expanso-cli job describe <job-name>
expanso-cli execution list --job-id <job-id>
expanso-cli job logs <job-name>
expanso-cli node list
```

`--job-id` is the only accepted flag on `execution list`. Also get the job spec
that was deployed, and run it through `expanso-edge validate`: a file accepted
by `expanso-cli job validate --offline` can still have an invalid pipeline
config.

## Step 2: match the symptom

| Symptom | Likely cause | Check or fix |
|---|---|---|
| No executions | No connected node matches the selector | `node list`; node labels vs `selector.match_labels`. |
| Pipeline fails to build on the node | Hyphen in a label key | Use underscores (`pipeline_role`). |
| `degraded`, log says `codec was not recognised: json_object` | `stdout` output with `codec: json_object` | Change to `stdout: {}`. |
| `degraded` or `failed` with a config error | Pipeline config invalid | Run `expanso-edge validate`; fix with the `validate-expanso-pipeline` skill. |
| `running`, many executions in seconds | Bounded job failing and restarting | Add top-level `restart_policy: never`, redeploy, then read the real error. |
| `completed`, no output | Input path, port or host not present **on the node**; input was `stdin` | Check the paths on the node itself; replace a `stdin` input. |
| Output written to an unexpected place | Paths resolve on the node, not the deploying machine | Look on the node. |
| Auth errors against a third-party API | Credential not set in the **node's** environment | Set it for the node agent, not in the deploying shell. |
| Fetch step fails with a confusing parse error downstream | HTTP error body parsed as data | Add an `errored()` guard right after the `http` processor (see `rss-feed-engine`). |
| Dedupe forgets on restart | `memory` cache | Use a `file` cache resource. |
| Native `qdrant` output reports success with 0 points | Known at v2.1.21: its id mapping could not read message fields | Write through Qdrant's REST API with `http_client`. |
| Deploy fails with `failed to read job specification file` | A URL was passed to `job deploy` | Download the file first, or pipe it with `-`. |

## Step 3: fix and prove

Make the smallest change that addresses the evidence, validate it with both
validators, redeploy, and repeat the checks in `deploy-expanso-job` Step 4 and
Step 5. Report what the evidence showed, what you changed, and whether the new
execution produced output at the destination. If it still fails, say what you
ruled out and what the next hypothesis is.
