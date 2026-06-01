from __future__ import annotations

import hashlib
import re
from typing import Any

from src.core.advisor_cockpit.source_read_model import (
    AdvisorCockpitSourceBatch,
    build_advisor_cockpit_source_read_model,
)
from src.core.advisory_copilot.models import (
    CopilotActionFamily,
    CopilotEvidenceSectionInput,
    CopilotSourceRef,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)

EVIDENCE_PACKET_ID_MAX_LENGTH = 160
LINEAGE_REF_ID_MAX_LENGTH = 160

_SOURCE_REF_ID_MAX_LENGTH = 160
_CONTENT_HASH_MAX_LENGTH = 128
_SUMMARY_ITEM_MAX_LENGTH = 1000
_REFERENCE_DIGEST_LENGTH = 16


def build_proposal_version_source_sections(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    memo: ProposalMemoRecord | None,
    memos: list[ProposalMemoRecord],
    approvals: list[ProposalApprovalRecordData],
    events: list[ProposalWorkflowEventRecord],
    policy_evaluations: list[PolicyEvaluationRecord],
) -> tuple[CopilotEvidenceSectionInput, ...]:
    sections = [
        _proposal_context_section(proposal=proposal, version=version),
        _narrative_posture_section(proposal=proposal, version=version),
        _cockpit_actions_section(
            proposal=proposal,
            memos=memos,
            approvals=approvals,
            events=events,
            policy_evaluations=policy_evaluations,
        ),
    ]
    if memo is not None:
        sections.append(_memo_evidence_section(memo=memo))
        if _has_report_readiness(memo):
            sections.append(_report_readiness_section(memo=memo))
    if policy_evaluations:
        sections.append(_policy_posture_section(policy_evaluations=policy_evaluations))
    if _has_operations_handoff(events):
        sections.append(_operations_handoff_section(proposal=proposal, events=events))
    return tuple(sections)


def default_proposal_version_packet_id(
    *, action_family: CopilotActionFamily, proposal_id: str, version_no: int
) -> str:
    return bounded_projection_reference(
        _identifier(f"copilot_packet_{action_family.lower()}_{proposal_id}_v{version_no}"),
        max_length=EVIDENCE_PACKET_ID_MAX_LENGTH,
    )


def bounded_projection_reference(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:_REFERENCE_DIGEST_LENGTH]
    prefix_length = max_length - _REFERENCE_DIGEST_LENGTH - 1
    return f"{normalized[:prefix_length].rstrip('_')}_{digest}"


