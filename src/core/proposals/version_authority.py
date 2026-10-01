"""Bind lifecycle mutations to one immutable, current proposal version."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.proposals.exceptions import ProposalNotFoundError, ProposalStateConflictError
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalRecord,
    ProposalVersionRecord,
)
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalVersionAuthority:
    """Server-resolved immutable version evidence for one lifecycle mutation."""

    version_no: int
    proposal_version_id: str
    request_hash: str
    artifact_hash: str
    simulation_hash: str

    @classmethod
    def from_version(cls, version: ProposalVersionRecord) -> "ProposalVersionAuthority":
        return cls(
            version_no=version.version_no,
            proposal_version_id=version.proposal_version_id,
            request_hash=version.request_hash,
            artifact_hash=version.artifact_hash,
            simulation_hash=version.simulation_hash,
        )

    def audit_payload(self) -> dict[str, str | int]:
        return {
            "version_no": self.version_no,
            "proposal_version_id": self.proposal_version_id,
            "request_hash": self.request_hash,
            "artifact_hash": self.artifact_hash,
            "simulation_hash": self.simulation_hash,
        }


def resolve_current_proposal_version_authority(
    *,
    repository: ProposalRepository,
    proposal: ProposalRecord,
    requested_version_no: int | None,
) -> ProposalVersionAuthority:
    """Resolve omitted input atomically to current evidence and reject stale instructions.

    The caller may omit the version for compatibility, but persisted approval, transition and
    handoff evidence always carries the server-resolved immutable version.  A concurrent new
    version is fenced by the existing proposal state/version compare-and-set at persistence.
    """

    if requested_version_no is not None and requested_version_no != proposal.current_version_no:
        raise ProposalStateConflictError("PROPOSAL_VERSION_CONFLICT")

    version = repository.get_version(
        proposal_id=proposal.proposal_id,
        version_no=proposal.current_version_no,
    )
    if version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    return ProposalVersionAuthority.from_version(version)


def require_current_version_approvals(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    authority: ProposalVersionAuthority,
    require_consent: bool,
) -> None:
    """Do not infer approval from workflow state or an earlier proposal version.

    Pre-existing approvals without an embedded authority snapshot remain usable only when their
    persisted related version matches. New records additionally have to match the immutable
    version identity and content hashes.
    """

    approvals = repository.list_approvals(proposal_id=proposal_id)
    risk_or_compliance = any(
        _applies_to_authority(approval, authority)
        and approval.approval_type in {"RISK", "COMPLIANCE"}
        for approval in approvals
    )
    consent = any(
        _applies_to_authority(approval, authority) and approval.approval_type == "CLIENT_CONSENT"
        for approval in approvals
    )
    if not risk_or_compliance or (require_consent and not consent):
        raise ProposalStateConflictError("CURRENT_VERSION_APPROVALS_MISSING")


def _applies_to_authority(
    approval: ProposalApprovalRecordData, authority: ProposalVersionAuthority
) -> bool:
    if not approval.approved or approval.related_version_no != authority.version_no:
        return False
    recorded = approval.details_json.get("proposal_version_authority")
    return recorded is None or recorded == authority.audit_payload()
