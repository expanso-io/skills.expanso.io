# Expanso for Claude

Build data pipelines that run where your data already lives. Expanso schedules
pipeline jobs from a control plane (Expanso Cloud) onto edge nodes that you own
and run, so the processing happens next to the data instead of after you have
shipped all of it somewhere central.

This plugin teaches Claude the Expanso workflow end to end, including the parts
that are easy to get wrong: which of the two validators answers which question,
why a successful deploy is not proof that anything ran, and why a `stdin` input
goes nowhere once a job is scheduled onto a remote node.

## What's inside

| Skill | Use it when you want to... |
|---|---|
| `find-expanso-skill` | find an existing job or recipe in the [Expanso Skills catalog](https://skills.expanso.io) before writing one, and see how far each has been proven |
| `build-expanso-pipeline` | write a new pipeline job spec (inputs, Bloblang mappings, outputs, selectors) |
| `validate-expanso-pipeline` | check a pipeline with both `expanso-edge validate` and `expanso-cli job validate --offline`, and fix what they report |
| `deploy-expanso-job` | install the CLIs, connect to Expanso Cloud, deploy a job and confirm it executed |
| `debug-expanso-job` | work out why a job is `degraded`, `failed`, or produced no output |

Commands: `/expanso:find`, `/expanso:new-pipeline`, `/expanso:validate`,
`/expanso:deploy`. In chat on claude.ai the commands load as skills and apply
when the request fits.

## Use it

Ask for the data job in plain terms, for example "cut our access-log volume but
keep every error", "fan out webhooks to two endpoints", or "why is my Expanso
job degraded?". Claude checks the catalog for a proven job first, adapts or
writes the job spec, validates it, and, if you have the Expanso CLIs installed
and ask it to, deploys it and checks that it ran.

Deploying needs an Expanso Cloud account and at least one connected edge node.
The first five nodes are free. Writing and reviewing pipelines needs neither.

## Data and network use

The plugin itself is Markdown only. It bundles no MCP server, hooks,
executables or credentials, and it sends nothing anywhere on its own. What
Claude does while following its skills:

- **Reads the public catalog.** To find existing jobs, Claude may fetch the
  public JSON files `catalog.json` and `validation-report.json` from
  `https://skills.expanso.io`. No user data is sent in those requests.
- **Runs the Expanso CLIs on your machine, when you ask it to.** In Claude Code
  and Cowork, Claude can run `expanso-cli` and `expanso-edge` commands (each
  one needs your permission). `expanso-cli` talks to the Expanso Cloud control
  plane in the profile you configured, using your own API key, and sends it the
  job spec you deploy. The install commands the skills show download the
  binaries from `https://get.expanso.io`.
- **Pipelines move data where you point them.** A deployed pipeline runs on
  your edge node and reads and writes whatever its inputs and outputs name.
  A pipeline that calls a third-party API (an LLM provider, Slack, a webhook)
  sends that provider the credential and the data the pipeline gives it. The
  skills tell Claude to state that for every pipeline it writes.

Credentials are never written into pipeline files. They are read from the
environment of the node that executes the job.

## Links

- Expanso Skills catalog: <https://skills.expanso.io>
- Source: <https://github.com/expanso-io/skills.expanso.io>
- Expanso documentation: <https://docs.expanso.io>
- Expanso Cloud: <https://cloud.expanso.io>

## License

MIT. See [LICENSE](LICENSE).
