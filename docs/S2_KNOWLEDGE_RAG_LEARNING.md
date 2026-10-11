# Sprint 2: Knowledge and RAG learning map

This note describes the current Sprint 2 path. PostgreSQL is authoritative;
the vector index is optional, derived data. The default `VECTOR_BACKEND` is
`disabled`, so the existing lexical retrieval path remains the default. Set it
explicitly to `qdrant` to use the local Qdrant candidate index. An explicitly
selected vector backend that fails does not silently fall back to lexical
retrieval.

## 1. Upload and source lifecycle

`POST /api/sources/file` accepts TXT, Markdown, and text-only PDF. The
extraction layer validates the file and produces normalized text plus
provenance. `POST /api/sources/text` accepts text directly. Both paths create
canonical source/chunk rows in PostgreSQL, then index the READY source when a
derived backend is enabled. An extraction, persistence, or configured index
failure must not be reported as READY; index failures produce a visible error
and mark the source FAILED.

The lifecycle is:

```text
PROCESSING -> READY
           -> FAILED
```

Source list/detail endpoints expose the owner’s sources; detail includes the
current processing status and chunk provenance.

## 2. PostgreSQL and Qdrant responsibilities

- PostgreSQL stores users’ canonical source, chunk text, stable chunk/source
  IDs, status, and provenance. It is the source of truth.
- Qdrant stores derived vectors with `owner_user_id`, `source_id`, `chunk_id`,
  provenance, and embedding-version payload. It can be recreated from READY
  PostgreSQL sources by calling `CandidateIndex.index_source` per source; no
  bulk rebuild command is currently provided.
- `LocalHashEmbedder` (`local-hash-embedding-v1`) is a deterministic lexical
  hash vectorizer, not a semantic embedding model.
- `VECTOR_BACKEND=disabled` preserves lexical retrieval. `memory` is a
  process-local test/demo index. `qdrant` selects the local persistent Qdrant
  index. A selected vector backend failure is explicit, never a silent
  lexical fallback.

## 3. Question, retrieval, and evidence flow

`POST /api/chat` validates the authenticated owner, conversation, and selected
source IDs before the run starts. The pipeline loads chunks from that owner’s
PostgreSQL store. With vector retrieval enabled, Qdrant receives owner and
optional source filters in the candidate-search request before top-k; returned
IDs are hydrated only from the owner-scoped canonical chunk set. Otherwise,
the lexical retriever scores the PostgreSQL chunks. Both paths produce the
same canonical `SourceChunk` evidence shape for the answer pipeline.

Each retrieval event records the selected backend and candidate/selected
chunk IDs. Evidence sent to the answerer carries canonical chunk IDs. The
answerer’s citations are validated against supplied evidence before they are
returned; invalid IDs cannot become accepted citations.

## 4. Conversation context and security boundary

The current conversation may contribute a bounded recent-history suffix to
help interpret a follow-up question. It is marked `is_rag_evidence: false` and
is not added to the source chunks or citation set. User identity is resolved
from the session; source selection is checked for ownership before retrieval;
Qdrant candidate searches apply owner filtering before top-k; canonical chunk
hydration also uses only the current owner’s source store.

## 5. Main module inputs and outputs

| Module | Input | Output / responsibility |
| --- | --- | --- |
| `app/ingestion/documents.py` | uploaded bytes, name, media type | normalized text and extraction provenance; rejects unsupported or textless files |
| `app/storage/postgres/runtime.py` | authenticated owner, source text or IDs | canonical source/chunk persistence, status, owner-scoped reads and selection validation |
| `app/retrieval/embeddings.py` | text | versioned deterministic local hash vector |
| `app/retrieval/candidate_index.py` | owner-scoped READY source and vector store | derived source indexing and owner/source-scoped vector candidates |
| `app/storage/vector_store.py` | vectors and owner/source filters | in-memory or local Qdrant upsert/search; filters are included in candidate request |
| `app/retrieval/text.py` | query and canonical chunks | lexical ranking, chunking, token budgeting |
| `app/research/pipeline.py` | question, condition, owner source/run stores | retrieval, task execution, trace, grounded run result; retrieval backend is explicitly recorded |
| `app/research/conversation_context.py` | current conversation messages | bounded context marked as non-evidence |
| `app/research/vanilla.py` and `app/core/citations.py` | answer request and evidence chunks | answer result and citation validation against canonical chunk IDs |

## 6. Suggested student reading order

1. `app/main.py` — authenticated upload/chat endpoints and backend selection.
2. `app/ingestion/documents.py` — supported formats and extraction failures.
3. `app/retrieval/text.py` — chunking, lexical ranking, and context cap.
4. `app/retrieval/embeddings.py` and `app/retrieval/candidate_index.py` — the
   explicitly versioned derived-index path.
5. `app/storage/vector_store.py` — owner/source filtering and Qdrant adapter.
6. `app/storage/postgres/runtime.py` — canonical persistence and owner checks.
7. `app/research/pipeline.py`, then `app/research/vanilla.py` and
   `app/core/citations.py` — retrieval-to-answer and evidence-to-citation.
8. `app/research/conversation_context.py` — follow-up context boundary.

## 7. Relevant focused tests

- `tests/test_s2_hai_ingestion.py` — supported extraction and ingestion.
- `tests/test_s2_hai_lifecycle.py` — source terminal status.
- `tests/test_s2_hai_provenance.py` — source/chunk provenance.
- `tests/test_s2_hai_qdrant_index.py` — Qdrant request filters, local upsert,
  owner/source top-k, ingestion failure behavior, and pipeline integration.
- `tests/test_s2_hai_source_selection.py` and
  `tests/test_source_owner_scope.py` — source ownership boundaries.
- `tests/test_s2_hai_conversation_context.py` — bounded context is not evidence.
- `tests/test_execution_contract.py`, `tests/test_ollama_provider.py`, and
  `tests/test_auth_*_api.py` — result/provider/auth contracts.

PostgreSQL 16 clean-migration, persistence, and reconnect behavior still
requires a live PostgreSQL environment; SQLite unit fixtures are not a
substitute for that gate.
