from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.memo_models import (
    AdvisoryProposalMemoEvidencePack,
    ProposalMemoSection,
    ProposalMemoSectionStatus,
    ProposalMemoSourceAuthorityManifest,
)
from src.core.proposals.memo_section_factory import (
    build_appendix_section,
    build_memo_claims,
    build_memo_section,
)
from src.core.proposals.memo_section_groups import (
    build_appendix_memo_sections,
    build_foundational_memo_sections,
    build_operational_memo_sections,
    build_policy_review_memo_sections,
)

_MEMO_VERSION = "advisory-proposal-memo-evidence-pack.v1"


def build_advisory_proposal_memo_evidence_pack(
    *,
    proposal_id: str,
    proposal_version_no: int,
    artifact_json: dict[str, Any],
    evidence_bundle: dict[str, Any],
    proposal_version_id: str | None = None,
) -> AdvisoryProposalMemoEvidencePack:
    """Build a deterministic RFC-0024 memo evidence pack from stored proposal evidence.

    Slice 5 deliberately does not persist, publish, render, archive, or promote the memo. It is a
    pure projection over already persisted proposal evidence and source-readiness posture.
    """

    memo_input = {
        "proposal_id": proposal_id,
        "proposal_version_no": proposal_version_no,
        "proposal_version_id": proposal_version_id,
        "artifact": deepcopy(artifact_json),
        "evidence_bundle": deepcopy(evidence_bundle),
    }
    source_input_hash = hash_canonical_payload(memo_input)
    source_manifest = _build_source_authority_manifest(evidence_bundle)
    sections = _build_sections(
        artifact=artifact_json,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
    )
    status = _overall_status(sections)
    memo_without_hash = {
        "memo_version": _MEMO_VERSION,
        "proposal_id": proposal_id,
        "proposal_version_no": proposal_version_no,
        "proposal_version_id": proposal_version_id,
        "artifact_id": artifact_json.get("artifact_id"),
        "status": status,
        "projection_policy": _projection_policy(),
        "source_authority_manifest": source_manifest.model_dump(mode="json"),
        "sections": [section.model_dump(mode="json") for section in sections],
        "source_input_hash": source_input_hash,
        "supportability": _supportability(),
    }
    memo_hash = hash_canonical_payload(memo_without_hash)
    memo_id = memo_hash.replace("sha256:", "memo_", 1)[:24]
    return AdvisoryProposalMemoEvidencePack(
        memo_id=memo_id,
        memo_version=_MEMO_VERSION,
        proposal_id=proposal_id,
        proposal_version_no=proposal_version_no,
        proposal_version_id=proposal_version_id,
        artifact_id=_optional_str(artifact_json.get("artifact_id")),
        status=status,
        projection_policy=_projection_policy(),
        source_authority_manifest=source_manifest,
        sections=sections,
        source_input_hash=source_input_hash,
        memo_hash=memo_hash,
        supportability=_supportability(),
    )


def _build_source_authority_manifest(
    evidence_bundle: dict[str, Any],
) -> ProposalMemoSourceAuthorityManifest:
    readiness = _dict_at(evidence_bundle, "memo_source_readiness")
    return ProposalMemoSourceAuthorityManifest(
        contract_version=str(readiness.get("contract_version") or "UNKNOWN"),
        overall_posture=str(readiness.get("overall_posture") or "PENDING_REVIEW"),
        source_authority=deepcopy(_dict_at(readiness, "source_authority")),
        section_statuses=_source_readiness_section_statuses(readiness),
    )


def _source_readiness_section_statuses(readiness: dict[str, Any]) -> dict[str, str]:
    return dict(
        status
        for section in _list_at(readiness, "sections")
        if (status := _source_readiness_section_status(section)) is not None
    )


def _source_readiness_section_status(section: Any) -> tuple[str, str] | None:
    if not isinstance(section, dict):
        return None
    key = section.get("key")
    status = section.get("status")
    if not key or not status:
        return None
    return str(key), str(status)


def _build_sections(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
) -> list[ProposalMemoSection]:
    return [
        *build_foundational_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=build_memo_section,
            claims_factory=build_memo_claims,
        ),
        *build_policy_review_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=build_memo_section,
        ),
        *build_operational_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=build_memo_section,
            claims_factory=build_memo_claims,
        ),
        *build_appendix_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            appendix_factory=build_appendix_section,
        ),
    ]


def _overall_status(sections: list[ProposalMemoSection]) -> ProposalMemoSectionStatus:
    statuses = {section.status for section in sections}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "PENDING_REVIEW" in statuses:
        return "PENDING_REVIEW"
    return "READY"


def _projection_policy() -> dict[str, Any]:
    return {
        "advisor_projection": "SUPPORTED_BY_PURE_BUILDER",
        "client_draft_projection": "BLOCKED_UNTIL_POLICY_REDACTION_AND_REVIEW",
        "client_ready_publication": "BLOCKED",
        "report_render_archive": "BLOCKED_UNTIL_LATER_RFC0024_SLICES",
    }


def _supportability() -> dict[str, Any]:
    return {
        "capability_posture": "ADVISE_MEMO_EVIDENCE_PACK_SUPPORTED_INTERNAL",
        "persistence": "SUPPORTED_BY_RFC0024_SLICE6",
        "api": "SUPPORTED_BY_RFC0024_SLICE7",
        "policy_fee_conflict_enrichment": "SUPPORTED_BY_RFC0024_SLICE8",
        "memo_generation": "DETERMINISTIC_SOURCE_EVIDENCE_PROJECTION",
        "report_render_archive": "NOT_IMPLEMENTED",
        "client_ready_publication": "BLOCKED",
    }


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_at(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
