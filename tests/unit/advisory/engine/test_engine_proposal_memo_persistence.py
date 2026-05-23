from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from src.core.proposals.memo_persistence import (
    ProposalMemoPersistenceError,
    create_or_replay_proposal_memo,
)
from src.core.proposals.memo_source_readiness import build_memo_source_readiness
from src.core.proposals.models import ProposalVersionRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 23, 12, 0, tzinfo=timezone.utc)


def _evidence_bundle() -> dict:
    evidence = {
        "context_resolution": {
            "resolution_source": "LOTUS_CORE",
            "resolved_context": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "portfolio_snapshot_id": "core-portfolio-snapshot-001",
                "market_data_snapshot_id": "core-market-data-snapshot-001",
            },
            "advisory_policy_context": {
                "context_source": "LOTUS_CORE",
                "household_id": "HH-PB-001",
                "mandate_id": "MANDATE-BALANCED-001",
                "jurisdiction": "SG",
            },
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {
                        "instrument_id": "US_EQ_ETF",
                        "price": "100",
                        "currency": "USD",
                        "valid_to": "3999-12-31",
                    }
                ],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35", "effective_to": "3999-12-31"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "complexity": "NON_COMPLEX",
                }
            ],
            "proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}],
            "proposed_cash_flows": [],
        },
        "engine_outputs": {
            "proposal_result": {
                "proposal_decision_summary": {
                    "primary_summary": "Deploy excess cash within mandate.",
                    "recommended_next_action": "DISCUSS_WITH_CLIENT",
                },
                "proposal_alternatives": {"alternatives": []},
                "gate_decision": {"gate": "CLIENT_CONSENT_REQUIRED"},
            }
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
        },
    }
    evidence["memo_source_readiness"] = build_memo_source_readiness(evidence)
    return evidence


def _artifact() -> dict:
    return {
        "artifact_id": "pa_memo_persist_001",
        "proposal_decision_summary": {
            "primary_summary": "Deploy excess cash within mandate.",
            "recommended_next_action": "DISCUSS_WITH_CLIENT",
            "suitability_posture": {"status": "AVAILABLE"},
        },
        "proposal_alternatives": {
            "alternatives": [
                {"alternative_id": "alt_selected", "selected": True},
                {"alternative_id": "alt_rejected", "selected": False},
            ]
        },
        "summary": {
            "objective_tags": ["CASH_DEPLOYMENT", "RISK_ALIGNMENT"],
            "recommended_next_step": "CLIENT_CONSENT",
        },
        "portfolio_impact": {"delta": {"largest_weight_changes": []}},
        "risk_lens": {
            "status": "AVAILABLE",
            "source_service": "lotus-risk",
            "summary": "Concentration remains reviewable after the proposal.",
        },
        "suitability_summary": {
            "status": "AVAILABLE",
            "new_issues": 0,
            "persistent_issues": 0,
            "resolved_issues": 1,
        },
        "gate_decision": {"gate": "CLIENT_CONSENT_REQUIRED"},
        "trades_and_funding": {"trade_list": [{"instrument_id": "US_EQ_ETF"}]},
    }


def _version() -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id="ppv_memo_persist_001",
        proposal_id="pp_memo_persist_001",
        version_no=1,
        created_at=_now(),
        request_hash="sha256:proposal-request",
        artifact_hash="sha256:proposal-artifact",
        simulation_hash="sha256:proposal-simulation",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json=_artifact(),
        evidence_bundle_json=_evidence_bundle(),
        gate_decision_json={"gate": "CLIENT_CONSENT_REQUIRED"},
    )


def test_create_or_replay_proposal_memo_persists_draft_with_audit_and_replay_metadata() -> None:
    repository = InMemoryProposalRepository()
    version = _version()

    result = create_or_replay_proposal_memo(
        repository=repository,
        version=version,
        idempotency_key="memo-idem-001",
        created_by="advisor_1",
        created_at=_now(),
        event_id="pme_001",
    )

    assert result.created is True
    assert result.replayed is False
    assert result.memo.lifecycle_status == "DRAFT"
    assert result.memo.memo_status == "BLOCKED"
    assert result.memo.projection_json["client_ready_publication"] == "BLOCKED"
    assert result.memo.review_events_json == []
    assert result.memo.report_package_events_json == []
    assert result.memo.archive_refs_json == []
    assert result.memo.ai_refs_json == []
    assert result.memo.replay_metadata_json["proposal_artifact_hash"] == "sha256:proposal-artifact"
    assert result.audit_event is not None
    assert result.audit_event.event_type == "MEMO_DRAFT_CREATED"

    stored = repository.get_memo(memo_id=result.memo.memo_id)
    assert stored is not None
    assert stored.memo_hash == result.memo.memo_hash
    assert repository.list_memo_events(memo_id=result.memo.memo_id)[0].event_id == "pme_001"

    replayed = create_or_replay_proposal_memo(
        repository=repository,
        version=deepcopy(version),
        idempotency_key="memo-idem-001",
        created_by="advisor_1",
        created_at=_now(),
        event_id="pme_replay_should_not_persist",
    )

    assert replayed.created is False
    assert replayed.replayed is True
    assert replayed.memo.memo_id == result.memo.memo_id
    assert replayed.audit_event is None
    assert len(repository.list_memo_events(memo_id=result.memo.memo_id)) == 1


def test_memo_idempotency_rejects_payload_drift() -> None:
    repository = InMemoryProposalRepository()
    version = _version()
    create_or_replay_proposal_memo(
        repository=repository,
        version=version,
        idempotency_key="memo-idem-conflict",
        created_by="advisor_1",
        created_at=_now(),
        event_id="pme_conflict_001",
    )
    original_key = repository.get_memo_idempotency(idempotency_key="memo-idem-conflict")
    assert original_key is not None
    drifted = version.model_copy(update={"artifact_hash": "sha256:different-artifact"})

    with pytest.raises(ProposalMemoPersistenceError, match="MEMO_IDEMPOTENCY_KEY_CONFLICT"):
        create_or_replay_proposal_memo(
            repository=repository,
            version=drifted,
            idempotency_key="memo-idem-conflict",
            created_by="advisor_1",
            created_at=_now(),
            event_id="pme_conflict_002",
        )

    persisted_key = repository.get_memo_idempotency(idempotency_key="memo-idem-conflict")
    assert persisted_key is not None
    assert persisted_key.request_hash == original_key.request_hash
    assert persisted_key.memo_id == original_key.memo_id


def test_memo_finalization_requires_ready_evidence() -> None:
    repository = InMemoryProposalRepository()

    with pytest.raises(
        ProposalMemoPersistenceError,
        match="MEMO_FINALIZATION_BLOCKED_BY_EVIDENCE_POSTURE",
    ):
        create_or_replay_proposal_memo(
            repository=repository,
            version=_version(),
            idempotency_key="memo-finalize-blocked",
            created_by="advisor_1",
            created_at=_now(),
            event_id="pme_finalize_001",
            lifecycle_status="FINALIZED",
        )
