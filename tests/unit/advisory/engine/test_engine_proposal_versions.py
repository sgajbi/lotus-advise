from datetime import datetime, timezone

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.models import GateDecision, GateDecisionSummary, ProposalResult
from src.core.proposals.models import ProposalRecord
from src.core.proposals.versions import (
    apply_new_version_lifecycle_state,
    build_proposal_version_record,
)


def _proposal_result(*, correlation_id: str = "corr_version") -> ProposalResult:
    gate_decision = GateDecision(
        gate="EXECUTION_READY",
        recommended_next_step="EXECUTE",
        reasons=[],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        ),
    )
    return ProposalResult.model_construct(
        proposal_run_id="pr_version",
        correlation_id=correlation_id,
        status="READY",
        before={"portfolio_id": "pf_version"},
        intents=[],
        after_simulated={"portfolio_id": "pf_version"},
        explanation={"summary": "ready"},
        diagnostics={"warnings": [], "data_quality": {}},
        lineage={"request_hash": "sha256:req", "idempotency_key": "idem_version"},
        gate_decision=gate_decision,
    )


def _artifact() -> dict:
    return {
        "artifact_id": "pa_version",
        "evidence_bundle": {
            "hashes": {
                "artifact_hash": "sha256:artifact",
            }
        },
    }


def test_build_proposal_version_record_captures_hashes_and_gate_decision():
    proposal_result = _proposal_result(correlation_id="corr_one")
    created_at = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
    evidence_bundle = {"hashes": {"artifact_hash": "sha256:artifact"}}

    version = build_proposal_version_record(
        proposal_version_id="ppv_version",
        proposal_id="pp_version",
        version_no=2,
        request_hash="sha256:request",
        proposal_result=proposal_result,
        artifact=_artifact(),
        evidence_bundle=evidence_bundle,
        created_at=created_at,
        store_evidence_bundle=True,
    )

    expected_simulation_payload = proposal_result.model_dump(mode="json", warnings=False)
    expected_simulation_hash = hash_canonical_payload(
        strip_keys(expected_simulation_payload, exclude={"correlation_id", "idempotency_key"})
    )
    assert version.proposal_version_id == "ppv_version"
    assert version.proposal_id == "pp_version"
    assert version.version_no == 2
    assert version.created_at == created_at
    assert version.request_hash == "sha256:request"
    assert version.artifact_hash == "sha256:artifact"
    assert version.simulation_hash == expected_simulation_hash
    assert version.status_at_creation == "READY"
    assert version.proposal_result_json == expected_simulation_payload
    assert version.artifact_json == _artifact()
    assert version.evidence_bundle_json == evidence_bundle
    assert version.gate_decision_json == proposal_result.gate_decision.model_dump(mode="json")


def test_build_proposal_version_record_can_omit_evidence_bundle():
    version = build_proposal_version_record(
        proposal_version_id="ppv_version_redacted",
        proposal_id="pp_version",
        version_no=3,
        request_hash="sha256:request",
        proposal_result=_proposal_result(),
        artifact=_artifact(),
        evidence_bundle={"sensitive": "lineage"},
        created_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
        store_evidence_bundle=False,
    )

    assert version.evidence_bundle_json == {}


def test_apply_new_version_lifecycle_state_resets_proposal_to_draft():
    original_event_at = datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)
    occurred_at = datetime(2026, 5, 20, 9, 10, tzinfo=timezone.utc)
    proposal = ProposalRecord(
        proposal_id="pp_version_state",
        portfolio_id="pf_version_state",
        mandate_id="mandate_version_state",
        jurisdiction="SG",
        created_by="advisor_version_state",
        created_at=original_event_at,
        last_event_at=original_event_at,
        current_state="EXECUTION_READY",
        current_version_no=1,
        title="Version lifecycle state",
        advisor_notes=None,
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )

    apply_new_version_lifecycle_state(
        proposal=proposal,
        version_no=2,
        occurred_at=occurred_at,
    )

    assert proposal.current_version_no == 2
    assert proposal.current_state == "DRAFT"
    assert proposal.last_event_at == occurred_at
