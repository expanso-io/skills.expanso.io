---
description: Validate an Expanso pipeline with both validators and fix what they report
argument-hint: <path to pipeline YAML>
---

Use the `validate-expanso-pipeline` skill on: $ARGUMENTS

Run `expanso-edge validate` and `expanso-cli job validate --offline`, fix each reported error, re-run until both pass, then check the items neither validator catches. Report the two results separately with the tool version, and state that the pipeline has not been executed.
