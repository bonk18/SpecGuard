"""Orchestration service for grounded, advisory safety intelligence."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Callable, Protocol

from pydantic import ValidationError

from app.intelligence.confidence import calculate_confidence
from app.intelligence.grounding import validate_actions
from app.intelligence.models import GeneratedIntelligence, RetrievedEvidence
from app.intelligence.prompt_builder import build_prompts
from app.intelligence.providers import GroqLLMProvider, LLMProvider, MockLLMProvider
from app.rag.models import RetrievalQuery, RetrievalResult
from app.rag.retriever import risk_to_retrieval_query
from app.schemas import (
    EvidenceReference,
    EvidenceType,
    RiskEngineInput,
    SafetyIntelligenceResponse,
    SimilarIncident,
)
from app.schemas.common import HazardCode


class RetrievalInterface(Protocol):
    """The existing retriever surface consumed by this service."""

    def retrieve(
        self,
        query: RetrievalQuery | str,
        *,
        mode: str = "all",
        top_k: int | None = None,
    ) -> list[RetrievalResult]: ...


def provider_from_environment() -> LLMProvider:
    """Construct the configured provider; mock is the safe offline default."""

    provider_name = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "groq":
        return GroqLLMProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider_name}")


def _normalized_text(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _deduplicate(results: list[RetrievalResult]) -> list[RetrievalResult]:
    """Remove duplicate and near-identical chunks while retaining highest rank."""

    ordered = sorted(
        results,
        key=lambda item: -(
            item.final_score if item.final_score is not None else item.similarity_score
        ),
    )
    kept: list[RetrievalResult] = []
    normalized: list[str] = []
    seen_ids: set[str] = set()
    for result in ordered:
        candidate = _normalized_text(result.text)
        if result.chunk_id in seen_ids:
            continue
        if any(SequenceMatcher(None, candidate, prior).ratio() >= 0.94 for prior in normalized):
            continue
        kept.append(result)
        normalized.append(candidate)
        seen_ids.add(result.chunk_id)
    return kept


def _evidence_reference(item: RetrievedEvidence) -> EvidenceReference:
    document_type = item.document_type.upper()
    evidence_type = EvidenceType.REGULATION if document_type == "REGULATION" else EvidenceType.SOP
    authority = item.metadata.get("authority")
    locator = item.source_path or item.source_url
    source_name = " — ".join(str(value) for value in (authority, locator) if value) or item.source_title
    page_number = item.page_start if item.page_start == item.page_end else item.page_start
    return EvidenceReference(
        evidence_id=item.evidence_id,
        evidence_type=evidence_type,
        title=item.source_title,
        excerpt=item.text,
        source_name=source_name,
        source_url=item.source_url,
        page_number=page_number,
        section_name=item.section,
        relevance_score=item.reranked_score,
    )


def _similar_incident(
    item: RetrievedEvidence, risk: RiskEngineInput
) -> SimilarIncident:
    metadata = item.metadata
    valid_hazards = {hazard.value for hazard in HazardCode}
    shared = [
        value
        for value in item.matched_hazards
        if value in valid_hazards and value in {hazard.value for hazard in risk.contributing_factors}
    ]
    root_causes = metadata.get("root_causes", [])
    preventive_actions = metadata.get("preventive_actions", [])
    return SimilarIncident(
        incident_id=str(metadata.get("incident_id") or metadata.get("document_id") or item.chunk_id),
        title=str(metadata.get("title") or item.source_title),
        similarity_score=item.reranked_score,
        shared_hazards=shared,
        summary=item.text,
        root_causes=root_causes if isinstance(root_causes, list) else [],
        preventive_actions=(
            preventive_actions if isinstance(preventive_actions, list) else []
        ),
        source_title=item.source_title,
        source_url=item.source_url,
        source_page=item.page_start,
    )


def _intelligence_id(risk: RiskEngineInput, evidence: list[RetrievedEvidence]) -> str:
    material = "|".join(
        [risk.alert_id, risk.timestamp.isoformat()] + [item.chunk_id for item in evidence]
    )
    return "INT-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def _factual_summary(risk: RiskEngineInput) -> tuple[str, str]:
    factors = ", ".join(factor.value for factor in risk.contributing_factors)
    summary = (
        f"The risk engine reports {risk.severity.value} {risk.risk_type.value} risk "
        f"in {risk.zone_id.value}; qualified personnel must review the alert."
    )
    explanation = (
        f"The supplied prediction is {risk.predicted_incident}. The recorded contributing "
        f"factors are {factors}. No operational action is claimed or automatically directed."
    )
    return summary, explanation


class SafetyIntelligenceService:
    """Retrieve, generate, ground, and assemble the public response contract."""

    def __init__(
        self,
        retriever: RetrievalInterface,
        provider: LLMProvider,
        *,
        clock: Callable[[], datetime] | None = None,
        sop_limit: int = 5,
        incident_limit: int = 3,
    ) -> None:
        self.retriever = retriever
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sop_limit = sop_limit
        self.incident_limit = incident_limit

    def _retrieve(
        self, risk: RiskEngineInput
    ) -> tuple[list[RetrievedEvidence], list[RetrievedEvidence], list[str]]:
        query = risk_to_retrieval_query(risk)
        limitations: list[str] = []
        sop_results: list[RetrievalResult] = []
        incident_results: list[RetrievalResult] = []
        try:
            sop_query = query.model_copy(
                update={"permit_types": [], "top_k": self.sop_limit}
            )
            sop_results = self.retriever.retrieve(
                sop_query, mode="regulations_and_sops"
            )
        except Exception as exc:
            limitations.append(
                f"SOP/regulatory retrieval failed: {exc.__class__.__name__}: {exc}"
            )
        try:
            incident_query = query.model_copy(
                update={"permit_types": [], "top_k": self.incident_limit}
            )
            incident_results = self.retriever.retrieve(
                incident_query, mode="similar_incidents"
            )
        except Exception as exc:
            limitations.append(
                f"Historical incident retrieval failed: {exc.__class__.__name__}: {exc}"
            )
        return (
            [RetrievedEvidence.from_result(item) for item in _deduplicate(sop_results)],
            [RetrievedEvidence.from_result(item) for item in _deduplicate(incident_results)],
            limitations,
        )

    def generate(self, risk: RiskEngineInput) -> SafetyIntelligenceResponse:
        """Return a valid advisory response even when retrieval or generation fails."""

        sop_evidence, incident_evidence, limitations = self._retrieve(risk)
        evidence_refs = [_evidence_reference(item) for item in sop_evidence]
        similar_incidents = [
            _similar_incident(item, risk) for item in incident_evidence
        ]
        for item in sop_evidence + incident_evidence:
            if item.is_synthetic:
                limitations.append(
                    f"Evidence {item.evidence_id} is synthetic and is not an approved real-world source."
                )

        fallback_used = False
        rejected_count = 0
        generated: GeneratedIntelligence | None = None
        actions = []
        if not sop_evidence:
            fallback_used = True
            limitations.append(
                "Insufficient SOP or regulatory evidence was retrieved; no recommendations were generated."
            )
        else:
            system_prompt, user_prompt = build_prompts(
                risk, sop_evidence, similar_incidents
            )
            try:
                raw_output = self.provider.generate(system_prompt, user_prompt)
                generated = GeneratedIntelligence.model_validate_json(raw_output)
                actions, rejections = validate_actions(
                    generated.recommended_actions, risk, sop_evidence
                )
                rejected_count = len(rejections)
                for rejection in rejections:
                    limitations.append(
                        f"Rejected action {rejection.action_id}: "
                        + "; ".join(rejection.reasons)
                    )
                if generated.recommended_actions and not actions:
                    fallback_used = True
                    generated = None
                    limitations.append(
                        "All generated actions failed deterministic grounding validation."
                    )
                elif not generated.recommended_actions:
                    fallback_used = True
                    generated = None
                    limitations.append(
                        "The generation provider returned no advisory recommendations."
                    )
            except (json.JSONDecodeError, ValidationError, ValueError, RuntimeError) as exc:
                fallback_used = True
                generated = None
                limitations.append(
                    f"Generation provider output was unavailable or invalid: "
                    f"{exc.__class__.__name__}: {exc}"
                )
            except Exception as exc:
                fallback_used = True
                generated = None
                limitations.append(
                    f"Generation provider failed safely: {exc.__class__.__name__}: {exc}"
                )

        if generated is None:
            executive_summary, risk_explanation = _factual_summary(risk)
            provider_limitations: list[str] = []
            insufficient = not bool(sop_evidence) or fallback_used
            actions = []
        else:
            executive_summary = generated.executive_summary
            risk_explanation = generated.risk_explanation
            provider_limitations = generated.limitations
            insufficient = generated.insufficient_evidence or not bool(sop_evidence)

        confidence = calculate_confidence(
            risk,
            sop_evidence,
            incident_evidence,
            grounded_actions=len(actions),
            rejected_actions=rejected_count,
            fallback_used=fallback_used,
            insufficient_evidence=insufficient,
        )
        response = SafetyIntelligenceResponse(
            intelligence_id=_intelligence_id(risk, sop_evidence + incident_evidence),
            alert_id=risk.alert_id,
            generated_at=self.clock(),
            executive_summary=executive_summary,
            risk_explanation=risk_explanation,
            recommended_actions=actions,
            evidence=evidence_refs,
            similar_incidents=similar_incidents,
            intelligence_confidence=confidence,
            insufficient_evidence=insufficient,
            limitations=list(dict.fromkeys(limitations + provider_limitations)),
            requires_human_review=True,
        )
        return SafetyIntelligenceResponse.model_validate(response.model_dump())
