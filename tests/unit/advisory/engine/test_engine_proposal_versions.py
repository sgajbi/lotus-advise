from datetime import datetime, timezone

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.models import GateDecision, GateDecisionSummary, ProposalResult
from src.core.proposals.models import ProposalRecord
from src.core.proposals.versions import (
    ProposalVersionConflictError,
    ProposalVersionPortfolioContextError,
    ProposalVersionTerminalStateError,
    apply_new_version_lifecycle_state,
    build_proposal_version_record,
    validate_create_version_portfolio_context,
    validate_create_version_state,
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


def _proposal(
    *,
    current_state: str = "DRAFT",
    current_version_no: int = 2,
    portfolio_id: str = "pf_version",
) -> ProposalRecord:
    created_at = datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)
    return ProposalRecord(
        proposal_id="pp_version_state",
        portfolio_id=portfolio_id,
        mandate_id="mandate_version_state",
        jurisdiction="SG",
        created_by="advisor_version_state",
        created_at=created_at,
        last_event_at=created_at,
        current_state=current_state,
        current_version_no=current_version_no,
        title="Version lifecycle state",
        advisor_notes=None,
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )


def test_validate_create_version_state_rejects_terminal_state_and_version_conflict():
    validate_create_version_state(
        proposal=_proposal(current_state="DRAFT", current_version_no=2),
        expected_current_version_no=2,
        terminal_states={"EXECUTED", "REJECTED", "CANCELLED", "EXPIRED"},
    )

    try:
        validate_create_version_state(
            proposal=_proposal(current_state="EXECUTED", current_version_no=2),
            expected_current_version_no=2,
            terminal_states={"EXECUTED", "REJECTED", "CANCELLED", "EXPIRED"},
        )
    except ProposalVersionTerminalStateError as exc:
        assert str(exc) == "PROPOSAL_TERMINAL_STATE: cannot create version"
    else:
        raise AssertionError("Expected terminal-state rejection")

    try:
        validate_create_version_state(
            proposal=_proposal(current_state="DRAFT", current_version_no=2),
            expected_current_version_no=1,
            terminal_states={"EXECUTED", "REJECTED", "CANCELLED", "EXPIRED"},
        )
    except ProposalVersionConflictError as exc:
        assert str(exc) == "VERSION_CONFLICT: expected_current_version_no mismatch"
    else:
        raise AssertionError("Expected expected-version conflict")


def test_validate_create_version_portfolio_context_allows_only_configured_changes():
    validate_create_version_portfolio_context(
        proposal_portfolio_id="pf_version",
        request_portfolio_id="pf_version",
        allow_portfolio_id_change=False,
    )
    validate_create_version_portfolio_context(
        proposal_portfolio_id="pf_version",
        request_portfolio_id="pf_other",
        allow_portfolio_id_change=True,
    )

    try:
        validate_create_version_portfolio_context(
            proposal_portfolio_id="pf_version",
            request_portfolio_id="pf_other",
            allow_portfolio_id_change=False,
        )
    except ProposalVersionPortfolioContextError as exc:
        assert str(exc) == "PORTFOLIO_CONTEXT_MISMATCH"
    else:
        raise AssertionError("Expected portfolio context mismatch")


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
    proposal = _proposal(
        current_state="EXECUTION_READY",
        current_version_no=1,
        portfolio_id="pf_version_state",
    )
    proposal.created_at = original_event_at
    proposal.last_event_at = original_event_at

    apply_new_version_lifecycle_state(
        proposal=proposal,
        version_no=2,
        occurred_at=occurred_at,
    )

    assert proposal.current_version_no == 2
    assert proposal.current_state == "DRAFT"
    assert proposal.last_event_at == occurred_at
