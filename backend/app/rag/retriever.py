"""Metadata-aware retrieval and deterministic risk-to-query translation."""

from __future__ import annotations

import re
from dataclasses import dataclass

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


@dataclass(frozen=True)
class RerankConfig:
    """Small, inspectable boosts for safety metadata-aware ranking."""

    risk_type_boost: float = 0.05
    hazard_code_boost: float = 0.06
    permit_type_boost: float = 0.10
    title_hint_boost: float = 0.08
    document_mode_boost: float = 0.03
    exact_ventilation_boost: float = 0.04
    maximum_metadata_boost: float = 0.45


_RISK_QUERY_TERMS: dict[RiskType, tuple[str, ...]] = {
    RiskType.FIRE_EXPLOSION: ("fire", "explosion", "hydrocarbon", "hot work", "ignition"),
    RiskType.TOXIC_GAS_EXPOSURE: ("toxic gas", "h2s", "hydrogen sulfide"),
    RiskType.OXYGEN_DEFICIENCY: ("low oxygen", "oxygen deficiency", "confined space"),
    RiskType.OVERPRESSURE: ("overpressure", "pressure rising", "pressure increase"),
    RiskType.EQUIPMENT_FAILURE: ("equipment failure", "ventilation failed", "malfunction"),
}
_HAZARD_QUERY_TERMS: dict[HazardCode, tuple[str, ...]] = {
    HazardCode.RISING_LEL: (
        "rising lel",
        "rising hydrocarbon",
        "hydrocarbon gas is rising",
        "gas is rising",
        "hydrocarbon concentration",
    ),
    HazardCode.HIGH_H2S: ("high h2s", "h2s", "hydrogen sulfide"),
    HazardCode.LOW_OXYGEN: ("low oxygen", "oxygen deficiency"),
    HazardCode.PRESSURE_RISING: ("pressure rising", "pressure increase"),
    HazardCode.VENTILATION_FAILURE: (
        "ventilation failure",
        "ventilation failed",
        "ventilation has failed",
        "failed ventilation",
        "ventilation is unavailable",
    ),
    HazardCode.INCOMPLETE_ISOLATION: ("incomplete isolation", "isolation is incomplete"),
    HazardCode.HOT_WORK_ACTIVE: ("hot work", "hot-work", "ignition-producing"),
    HazardCode.CONFINED_SPACE_ACTIVE: ("confined space", "entry permit"),
    HazardCode.WORKERS_PRESENT: ("workers present", "workers are present", "personnel present"),
    HazardCode.OVERDUE_MAINTENANCE: ("overdue maintenance", "maintenance overdue"),
}
_PERMIT_QUERY_TERMS: dict[PermitType, tuple[str, ...]] = {
    PermitType.HOT_WORK: ("hot work", "hot-work", "hot work permit"),
    PermitType.CONFINED_SPACE: ("confined space", "confined space permit"),
    PermitType.LINE_BREAKING: ("line breaking", "line-breaking", "line break"),
    PermitType.ELECTRICAL: ("electrical permit", "electrical isolation"),
}
_TITLE_HINTS: dict[str, tuple[str, ...]] = {
    HazardCode.RISING_LEL.value: ("gas", "atmosphere"),
    HazardCode.VENTILATION_FAILURE.value: ("ventilation",),
    HazardCode.HOT_WORK_ACTIVE.value: ("hot work",),
    HazardCode.WORKERS_PRESENT.value: ("evacuation",),
    PermitType.HOT_WORK.value: ("hot work",),
}


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _inferred_targets(query_text: str) -> tuple[set[str], set[str], set[str]]:
    normalized = _normalized(query_text)

    def matching(mapping: dict[object, tuple[str, ...]]) -> set[str]:
        return {
            key.value
            for key, terms in mapping.items()
            if any(_normalized(term) in normalized for term in terms)
        }

    return (
        matching(_RISK_QUERY_TERMS),
        matching(_HAZARD_QUERY_TERMS),
        matching(_PERMIT_QUERY_TERMS),
    )


def risk_to_retrieval_query(risk: RiskEngineInput, top_k: int = 5) -> RetrievalQuery:
    """Create a stable evidence query from the existing risk-engine contract."""

    hazard_words = {
        HazardCode.RISING_LEL: "hydrocarbon gas concentration is rising",
        HazardCode.HOT_WORK_ACTIVE: "hot work is active",
        HazardCode.VENTILATION_FAILURE: "ventilation is unavailable",
        HazardCode.WORKERS_PRESENT: "workers are present",
    }
    details = [
        hazard_words.get(hazard, hazard.value.replace("_", " ").lower())
        for hazard in risk.contributing_factors
    ]
    detail_text = ", ".join(details[:-1]) + (
        f" and {details[-1]}" if len(details) > 1 else (details[0] if details else "")
    )
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


