from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.advisory_copilot import (
    ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION,
    ADVISORY_COPILOT_DELETION_POLICY,
    ADVISORY_COPILOT_PROVIDER_RESIDENCY,
    ADVISORY_COPILOT_PROVIDER_RETENTION_POLICY,
    CopilotEvidencePacket,
    CopilotEvidencePacketSection,
    CopilotLineageRef,
    CopilotSourceRef,
    advisory_copilot_ai_data_controls,
    minimized_copilot_evidence_packet,
)

CONTRACT_PATH = Path("contracts/advisory-copilot/ai-data-boundary.v1.json")


def test_advisory_copilot_ai_data_boundary_contract_aligns_to_code() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["contract_version"] == ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION
    assert contract["approved_provider_id"] == "lotus-ai"
    assert contract["provider_terms"] == {
        "training_allowed": False,
        "provider_retention_policy": ADVISORY_COPILOT_PROVIDER_RETENTION_POLICY,
        "residency": ADVISORY_COPILOT_PROVIDER_RESIDENCY,
        "deletion_policy": ADVISORY_COPILOT_DELETION_POLICY,
    }
    assert contract["payload_minimization"]["portfolio_id"] == "tokenized"
    assert contract["payload_minimization"]["raw_prompt"] == "forbidden"
    assert (
        "copilot_evidence_packet.sections.source_refs.source_ref_token"
        in (contract["field_classes"])
    )


def test_minimized_copilot_evidence_packet_tokenizes_sensitive_identifiers() -> None:
    minimized = minimized_copilot_evidence_packet(_packet())
    serialized = json.dumps(minimized, sort_keys=True)

    assert minimized["contract_version"] == ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION
    assert minimized["portfolio_ref"].startswith("tok_portfolio_")
    assert minimized["proposal_ref"].startswith("tok_proposal_")
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "proposal_sg_structured_note_001" not in serialized
    assert "policy_eval_sg_001" not in serialized
    assert minimized["sections"][0]["source_refs"][0]["source_ref_token"].startswith(
        "tok_source-ref_"
    )
    assert minimized["sections"][0]["source_refs"][0]["content_hash"] == (
        "sha256:policy-evaluation"
    )


def test_minimized_copilot_evidence_packet_rejects_unclassified_evidence() -> None:
    unsafe_section = _packet().sections[0].model_copy(update={"evidence_class": "SECRET"})
    unsafe_packet = _packet().model_copy(update={"sections": (unsafe_section,)})

    with pytest.raises(ValueError, match="COPILOT_AI_DATA_CLASSIFICATION_UNAPPROVED"):
        minimized_copilot_evidence_packet(unsafe_packet)


def test_advisory_copilot_ai_data_controls_are_provider_bound() -> None:
    controls = advisory_copilot_ai_data_controls(approved_provider_id="lotus-ai")

    assert controls == {
        "contract_version": ADVISORY_COPILOT_AI_DATA_BOUNDARY_CONTRACT_VERSION,
        "approved_provider_id": "lotus-ai",
        "training_allowed": False,
        "provider_retention_policy": ADVISORY_COPILOT_PROVIDER_RETENTION_POLICY,
        "residency": ADVISORY_COPILOT_PROVIDER_RESIDENCY,
        "deletion_policy": ADVISORY_COPILOT_DELETION_POLICY,
        "payload_minimization": "TOKENIZED_IDENTIFIERS_CLASSIFIED_EVIDENCE_ONLY",
        "source_ref_policy": "GROUNDING_REFERENCES_RETAINED_IN_CONTEXT_SOURCE_REFS",
    }


def _packet() -> CopilotEvidencePacket:
    source_ref = CopilotSourceRef(
        source_system="lotus-advise",
        source_type="POLICY_EVALUATION",
        source_id="policy_eval_sg_001",
        content_hash="sha256:policy-evaluation",
        access_class="COMPLIANCE_REVIEW_EVIDENCE",
    )
    return CopilotEvidencePacket(
        evidence_packet_id="copilot_packet_pb_sg_001",
        evidence_packet_hash="sha256:copilot-evidence-packet-001",
        action_family="PROPOSAL_EXPLANATION",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proposal_id="proposal_sg_structured_note_001",
        sections=(
            CopilotEvidencePacketSection(
                section_key="POLICY_POSTURE",
                title="Policy posture",
                evidence_class="COMPLIANCE_REVIEW_EVIDENCE",
                source_refs=(source_ref,),
                summary_items=("Policy evaluation requires compliance review.",),
            ),
        ),
        lineage_refs=(
            CopilotLineageRef(
                lineage_type="EVIDENCE_PACKET",
                lineage_id="copilot_packet_pb_sg_001",
                source_system="lotus-advise",
            ),
        ),
        retention_class="ADVISORY_REVIEW_RECORD",
    )
