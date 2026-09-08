from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.policy_packs import (
    DurablePolicyEvaluationRepository,
    configure_policy_evaluation_repository,
)
from src.core.proposals.exceptions import ProposalIdempotencyConflictError
from src.infrastructure.policy_packs.postgres import PostgresPolicyEvaluationRepository
from src.infrastructure.policy_packs.postgres_state import PostgresPolicyEvaluationStateStore

_DSN = os.getenv("POLICY_POSTGRES_INTEGRATION_DSN", "").strip()


@pytest.fixture
def postgres_store() -> PostgresPolicyEvaluationStateStore:
    if not _DSN:
        pytest.skip("POLICY_POSTGRES_INTEGRATION_DSN is required for real PostgreSQL proof")
    repository = PostgresPolicyEvaluationRepository(dsn=_DSN)
    return PostgresPolicyEvaluationStateStore(connect=repository._connect)


def _snapshot(*, evaluation_id: str, tenant_id: str, key: str, status: str) -> dict:
    event_id = f"event-{evaluation_id}"
    record = {
        "evaluation_id": evaluation_id,
        "proposal_id": f"proposal-{evaluation_id}",
        "proposal_version_id": f"version-{evaluation_id}",
        "portfolio_id": f"portfolio-{tenant_id}",
        "tenant_id": tenant_id,
        "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
        "policy_version": "2026.05",
        "generated_at": "2026-09-09T00:00:00+00:00",
        "created_by": "advisor-test",
        "evaluation_status": status,
        "source_evidence_hash": f"sha256:source-{evaluation_id}",
        "policy_content_hash": "sha256:policy",
        "evaluation_hash": f"sha256:evaluation-{evaluation_id}",
        "evaluation_json": {},
        "marker": f"{tenant_id}:{status}",
    }
    event = {
        "evaluation_id": evaluation_id,
        "event_id": event_id,
        "proposal_id": record["proposal_id"],
        "proposal_version_id": record["proposal_version_id"],
        "event_type": "POLICY_EVALUATION_FINALIZED",
        "actor_id": "advisor-test",
        "occurred_at": "2026-09-09T00:00:00+00:00",
        "content_hash": record["evaluation_hash"],
        "idempotency_key": key,
        "reason_json": {"idempotency_request_hash": f"sha256:request-{tenant_id}"},
    }
    return {
        "records": {evaluation_id: record},
        "events": {evaluation_id: [event]},
        "idempotency": [
            {
                "tenant_id": tenant_id,
                "idempotency_key": key,
                "request_hash": f"sha256:request-{tenant_id}",
                "evaluation_id": evaluation_id,
                "event_id": event_id,
            }
        ],
    }


def test_postgres_tenant_upsert_refusal_preserves_owner_and_survives_restart(
    postgres_store: PostgresPolicyEvaluationStateStore,
) -> None:
    suffix = uuid.uuid4().hex
    evaluation_id = f"pev-tenant-isolation-{suffix}"
    key = f"shared-key-{suffix}"
    owner_tenant = f"tenant-sg-{suffix}"
    foreign_tenant = f"tenant-hk-{suffix}"
    owner = _snapshot(
        evaluation_id=evaluation_id,
        tenant_id=owner_tenant,
        key=key,
        status="PENDING_REVIEW",
    )
    postgres_store.save_snapshot(owner)
    postgres_store.save_snapshot(owner)

    foreign = _snapshot(
        evaluation_id=evaluation_id,
        tenant_id=foreign_tenant,
        key=key,
        status="READY",
    )
    with pytest.raises(ProposalIdempotencyConflictError) as refusal:
        postgres_store.save_snapshot(foreign)
    assert str(refusal.value) == "POLICY_EVALUATION_RECORD_CONFLICT"

    restarted = PostgresPolicyEvaluationRepository(dsn=_DSN)
    stored = PostgresPolicyEvaluationStateStore(connect=restarted._connect).load_snapshot(
        tenant_id=owner_tenant
    )
    assert stored["records"][evaluation_id] == owner["records"][evaluation_id]
    assert stored["idempotency"][0]["request_hash"] == f"sha256:request-{owner_tenant}"


