# SpecGuard RAG Knowledge Base

This is the Task 2 retrieval layer for the refinery-safety prototype. It stops
at evidence retrieval: it does not generate final recommendations, call an
LLM, or control refinery equipment.

## What RAG is and why SpecGuard uses it

Retrieval-augmented generation (RAG) first finds relevant passages in a known
collection and may later give those passages to a language model. Retrieval is
evidence, not a validated answer. SpecGuard uses it to connect sensor, permit,
and risk signals to procedures, regulations, and incident records that a human
reviewer can inspect and cite.

```text
authorized local documents
  -> loader -> conservative cleaner -> chunker -> safety metadata
  -> local embeddings -> persistent JSON vector store -> filtered retrieval
```

## Folder structure

```text
backend/app/rag/
├── models.py             # internal page, chunk, manifest, and result models
├── document_loader.py    # PDF, Markdown, and plain-text loading
├── text_cleaner.py       # conservative layout cleanup
├── chunker.py            # deterministic section-aware chunks
├── metadata.py           # manifest parsing and keyword tags
├── embedder.py           # deterministic and local Sentence Transformers modes
├── vector_store.py       # persistent JSON vector store
├── retriever.py          # filtering and RiskEngineInput conversion
└── cli.py                # inspect, ingest, and query commands

backend/data/knowledge/
├── raw/case_studies/
├── raw/regulations/
├── raw/synthetic_sops/
├── manifests/documents.json
├── processed/
└── vector_store/
```

The manifest currently contains six public synthetic SOPs and twelve local PDF
entries. The PDFs use their real local filenames, have no fabricated URLs, and
are marked `pending_review` and not public-repository safe until authorization
and provenance are verified.

## Loading documents

The loader accepts `.pdf`, `.md`, and `.txt`. Markdown and text become page 1;
PDF pages retain their page numbers. Source document ID, title, local path,
URL, authority, publication metadata, version, tags, document type, and
synthetic status are carried into pages, chunks, and result metadata.

Missing files, empty files, unsupported extensions, decode errors, PDF parser
errors, and PDFs with no extractable text are reported as skips. OCR is not
attempted. A scanned PDF therefore needs an authorized, separate OCR workflow.

## Conservative cleaning

Cleaning removes null bytes, normalizes line endings and repeated whitespace,
collapses excessive blank lines, and joins only a clear lowercase word break at
a line boundary. An exact first/last line repeated across pages is treated as a
header/footer. Headings, numbered clauses, bullets, equipment identifiers,
units, and negations such as `not`, `must not`, and `prohibited` are preserved.

Aggressive rewriting is dangerous for safety documents: changing one negation,
unit, identifier, or clause can reverse the meaning of a control. The cleaner
therefore does not paraphrase or summarize.

## Chunking and metadata

The chunker uses word count as a transparent token approximation. Defaults are
700 words per chunk and 120 words of overlap, both configurable. It recognizes
Markdown and numbered headings, emits no empty or meaningless tiny chunks, and
stores deterministic IDs, page ranges, section hints, document metadata, and
source provenance. Rebuilding the same source produces the same chunk IDs.

`metadata.py` applies deterministic keyword mappings; no LLM is used for
ingestion. It reuses the controlled `RiskType`, `HazardCode`, and `PermitType`
enums from `app.schemas.common`. Supported mappings include `FIRE_EXPLOSION`,
`TOXIC_GAS_EXPOSURE`, `OXYGEN_DEFICIENCY`, `OVERPRESSURE`,
`EQUIPMENT_FAILURE`, `RISING_LEL`, `HIGH_H2S`, `LOW_OXYGEN`,
`PRESSURE_RISING`, `VENTILATION_FAILURE`, `INCOMPLETE_ISOLATION`,
`HOT_WORK_ACTIVE`, `CONFINED_SPACE_ACTIVE`, `WORKERS_PRESENT`,
`OVERDUE_MAINTENANCE`, and the requested permit types.

## Embeddings and vector retrieval