def _metadata_values(result: RetrievalResult, key: str) -> set[str]:
    return {str(value).upper() for value in result.metadata.get(key, [])}


def _metadata_boost(
    result: RetrievalResult,
    query: RetrievalQuery,
    mode: str,
    config: RerankConfig,
) -> float:
    inferred_risks, inferred_hazards, inferred_permits = _inferred_targets(query.query_text)
    risk_targets = inferred_risks | {value.value for value in query.risk_types}
    hazard_targets = inferred_hazards | {value.value for value in query.hazard_codes}
    permit_targets = inferred_permits | {value.value for value in query.permit_types}

    boost = 0.0
    boost += config.risk_type_boost * len(risk_targets & _metadata_values(result, "risk_types"))
    boost += config.hazard_code_boost * len(hazard_targets & _metadata_values(result, "hazard_codes"))
    boost += config.permit_type_boost * len(permit_targets & _metadata_values(result, "permit_types"))
    if (
        HazardCode.VENTILATION_FAILURE.value in hazard_targets
        and HazardCode.VENTILATION_FAILURE.value in _metadata_values(result, "hazard_codes")
    ):
        # Ventilation loss is a direct operational control failure, so an exact
        # match gets a small additional boost over a general evacuation passage.
        boost += config.exact_ventilation_boost

    # A title hint is intentionally small. It makes an explicitly named
    # operational topic easier to find without allowing labels to overwhelm
    # the passage's semantic similarity.
    title = _normalized(result.source_title)
    for target in sorted(hazard_targets | permit_targets):
        if any(hint in title for hint in _TITLE_HINTS.get(target, ())):
            boost += config.title_hint_boost

    if mode == "regulations_and_sops":
        if result.document_type == "SOP":
            boost += config.document_mode_boost
        elif result.document_type == "REGULATION":
            boost += config.document_mode_boost * 0.5
    elif mode == "similar_incidents" and result.document_type in {
        "HISTORICAL_INCIDENT",
        "NEAR_MISS",
        "CASE_STUDY",
    }:
        boost += config.document_mode_boost

    return min(boost, config.maximum_metadata_boost)


class Retriever:
    """Embed, filter, and deterministically rerank evidence results."""

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        rerank_config: RerankConfig | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.rerank_config = rerank_config or RerankConfig()

    def retrieve(
        self,
        query: RetrievalQuery | str,
        *,
        mode: str = "all",
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        if isinstance(query, str):
            query = RetrievalQuery(query_text=query, top_k=top_k if top_k is not None else 5)
        elif top_k is not None:
            query = query.model_copy(update={"top_k": top_k})
        if mode not in {"regulations_and_sops", "similar_incidents", "all"}:
            raise ValueError("mode must be regulations_and_sops, similar_incidents, or all")
        document_types = list(query.document_types)
        if mode == "regulations_and_sops":
            document_types = ["REGULATION", "SOP"]
        elif mode == "similar_incidents":
            document_types = ["HISTORICAL_INCIDENT", "NEAR_MISS", "CASE_STUDY"]
        filters = {
            "risk_types": [value.value for value in query.risk_types],
            "hazard_codes": [value.value for value in query.hazard_codes],
            "permit_types": [value.value for value in query.permit_types],
            "document_type": document_types,
        }
        vectors = self.embedder.embed([query.query_text])
        if len(vectors) != 1:
            raise ValueError("Embedder must return exactly one vector for one query")

        # Retrieve a larger deterministic candidate pool before applying small
        # metadata boosts, otherwise a semantically strong but less exact chunk
        # could crowd an exact safety control out before reranking.
        candidate_k = max(query.top_k * 4, query.top_k)
        candidates = self.store.query(vectors[0], top_k=candidate_k, filters=filters)
        reranked = [
            result.model_copy(
                update={
                    "final_score": min(
                        1.0,
                        result.similarity_score
                        + _metadata_boost(result, query, mode, self.rerank_config),
                    )
                }
            )
            for result in candidates
        ]
        reranked.sort(
            key=lambda result: (
                -(result.final_score if result.final_score is not None else result.similarity_score),
                -result.similarity_score,
                result.chunk_id,
            )
        )
        return reranked[: query.top_k]
