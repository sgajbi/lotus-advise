from __future__ import annotations

from typing import Any


def extract_risk_lens(proposal_result: Any) -> dict[str, Any] | None:
    explanation = getattr(proposal_result, "explanation", None)
    if not isinstance(explanation, dict):
        return None
    risk_lens = explanation.get("risk_lens")
    if not isinstance(risk_lens, dict):
        return None
    source_service = risk_lens.get("source_service")
    if not isinstance(source_service, str) or not source_service:
        return None
    return {key: value for key, value in risk_lens.items()}
