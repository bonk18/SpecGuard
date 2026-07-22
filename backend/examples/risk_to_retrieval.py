"""Demonstrate the deterministic RiskEngineInput-to-RAG handoff.

Run from the repository root after building the local deterministic index:

    PYTHONPATH=backend .venv/bin/python backend/examples/risk_to_retrieval.py
"""

from __future__ import annotations

import json
from pathlib import Path

from app.rag.embedder import DeterministicEmbedder
from app.rag.models import RetrievalQuery, RetrievalResult
from app.rag.retriever import Retriever, risk_to_retrieval_query
from app.rag.vector_store import JsonVectorStore
from app.schemas import RiskEngineInput


ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "backend/data/knowledge/vector_store/chunks.json"


def _result_payload(result: RetrievalResult) -> dict[str, object]:
    return {
        "chunk_id": result.chunk_id,
        "title": result.source_title,
        "document_type": result.document_type,
        "raw_similarity_score": result.similarity_score,
        "final_score": result.final_score,
        "source_path": result.source_path,
        "source_url": result.source_url,
        "page_start": result.page_start,
        "page_end": result.page_end,
        "section": result.section,
        "is_synthetic": result.is_synthetic,
        "matched_risk_types": result.metadata.get("risk_types", []),
        "matched_hazard_codes": result.metadata.get("hazard_codes", []),
        "matched_permit_types": result.metadata.get("permit_types", []),
        "excerpt": result.text,
    }


def main() -> None:
    if not STORE_PATH.exists():
        raise SystemExit(
            f"Vector index not found at {STORE_PATH}; run app.rag.cli ingest --rebuild first."
        )

    risk = RiskEngineInput(
        alert_id="ALT-DEMO-001",
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
        sensor_evidence={"hc_gas_lel": {"trend": "rising"}},
        active_permit_ids=["PTW-DEMO-HOT-WORK"],
    )
    retrieval_query = risk_to_retrieval_query(risk, top_k=6)
    retriever = Retriever(JsonVectorStore(STORE_PATH), DeterministicEmbedder())

    # Permit metadata remains part of the query text and reranking context, but
    # operational evidence should not exclude a ventilation or evacuation SOP
    # simply because that document is not itself a permit record.
    procedure_query: RetrievalQuery = retrieval_query.model_copy(
        update={"permit_types": [], "top_k": 6}
    )
    sop_results = retriever.retrieve(procedure_query, mode="regulations_and_sops")
    # Incident search keeps the risk and hazard context but does not require an
    # incident chunk to carry the operational permit classification.
    incident_query: RetrievalQuery = retrieval_query.model_copy(
        update={"permit_types": [], "top_k": 5}
    )
    incident_results = retriever.retrieve(incident_query, mode="similar_incidents")

    print(
        json.dumps(
            {
                "query_text": retrieval_query.query_text,
                "risk_engine_input": risk.model_dump(mode="json"),
                "sop_or_regulatory_evidence": [_result_payload(result) for result in sop_results],
                "historical_incident_evidence": [
                    _result_payload(result) for result in incident_results
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
