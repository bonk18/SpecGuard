"""Run grounded safety-intelligence generation with local retrieval.

From the repository root (Mock provider is the default):

    PYTHONPATH=backend .venv/bin/python backend/examples/generate_safety_intelligence.py

Set LLM_PROVIDER=groq, LLM_MODEL, and GROQ_API_KEY to exercise Groq. A missing
or unavailable provider still produces a valid cautious fallback response.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv

from app.intelligence import SafetyIntelligenceService, provider_from_environment
from app.rag.chunker import chunk_pages
from app.rag.document_loader import load_document
from app.rag.embedder import DeterministicEmbedder
from app.rag.metadata import enrich_chunks, load_manifest
from app.rag.retriever import Retriever
from app.rag.text_cleaner import clean_pages
from app.rag.vector_store import JsonVectorStore
from app.schemas import RiskEngineInput


ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = ROOT / "backend/data/knowledge"
MANIFEST = KNOWLEDGE_ROOT / "manifests/documents.json"


def _build_offline_retriever(store_path: Path) -> Retriever:
    entries = [entry for entry in load_manifest(MANIFEST) if entry.is_synthetic]
    chunks = []
    for entry in entries:
        pages = load_document(entry.to_source_document(), KNOWLEDGE_ROOT)
        chunks.extend(enrich_chunks(chunk_pages(clean_pages(pages))))
    embedder = DeterministicEmbedder()
    store = JsonVectorStore(store_path)
    store.add(chunks, embedder.embed([chunk.text for chunk in chunks]))
    return Retriever(store, embedder)


def main() -> None:
    load_dotenv(ROOT / ".env")
    risk = RiskEngineInput(
        alert_id="ALT-DEMO-SAFETY-001",
        timestamp="2026-07-22T09:30:00Z",
        zone_id="ZONE_B",
        equipment_ids=["P-101"],
        risk_type="FIRE_EXPLOSION",
        risk_score=0.88,
        severity="CRITICAL",
        predicted_incident="Hydrocarbon flash fire",
        contributing_factors=[
            "RISING_LEL",
            "HOT_WORK_ACTIVE",
            "VENTILATION_FAILURE",
            "WORKERS_PRESENT",
        ],
        sensor_evidence={
            "hydrocarbon_gas": {"trend": "rising"},
            "ventilation": {"status": "failed"},
            "workers_present": True,
        },
        active_permit_ids=["PTW-DEMO-HOT-WORK"],
        maintenance_event_ids=["MNT-DEMO-VENTILATION"],
        model_confidence=0.86,
    )
    with TemporaryDirectory(prefix="specguard-intelligence-") as temporary:
        retriever = _build_offline_retriever(Path(temporary) / "chunks.json")
        response = SafetyIntelligenceService(
            retriever, provider_from_environment()
        ).generate(risk)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
