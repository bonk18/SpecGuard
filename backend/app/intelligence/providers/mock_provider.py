"""Deterministic, network-free provider for tests and demonstrations."""

from __future__ import annotations

import json

from app.intelligence.providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Produce realistic structured output from the prompt payload only."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt
        marker = "INPUT_AND_EVIDENCE_JSON:\n"
        if marker not in user_prompt:
            raise ValueError("Mock provider could not find the prompt payload")
        payload = json.loads(user_prompt.split(marker, 1)[1])
        risk = payload["risk_input"]
        evidence = payload["sop_regulatory_evidence"]
        evidence_ids = [item["evidence_id"] for item in evidence]

        actions: list[dict[str, object]] = []
        if evidence_ids:
            actions.append(
                {
                    "action_id": "ACT-001",
                    "title": "Review immediate work-area safeguards",
                    "description": (
                        "The area supervisor should review the cited procedure, "
                        "verify current conditions around "
                        f"{risk['equipment_ids'][0]}, and decide whether work should pause."
                    ),
                    "priority": 10,
                    "target_role": "Area Supervisor",
                    "supporting_evidence_ids": [evidence_ids[0]],
                    "requires_human_approval": True,
                }
            )
            actions.append(
                {
                    "action_id": "ACT-002",
                    "title": "Review worker protection measures",
                    "description": (
                        "The shift supervisor should assess worker exposure and apply "
                        "the approved site procedure if the observed conditions are confirmed."
                    ),
                    "priority": 9,
                    "target_role": "Shift Supervisor",
                    "supporting_evidence_ids": evidence_ids[:2],
                    "requires_human_approval": True,
                }
            )

        output = {
            "executive_summary": (
                f"{risk['severity']} {risk['risk_type']} risk is indicated in "
                f"{risk['zone_id']} and requires prompt human review."
            ),
            "risk_explanation": (
                f"The risk engine predicts {risk['predicted_incident']} from the supplied "
                "contributing factors and sensor evidence; retrieved material provides "
                "advisory context but does not confirm field conditions."
            ),
            "recommended_actions": actions,
            "confidence_suggestion": 0.78 if actions else 0.25,
            "limitations": [
                "Recommendations require verification by qualified site personnel."
            ],
            "insufficient_evidence": not bool(actions),
        }
        return json.dumps(output, sort_keys=True)
