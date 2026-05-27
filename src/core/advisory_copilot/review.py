from __future__ import annotations

from typing import Literal

from src.core.advisory_copilot.models import CopilotReviewPosture

CopilotReviewAction = Literal["APPROVE_FOR_INTERNAL_USE", "REJECT", "SUPERSEDE", "EXPIRE"]

REVIEW_ACTION_TO_POSTURE: dict[CopilotReviewAction, CopilotReviewPosture] = {
    "APPROVE_FOR_INTERNAL_USE": "APPROVED_FOR_INTERNAL_USE",
    "REJECT": "REJECTED",
    "SUPERSEDE": "SUPERSEDED",
    "EXPIRE": "EXPIRED",
}

TERMINAL_REVIEW_POSTURES: frozenset[CopilotReviewPosture] = frozenset(
    {
        "APPROVED_FOR_INTERNAL_USE",
        "REJECTED",
        "SUPERSEDED",
        "EXPIRED",
        "UNSUPPORTED",
        "GUARDRAIL_REJECTED",
        "UNAVAILABLE",
    }
)


def review_posture_for_action(action: CopilotReviewAction) -> CopilotReviewPosture:
    return REVIEW_ACTION_TO_POSTURE[action]


def is_terminal_review_posture(posture: CopilotReviewPosture) -> bool:
    return posture in TERMINAL_REVIEW_POSTURES

