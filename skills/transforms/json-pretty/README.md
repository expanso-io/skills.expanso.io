# json-pretty

Pretty print JSON with proper indentation.

## Usage

For a first run on Expanso Cloud, use `pipeline-cloud.yaml`: it needs no
credentials and no terminal input. Its header lists the validate, deploy and
confirm-execution commands.

`pipeline-cli.yaml` reads `stdin`, so it cannot receive input once scheduled on
a remote node. Check it locally with:

```bash
expanso-edge validate pipeline-cli.yaml
```
