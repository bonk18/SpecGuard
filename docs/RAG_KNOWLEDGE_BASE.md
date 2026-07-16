# SpecGuard RAG Knowledge Base

This document explains the Task 2 knowledge-base foundation for a teammate who
knows basic Python but is new to retrieval-augmented generation (RAG).

## 1. What RAG is

RAG is a two-stage pattern. First, a system retrieves relevant passages from a
known document collection. Later, an AI model may use those passages to write an
explanation. Retrieval evidence is not an answer and does not make a safety
recommendation automatically correct.

SpecGuard currently implements ingestion and retrieval only. It does not call an
LLM and it does not control refinery equipment.

## 2. Why SpecGuard uses RAG

Sensor and permit alerts tell us what the system observes. Procedures,
historical incidents, and authorized regulations provide context for a human
reviewer. Returning passages with document titles, paths, URLs, and page ranges
lets the future intelligence pipeline cite its evidence instead of inventing a
clause or copying an entire document into every response.

The data flow is:

```text
Authorized safety documents
        ↓
Loader
        ↓
Cleaner
        ↓
Chunker
        ↓
Metadata enrichment
        ↓
Embedding model
        ↓
Vector store
        ↓
Retriever
        ↓
EvidenceReference / SimilarIncident
        ↓
Future LLM recommendation pipeline
```

## 3. Embeddings, vector store, retriever, and LLM

An embedding is a list of numbers representing the words and concepts in a
passage. Similar passages have nearby vectors. A vector database stores those
vectors and the original text. A retriever embeds a query, finds nearby vectors,
applies metadata filters, and returns ranked evidence. An LLM is a separate,
later component that could explain the evidence; it is not part of this task.

The repository includes a small persistent JSON vector store so the prototype
works without a database dependency. `SentenceTransformerEmbedder` is an
optional adapter for `sentence-transformers/all-MiniLM-L6-v2` when that model is
available locally. The deterministic embedder is used by tests and offline
demos. A Chroma adapter can be added behind the `VectorStore` interface later if
the project adopts Chroma.

## 4. Folder structure

```text
backend/app/rag/
├── models.py             # internal document and retrieval contracts
├── document_loader.py    # .pdf, .md, and .txt extraction
├── text_cleaner.py       # conservative layout cleanup
├── chunker.py            # deterministic section-aware chunks
├── metadata.py           # manifest parsing and keyword tags
├── embedder.py           # deterministic and optional ML embedders
├── vector_store.py       # persistent backend-neutral store
├── retriever.py          # filtering and risk-to-query conversion
└── cli.py                # ingest, inspect, and query commands

backend/data/knowledge/
├── raw/regulations/      # authorized files added manually; not committed
├── raw/case_studies/     # authorized files added manually; not committed
├── raw/synthetic_sops/   # public prototype Markdown documents
├── processed/            # optional local intermediate files
├── manifests/documents.json
└── vector_store/         # generated JSON index; ignored by Git
```

The internal models in `backend/app/rag/models.py` are deliberately separate
from public API contracts such as `EvidenceReference` and `RiskEngineInput`.

## 5. Add a document legally

Only process material that the team is authorized to use. Do not automatically
download paid, restricted, or copyrighted OISD standards, and do not scrape a
site that prohibits automated downloading. Synthetic SOPs in this repository
are clearly labelled `SYNTHETIC PROTOTYPE SOP — NOT FOR REAL INDUSTRIAL USE`.

To add an authorized PDF manually:

1. Download it legally using the publisher's permitted process.
2. Place it under `backend/data/knowledge/raw/regulations/` or
   `backend/data/knowledge/raw/case_studies/`.
3. Add a manifest entry with the real title, authority, source URL, page/source
   metadata, checksum if available, and `allowed_for_public_repo` set correctly.
4. Run ingestion and inspect the extracted chunks.
5. Verify page numbers and source attribution before using a result.
6. Never commit a restricted document or a generated vector index.

The manifest must not claim that a local file exists when it does not. The
initial manifest contains only public synthetic SOPs.

## 6. Manifest format

`backend/data/knowledge/manifests/documents.json` is a JSON array. Each entry
has a stable `document_id`, title, document type, authority, optional URL and
publication metadata, a repository-relative `local_path`, a synthetic flag,
tags, and `processing_status`. Pydantic validates this file before ingestion.

## 7. Text extraction

Markdown and text files are read as UTF-8 and become one page. PDF files use the
optional `pypdf` dependency and preserve the PDF page number. Pages with no
extractable text are skipped and reported; OCR is intentionally out of scope.
An empty or missing file, unsupported extension, or undecodable file produces a
clear ingestion error.

