from __future__ import annotations

from src.core.advisory_copilot import (
    CopilotEvidencePacket,
    CopilotEvidencePacketSection,
    CopilotSourceRef,
)
from src.integrations.lotus_ai.advisory_copilot_request import (
    MAX_COPILOT_SOURCE_REFS,
    caller_correlation_id,
    requested_output_keys,
    safe_reason,
    source_refs,
)


def _packet(*, evidence_packet_id: str = "copilot_packet_pb_sg_001") -> CopilotEvidencePacket:
    return CopilotEvidencePacket(
        evidence_packet_id=evidence_packet_id,
        evidence_packet_hash="sha256:copilot-evidence-packet-001",
        action_family="PROPOSAL_EXPLANATION",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proposal_id="proposal_sg_structured_note_001",
        sections=tuple(
            CopilotEvidencePacketSection(
                section_key=f"POLICY_POSTURE_{index}",
                title="Policy posture",
                evidence_class="COMPLIANCE_REVIEW_EVIDENCE",
                source_refs=tuple(
                    CopilotSourceRef(
                        source_system="lotus-advise",
                        source_type="POLICY_EVALUATION",
                        source_id=f"policy_eval_sg_{index:03d}_{ref_index:02d}",
                        content_hash="sha256:policy-evaluation",
                        access_class="COMPLIANCE_REVIEW_EVIDENCE",
                    )
                    for ref_index in range(8)
                ),
                summary_items=("Policy evaluation requires compliance review.",),
            )
            for index in range(12)
        ),
        retention_class="ADVISORY_REVIEW_RECORD",
    )


def test_source_refs_bound_packet_refs_and_cited_evidence_without_raw_objects() -> None:
    refs = source_refs(_packet())

    assert len(refs) == MAX_COPILOT_SOURCE_REFS
    assert refs[0] == "lotus-advise:copilot-evidence-packet:copilot_packet_pb_sg_001"
    assert refs[1] == (
        "lotus-advise:copilot-evidence-packet-hash:sha256:copilot-evidence-packet-001"
    )
    assert refs[2].startswith("lotus-advise:POLICY_EVALUATION:policy_eval_sg_000_00:")
    assert all("CopilotSourceRef" not in ref for ref in refs)


def test_caller_correlation_id_hashes_oversized_packet_identifier() -> None:
    correlation_id = caller_correlation_id(_packet(evidence_packet_id="pkt_" + ("x" * 150)))

    assert correlation_id.startswith("advisory-copilot-")
    assert len(correlation_id) <= 128
    assert "x" * 120 not in correlation_id


def test_requested_outputs_dedupe_and_bound_advisor_requested_keys() -> None:
    outputs = requested_output_keys(
        ["advisor_review_summary", "advisor_review_summary", "x" * 140]
        + [f"section_{index}" for index in range(12)]
    )

    assert len(outputs) == 8
    assert outputs[0] == "advisor_review_summary"
    assert all(len(output) <= 96 for output in outputs)


def test_safe_reason_removes_raw_prompt_material_and_bounds_values() -> None:
    reason = safe_reason(
        {
            "purpose": "advisor review " * 120,
            "raw_prompt": "secret raw prompt should not leave advise",
            "notes": [" cited evidence only ", "x" * 1200, 7],
            "tuple_notes": (" first tuple note ", "", 8),
            "metadata": {"proposal_id": "proposal_sg_structured_note_001"},
            "count": 2,
            "accepted": True,
        }
    )

    assert "raw_prompt" not in reason
    assert "secret raw prompt" not in str(reason).lower()
    assert len(reason["purpose"]) <= 1000
    assert isinstance(reason["notes"], list)
    assert reason["notes"][0] == "cited evidence only"
    assert len(reason["notes"][1]) <= 1000
    assert reason["tuple_notes"] == ["first tuple note"]
    assert reason["metadata"] == "{'proposal_id': 'proposal_sg_structured_note_001'}"
    assert reason["count"] == 2
    assert reason["accepted"] is True
