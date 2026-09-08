"""#624 slice 1: the policy evaluation record records the tenant it was admitted under.

The evaluation reads could not be tenant-scoped because the table recorded no tenant.
The only anchor was `portfolio_id`, and the portfolio-to-tenant mapping belongs to
lotus-core rather than here -- so deriving the tenant at read time would make the scope
only as stable as the deriving code. It is captured at write time from the admitted
principal, whose `tenant_id` was already resolved and audited at that frame and simply
never reached the record.
"""

from __future__ import annotations

import inspect
from typing import Any

from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.policy_packs.persistence_record_builder import policy_evaluation_hash


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


def test_the_replay_identity_does_not_depend_on_the_record() -> None:
    """Adding a field to the record cannot move `evaluation_hash`, by construction.

    Asserted because a later refactor could remove the property by folding the record
    into the hash input; the lotus-idea owner measured that case at 797 unit failures.
    Checked against the signature, not today's output: the claim is that nothing
    record-shaped can reach the hash, not that one example matches.
    """

    assert set(inspect.signature(policy_evaluation_hash).parameters) == {
        "evaluation",
        "source_evidence_hash",
        "policy_content_hash",
    }, "the replay identity takes something new; if it is the record, every historical hash moves"


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


def test_the_write_path_requires_a_tenant_rather_than_defaulting_one() -> None:
    """Required and undefaulted, so a new caller cannot reintroduce the gap.

    Threading it found six frames that had to state a tenant, plus 41 test call sites.
    That enumeration is the mechanism: a default would have preserved the omission at
    every one of them behind a plausible value.
    """

    import dataclasses

    from src.core.policy_packs import persistence, persistence_record_builder
    from src.core.policy_packs.repositories import PolicyEvaluationFinalizationRequest

    # The keyword-taking entry points, where a caller supplies loose arguments.
    for site in (
        persistence_record_builder.build_policy_evaluation_record,
        persistence.finalize_policy_evaluation_record,
    ):
        parameter = inspect.signature(site).parameters.get("tenant_id")
        assert parameter is not None, f"{site.__qualname__} does not take a tenant"
        assert parameter.default is inspect.Parameter.empty, (
            f"{site.__qualname__} defaults the tenant, preserving the gap it exists to close"
        )

    # The layers beneath them take a request object instead of eleven parameters, so
    # the requirement lives on the field. Followed to where it moved rather than
    # pinned to the old shape: the claim is that no path can finalize without stating
    # a tenant, not that a particular function signature contains one.
    field = next(
        f for f in dataclasses.fields(PolicyEvaluationFinalizationRequest) if f.name == "tenant_id"
    )
    assert field.default is dataclasses.MISSING, "the request object defaults the tenant"
    assert field.default_factory is dataclasses.MISSING, "the request object manufactures a tenant"


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
