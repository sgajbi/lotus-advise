"""#624 slice 1: the policy evaluation record can carry the tenant it was admitted under.

The evaluation reads could not be tenant-scoped because the table recorded no tenant.
The only anchor was `portfolio_id`, and the portfolio-to-tenant mapping belongs to
lotus-core rather than here -- so deriving the tenant at read time would make the scope
only as stable as the deriving code. It is captured at write time from the admitted
principal, whose `tenant_id` was already resolved and audited at that frame and simply
never reached the record.

This change is the storage half: the record can hold the value, persistence keeps it,
and a row written before the column existed stays distinguishable from one written
without a tenant. Nothing populates it yet -- the write path that requires a tenant and
refuses a cross-tenant identity collision follows separately, so that each half is a
change of reviewable size rather than one batch that has to be taken on trust.
"""

from __future__ import annotations

from typing import Any

from src.core.policy_packs.persistence_models import PolicyEvaluationRecord


def _record_payload(**overrides: Any) -> dict[str, Any]:
    """A complete record payload, overridable per case."""

    payload: dict[str, Any] = {
        "evaluation_id": "pev_1",
        "proposal_id": "pp_1",
        "proposal_version_id": "ppv_1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "tenant_id": "tenant-sg",
        "policy_pack_id": "PACK",
        "policy_version": "2026.05",
        "generated_at": "2026-09-08T00:00:00+00:00",
        "created_by": "advisor_1",
        "evaluation_status": "PENDING_REVIEW",
        "policy_content_hash": "sha256:content",
        "source_evidence_hash": "sha256:evidence",
        "evaluation_hash": "sha256:evaluation",
        "rule_result_hashes": {},
        "evaluation_json": {},
        "source_refs": [],
        "source_gaps": [],
        "approval_dependencies": [],
        "disclosure_requirements": [],
        "consent_requirements": [],
        "replay_metadata_json": {},
    }
    payload.update(overrides)
    return payload


def test_the_record_carries_the_admitted_tenant_without_serialising_it() -> None:
    """Stored as durable identity, and absent from every response body.

    Both halves matter and they pull against each other. The review queue resolves no
    principal and filters by no tenant, so a serialised `tenant_id` would let any
    caller reaching it enumerate every tenant's admitted identifier -- adding a scope
    to what is stored must not widen what an unscoped read returns.

    So the field is `exclude=True`, and the persistence path re-adds it deliberately.
    Asserted together because excluding it is one edit away from silently dropping it
    from storage as well, which would leave the column empty and the durable identity
    lost with nothing failing.
    """

    record = PolicyEvaluationRecord(**_record_payload())

    assert record.tenant_id == "tenant-sg"
    assert "tenant_id" not in record.model_dump(mode="json"), (
        "the admitted tenant is serialised, so an unscoped read would return it"
    )


def test_a_record_written_before_the_column_existed_reads_as_unrecorded() -> None:
    """`None` is not a tenant, and must not be turned into one.

    Rows persisted before this field do not record what the caller presented: that is
    unknowable rather than absent. Defaulting it makes a historical row
    indistinguishable from a genuine tenantless submission, which is where
    refuse-do-not-default stops being implementable downstream. Driven through
    `model_validate` on a payload with no `tenant_id`, as a legacy `record_json`
    deserialises.
    """

    legacy = _record_payload()
    del legacy["tenant_id"]

    record = PolicyEvaluationRecord.model_validate(legacy)

    assert record.tenant_id is None
    assert record.tenant_id != "", "an unrecorded tenant was flattened into an absent one"


def test_the_persistence_snapshot_still_carries_the_tenant() -> None:
    """Excluding it from responses must not drop it from storage.

    `snapshot()` re-adds the field the model excludes, because the durable column is
    what the tenant-scoped reads will query and what survives an old binary rewriting
    `record_json` during a mixed-version deploy. Without this the exclusion would look
    correct and quietly leave every column NULL.
    """

    from src.core.policy_packs.persistence_store import PolicyEvaluationRecordStore

    store = PolicyEvaluationRecordStore()
    store._records["pev_1"] = PolicyEvaluationRecord(**_record_payload())

    persisted = store.snapshot()["records"]["pev_1"]

    assert persisted["tenant_id"] == "tenant-sg"
