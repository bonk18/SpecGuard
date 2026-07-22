"""Manifest parsing and deterministic safety metadata enrichment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.rag.models import DocumentChunk, ManifestEntry
from app.schemas.common import HazardCode, PermitType, RiskType


def load_manifest(path: Path) -> list[ManifestEntry]:
    """Parse and validate a JSON manifest before ingestion begins."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Knowledge-base manifest not found: {path}") from exc
    if not isinstance(payload, list):
        raise ValueError("Knowledge-base manifest must contain a JSON array")
    return [ManifestEntry.model_validate(item) for item in payload]


_RISK_KEYWORDS: dict[RiskType, tuple[str, ...]] = {
    RiskType.FIRE_EXPLOSION: (
        "fire",
        "explosion",
        "flash fire",
        "hydrocarbon",
        "ignition",
        "hot work",
    ),
    RiskType.TOXIC_GAS_EXPOSURE: ("h2s", "toxic gas", "poisonous gas"),
    RiskType.OXYGEN_DEFICIENCY: ("low oxygen", "oxygen deficiency", "oxygen level", "confined space"),
    RiskType.OVERPRESSURE: ("overpressure", "pressure rising", "pressure relief"),
    RiskType.EQUIPMENT_FAILURE: ("equipment failure", "pump failure", "malfunction", "ventilation"),
}
_HAZARD_KEYWORDS: dict[HazardCode, tuple[str, ...]] = {
    HazardCode.RISING_LEL: (
        "rising lel",
        "rising hydrocarbon",
        "hydrocarbon concentration",
        "hydrocarbon readings",
        "gas concentration",
        "%lel",
    ),
    HazardCode.HIGH_H2S: ("h2s", "hydrogen sulfide"),
    HazardCode.LOW_OXYGEN: ("low oxygen", "oxygen deficiency"),
    HazardCode.PRESSURE_RISING: ("pressure rising", "pressure increase"),
    HazardCode.VENTILATION_FAILURE: (
        "ventilation failure",
        "ventilation unavailable",
        "ventilation is unavailable",
        "ventilation failed",
        "ventilation has failed",
        "ventilation fails",
    ),
    HazardCode.INCOMPLETE_ISOLATION: ("incomplete isolation", "isolation not verified", "lockout"),
    HazardCode.HOT_WORK_ACTIVE: ("hot work", "ignition source", "welding", "cutting"),
    HazardCode.CONFINED_SPACE_ACTIVE: ("confined space", "entry permit"),
    HazardCode.WORKERS_PRESENT: (
        "workers present",
        "workers are present",
        "personnel present",
        "people are present",
        "workers",
        "personnel",
    ),
    HazardCode.OVERDUE_MAINTENANCE: ("overdue maintenance", "maintenance overdue"),
}
_PERMIT_KEYWORDS: dict[PermitType, tuple[str, ...]] = {
    PermitType.HOT_WORK: ("hot work permit", "hot work"),
    PermitType.CONFINED_SPACE: ("confined space permit", "confined space entry"),
    PermitType.LINE_BREAKING: ("line breaking", "line break", "breaking containment"),
    PermitType.ELECTRICAL: ("electrical permit", "electrical isolation"),
}
_EQUIPMENT_KEYWORDS = {
    "PUMP": ("pump",),
    "PIPELINE": ("pipeline", "pipe"),
    "VALVE": ("valve",),
    "VENTILATION": ("ventilation", "fan"),
    "STORAGE_TANK": ("storage tank", "tank"),
}


def _matches(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def enrich_chunk(chunk: DocumentChunk) -> DocumentChunk:
    """Add transparent keyword-derived tags; no model or LLM is involved."""

    text = f"{chunk.document_title} {chunk.section or ''} {chunk.text}".lower()
    risks = [risk for risk, words in _RISK_KEYWORDS.items() if _matches(text, words)]
    hazards = [hazard for hazard, words in _HAZARD_KEYWORDS.items() if _matches(text, words)]
    permits = [permit for permit, words in _PERMIT_KEYWORDS.items() if _matches(text, words)]
    equipment = [name for name, words in _EQUIPMENT_KEYWORDS.items() if _matches(text, words)]
    return chunk.model_copy(
        update={
            "risk_types": risks,
            "hazard_codes": hazards,
            "permit_types": permits,
        }
    ).model_copy(update={"equipment_types": equipment})


def enrich_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    return [enrich_chunk(chunk) for chunk in chunks]
