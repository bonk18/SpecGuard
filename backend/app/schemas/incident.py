"""Historical incident, near-miss, and similarity-search contracts."""

from datetime import datetime

from pydantic import Field

from app.schemas.common import (
    HazardCode,
    NonEmptyString,
    PermitType,
    RiskType,
    Severity,
    SpecGuardSchema,
    UsefulText,
    ZoneId,
)


class HistoricalIncident(SpecGuardSchema):
    """A normalized incident used for retrieval and prevention analysis."""

    incident_id: NonEmptyString
    title: NonEmptyString
    occurred_at: datetime | None = None
    industry: NonEmptyString = "PETROLEUM_REFINERY"
    facility_type: NonEmptyString = "REFINERY_PROCESS_UNIT"
    zone_id: ZoneId | None = None
    equipment_ids: list[NonEmptyString] = Field(default_factory=list)
    risk_type: RiskType
    severity: Severity
    permit_types: list[PermitType] = Field(default_factory=list)
    contributing_hazards: list[HazardCode] = Field(default_factory=list)
    summary: UsefulText
    root_causes: list[NonEmptyString] = Field(default_factory=list)
    consequences: list[NonEmptyString] = Field(default_factory=list)
    preventive_actions: list[NonEmptyString] = Field(default_factory=list)
    source_title: NonEmptyString | None = None
    source_url: NonEmptyString | None = None
    source_page: int | None = Field(default=None, ge=1)
    is_synthetic: bool


class NearMissRecord(SpecGuardSchema):
    """A hazardous event that did not result in an incident.

    Near misses are modeled separately because their potential severity differs
    from their actual outcome. They provide valuable weak signals for prevention
    even when nobody was injured and no equipment was damaged.
    """

    near_miss_id: NonEmptyString
    title: NonEmptyString
    occurred_at: datetime | None = None
    zone_id: ZoneId | None = None
    equipment_ids: list[NonEmptyString] = Field(default_factory=list)
    risk_type: RiskType
    potential_severity: Severity
    permit_types: list[PermitType] = Field(default_factory=list)
    contributing_hazards: list[HazardCode] = Field(default_factory=list)
    description: UsefulText
    immediate_actions: list[NonEmptyString] = Field(default_factory=list)
    recommended_preventive_actions: list[NonEmptyString] = Field(
        default_factory=list
    )
    source_title: NonEmptyString | None = None
    source_url: NonEmptyString | None = None
    source_page: int | None = Field(default=None, ge=1)
    is_synthetic: bool


class IncidentSearchQuery(SpecGuardSchema):
    """Filters and free text supplied to incident-similarity retrieval."""

    risk_type: RiskType | None = None
    zone_id: ZoneId | None = None
    equipment_ids: list[NonEmptyString] = Field(default_factory=list)
    hazards: list[HazardCode] = Field(default_factory=list)
    active_permits: list[PermitType] = Field(default_factory=list)
    natural_language_query: NonEmptyString | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SimilarIncident(SpecGuardSchema):
    """A compact historical result returned by the retrieval pipeline."""

    incident_id: NonEmptyString
    title: NonEmptyString
    similarity_score: float = Field(ge=0.0, le=1.0)
    shared_hazards: list[HazardCode] = Field(default_factory=list)
    summary: UsefulText
    root_causes: list[NonEmptyString] = Field(default_factory=list)
    preventive_actions: list[NonEmptyString] = Field(default_factory=list)
    source_title: NonEmptyString | None = None
    source_url: NonEmptyString | None = None
    source_page: int | None = Field(default=None, ge=1)
