"""Contracts for raw operator logs and NLP-derived safety information."""

from datetime import datetime

from pydantic import Field

from app.schemas.common import (
    HazardCode,
    NonEmptyString,
    Severity,
    SpecGuardSchema,
    UsefulText,
    ZoneId,
)


class ShiftLogEntry(SpecGuardSchema):
    """An operator's original shift observation before NLP processing.

    Raw text is retained separately from extracted facts so that reviewers can
    audit the source statement and rerun improved extraction logic later.
    """

    log_id: NonEmptyString
    timestamp: datetime
    shift_id: NonEmptyString
    author_role: NonEmptyString
    zone_id: ZoneId | None = None
    equipment_ids: list[NonEmptyString] = Field(default_factory=list)
    raw_text: UsefulText
    acknowledged: bool
    resolved: bool


class ExtractedSafetyEvent(SpecGuardSchema):
    """Structured safety facts produced by NLP from one raw shift log.

    The extracted event is a machine-friendly interpretation, not a replacement
    for the source log. Its confidence and method expose extraction uncertainty.
    """

    source_log_id: NonEmptyString
    zone_id: ZoneId | None = None
    equipment_ids: list[NonEmptyString] = Field(default_factory=list)
    hazards: list[HazardCode] = Field(default_factory=list)
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    summary: UsefulText
    requires_follow_up: bool
    extraction_method: NonEmptyString = "RULE_LLM_HYBRID"
