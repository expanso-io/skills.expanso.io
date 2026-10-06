# audio-duration

Format audio duration from seconds to HH:MM:SS.

## Usage

`expanso-edge run` starts the node agent; it does not run a pipeline file. Check a pipeline locally with `expanso-edge validate`, as below. To execute one, deploy it with `expanso-cli job deploy FILE` from a saved Cloud profile with a connected node, then confirm with `expanso-cli job describe` and `expanso-cli execution list --job-id` (see [Confirm it actually ran](https://github.com/expanso-io/skills.expanso.io#confirm-it-actually-ran)). No Cloud run of this skill has been confirmed. `pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on a remote node and has no supported Cloud run path as written (see [Providing input](https://github.com/expanso-io/skills.expanso.io#providing-input)).

```bash
expanso-edge validate pipeline-cli.yaml
```

## Output

```json
{
  "seconds": 3661,
  "minutes": 61.02,
  "formatted": "01:01:01",
  "short": "01:01:01"
}
```
