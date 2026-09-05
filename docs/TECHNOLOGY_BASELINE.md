# Technology baseline

Status: approved foundation baseline for local development and CI. Version
ranges below reflect the repository dependency contract; the exact runtime and
model used for a research run must still be recorded in its manifest.

## Approved baseline

| Area | Baseline | Current status |
| --- | --- | --- |
| Runtime | Python 3.13; UTF-8 output | CI baseline; local runtime must be recorded |
| API/application | FastAPI `>=0.115,<1`, Uvicorn `>=0.30,<1` | Implemented |
| Schemas | Pydantic `>=2.9,<3` | Implemented |
| HTTP/config | HTTPX `>=0.28,<1`, python-dotenv `>=1.0,<2`, multipart uploads | Implemented |
| Tests | pytest `>=8,<9` | Implemented; CI uses Fake provider |
| Local inference | Ollama HTTP API through the local adapter | Implemented; target-machine gate pending for M0 |
| Retrieval | Deterministic lexical retrieval and chunk IDs at M0 | Implemented; later embedding/vector work is milestone-scoped |
| UI | FastAPI-served static HTML/CSS/JS under `app/static/` | Implemented; no separate Node frontend currently exists |
| Inference policy | Local Ollama or Fake provider; no hosted inference | Approved invariant |

The `requirements.txt` file is the dependency source of truth for this
baseline. CI has read-only repository permissions and contains no model or cloud
inference secrets.

## Model candidate versus frozen model

`LOCAL_LLM_MODEL=qwen3:4b` is the current local model candidate and default
configuration. It is not a frozen model claim. The Fake provider uses
`fake-s0-v2` for deterministic tests and is not a substitute for local-model
calibration.

A model becomes frozen for an M0/M1/M2 evidence package only when the relevant
gate accepts it and the manifest records, at minimum:

- exact Ollama model tag and, where available, digest/checksum;
- provider/runtime version and model options such as JSON mode or thinking
  settings;
- hardware/runtime identity and the corpus/index snapshot;
- effective configuration and hash; and
- the accepted calibration/evaluation boundary and known limitations.

Changing any of these can make a run non-comparable. Re-run the appropriate
gate and issue a new manifest rather than silently relabeling old results.

## Persistence and retrieval responsibilities

The current M0 candidate uses JSON files (`data/sources.json` and run JSON
artifacts) so that the technical slice remains small and inspectable. The
approved responsibilities for a more durable implementation are:

| Concern | SQLite | Qdrant |
| --- | --- | --- |
| Run metadata, status, attempts, checkpoints, and ledger reconciliation | System of record | Not responsible |
| Source/chunk registry, versions, hashes, and corpus membership | System of record | Stores only retrieval-linked identifiers/payload metadata |
| Structured task results, failure taxonomy, and audit references | System of record | Not responsible |
| Embeddings and nearest-neighbor candidate retrieval | Not responsible | Vector index, local and versioned |
| Canonical source text, raw traces, manifests, and export files | References/metadata only | References/metadata only |

SQLite and Qdrant are complementary, not interchangeable. IDs, corpus snapshot
IDs, and content hashes join vector hits back to the canonical source registry;
an index hit alone is never a citation. Qdrant is optional until the relevant
milestone requires and evaluates vector retrieval. Introducing either store
must preserve the current local-first boundary and a restorable export path.

## Milestone technology boundaries

- M0: file-backed source/run artifacts, lexical retrieval, Vanilla RAG A,
  validated locators, hard budgets, and basic trace/metrics.
- M1: the same codebase with A/B/C, P-lite, rules-only N, O-lite, and a scored
  pilot. Storage/index changes are allowed only when they preserve comparability
  and are recorded in the manifest.
- M2: full P/N/O, six conditions, frozen benchmark and manifests, canonical
  attempts, grading, statistics, ablations, and failure analysis. A SQLite
  ledger and/or a Qdrant retrieval index may support this only with explicit
  versioning, integrity checks, and restore evidence.

No technology choice in this document changes the research questions, adds a
research module, or permits cloud inference.
