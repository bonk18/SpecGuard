"""Deterministic validation of provider-proposed recommendations."""

from __future__ import annotations

import json
import re

from app.intelligence.models import (
    GeneratedAction,
    GroundingRejection,
    RetrievedEvidence,
)
from app.schemas import RecommendedAction, RiskEngineInput


_EXECUTION_CLAIMS = re.compile(
    r"\b(?:has|have|had|was|were)\s+(?:already\s+)?(?:been\s+)?"
    r"(?:executed|completed|implemented|applied|shut\s*down|stopped|isolated|evacuated)\b"
    r"|\b(?:successfully completed|action completed|execution confirmed)\b",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"\b[A-Z][A-Z0-9]{0,12}-[A-Z0-9][A-Z0-9-]*\b")
_NUMBER = re.compile(
    r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?"
    r"(?:\s*(?:%\s*LEL|%|ppm|ppb|psi|bar|kpa|mpa|°?c|minutes?|seconds?))?",
    re.IGNORECASE,
)
_FORMAL_REFERENCE = re.compile(
    r"\b(?:OSHA|OISD|NFPA|ISO|API)\s*[-:]?\s*[A-Z0-9.()-]+"
    r"|\b(?:page|section)\s+\d+[A-Za-z0-9.()-]*",
    re.IGNORECASE,
)


def _context_text(risk: RiskEngineInput, evidence: list[RetrievedEvidence]) -> str:
    return "\n".join(
        [json.dumps(risk.model_dump(mode="json"), sort_keys=True)]
        + [
            " ".join(
                filter(
                    None,
                    [
                        item.text,
                        item.source_title,
                        item.source_url,
                        item.source_path,
                        item.section,
                        str(item.page_start),
                        str(item.page_end),
                    ],
                )
            )
            for item in evidence
        ]
    )


def _normalized_number(token: str) -> str:
    return re.sub(r"\s+", "", token).lower()


def validate_actions(
    actions: list[GeneratedAction],
    risk: RiskEngineInput,
    evidence: list[RetrievedEvidence],
) -> tuple[list[RecommendedAction], list[GroundingRejection]]:
    """Reject unsafe or ungrounded actions and return only public-schema actions."""

    evidence_by_id = {item.evidence_id: item for item in evidence}
    context = _context_text(risk, evidence)
    supported_ids = set(_IDENTIFIER.findall(context)) | set(risk.equipment_ids)
    supported_numbers = {_normalized_number(value) for value in _NUMBER.findall(context)}
    accepted: list[RecommendedAction] = []
    rejected: list[GroundingRejection] = []
    seen_action_ids: set[str] = set()

    for action in actions:
        reasons: list[str] = []
        prose = f"{action.title}\n{action.description}"
        cited = set(action.supporting_evidence_ids)
        if not cited:
            reasons.append("action cites no evidence")
        unknown = sorted(cited - evidence_by_id.keys())
        if unknown:
            reasons.append(f"unknown evidence IDs: {', '.join(unknown)}")
        if not action.requires_human_approval:
            reasons.append("human approval was disabled")
        if action.action_id in seen_action_ids:
            reasons.append("duplicate action ID")
        seen_action_ids.add(action.action_id)
        if _EXECUTION_CLAIMS.search(prose):
            reasons.append("action claims execution or completion")

        unsupported_ids = sorted(set(_IDENTIFIER.findall(prose)) - supported_ids)
        if unsupported_ids:
            reasons.append(f"unsupported equipment or operational IDs: {', '.join(unsupported_ids)}")

        unsupported_numbers = sorted(
            {
                _normalized_number(value)
                for value in _NUMBER.findall(prose)
                if _normalized_number(value) not in supported_numbers
            }
        )
        if unsupported_numbers:
            reasons.append(
                "unsupported numeric values or thresholds: " + ", ".join(unsupported_numbers)
            )

        cited_context = "\n".join(
            _context_text(risk, [evidence_by_id[value]])
            for value in cited
            if value in evidence_by_id
        )
        fabricated_refs = [
            match.group(0)
            for match in _FORMAL_REFERENCE.finditer(prose)
            if match.group(0).lower() not in cited_context.lower()
        ]
        if fabricated_refs:
            reasons.append(
                "unsupported regulation, source, page, or section: "
                + ", ".join(sorted(set(fabricated_refs)))
            )

        if reasons:
            rejected.append(GroundingRejection(action_id=action.action_id, reasons=reasons))
            continue
        accepted.append(
            RecommendedAction(
                action_id=action.action_id,
                title=action.title,
                description=action.description,
                priority=action.priority,
                status="PROPOSED",
                requires_human_approval=True,
                target_role=action.target_role,
                supporting_evidence_ids=action.supporting_evidence_ids,
            )
        )
    return accepted, rejected