def test_postgres_allows_same_raw_key_per_tenant_and_serializes_contention(
    postgres_store: PostgresPolicyEvaluationStateStore,
) -> None:
    suffix = uuid.uuid4().hex
    key = f"shared-key-{suffix}"
    sg_tenant = f"tenant-sg-{suffix}"
    hk_tenant = f"tenant-hk-{suffix}"
    sg = _snapshot(evaluation_id=f"pev-sg-{suffix}", tenant_id=sg_tenant, key=key, status="READY")
    hk = _snapshot(evaluation_id=f"pev-hk-{suffix}", tenant_id=hk_tenant, key=key, status="READY")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(postgres_store.save_snapshot, (sg, hk)))
    assert results == [None, None]

    restarted = PostgresPolicyEvaluationRepository(dsn=_DSN)
    scoped = PostgresPolicyEvaluationStateStore(connect=restarted._connect)
    sg_state = scoped.load_snapshot(tenant_id=sg_tenant)
    hk_state = scoped.load_snapshot(tenant_id=hk_tenant)
    assert f"pev-sg-{suffix}" in sg_state["records"]
    assert f"pev-hk-{suffix}" in hk_state["records"]
    assert key in {item["idempotency_key"] for item in sg_state["idempotency"]}
    assert key in {item["idempotency_key"] for item in hk_state["idempotency"]}


def test_postgres_quarantines_unattributable_rows_before_hydration(
    postgres_store: PostgresPolicyEvaluationStateStore,
) -> None:
    suffix = uuid.uuid4().hex
    evaluation_id = f"pev-legacy-null-{suffix}"
    tenant_id = f"tenant-sg-{suffix}"
    postgres_store.save_snapshot(
        _snapshot(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            key=f"legacy-null-{suffix}",
            status="READY",
        )
    )
    with closing(postgres_store._connect()) as connection:
        connection.execute(
            "UPDATE policy_evaluation_records SET tenant_id = NULL, record_json = %s "
            "WHERE evaluation_id = %s",
            ("{malformed", evaluation_id),
        )
        connection.execute(
            "UPDATE policy_evaluation_audit_events SET event_json = %s WHERE evaluation_id = %s",
            ("{malformed", evaluation_id),
        )
        connection.execute(
            "UPDATE policy_evaluation_idempotency SET tenant_id = NULL WHERE evaluation_id = %s",
            (evaluation_id,),
        )
        connection.commit()

    assert postgres_store.load_snapshot(tenant_id=tenant_id) == {
        "records": {},
        "events": {},
        "idempotency": [],
        "identity_index": [],
    }


def test_review_queue_scopes_real_postgres_before_hydration(
    postgres_store: PostgresPolicyEvaluationStateStore,
) -> None:
    suffix = uuid.uuid4().hex
    sg_id = f"pev-api-sg-{suffix}"
    hk_id = f"pev-api-hk-{suffix}"
    sg_tenant = f"tenant-api-sg-{suffix}"
    hk_tenant = f"tenant-api-hk-{suffix}"
    postgres_store.save_snapshot(
        _snapshot(evaluation_id=sg_id, tenant_id=sg_tenant, key=f"sg-{suffix}", status="READY")
    )
    postgres_store.save_snapshot(
        _snapshot(evaluation_id=hk_id, tenant_id=hk_tenant, key=f"hk-{suffix}", status="READY")
    )

    with TestClient(app) as client:
        configure_policy_evaluation_repository(
            DurablePolicyEvaluationRepository(state_store=postgres_store)
        )
        for tenant_id, expected_id in ((sg_tenant, sg_id), (hk_tenant, hk_id)):
            response = client.get(
                "/advisory/policy-evaluations/review-queue",
                params={"evaluation_status": "READY"},
                headers={
                    "X-Actor-Id": "advisor-test",
                    "X-Role": "ADVISOR",
                    "X-Tenant-Id": tenant_id,
                    "X-Legal-Entity-Code": "REFERENCE",
                    "X-Correlation-Id": f"corr-{tenant_id}",
                    "X-Service-Identity": "lotus-gateway",
                    "X-Capabilities": "advisory.policy_evaluation.read",
                },
            )
            assert response.status_code == 200
            assert [item["evaluation_id"] for item in response.json()["items"]] == [expected_id]
