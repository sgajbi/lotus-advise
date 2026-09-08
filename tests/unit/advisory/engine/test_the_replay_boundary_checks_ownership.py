"""#624/#630 finalization authority and tenant-scoped replay regressions."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.policy_packs import (
    finalize_policy_evaluation_record,
    reset_policy_evaluation_store_for_tests,
    reset_policy_pack_catalog_for_tests,
)
from src.core.proposals.exceptions import ProposalIdempotencyConflictError, ProposalValidationError
from tests.unit.advisory.engine.policy_evaluation_fixtures import (
    _base_evidence_bundle,
    _trusted_reason,
)

OWNER = "tenant_sg_001"
INTRUDER = "tenant_hk_002"
SHARED_KEY = "shared-idempotency-key"


@pytest.fixture(autouse=True)
def _clean_store() -> Any:
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()
    yield
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()


def _finalize_as(tenant_id: str, **overrides: Any) -> Any:
    arguments: dict[str, Any] = {
        "evidence_bundle": _base_evidence_bundle(),
        "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
        "policy_version": "2026.05",
        "created_by": "advisor_1",
        "tenant_id": tenant_id,
        "proposal_id": "pp_shared",
        "proposal_version_id": "ppv_shared",
        "idempotency_key": SHARED_KEY,
        "reason": _trusted_reason("finalize", tenant_id=tenant_id),
    }
    arguments.update(overrides)
    return finalize_policy_evaluation_record(**arguments)


def test_the_owning_tenant_still_replays_its_own_evaluation() -> None:
    """An admitted owner receives its unchanged evaluation as a replay."""

    created = _finalize_as(OWNER)
    replayed = _finalize_as(OWNER)

    assert created.created is True
    assert replayed.replayed is True
    assert replayed.created is False
    assert replayed.record.evaluation_id == created.record.evaluation_id


def test_request_and_trusted_tenant_mismatch_is_refused_before_mutation() -> None:
    """The exported call cannot disagree with its trusted principal."""

    from src.core.policy_packs.persistence import _repository

    before = _repository().snapshot()
    with pytest.raises(ProposalValidationError) as refusal:
        _finalize_as(INTRUDER, reason=_trusted_reason("finalize", tenant_id=OWNER))

    assert str(refusal.value) == "POLICY_EVALUATION_TENANT_PRINCIPAL_MISMATCH"
    assert _repository().snapshot() == before


def test_missing_trusted_tenant_is_refused_before_mutation() -> None:
    """A request tenant is not authority when trusted tenant scope is absent."""

    from src.core.policy_packs.persistence import _repository

    reason = _trusted_reason("finalize", tenant_id=OWNER)
    del reason["trusted_principal"]["tenant_id"]
    before = _repository().snapshot()
    with pytest.raises(ProposalValidationError) as refusal:
        _finalize_as(OWNER, reason=reason)

    assert str(refusal.value) == "POLICY_EVALUATION_TRUSTED_TENANT_REQUIRED"
    assert _repository().snapshot() == before


def test_independent_tenants_can_reuse_the_same_raw_idempotency_key() -> None:
    """Tenant scope, not global caller key uniqueness, separates valid work."""

    owner = _finalize_as(OWNER)
    intruder = _finalize_as(
        INTRUDER,
        proposal_id="pp_hk",
        proposal_version_id="ppv_hk",
    )

    assert owner.created is True
    assert intruder.created is True
    assert intruder.record.tenant_id == INTRUDER
    assert intruder.record.evaluation_id != owner.record.evaluation_id


def test_a_record_with_no_stored_tenant_is_quarantined_rather_than_matched() -> None:
    """Unknown stored ownership is quarantined without rewriting the record."""

    from src.core.policy_packs.persistence import _repository

    created = _finalize_as(OWNER)
    store = _repository()
    store._records[created.record.evaluation_id].tenant_id = None  # type: ignore[attr-defined]

    assert store._records[created.record.evaluation_id].tenant_id is None, (  # type: ignore[attr-defined]
        "fixture does not reproduce a legacy row"
    )

    with pytest.raises(ProposalIdempotencyConflictError) as refusal:
        _finalize_as(OWNER)

    assert str(refusal.value) == "POLICY_EVALUATION_TENANT_UNATTRIBUTABLE_RECORD"
