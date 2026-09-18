# RAG: fetch, chunk, embed, store, retrieve

Fetch documents over HTTP, split them into paragraph chunks that keep their source URL, embed each chunk with Ollama, store vectors in Qdrant, and answer questions by vector search.

**Use it when you are asked to build:** Document embedding for retrieval (RAG): fetch, chunk, embed, store, search.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21`, on Expanso Cloud (12/12 checks) and on a local-mode node (12/12). The Cloud run was scheduled by label onto one operator-registered node, not a hosted runner, with its dependencies on the same host.

Proved:

- 4 documents fetched over HTTP became 16 chunks, each carrying its source URL through storage and retrieval.
- Stored vectors equal a direct Ollama embedding of the same text (cosine 1.000000); re-ingest is idempotent.
- All 4 test questions returned the right chunk first (qdrant processor search).

Not proved:

- The native qdrant OUTPUT. On expanso-edge v2.1.21 its id mapping could not read message fields or metadata, and the job still reported completed with 0 points. Vectors are written with http_client to the Qdrant REST upsert API instead.

## Components

- inputs: `generate`, `file`
- processors: `http`, `unarchive`, `mapping`, `branch`, `ollama_embeddings`, `qdrant`
- outputs: `http_client`, `file`

## Files

- `docs/data-center-cooling-runbook.md`
- `docs/field-sensor-battery-guide.md`
- `docs/harbor-crane-maintenance.md`
- `docs/index.json`
- `docs/orchard-irrigation-policy.md`
- `pipeline-query.yaml`
- `pipeline.yaml`
- `questions.jsonl`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
ollama pull nomic-embed-text
docker run -d --name qdrant \
  -p 127.0.0.1:6333:6333 -p 127.0.0.1:6334:6334 \
  qdrant/qdrant
curl -X PUT http://127.0.0.1:6333/collections/docs \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"size":768,"distance":"Cosine"}}'
# Serve the sample docs, then set the first http url
# (https://DOCS_HOST/docs/index.json) to
# http://127.0.0.1:8000/docs/index.json:
uv run python -m http.server 8000 --bind 127.0.0.1 &
mkdir -p /var/tmp/expanso-rag \
  /var/tmp/expanso-rag/out
cp questions.jsonl /var/tmp/expanso-rag/questions.jsonl
```

## Validate, deploy, confirm

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-edge validate pipeline-query.yaml
expanso-cli job validate pipeline-query.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job deploy pipeline-query.yaml
expanso-cli job describe rag-ingest
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# points_count should be 16:
curl -s http://127.0.0.1:6333/collections/docs
# after pipeline-query.yaml has run:
head -1 /var/tmp/expanso-rag/out/answers.jsonl
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
