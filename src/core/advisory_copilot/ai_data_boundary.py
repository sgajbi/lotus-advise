from __future__ import annotations

import hashlib
from typing import Any, get_args

from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.reference_models import CopilotSourceRef
from src.core.advisory_copilot.type_models import CopilotEvidenceAccessClass

ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION = "advisory-copilot-ai-data-boundary.v1"
ADVISORY_COPILOT_PROVIDER_RETENTION_POLICY = "NO_TRAINING_ZERO_PROVIDER_RETENTION"
ADVISORY_COPILOT_PROVIDER_RESIDENCY = "SG"
ADVISORY_COPILOT_DELETION_POLICY = "DELETE_WITH_ADVISE_RETENTION_OR_LEGAL_HOLD"
_ALLOWED_EVIDENCE_CLASSES = set(get_args(CopilotEvidenceAccessClass))


def minimized_copilot_evidence_packet(evidence_packet: CopilotEvidencePacket) -> dict[str, Any]:
    _validate_evidence_classes(evidence_packet)
    return {
        "contract_version": ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION,
        "evidence_packet_hash": evidence_packet.evidence_packet_hash,
        "action_family": evidence_packet.action_family,
        "portfolio_ref": _tokenized_identifier("portfolio", evidence_packet.portfolio_id),
        "proposal_ref": _tokenized_identifier("proposal", evidence_packet.proposal_id),
        "retention_class": evidence_packet.retention_class,
        "client_ready_publication": evidence_packet.client_ready_publication,
        "sections": [
            {
                "section_key": section.section_key,
                "title": section.title,
                "evidence_class": section.evidence_class,
                "summary_items": list(section.summary_items),
                "source_refs": [
                    minimized_source_ref(source_ref) for source_ref in section.source_refs
                ],
            }
            for section in evidence_packet.sections
        ],
        "unsupported_evidence": [
            {
                "reason_code": item.reason_code,
                "source_dependency": item.source_dependency,
                "advisor_message": item.advisor_message,
            }
            for item in evidence_packet.unsupported_evidence
        ],
    }


def advisory_copilot_ai_data_controls(*, approved_provider_id: str) -> dict[str, Any]:
    return {
        "contract_version": ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION,
        "approved_provider_id": approved_provider_id,
        "training_allowed": False,
        "provider_retention_policy": ADVISORY_COPILOT_PROVIDER_RETENTION_POLICY,
        "residency": ADVISORY_COPILOT_PROVIDER_RESIDENCY,
        "deletion_policy": ADVISORY_COPILOT_DELETION_POLICY,
        "payload_minimization": "TOKENIZED_IDENTIFIERS_CLASSIFIED_EVIDENCE_ONLY",
        "source_ref_policy": "GROUNDING_REFERENCES_RETAINED_IN_CONTEXT_SOURCE_REFS",
    }


def minimized_source_ref(source_ref: CopilotSourceRef) -> dict[str, str | None]:
    _validate_access_class(str(source_ref.access_class))
    return {
        "source_system": source_ref.source_system,
        "source_type": source_ref.source_type,
        "source_ref_token": _tokenized_identifier(
            "source-ref",
            ":".join(
                (
                    source_ref.source_system,
                    source_ref.source_type,
                    source_ref.source_id,
                    source_ref.content_hash or "no-content-hash",
                )
            ),
        ),
        "content_hash": source_ref.content_hash,
        "access_class": source_ref.access_class,
    }


def _validate_evidence_classes(evidence_packet: CopilotEvidencePacket) -> None:
    for section in evidence_packet.sections:
        _validate_access_class(str(section.evidence_class))
        for source_ref in section.source_refs:
            _validate_access_class(str(source_ref.access_class))


def _validate_access_class(value: str) -> None:
    if value not in _ALLOWED_EVIDENCE_CLASSES:
        raise ValueError("COPILOT_AI_DATA_CLASSIFICATION_UNAPPROVED")


def _tokenized_identifier(scope: str, value: str | None) -> str | None:
    if value is None:
        return None
    digest = hashlib.sha256(f"{scope}:{value}".encode("utf-8")).hexdigest()[:32]
    return f"tok_{scope}_{digest}"
