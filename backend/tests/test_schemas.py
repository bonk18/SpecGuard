"""Validation tests for the shared SpecGuard service contracts."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas import (
    ExtractedSafetyEvent,
    HistoricalIncident,
    IncidentSearchQuery,
    RecommendedAction,
    RiskEngineInput,
    SafetyIntelligenceResponse,
    ShiftLogEntry,
)
from app.schemas.maintainance import MaintenanceEvent as LegacyMaintenanceEvent
from app.schemas.maintenance import MaintenanceEvent


EXAMPLES_DIR = Path(__file__).parents[2] / "docs" / "examples"
NOW = datetime(2026, 7, 16, 9, 30, tzinfo=timezone.utc)


def valid_risk_input() -> dict[str, object]:
    return {
        "alert_id": "ALT-2026-001",
        "timestamp": NOW,
        "zone_id": "ZONE_B",
        "equipment_ids": ["P-101"],
        "risk_type": "FIRE_EXPLOSION",
        "risk_score": 0.91,
        "severity": "CRITICAL",
        "predicted_incident": "Hydrocarbon flash fire near pump P-101",
        "contributing_factors": [
            "RISING_LEL",
            "HOT_WORK_ACTIVE",
            "VENTILATION_FAILURE",
            "WORKERS_PRESENT",
        ],
        "sensor_evidence": {"hc_gas_lel": {"value": 8.4, "unit": "%LEL"}},
        "active_permit_ids": ["PTW-HW-204"],
        "maintenance_event_ids": ["MNT-VENT-031"],
        "shift_log_ids": ["LOG-NIGHT-118"],
        "cctv_event_ids": ["CCTV-ZB-778"],
        "estimated_lead_time_minutes": 12.0,
        "model_confidence": 0.88,
    }


def test_valid_risk_engine_input_is_accepted() -> None:
    model = RiskEngineInput.model_validate(valid_risk_input())

    assert model.alert_id == "ALT-2026-001"
    assert model.zone_id.value == "ZONE_B"


def test_risk_score_above_one_is_rejected() -> None:
    payload = valid_risk_input()
    payload["risk_score"] = 1.01

    with pytest.raises(ValidationError):
        RiskEngineInput.model_validate(payload)


def test_negative_lead_time_is_rejected() -> None:
    payload = valid_risk_input()
    payload["estimated_lead_time_minutes"] = -0.1

    with pytest.raises(ValidationError):
        RiskEngineInput.model_validate(payload)


def test_invalid_enum_value_is_rejected() -> None:
    payload = valid_risk_input()
    payload["severity"] = "EXTREME"

    with pytest.raises(ValidationError):
        RiskEngineInput.model_validate(payload)


def test_extraction_confidence_above_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractedSafetyEvent(
            source_log_id="LOG-1",
            severity="HIGH",
            confidence=1.1,
            summary="Hydrocarbon readings are trending upward.",
            requires_follow_up=True,
        )


def test_empty_required_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ShiftLogEntry(
            log_id="LOG-1",
            timestamp=NOW,
            shift_id="NIGHT-1",
            author_role="Operator",
            raw_text="   ",
            acknowledged=False,
            resolved=False,
        )


def test_valid_shift_log_is_accepted() -> None:
    model = ShiftLogEntry(
        log_id="LOG-1",
        timestamp=NOW,
        shift_id="NIGHT-1",
        author_role="Console Operator",
        zone_id="ZONE_B",
        equipment_ids=["P-101"],
        raw_text="Hydrocarbon smell reported near P-101 during rounds.",
        acknowledged=True,
        resolved=False,
    )

    assert model.equipment_ids == ["P-101"]


def test_valid_extracted_safety_event_is_accepted() -> None:
    model = ExtractedSafetyEvent(
        source_log_id="LOG-1",
        zone_id="ZONE_B",
        equipment_ids=["P-101"],
        hazards=["RISING_LEL"],
        severity="HIGH",
        confidence=0.87,
        summary="Possible hydrocarbon accumulation near pump P-101.",
        requires_follow_up=True,
    )

    assert model.extraction_method == "RULE_LLM_HYBRID"


def test_valid_historical_incident_is_accepted() -> None:
    model = HistoricalIncident(
        incident_id="INC-001",
        title="Pump seal leak ignited during hot work",
        risk_type="FIRE_EXPLOSION",
        severity="CRITICAL",
        summary="A seal leak accumulated vapour near an ignition source.",
        is_synthetic=True,
    )

    assert model.industry == "PETROLEUM_REFINERY"


@pytest.mark.parametrize("top_k", [0, 21])
def test_invalid_top_k_is_rejected(top_k: int) -> None:
    with pytest.raises(ValidationError):
        IncidentSearchQuery(top_k=top_k)


def test_complete_response_serializes_to_json() -> None:
    payload = json.loads(
        (EXAMPLES_DIR / "safety_intelligence_response.json").read_text()
    )
    model = SafetyIntelligenceResponse.model_validate(payload)
    serialized = json.loads(model.model_dump_json())

    assert serialized["alert_id"] == "ALT-2026-001"
    assert serialized["recommended_actions"][0]["status"] == "PROPOSED"
    assert serialized["requires_human_review"] is True


def test_unknown_extra_fields_are_rejected() -> None:
    payload = valid_risk_input()
    payload["unexpected_control_command"] = "START_PUMP"

    with pytest.raises(ValidationError):
        RiskEngineInput.model_validate(payload)


def test_recommended_action_defaults_to_human_approval() -> None:
    action = RecommendedAction(
        action_id="ACT-001",
        title="Review suspension of hot work",
        description="A supervisor should verify conditions and apply the site SOP.",
        priority=10,
        status="PROPOSED",
        target_role="Area Supervisor",
    )

    assert action.requires_human_approval is True


def test_intelligence_response_defaults_to_human_review() -> None:
    response = SafetyIntelligenceResponse(
        intelligence_id="INT-001",
        alert_id="ALT-001",
        generated_at=NOW,
        executive_summary="A compound flash-fire risk exists in Zone B.",
        risk_explanation="Rising hydrocarbons coincide with an ignition source.",
        intelligence_confidence=0.8,
        insufficient_evidence=False,
    )

    assert response.requires_human_review is True


@pytest.mark.parametrize(
    ("filename", "schema"),
    [
        ("risk_engine_input.json", RiskEngineInput),
        ("safety_intelligence_response.json", SafetyIntelligenceResponse),
        ("shift_log_entry.json", ShiftLogEntry),
        ("extracted_safety_event.json", ExtractedSafetyEvent),
        ("historical_incident.json", HistoricalIncident),
    ],
)
def test_documentation_example_validates(
    filename: str,
    schema: type[BaseModel],
) -> None:
    schema.model_validate_json((EXAMPLES_DIR / filename).read_text())


def test_maintenance_typo_shim_preserves_legacy_import() -> None:
    assert LegacyMaintenanceEvent is MaintenanceEvent
