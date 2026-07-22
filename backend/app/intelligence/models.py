"""Internal contracts for grounded safety-intelligence generation.

These models deliberately contain only fields an LLM may propose. Provenance,
response identifiers, timestamps, and review controls are populated by the
application service.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models import RetrievalResult
from app.schemas.common import NonEmptyString, UsefulText


class GeneratedAction(BaseModel):
    """Provider-proposed advisory action awaiting deterministic validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action_id: NonEmptyString
    title: NonEmptyString
    description: UsefulText
    priority: int = Field(ge=1, le=10)
    target_role: NonEmptyString
    supporting_evidence_ids: list[NonEmptyString] = Field(min_length=1)
    requires_human_approval: bool


class GeneratedIntelligence(BaseModel):
    """Strict intermediate JSON contract shared by every provider."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    executive_summary: UsefulText
    risk_explanation: UsefulText
    recommended_actions: list[GeneratedAction] = Field(default_factory=list)
    confidence_suggestion: float | None = Field(default=None, ge=0.0, le=1.0)
    limitations: list[NonEmptyString] = Field(default_factory=list)
    insufficient_evidence: bool = False


class GroundingRejection(BaseModel):
    """Auditable reason that a generated action was excluded."""

    action_id: str
    reasons: list[str]


class RetrievedEvidence(BaseModel):
    """Full-fidelity retrieval record retained until public-schema conversion."""

    evidence_id: str
    chunk_id: str
    text: str
    source_title: str
    document_type: str
    source_url: str | None = None
    source_path: str | None = None
    page_start: int
    page_end: int
    section: str | None = None
    raw_similarity_score: float
    reranked_score: float
    is_synthetic: bool
    matched_hazards: list[str] = Field(default_factory=list)
    matched_permit_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_result(cls, result: RetrievalResult) -> "RetrievedEvidence":
        return cls(
            evidence_id=f"EVD-{result.chunk_id}",
            chunk_id=result.chunk_id,
            text=result.text,
            source_title=result.source_title,
            document_type=result.document_type,
            source_url=result.source_url,
            source_path=result.source_path,
            page_start=result.page_start,
            page_end=result.page_end,
            section=result.section,
            raw_similarity_score=result.similarity_score,
            reranked_score=(
                result.final_score
                if result.final_score is not None
                else result.similarity_score
            ),
            is_synthetic=result.is_synthetic,
            matched_hazards=[
                str(value) for value in result.metadata.get("hazard_codes", [])
            ],
            matched_permit_types=[
                str(value) for value in result.metadata.get("permit_types", [])
            ],
            metadata=result.metadata,
        )
