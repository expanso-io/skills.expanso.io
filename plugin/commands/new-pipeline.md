---
description: Write a new Expanso pipeline job spec for a data task
argument-hint: <source, transformation and destination>
---

Use the `build-expanso-pipeline` skill to write an Expanso pipeline job spec for: $ARGUMENTS

Check for an existing job first. Ask only for details you cannot infer (source as seen from the node, one example record, destination, bounded or streaming, node label). Save the spec with its header comment, then validate it with the `validate-expanso-pipeline` skill and report both validator results and what leaves the host.
