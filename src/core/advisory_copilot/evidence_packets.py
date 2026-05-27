from __future__ import annotations

from types import MappingProxyType
from typing import Literal

from src.core.advisory_copilot.models import CopilotActionFamily, CopilotSourceDependency

CopilotEvidenceSectionKey = Literal[
    "PROPOSAL_CONTEXT",
    "NARRATIVE_POSTURE",
    "MEMO_EVIDENCE",
    "POLICY_POSTURE",
    "COCKPIT_ACTIONS",
    "REPORT_READINESS",
    "OPERATIONS_HANDOFF",
]

_SOURCE_SECTIONS: dict[CopilotSourceDependency, tuple[CopilotEvidenceSectionKey, ...]] = {
    "RFC0023_PROPOSAL_NARRATIVE": ("PROPOSAL_CONTEXT", "NARRATIVE_POSTURE"),
    "RFC0024_PROPOSAL_MEMO": ("PROPOSAL_CONTEXT", "MEMO_EVIDENCE"),
    "RFC0025_POLICY_EVALUATION": ("POLICY_POSTURE",),
    "RFC0026_ADVISOR_COCKPIT": ("COCKPIT_ACTIONS",),
    "REPORT_READINESS": ("REPORT_READINESS",),
    "OPERATIONS_HANDOFF": ("OPERATIONS_HANDOFF",),
}

_ACTION_REQUIRED_SECTIONS: dict[CopilotActionFamily, tuple[CopilotEvidenceSectionKey, ...]] = {
    "PROPOSAL_EXPLANATION": (
        "PROPOSAL_CONTEXT",
        "NARRATIVE_POSTURE",
        "MEMO_EVIDENCE",
        "POLICY_POSTURE",
    ),
    "EVIDENCE_QA": (
        "PROPOSAL_CONTEXT",
        "NARRATIVE_POSTURE",
        "MEMO_EVIDENCE",
        "POLICY_POSTURE",
        "COCKPIT_ACTIONS",
    ),
    "MEETING_PREPARATION": ("MEMO_EVIDENCE", "POLICY_POSTURE", "COCKPIT_ACTIONS"),
    "COMPLIANCE_REVIEW_SUMMARY": ("NARRATIVE_POSTURE", "MEMO_EVIDENCE", "POLICY_POSTURE"),
    "OPERATIONS_REPORT_HANDOFF": ("MEMO_EVIDENCE", "COCKPIT_ACTIONS", "REPORT_READINESS"),
    "CLIENT_FOLLOW_UP_DRAFT": ("MEMO_EVIDENCE", "POLICY_POSTURE", "COCKPIT_ACTIONS"),
}

SOURCE_EVIDENCE_SECTIONS = MappingProxyType(_SOURCE_SECTIONS)
ACTION_REQUIRED_EVIDENCE_SECTIONS = MappingProxyType(_ACTION_REQUIRED_SECTIONS)


def required_evidence_sections(
    action_family: CopilotActionFamily,
) -> tuple[CopilotEvidenceSectionKey, ...]:
    return ACTION_REQUIRED_EVIDENCE_SECTIONS[action_family]

