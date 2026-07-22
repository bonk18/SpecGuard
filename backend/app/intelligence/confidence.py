"""Transparent prototype confidence heuristic for intelligence responses."""

from __future__ import annotations

from app.intelligence.models import RetrievedEvidence
from app.schemas import RiskEngineInput


def calculate_confidence(
    risk: RiskEngineInput,
    sop_evidence: list[RetrievedEvidence],
    incident_evidence: list[RetrievedEvidence],
    *,
    grounded_actions: int,
    rejected_actions: int,
    fallback_used: bool,
    insufficient_evidence: bool,
) -> float:
    """Calculate an auditable heuristic score, not a calibrated probability."""

    risk_confidence = (
        risk.model_confidence if risk.model_confidence is not None else risk.risk_score
    )
    all_evidence = sop_evidence + incident_evidence
    average_score = (
        sum(item.reranked_score for item in all_evidence) / len(all_evidence)
        if all_evidence
        else 0.0
    )
    score = 0.30 * risk_confidence
    score += 0.15 * min(len(all_evidence) / 5.0, 1.0)
    score += 0.20 * average_score
    score += 0.10 if sop_evidence else 0.0
    score += 0.05 if incident_evidence else 0.0
    score += 0.15 * min(grounded_actions / 2.0, 1.0)
    if rejected_actions:
        score -= 0.10 * min(rejected_actions / max(grounded_actions + rejected_actions, 1), 1.0)
    if fallback_used:
        score -= 0.25
    if insufficient_evidence:
        score -= 0.15
    return round(max(0.05, min(0.95, score)), 3)
