# text-translate

Translate text between languages using LLM.

## Usage

```bash
TARGET=spanish echo "Hello, how are you?" | expanso-edge run pipeline-cli.yaml
TARGET=french echo "Good morning" | expanso-edge run pipeline-cli.yaml
```

## Output

```json
{
  "translation": "Hola, ¿cómo estás?",
  "source_language": "english",
  "target_language": "spanish"
}
```