`DeterministicEmbedder` is a hash-based fake embedder for tests and repeatable
offline demos. It never downloads a model. `SentenceTransformerEmbedder` is the
real local adapter and defaults to
`sentence-transformers/all-MiniLM-L6-v2`; its model name is configurable with
`SPECGUARD_EMBEDDING_MODEL` or the adapter constructor. It batches text,
normalizes vectors, and reports a helpful error if the package or model is not
available. No API key or paid API is required.

The lightweight persistent backend is an inspectable JSON file. It supports
add, rebuild, persistent reload, document replacement, top-k cosine search,
document-type/risk/hazard/permit filters, dimension validation, and deterministic
tie ordering. Reprocessing a document replaces its records, so repeated
ingestion does not create uncontrolled duplicate chunks. Generated indexes are
ignored by Git.

Every result includes chunk ID, text, score, title, document type, source path
or URL, page range, section when available, synthetic status, and the complete
chunk metadata dictionary.

## Adding an authorized PDF

1. Obtain the document through a permitted, authorized process; do not
   automatically download standards or incident reports.
2. Place it in `backend/data/knowledge/raw/regulations/` or
   `backend/data/knowledge/raw/case_studies/`.
3. Add a manifest entry using a path relative to
   `backend/data/knowledge/`, for example
   `raw/regulations/oisd_std_116_fire_protection.pdf`.
4. Use the real title and filename, a real source URL only when verified, the
   correct authority/publication/version values, and an optional SHA-256
   checksum. Use `pending_review` or `missing` when it is not ready; never
   pretend a missing file was loaded.
5. Confirm licensing and set `allowed_for_public_repo` correctly. A local file
   marked false must not be committed or redistributed.
6. Ingest, inspect the report, and verify extracted pages and attribution.

## Verified commands

From the repository root, the offline deterministic commands are:

```bash
PYTHONPATH=backend .venv/bin/python -m app.rag.cli inspect
PYTHONPATH=backend .venv/bin/python -m app.rag.cli ingest --rebuild
PYTHONPATH=backend .venv/bin/python -m app.rag.cli query \
  "Hydrocarbon gas is rising near Pump P-101 while a hot-work permit is active. Ventilation has failed and workers are present in Zone B." \
  --mode all --top-k 6 --document-type SOP
```

The equivalent commands from `backend/` are:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli inspect
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli ingest --rebuild
```

`inspect` displays manifest entries, statuses, persisted chunk count, and
embedding dimension. `ingest` displays documents loaded/skipped, missing files,
extraction failures, chunks created/indexed, and every skip reason. Use
`--embedder sentence-transformers` before the subcommand when the package and
model are installed locally. Query also supports `--mode` values
`regulations_and_sops`, `similar_incidents`, or `all`, plus repeatable
`--risk-type`, `--hazard`, `--permit-type`, and `--document-type` filters.

## RiskEngineInput integration

`risk_to_retrieval_query` deterministically converts the existing public
`RiskEngineInput` into a `RetrievalQuery`. It includes the predicted incident,
zone, hazard wording, and requests for stop-work precautions, gas testing,
permit suspension, isolation verification, evacuation, reauthorization, and
similar incidents. It also carries controlled risk, hazard, and hot-work permit
filters. No LLM is involved.

```python
from app.rag.retriever import risk_to_retrieval_query

retrieval_query = risk_to_retrieval_query(risk_engine_input)
results = retriever.retrieve(retrieval_query, mode="regulations_and_sops")
```

This task does not map results into a final `SafetyIntelligenceResponse` yet.
Future actions must remain advisory, human-approved, and explicitly supported
by checked evidence.

## Tests, limitations, and safety

Run the complete offline suite with:

```bash
.venv/bin/python -m pytest
```

Tests use local fixtures and deterministic embeddings; they require no internet,
model download, API key, or real OISD PDF. The prototype has no OCR, no
validated industrial thresholds, no guarantee that keyword tags are complete,
and no guarantee that a retrieved passage is current or sufficient. Synthetic
SOPs are not approved procedures. Never use this repository to direct real
industrial work, bypass human approvals, or operate equipment.

Respect copyright, licensing, and access restrictions for every local source.
Do not commit `.env`, model caches, generated indexes, restricted standards, or
incident reports without authorization.
