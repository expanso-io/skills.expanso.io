# text-analyze

> Analyze text for sentiment, entities, topics, and key phrases.

Extract structured insights from any text. Perfect for:
- Customer feedback analysis
- Social media monitoring
- Content categorization
- Named entity recognition

## Quick Start

### CLI Mode

```bash
export OPENAI_API_KEY=sk-...

# Full analysis
echo "I absolutely love Apple's new iPhone! The camera is incredible." | \
  expanso-edge run pipeline-cli.yaml

# Specific analyses only
echo "Apple Inc. announced Q1 earnings..." | \
  ANALYSES="entities,sentiment" expanso-edge run pipeline-cli.yaml
```

### MCP Mode

```bash
PORT=8080 expanso-edge run pipeline-mcp.yaml &

curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Microsoft CEO Satya Nadella announced new AI features in Seattle.",
    "analyses": ["entities", "sentiment"]
  }'
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `ANALYSES` | No | all | Comma-separated: sentiment,entities,topics,keywords |
| `PORT` | No | 8080 | HTTP port for MCP mode |

## Analysis Types

| Type | Description | Output |
|------|-------------|--------|
| `sentiment` | Positive/negative/neutral classification | label, score (0-1), explanation |
| `entities` | Named entity recognition | text, type, position |
| `topics` | Main topics/themes | list of topics |
| `keywords` | Important words/phrases | list of keywords |

## Example Output

### Input
```
Apple Inc. CEO Tim Cook announced record quarterly revenue of $123.9 billion
in Cupertino yesterday. Investors responded positively to the news.
```

### Output
```json
{
  "analysis": {
    "sentiment": {
      "label": "positive",
      "score": 0.85,
      "explanation": "The text describes 'record revenue' and 'positive' investor response."
    },
    "entities": [
      {"text": "Apple Inc.", "type": "ORG", "start": 0, "end": 10},
      {"text": "Tim Cook", "type": "PERSON", "start": 15, "end": 23},
      {"text": "$123.9 billion", "type": "MONEY", "start": 55, "end": 69},
      {"text": "Cupertino", "type": "LOCATION", "start": 73, "end": 82},
      {"text": "yesterday", "type": "DATE", "start": 83, "end": 92}
    ],
    "topics": ["corporate earnings", "technology", "finance"],
    "keywords": ["Apple", "revenue", "quarterly", "record", "investors"]
  },
  "metadata": {
    "skill": "text-analyze",
    "input_hash": "abc123...",
    "trace_id": "550e8400-..."
  }
}
```

## Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| `PERSON` | People, characters | Tim Cook, John Doe |
| `ORG` | Organizations | Apple Inc., NASA |
| `LOCATION` | Places | Cupertino, California |
| `DATE` | Dates and times | yesterday, January 2026 |
| `MONEY` | Monetary values | $123.9 billion |
| `PRODUCT` | Products | iPhone, Model 3 |
| `EVENT` | Events | WWDC, Olympics |

## Related Skills

- [text-summarize](../text-summarize/) - Summarize text
- [pii-detect](../pii-detect/) - Detect personally identifiable information
- [json-extract](../json-extract/) - Extract structured JSON

---

*Built with [Expanso Edge](https://expanso.io) - Your keys, your machine.*
