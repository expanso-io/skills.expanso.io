---
description: Deploy an Expanso job and confirm it actually executed
argument-hint: <path to pipeline YAML>
---

Use the `deploy-expanso-job` skill to deploy: $ARGUMENTS

Confirm the tools, profile and a connected node matching the job's selector. Validate first, then deploy only after the user agrees. Afterwards check `job describe`, `execution list --job-id` and the output at the destination, and report what you saw. If the job is degraded or failed, switch to the `debug-expanso-job` skill.
