from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Literal

from src.core.advisory_copilot.models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotEvidencePacket,
    CopilotEvidencePacketSection,
    CopilotEvidenceSectionInput,
    CopilotLineageRef,
    CopilotSourceDependency,
    CopilotUnsupportedEvidence,
)

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

_TECHNICAL_LEAK_TERMS = (
    "raw prompt",
    "provider response",
    "trace id",
    "correlation id",
    "run ledger",
    "raw payload",
)


def required_evidence_sections(
    action_family: CopilotActionFamily,
) -> tuple[CopilotEvidenceSectionKey, ...]:
    return ACTION_REQUIRED_EVIDENCE_SECTIONS[action_family]


class CopilotEvidencePacketBuildError(ValueError):
    pass


def build_copilot_evidence_packet(
    *,
    evidence_packet_id: str,
    action_family: CopilotActionFamily,
    portfolio_id: str,
    proposal_id: str | None,
    audience: CopilotAudience,
    source_sections: tuple[CopilotEvidenceSectionInput, ...],
) -> CopilotEvidencePacket:
    required_sections = required_evidence_sections(action_family)
    sections_by_key = {section.section_key: section for section in source_sections}
    projected_sections: list[CopilotEvidencePacketSection] = []
    unsupported: list[CopilotUnsupportedEvidence] = []

    for section_key in required_sections:
        section = sections_by_key.get(section_key)
        if section is None:
            unsupported.append(
                CopilotUnsupportedEvidence(
                    reason_code="SOURCE_NOT_AVAILABLE",
                    source_dependency=None,
                    advisor_message=f"{section_key.replace('_', ' ').title()} is not available.",
                )
            )
            continue
        if audience not in section.allowed_audiences:
            unsupported.append(
                CopilotUnsupportedEvidence(
                    reason_code="RESTRICTED_BY_ROLE",
                    source_dependency=None,
                    advisor_message=(
                        f"{section.title} is restricted for the requested reviewer role."
                    ),
                )
            )
            continue
        _assert_business_safe_text(section.title, *section.summary_items)
        projected_sections.append(
            CopilotEvidencePacketSection(
                section_key=section.section_key,
                title=section.title,
                evidence_class=section.evidence_class,
                source_refs=section.source_refs,
                summary_items=section.summary_items,
            )
        )

    lineage_refs = (
        CopilotLineageRef(
            lineage_type="EVIDENCE_PACKET",
            lineage_id=evidence_packet_id,
            source_system="lotus-advise",
        ),
    )
    packet_hash = _packet_hash(
        evidence_packet_id=evidence_packet_id,
        action_family=action_family,
        portfolio_id=portfolio_id,
        proposal_id=proposal_id,
        audience=audience,
        sections=tuple(projected_sections),
        unsupported=tuple(unsupported),
        lineage_refs=lineage_refs,
    )
    return CopilotEvidencePacket(
        evidence_packet_id=evidence_packet_id,
        evidence_packet_hash=packet_hash,
        action_family=action_family,
        portfolio_id=portfolio_id,
        proposal_id=proposal_id,
        sections=tuple(projected_sections),
        unsupported_evidence=tuple(unsupported),
        lineage_refs=lineage_refs,
        retention_class="ADVISORY_REVIEW_RECORD",
    )


def _assert_business_safe_text(*values: str) -> None:
    text = " ".join(values).lower()
    for term in _TECHNICAL_LEAK_TERMS:
        if term in text:
            raise CopilotEvidencePacketBuildError("COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL")


def _packet_hash(
    *,
    evidence_packet_id: str,
    action_family: CopilotActionFamily,
    portfolio_id: str,
    proposal_id: str | None,
    audience: CopilotAudience,
    sections: tuple[CopilotEvidencePacketSection, ...],
    unsupported: tuple[CopilotUnsupportedEvidence, ...],
    lineage_refs: tuple[CopilotLineageRef, ...],
) -> str:
    payload = {
        "evidence_packet_id": evidence_packet_id,
        "action_family": action_family,
        "portfolio_id": portfolio_id,
        "proposal_id": proposal_id,
        "audience": audience,
        "sections": [section.model_dump(mode="json") for section in sections],
        "unsupported": [item.model_dump(mode="json") for item in unsupported],
        "lineage_refs": [item.model_dump(mode="json") for item in lineage_refs],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
