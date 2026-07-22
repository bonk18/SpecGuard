# SpecGuard

SpecGuard is an AI-powered industrial safety intelligence platform for
petroleum-refinery maintenance operations. It combines operational signals,
compound-risk detection, safety-document retrieval, and human-reviewed
interventions in one prototype platform.

## Problem

Industrial facilities often already have SCADA, gas sensors, permits, work
orders, shift logs, and cameras. These sources usually remain isolated,
however, so weak signals are considered independently and are not converted
into timely compound-risk decisions. SpecGuard connects those signals and
returns evidence-backed context for a qualified human reviewer.

## Core demo scenario

The primary demonstration follows Pump P-101 during maintenance:

- A hot-work permit is active.
- Hydrocarbon gas concentration is rising.
- Ventilation fails.
- Workers remain in Zone B.
- No individual signal initially exceeds its standalone alarm threshold.

SpecGuard correlates the permit, atmosphere, ventilation, maintenance, and
worker context to identify an emerging fire/explosion risk earlier than a
single-sensor alarm workflow.

## Architecture

```text
Digital twin
    ↓
SCADA / gas / permit / maintenance / worker / CCTV streams
    ↓
Compound-risk engine
    ↓
RiskEngineInput
    ↓
Safety-document and incident RAG
    ↓
SafetyIntelligenceResponse
    ↓
FastAPI
    ↓
Frontend command centre
```

The current RAG layer stops at evidence retrieval. Future response generation
must remain advisory and human-approved; it must not directly control plant
equipment.

## Platform components

- Synthetic petroleum-refinery digital twin with process, SCADA, gas, permit,
  maintenance, shift-log, worker, and CCTV event streams.
- Compound-risk contracts shared through Pydantic schemas.
- Deterministic local safety metadata and persistent JSON vector retrieval.
- Authorized local incident/regulatory documents and clearly labelled synthetic
  SOPs.
- FastAPI backend foundations and a frontend safety-command-centre scaffold.
- Evidence-backed intervention workflow for the next intelligence layer.

## Repository structure

```text
digital twin/                  # synthetic refinery simulator and scenarios
backend/app/schemas/           # public Pydantic safety contracts
backend/app/rag/               # loading, cleaning, chunking, embedding, retrieval
backend/data/knowledge/        # manifest, source corpus, and generated local index
backend/tests/                 # schema and RAG tests
backend/examples/              # integration handoff examples
docs/                          # schema and RAG architecture guides
frontend/                      # frontend command-centre scaffold
```

## Current implementation status

### Completed

- Digital-twin simulator with compound refinery scenarios.
- Shared safety schemas, including `RiskEngineInput` and `SafetyIntelligenceResponse`.
- PDF/Markdown/text RAG ingestion and conservative cleaning.
- Deterministic offline embeddings and persistent local vector retrieval.
- Optional Sentence Transformers support using MiniLM.
- Synthetic SOP corpus and official/local incident corpus, subject to provenance and licensing review.
- Metadata filtering, deterministic safety-aware reranking, tests, and subsystem documentation.
- Integrated the compound-risk model with live simulated event streams via FastAPI endpoints.
- Connected a beautiful, responsive frontend safety-command-centre dashboard with live telemetry, dynamic risk mapping, and CCTV feed UI.
- Simulated real-world metrics (pressure, LEL, H2S) mapped to accurate simulation scenarios.

### Next

- Add an LLM-grounded intelligence response while preserving citations and human approval.
- Evaluate compound detection against a single-sensor baseline.

## Quick start

Create and activate a virtual environment, then install the core and test
dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

The deterministic backend test command verified in this repository is:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v
```

To enable real local semantic embeddings, install the optional RAG dependency
set. This downloads no model during tests; model weights are managed by the
local Sentence Transformers environment:

```bash
pip install -r requirements-rag.txt
```

### Rebuild and query the knowledge base

From `backend/`, the verified deterministic commands are:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli inspect
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli ingest --rebuild
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli query \
  "Hydrocarbon gas is rising near Pump P-101 while hot work is active, ventilation has failed and workers are present" \
  --mode all --top-k 6
```

Use optional MiniLM embeddings explicitly after installing
`requirements-rag.txt`:

```bash
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli ingest --rebuild \
  --embedder sentence-transformers
PYTHONPATH=. ../.venv/bin/python -m app.rag.cli query \
  --embedder sentence-transformers \
  "Hydrocarbon gas is rising while hot work is active and ventilation has failed"
```

The default is deterministic. It can also be selected through
`RAG_EMBEDDER=deterministic` or `RAG_EMBEDDER=sentence-transformers`. The real
model defaults to `sentence-transformers/all-MiniLM-L6-v2` and can be changed
with `RAG_EMBEDDING_MODEL`.

### RiskEngineInput handoff example

After rebuilding the index, run:

```bash
PYTHONPATH=backend .venv/bin/python backend/examples/risk_to_retrieval.py
```

The example converts a validated `RiskEngineInput` into a deterministic query,
searches operational SOP/regulatory evidence and historical incidents, and
prints structured JSON with raw similarity, final reranking score, source
metadata, synthetic status, and matched safety tags.

### Run a digital-twin scenario

The following short smoke command was verified without generating a large
dataset:

```bash
cd "digital twin"
../.venv/bin/python simulate.py --scenario explosion_risk --duration 10 \
  --format json --output /tmp/specguard-digital-twin-smoke --quiet
```

For a full scenario, omit `--duration` or select another scenario such as
`hot_work_gas_leak`, `ventilation_failure`, or `confined_space`. See
`digital twin/README.md` for simulator details.

### Run the Live Dashboard (FastAPI + Frontend)

To run the fully integrated safety command centre, launch the FastAPI server:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python -m uvicorn app.main:app --reload
```

Then, open your web browser and navigate to `http://127.0.0.1:8000` to view the live responsive UI with real-time telemetry updates!

## Documentation

- [Schema architecture](docs/SCHEMA_ARCHITECTURE.md) explains public contracts,
  validation, ownership, and integration boundaries.
- [RAG knowledge base](docs/RAG_KNOWLEDGE_BASE.md) explains the corpus,
  ingestion, embeddings, filters, reranking, and safety limitations.

## Safety disclaimer

SpecGuard is a hackathon prototype. Synthetic SOPs are explicitly **not for
real industrial use**. Retrieved evidence and future recommendations require
qualified human review and approval. The platform does not directly control
industrial equipment, replace approved refinery procedures, establish universal
alarm thresholds, or override a facility's permit, isolation, emergency, or
engineering controls.
