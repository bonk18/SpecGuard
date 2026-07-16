"""Contracts joining risk detection, evidence retrieval, and recommendations."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import (
    ActionStatus,
    EvidenceType,
    HazardCode,
    NonEmptyString,
    RiskType,
    Severity,
    SpecGuardSchema,
    UsefulText,
    ZoneId,
)
from app.schemas.incident import SimilarIncident


class RiskEngineInput(SpecGuardSchema):
    """The stable handoff from risk detection to safety intelligence.

    Rex's compound-risk engine produces this object. Ashish's NLP/RAG pipeline
    consumes it. The explicit contract prevents hidden coupling between those
    independently developed components.
    """

    alert_id: NonEmptyString
    timestamp: datetime
    zone_id: ZoneId
    equipment_ids: list[NonEmptyString] = Field(min_length=1)
    risk_type: RiskType
    risk_score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    predicted_incident: UsefulText
    contributing_factors: list[HazardCode] = Field(min_length=1)
    # Evidence keys vary by sensor family, so this boundary deliberately stays
    # flexible rather than pretending every process variable is one sensor type.
    sensor_evidence: dict[str, Any] = Field(min_length=1)
    active_permit_ids: list[NonEmptyString] = Field(default_factory=list)
    maintenance_event_ids: list[NonEmptyString] = Field(default_factory=list)
    shift_log_ids: list[NonEmptyString] = Field(default_factory=list)
    cctv_event_ids: list[NonEmptyString] = Field(default_factory=list)
    estimated_lead_time_minutes: float | None = Field(default=None, ge=0.0)
    model_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class EvidenceReference(SpecGuardSchema):
    """A compact pointer to source material used by the intelligence pipeline.

    Evidence IDs let actions cite relevant material without copying entire SOPs,
    regulations, sensor payloads, or incident documents into every response.
    """

    evidence_id: NonEmptyString
    evidence_type: EvidenceType
    title: NonEmptyString
    excerpt: UsefulText
    source_name: NonEmptyString
    source_url: NonEmptyString | None = None
    page_number: int | None = Field(default=None, ge=1)
    section_name: NonEmptyString | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)


class RecommendedAction(SpecGuardSchema):
    """An advisory response step that remains under human control.

    SpecGuard does not model an LLM as directly controlling refinery equipment.
    A qualified human must review proposed actions before operational execution.
    """

    action_id: NonEmptyString
    title: NonEmptyString
    description: UsefulText
    priority: int = Field(ge=1, le=10)
    status: ActionStatus
    requires_human_approval: bool = True
    target_role: NonEmptyString
    supporting_evidence_ids: list[NonEmptyString] = Field(default_factory=list)


class SafetyIntelligenceResponse(SpecGuardSchema):
    """Final safety-intelligence response returned to backend and frontend."""

    intelligence_id: NonEmptyString
    alert_id: NonEmptyString
    generated_at: datetime
    executive_summary: UsefulText
    risk_explanation: UsefulText
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    intelligence_confidence: float = Field(ge=0.0, le=1.0)
    insufficient_evidence: bool
    limitations: list[NonEmptyString] = Field(default_factory=list)
    requires_human_review: bool = True
