"""Metadata-aware retrieval and deterministic risk-to-query translation."""

from __future__ import annotations

from app.rag.embedder import Embedder
from app.rag.models import RetrievalQuery, RetrievalResult
from app.rag.vector_store import VectorStore
from app.schemas import RiskEngineInput
from app.schemas.common import HazardCode, PermitType, RiskType, ZoneId


_ZONE_NAMES = {
    ZoneId.STORAGE_AREA: "storage area",
    ZoneId.PUMP_STATION: "pump station",
    ZoneId.PIPELINE_AREA: "pipeline area",
    ZoneId.MAINTENANCE_AREA: "maintenance area",
    ZoneId.CONTROL_ROOM: "control room",
}


def risk_to_retrieval_query(risk: RiskEngineInput, top_k: int = 5) -> RetrievalQuery:
    """Create a stable evidence query from the existing risk-engine contract."""

    hazard_words = {
        HazardCode.RISING_LEL: "hydrocarbon gas concentration is rising",
        HazardCode.HOT_WORK_ACTIVE: "hot work is active",
        HazardCode.VENTILATION_FAILURE: "ventilation is unavailable",
        HazardCode.WORKERS_PRESENT: "workers are present",
    }
    details = [hazard_words.get(hazard, hazard.value.replace("_", " ").lower()) for hazard in risk.contributing_factors]
    detail_text = ", ".join(details[:-1]) + (f" and {details[-1]}" if len(details) > 1 else (details[0] if details else ""))
    query_text = (
        f"{risk.predicted_incident} risk at a refinery {_ZONE_NAMES[risk.zone_id]}. "
        f"{detail_text.capitalize()}. Retrieve applicable stop-work precautions, "
        "gas-testing requirements, permit suspension, isolation verification, "
        "evacuation procedures, reauthorization conditions, and similar incidents."
    )
    permits = [PermitType.HOT_WORK] if HazardCode.HOT_WORK_ACTIVE in risk.contributing_factors else []
    return RetrievalQuery(
        query_text=query_text,
        risk_types=[risk.risk_type],
        hazard_codes=list(risk.contributing_factors),
        permit_types=permits,
        top_k=top_k,
    )


class Retriever:
    """Embed a query, apply controlled metadata filters, and return evidence."""

    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    def retrieve(
        self,
        query: RetrievalQuery | str,
        *,
        mode: str = "all",
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        if isinstance(query, str):
            query = RetrievalQuery(query_text=query, top_k=top_k or 5)
        elif top_k is not None:
            query = query.model_copy(update={"top_k": top_k})
        if mode not in {"regulations_and_sops", "similar_incidents", "all"}:
            raise ValueError("mode must be regulations_and_sops, similar_incidents, or all")
        document_types = list(query.document_types)
        if mode == "regulations_and_sops":
            document_types = ["REGULATION", "SOP"]
        elif mode == "similar_incidents":
            document_types = ["HISTORICAL_INCIDENT", "NEAR_MISS", "CASE_STUDY"]
        elif document_types:
            document_types = list(document_types)
        filters = {
            "risk_types": [value.value for value in query.risk_types],
            "hazard_codes": [value.value for value in query.hazard_codes],
            "permit_types": [value.value for value in query.permit_types],
            "document_type": document_types,
        }
        vectors = self.embedder.embed([query.query_text])
        if len(vectors) != 1:
            raise ValueError("Embedder must return exactly one vector for one query")
        return self.store.query(vectors[0], top_k=query.top_k, filters=filters)
