from __future__ import annotations

from typing import Any


def decision_summary_text(artifact: dict[str, Any]) -> str:
    decision = dict_at(artifact, "proposal_decision_summary")
    return str(
        decision.get("primary_summary")
        or decision.get("summary")
        or "Proposal decision summary is not available from persisted evidence."
    )


def objective_summary(artifact: dict[str, Any]) -> str:
    tags = strings(dict_at(artifact, "summary").get("objective_tags"))
    if not tags:
        return "Advisory objective tags are not available from the proposal artifact."
    return "Proposal objective tags: " + ", ".join(tags) + "."


def recommendation_summary(artifact: dict[str, Any]) -> str:
    decision = dict_at(artifact, "proposal_decision_summary")
    action = decision.get("recommended_next_action") or dict_at(artifact, "summary").get(
        "recommended_next_step"
    )
    if not action:
        return "Recommendation posture is pending review."
    return f"Recommended next action is {action}."


def alternatives_summary(artifact: dict[str, Any]) -> str:
    alternatives = list_at(dict_at(artifact, "proposal_alternatives"), "alternatives")
    rejected = [
        item for item in alternatives if isinstance(item, dict) and not item.get("selected")
    ]
    if not alternatives:
        return "Proposal alternatives are not available from persisted evidence."
    return f"{len(rejected)} rejected alternatives are available for review."


def risk_summary(artifact: dict[str, Any]) -> str:
    risk = dict_at(artifact, "risk_lens")
    return str(risk.get("summary") or "Risk lens evidence is pending review.")


def dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def list_at(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]
