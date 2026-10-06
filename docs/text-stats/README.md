# text-stats

Calculate detailed text statistics.

## Usage

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
```

## Output

```json
{
  "characters": 29,
  "characters_no_spaces": 24,
  "words": 6,
  "lines": 1,
  "sentences": 2,
  "avg_word_length": 4,
  "reading_time_minutes": 1
}
```