def _proposal_context_section(
    *, proposal: ProposalRecord, version: ProposalVersionRecord
) -> CopilotEvidenceSectionInput:
    return CopilotEvidenceSectionInput(
        section_key="PROPOSAL_CONTEXT",
        title="Proposal context",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=(
            _source_ref(
                source_type="PROPOSAL_VERSION",
                source_id=version.proposal_version_id,
                content_hash=version.artifact_hash,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=(
            _summary_item(
                f"{proposal.title or 'Advisory proposal'} is in {proposal.current_state} "
                f"for portfolio {proposal.portfolio_id}."
            ),
            _summary_item(
                f"Proposal version {version.version_no} was created with "
                f"{version.status_at_creation} source readiness."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER", "OPERATIONS_SUPPORT"),
    )


def _narrative_posture_section(
    *, proposal: ProposalRecord, version: ProposalVersionRecord
) -> CopilotEvidenceSectionInput:
    narrative_status = _safe_nested_string(
        version.artifact_json,
        "narrative",
        "status",
    ) or _safe_nested_string(version.artifact_json, "narrative_status")
    if not narrative_status:
        narrative_status = str(version.status_at_creation)
    return CopilotEvidenceSectionInput(
        section_key="NARRATIVE_POSTURE",
        title="Proposal narrative posture",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=(
            _source_ref(
                source_type="PROPOSAL_NARRATIVE",
                source_id=version.proposal_version_id,
                content_hash=version.artifact_hash,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=(
            _summary_item(f"Advisor-use proposal narrative posture is {narrative_status}."),
            _summary_item(
                f"Client-ready publication remains blocked for proposal {proposal.proposal_id}."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
    )


def _memo_evidence_section(*, memo: ProposalMemoRecord) -> CopilotEvidenceSectionInput:
    return CopilotEvidenceSectionInput(
        section_key="MEMO_EVIDENCE",
        title="Proposal memo evidence",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=(
            _source_ref(
                source_type="PROPOSAL_MEMO",
                source_id=memo.memo_id,
                content_hash=memo.memo_hash,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=(
            _summary_item(f"Proposal memo {memo.memo_id} is {memo.memo_status}."),
            _summary_item(f"Memo lifecycle posture is {memo.lifecycle_status}."),
            (
                "Memo evidence remains advisor-use only until source review and publication "
                "gates pass."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER", "OPERATIONS_SUPPORT"),
    )


def _policy_posture_section(
    *, policy_evaluations: list[PolicyEvaluationRecord]
) -> CopilotEvidenceSectionInput:
    latest = sorted(policy_evaluations, key=lambda item: item.generated_at)[-1]
    review_items = sorted(
        set(
            latest.approval_dependencies
            + latest.disclosure_requirements
            + latest.consent_requirements
            + latest.source_gaps
        )
    )
    summary_items = [
        _summary_item(f"Policy evaluation {latest.evaluation_id} is {latest.evaluation_status}."),
        _summary_item(
            f"Policy pack {latest.policy_pack_id} version {latest.policy_version} is the "
            "source authority."
        ),
        "Client-ready publication remains blocked until policy and review gates are resolved.",
    ]
    if review_items:
        summary_items.append(
            _summary_item(f"Open policy evidence items: {', '.join(review_items[:5])}.")
        )
    return CopilotEvidenceSectionInput(
        section_key="POLICY_POSTURE",
        title="Policy posture",
        evidence_class="COMPLIANCE_REVIEW_EVIDENCE",
        source_refs=(
            _source_ref(
                source_type="POLICY_EVALUATION",
                source_id=latest.evaluation_id,
                content_hash=latest.evaluation_hash,
                access_class="COMPLIANCE_REVIEW_EVIDENCE",
            ),
        ),
        summary_items=tuple(summary_items),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
    )


def _cockpit_actions_section(
    *,
    proposal: ProposalRecord,
    memos: list[ProposalMemoRecord],
    approvals: list[ProposalApprovalRecordData],
    events: list[ProposalWorkflowEventRecord],
    policy_evaluations: list[PolicyEvaluationRecord],
) -> CopilotEvidenceSectionInput:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[proposal],
            policy_evaluations=policy_evaluations,
            memos=memos,
            approvals=approvals,
            workflow_events=events,
        )
    )
    action_items = read_model.action_items[:5]
    summaries = [
        _summary_item(f"{item.title} is {item.status}; owner is {item.owner_role}.")
        for item in action_items
    ] or ["No advisor cockpit action is currently open for this proposal."]
    return CopilotEvidenceSectionInput(
        section_key="COCKPIT_ACTIONS",
        title="Advisor cockpit actions",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=tuple(
            _source_ref(
                source_type="ADVISOR_COCKPIT_ACTION",
                source_id=item.action_item_id,
                content_hash=None,
                access_class="ADVISOR_USE_SUMMARY",
            )
            for item in action_items
        )
        or (
            _source_ref(
                source_type="ADVISOR_COCKPIT_SCOPE",
                source_id=proposal.proposal_id,
                content_hash=None,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=tuple(summaries),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER", "OPERATIONS_SUPPORT"),
    )


def _report_readiness_section(*, memo: ProposalMemoRecord) -> CopilotEvidenceSectionInput:
    latest_report_ref = _latest_ref(memo.report_package_events_json) or memo.memo_id
    latest_archive_ref = _latest_ref(memo.archive_refs_json) or "Not recorded"
    return CopilotEvidenceSectionInput(
        section_key="REPORT_READINESS",
        title="Report readiness",
        evidence_class="OPERATIONS_HANDOFF_EVIDENCE",
        source_refs=(
            _source_ref(
                source_type="MEMO_REPORT_PACKAGE",
                source_id=latest_report_ref,
                content_hash=memo.memo_hash,
                access_class="OPERATIONS_HANDOFF_EVIDENCE",
            ),
        ),
        summary_items=(
            "Advisor-use report package evidence is recorded for the memo.",
            _summary_item(f"Latest archive reference posture: {latest_archive_ref}."),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "OPERATIONS_SUPPORT"),
    )


def _operations_handoff_section(
    *, proposal: ProposalRecord, events: list[ProposalWorkflowEventRecord]
) -> CopilotEvidenceSectionInput:
    execution_events = [
        event
        for event in events
        if str(event.event_type).startswith("EXECUTION") or event.event_type == "EXECUTED"
    ]
    latest = sorted(execution_events, key=lambda item: (item.occurred_at, item.event_id))[-1]
    return CopilotEvidenceSectionInput(
        section_key="OPERATIONS_HANDOFF",
        title="Operations handoff",
        evidence_class="OPERATIONS_HANDOFF_EVIDENCE",
        source_refs=(
            _source_ref(
                source_type="PROPOSAL_WORKFLOW_EVENT",
                source_id=latest.event_id,
                content_hash=None,
                access_class="OPERATIONS_HANDOFF_EVIDENCE",
            ),
        ),
        summary_items=(
            _summary_item(f"Latest implementation handoff posture is {latest.event_type}."),
            _summary_item(
                f"Proposal {proposal.proposal_id} remains source-owned for lifecycle state."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "OPERATIONS_SUPPORT"),
    )


def _has_report_readiness(memo: ProposalMemoRecord) -> bool:
    return bool(memo.report_package_events_json or memo.archive_refs_json)


def _has_operations_handoff(events: list[ProposalWorkflowEventRecord]) -> bool:
    return any(
        str(event.event_type).startswith("EXECUTION") or event.event_type == "EXECUTED"
        for event in events
    )


def _source_ref(
    *,
    source_type: str,
    source_id: str,
    content_hash: str | None,
    access_class: str,
) -> CopilotSourceRef:
    return CopilotSourceRef(
        source_system="lotus-advise",
        source_type=source_type,
        source_id=bounded_projection_reference(source_id, max_length=_SOURCE_REF_ID_MAX_LENGTH),
        content_hash=_bounded_content_hash(content_hash),
        access_class=access_class,  # type: ignore[arg-type]
    )


def _identifier(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def _summary_item(value: str) -> str:
    return _bounded_text(value, max_length=_SUMMARY_ITEM_MAX_LENGTH)


def _bounded_text(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    suffix = "..."
    return normalized[: max_length - len(suffix)].rstrip() + suffix


def _bounded_content_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= _CONTENT_HASH_MAX_LENGTH:
        return normalized
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def _safe_nested_string(payload: dict[str, Any], *path: str) -> str | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current.strip() if isinstance(current, str) and current.strip() else None


def _latest_ref(items: list[dict[str, Any]]) -> str | None:
    for item in reversed(items):
        for key in ("report_reference_id", "archive_ref", "archive_reference_id", "event_id"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None