## 8. Conservative cleaning

Cleaning removes null bytes, normalizes line endings and repeated whitespace,
collapses excessive blank lines, and joins only obvious word breaks at a line
boundary. Repeated page headers and footers are removed only when the exact line
repeats across pages. The cleaner never paraphrases safety text, removes
negations such as “must not,” changes units, or rewrites equipment identifiers.

## 9. Chunking

The chunker recognizes Markdown and numbered headings, uses words as a
transparent token approximation, and defaults to about 700 words with 120 words
of overlap. Both values are configurable. Chunk IDs are deterministic hashes of
the document, position, and text, so rebuilding produces stable identifiers.
Empty or meaningless short chunks are not emitted. Every chunk keeps its
document ID, title, page range, section hint, and source path/URL.

## 10. Metadata

`metadata.py` uses transparent keyword mappings to tag risk types, hazards,
permit types, and equipment families. It recognizes concepts such as
`FIRE_EXPLOSION`, `RISING_LEL`, `VENTILATION_FAILURE`, and `HOT_WORK`. This is
not an LLM classification step. Tags are useful for filtering, but they should
be reviewed when a production knowledge base is introduced.

## 11. Ingestion and queries

From the repository root, use the deterministic offline embedder:

```bash
PYTHONPATH=backend .venv/bin/python -m app.rag.cli ingest --rebuild
PYTHONPATH=backend .venv/bin/python -m app.rag.cli inspect
PYTHONPATH=backend .venv/bin/python -m app.rag.cli query "hot work with rising hydrocarbon gas" --mode regulations_and_sops
```

The CLI reads the manifest, loads only local paths, cleans and chunks pages,
adds deterministic metadata, embeds chunks, and writes the ignored JSON index
under `backend/data/knowledge/vector_store/`. It prints skipped or missing
documents instead of pretending they were ingested.

To use the optional local Sentence Transformers model, install the project's
ML dependencies and run the same commands with `--embedder sentence-transformers`.
The model may need a one-time local download; no API key is required by this
adapter.

Retrieval has three modes: `regulations_and_sops`, `similar_incidents`, and
`all`. Metadata filters are applied before ranked results are returned. Results
are validated `RetrievalResult` objects containing source title, page range,
section, and a score between 0 and 1.

## 12. RiskEngineInput to a retrieval query

The existing public `RiskEngineInput` contract is converted by
`risk_to_retrieval_query`. For example, a Zone B alert for rising LEL, active hot
work, failed ventilation, and workers present becomes a deterministic query for
stop-work precautions, gas testing, permit actions, and similar incidents. The
same risk and hazard enums are reused, so a producer cannot silently change
`HOT_WORK_ACTIVE` into a differently-spelled filter.

```python
from app.rag.retriever import risk_to_retrieval_query

query = risk_to_retrieval_query(risk_engine_input)
results = retriever.retrieve(query, mode="regulations_and_sops")
```

## 13. Later connection to SafetyIntelligenceResponse

This task stops at evidence. A future NLP/RAG service can map each
`RetrievalResult` to the public `EvidenceReference` contract, combine it with
`SimilarIncident` records, and produce a `SafetyIntelligenceResponse`. Any
recommended action must remain advisory and `requires_human_approval=True` by
default. Evidence must be checked and cited; retrieval does not guarantee that
an AI explanation is factually correct or safe for a real refinery.

## 14. Limitations and safety warnings

- The prototype zones and synthetic SOPs are abstractions, not a refinery's
  approved operating procedures.
- Sensor ranges and metadata keywords are not a validated process-safety model.
- Recommendations are advisory and must not directly control equipment.
- Synthetic documents must remain visibly labelled.
- Public or restricted documents may have copyright and licensing conditions;
  preserve attribution and page numbers.
- A retrieved passage can be incomplete, stale, or incorrectly tagged.
- No OISD or other restricted standard is included in this repository.

## 15. Troubleshooting

**No chunks were ingested:** check `local_path`, the repository root, and the
manifest status. Missing files are reported rather than fabricated.

**PDF dependency error:** install the declared `pypdf` dependency from
`requirements.txt`. A scanned PDF may still contain no text; it needs an
authorized manual/OCR workflow, which is outside this task.

**No retrieval results:** run `inspect`, confirm the generated store exists,
try `--mode all`, and check that requested metadata filters match the chunk
tags. Use the deterministic embedder for repeatable offline tests.

**Generated files appear in Git:** the vector-store and processed-data paths
are ignored. Remove local generated files before committing if a custom path was
used.
