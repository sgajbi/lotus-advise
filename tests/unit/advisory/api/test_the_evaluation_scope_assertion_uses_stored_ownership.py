"""#624 regression coverage for stored policy-evaluation ownership."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from src.api.proposals.policy_control_principal import (
    PolicyControlPrincipal,
    assert_policy_evaluation_record_scope,
)

OWNER = "tenant_sg_001"
INTRUDER = "tenant_hk_002"


class _Record:
    def __init__(self, tenant_id: str | None) -> None:
        self.proposal_id = "pp_1"
        self.portfolio_id = "PB_SG_GLOBAL_BAL_001"
        self.tenant_id = tenant_id
        self.evaluation_json: dict[str, Any] = {}
        self.replay_metadata_json: dict[str, Any] = {}


class _Event:
    def __init__(self, tenant_id: str) -> None:
        self.reason_json = {"trusted_principal": {"tenant_id": tenant_id}}


class _Lineage:
    def __init__(self, tenant_id: str) -> None:
        self.audit_events = [_Event(tenant_id)]


def _principal(tenant_id: str) -> PolicyControlPrincipal:
    return PolicyControlPrincipal(
        actor_id="advisor_1",
        role="ADVISOR",
        tenant_id=tenant_id,
        legal_entity_code="REFERENCE",
        correlation_id="corr-1",
        service_identity="lotus-gateway",
        capabilities=frozenset({"advisory.policy_evaluation.read"}),
        authorized_proposal_id="pp_1",
        authorized_portfolio_id="PB_SG_GLOBAL_BAL_001",
    )


def _assert_forbidden(**kwargs: Any) -> HTTPException:
    with pytest.raises(HTTPException) as refusal:
        assert_policy_evaluation_record_scope(**kwargs)
    assert refusal.value.status_code == 403
    assert refusal.value.detail == "POLICY_CONTROL_SCOPE_FORBIDDEN"
    return refusal.value


def test_the_owning_tenant_reads_its_own_record() -> None:
    """An owned record with consistent lineage remains readable."""

    assert_policy_evaluation_record_scope(
        principal=_principal(OWNER), record=_Record(OWNER), lineage=_Lineage(OWNER)
    )


@pytest.mark.parametrize(
    ("principal_tenant", "record_tenant", "lineage_tenant"),
    [
        pytest.param(INTRUDER, OWNER, OWNER, id="foreign-stored-owner"),
        pytest.param(OWNER, None, None, id="unattributable-record"),
        pytest.param(INTRUDER, OWNER, INTRUDER, id="lineage-cannot-authorise"),
        pytest.param(OWNER, OWNER, INTRUDER, id="contradictory-lineage"),
    ],
)
def test_unowned_or_inconsistent_records_are_refused(
    principal_tenant: str,
    record_tenant: str | None,
    lineage_tenant: str | None,
) -> None:
    """Stored ownership is mandatory and contradictory lineage never overrides it."""

    lineage = _Lineage(lineage_tenant) if lineage_tenant is not None else None
    _assert_forbidden(
        principal=_principal(principal_tenant),
        record=_Record(record_tenant),
        lineage=lineage,
    )
