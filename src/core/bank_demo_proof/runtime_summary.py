from __future__ import annotations

from typing import Any

from src.core.bank_demo_proof.model_common import RFC28_CANONICAL_SCENARIO_ID
from src.core.bank_demo_proof.runtime_summary_access import dict_at, select_fields, value_at
from src.core.bank_demo_proof.runtime_summary_projection import (
    build_alternatives_path_summaries,
    build_decision_path_summaries,
    build_degraded_runtime_summary,
    build_proposal_lifecycle_summary,
    build_proposal_memo_summary,
    build_proposal_narrative_summary,
    build_proposal_policy_summary,
    build_workspace_rationale_summary,
)

__all__ = [
    "sanitize_live_runtime_summary",
    "select_fields",
    "value_at",
]


def sanitize_live_runtime_summary(live_runtime_payload: dict[str, Any]) -> dict[str, Any]:
    parity = dict_at(live_runtime_payload, "parity")
    degraded = dict_at(live_runtime_payload, "degraded")
    return {
        "scenario_id": RFC28_CANONICAL_SCENARIO_ID,
        "primary_portfolio_id": value_at(
            live_runtime_payload,
            "parity.complete_issuer_portfolio",
        ),
        "proposal_lifecycle": build_proposal_lifecycle_summary(parity),
        "workspace_rationale": build_workspace_rationale_summary(parity),
        "proposal_narrative": build_proposal_narrative_summary(parity),
        "proposal_memo": build_proposal_memo_summary(parity),
        "proposal_policy": build_proposal_policy_summary(parity),
        "decision_paths": build_decision_path_summaries(parity),
        "alternatives_paths": build_alternatives_path_summaries(parity),
        "degraded_runtime": build_degraded_runtime_summary(degraded),
    }
