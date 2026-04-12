from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class LiveDecisionSnapshot:
    path_name: str
    top_level_status: str
    decision_status: str
    primary_reason_code: str
    recommended_next_action: str
    approval_requirement_types: tuple[str, ...]


def extract_live_decision_snapshot(
    proposal_body: Mapping[str, Any],
    *,
    path_name: str,
) -> LiveDecisionSnapshot:
    summary = proposal_body.get("proposal_decision_summary")
    if not isinstance(summary, Mapping):
        raise ValueError(f"{path_name}: proposal_decision_summary missing from response body")
    approvals = summary.get("approval_requirements")
    if not isinstance(approvals, list):
        raise ValueError(f"{path_name}: approval_requirements missing from decision summary")

    approval_types = tuple(
        sorted(
            str(item.get("approval_type"))
            for item in approvals
            if isinstance(item, Mapping) and item.get("approval_type")
        )
    )
    return LiveDecisionSnapshot(
        path_name=path_name,
        top_level_status=str(summary.get("top_level_status") or ""),
        decision_status=str(summary.get("decision_status") or ""),
        primary_reason_code=str(summary.get("primary_reason_code") or ""),
        recommended_next_action=str(summary.get("recommended_next_action") or ""),
        approval_requirement_types=approval_types,
    )
