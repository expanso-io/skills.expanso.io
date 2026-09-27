---
name: validate-expanso-pipeline
description: Validate an Expanso pipeline job spec with both expanso-edge validate and expanso-cli job validate --offline, explain what each result does and does not prove, and fix the errors they report. Use when the user asks to validate, lint, check or fix an Expanso pipeline YAML, sees a VALIDATION_ERROR or bloblang syntax error from expanso-edge, or asks whether a pipeline is ready to deploy.
---

# Validate an Expanso pipeline

Expanso has **two validators, and they answer different questions**. Run both.
Many files pass the first and fail the second.

| Command | Question it answers |
|---|---|
| `expanso-cli job validate FILE --offline` | Is this a well-formed **job spec**? Does not check component configuration. |
| `expanso-edge validate FILE` | Is the inner **pipeline config** valid: known components, known fields, value types, Bloblang syntax and arity? |

Passing the first alone proves almost nothing about whether the pipeline will
build. Neither proves it will run: that needs a deploy and an execution check
(the `deploy-expanso-job` skill).

## Step 1: check the tools

```bash
expanso-edge version
expanso-cli version
```

Both use a `version` **subcommand**; there is no `--version` flag. If either is
missing, the install commands are in the `deploy-expanso-job` skill. Without
them you cannot validate: say so plainly and do not describe the file as valid.
In chat without a shell, review the file against the build skill's references
instead and label the result "reviewed, not validated".

## Step 2: run both

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
```

`expanso-edge validate` takes several files, or `-` to read stdin. Neither
command needs a control plane connection.

## Step 3: fix what `expanso-edge validate` reports

Errors name the line and the config path, for example
`(line 44) bloblang syntax error in pipeline.processors.0.mapping`. Fix them one
at a time and re-run. The common ones:

| Error text contains | Fix |
|---|---|
| ``Statement keyword `let` is not allowed inside an expression-position`` (or `meta`) | Move the `let`/`meta` statement above the `if`/`match` expression. |
| `filter() takes 1 argument(s)`, same for `map_each`, `or`, `merge`, `re_find_all` | Pass exactly one argument; `filter`/`map_each` take a lambda `x -> ...`. |
| `Dynamic array indexing requires .index() method` | `this.items.index(0)` instead of `this.items[0]`. |
| `Unrecognised method 'ts_add'` (or any `Unrecognised method`) | The method does not exist at this version. Find a supported one in the Bloblang docs; don't guess another name. |
| `parsing time "2h" as "2006-01-02T15:04:05..."` | A duration string was used where a timestamp is expected. |
| `Unknown field 'X' in <component>` | Remove the field or use the name the component's docs page gives. Seen in this catalog: `max_retries`, `backoff`, `compression`, `storage_class`, `time_partitioning`, `processors` in `broker`, `catch` in a `switch` case. |
| `Unknown component or field 'X'` | Misspelled or unsupported component. |
| `[output.switch] Expected object, got array` | The output `switch` is an object with `cases:`; only the processor `switch` is a bare list. |
| `Missing required field 'tools'` on `openai_chat_completion` | Add `tools: []`. |
| a numeric field given a string, often `${VAR}` | Numeric fields such as a rate-limit `count` or `batching.count` need a literal number. |

The `build-expanso-pipeline` skill's Bloblang and component reference files
have working forms of each construct.

## Step 4: check what neither validator checks

Read the file for these, which pass validation and still fail or misbehave:

- `stdin` input in a job that will run on a Cloud-scheduled node: nothing can
  reach it. Replace the input.
- `codec: json_object` on `stdout`: rejected at runtime in testing. Use
  `stdout: {}`.
- A bounded input without `restart_policy: never`: a failing job restarts
  forever.
- A hyphen in a `selector.match_labels` key: the pipeline failed to build on
  the node.
- A secret written into the file instead of a node environment variable.
- Paths, ports and env vars that exist on the user's laptop but not on the
  node.

## Report

State both results separately, with the tool version, for example: "`expanso-edge
validate` v2.1.21: pass. `expanso-cli job validate --offline`: pass. Not yet
executed." Never summarize a job-spec-only pass as "valid".
