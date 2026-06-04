from pathlib import Path

import pytest

from src.core.policy_packs import (
    PolicyPackCatalogStore,
    activate_policy_pack_version,
    get_policy_pack_version,
    reset_policy_pack_catalog_for_tests,
    validate_policy_pack_version,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalValidationError,
)

SOURCE_ROOT = Path(__file__).resolve().parents[4] / "src" / "core" / "policy_packs"


def setup_function() -> None:
    reset_policy_pack_catalog_for_tests()


def test_policy_pack_catalog_definition_helpers_stay_focused() -> None:
    catalog = (SOURCE_ROOT / "catalog.py").read_text(encoding="utf-8")
    definitions = (SOURCE_ROOT / "catalog_definitions.py").read_text(encoding="utf-8")

    assert "summary_from_definition" in catalog
    assert "validate_definition" in catalog
    assert "def _validate_definition" not in catalog
    assert "def _summary_from_definition" not in catalog
    assert "def _prepare_definition" not in catalog

    assert "def validate_definition" in definitions
    assert "def summary_from_definition" in definitions
    assert "def prepare_definition" in definitions


def test_policy_pack_reference_data_stays_outside_catalog_store() -> None:
    catalog = (SOURCE_ROOT / "catalog.py").read_text(encoding="utf-8")
    reference_packs = (SOURCE_ROOT / "catalog_reference_packs.py").read_text(encoding="utf-8")

    assert "reference_policy_packs" in catalog
    assert "_REFERENCE_PACKS" not in catalog
    assert "SG_PRIVATE_BANKING_REFERENCE" not in catalog
    assert "GLOBAL_PRIVATE_BANKING_BASELINE" not in catalog

    assert "def reference_policy_packs" in reference_packs
    assert "_REFERENCE_PACKS" in reference_packs
    assert "SG_PRIVATE_BANKING_REFERENCE" in reference_packs
    assert "GLOBAL_PRIVATE_BANKING_BASELINE" in reference_packs


def test_policy_pack_validation_is_hash_backed_and_idempotent() -> None:
    detail = get_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    response = validate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        requested_by="policy_steward_1",
        idempotency_key="  validate-sg-reference  ",
        reason={"purpose": "pre-activation validation"},
    )
    replayed = validate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        requested_by="policy_steward_1",
        idempotency_key="validate-sg-reference",
        reason={"purpose": "pre-activation validation"},
    )

    assert response.validation_status == "READY"
    assert response.policy_pack.content_hash == detail.policy_pack.content_hash
    assert response.validation_event.content_hash == detail.policy_pack.content_hash
    assert response.validation_event.idempotency_key == "validate-sg-reference"
    assert response.validation_event.reason["dry_run_status"] == "REFERENCE_FIXTURES_VALIDATED"
    assert "PB_SG_GLOBAL_BAL_001" in response.validation_event.reason["sample_fixture_refs"]
    assert replayed.replayed is True
    assert replayed.validation_event.event_id == response.validation_event.event_id


def test_policy_pack_validation_rejects_idempotency_key_reuse_with_different_payload() -> None:
    validate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        requested_by="policy_steward_1",
        idempotency_key="validate-conflict",
        reason={"purpose": "first validation"},
    )

    with pytest.raises(ProposalIdempotencyConflictError):
        validate_policy_pack_version(
            policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
            policy_version="2026.05",
            requested_by="policy_steward_1",
            idempotency_key="validate-conflict",
            reason={"purpose": "changed validation"},
        )


def test_policy_pack_activation_enforces_hash_maker_checker_and_immutability() -> None:
    detail = get_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )
    validate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        requested_by="policy_steward_1",
        idempotency_key="validate-before-activate",
        reason={"purpose": "pre-activation validation"},
    )

    with pytest.raises(ProposalValidationError, match="MAKER_CHECKER"):
        activate_policy_pack_version(
            policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
            policy_version="2026.05",
            activated_by="policy_steward_1",
            source_content_hash=detail.policy_pack.content_hash,
            idempotency_key="activate-same-actor",
            reason={"purpose": "same actor should fail"},
        )

    with pytest.raises(ProposalValidationError, match="CONTENT_HASH"):
        activate_policy_pack_version(
            policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
            policy_version="2026.05",
            activated_by="policy_checker_1",
            source_content_hash="sha256:stale",
            idempotency_key="activate-stale-hash",
            reason={"purpose": "stale hash should fail"},
        )

    activated = activate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        activated_by="policy_checker_1",
        source_content_hash=detail.policy_pack.content_hash,
        idempotency_key="  activate-sg-reference  ",
        reason={"purpose": "activate reference pack"},
    )
    replayed = activate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        activated_by="policy_checker_1",
        source_content_hash=detail.policy_pack.content_hash,
        idempotency_key="activate-sg-reference",
        reason={"purpose": "activate reference pack"},
    )

    assert activated.policy_pack.activation_state == "ACTIVE"
    assert activated.activation_event.idempotency_key == "activate-sg-reference"
    assert activated.policy_pack.content_hash == detail.policy_pack.content_hash
    assert activated.activation_event.reason["validated_by"] == "policy_steward_1"
    assert replayed.replayed is True
    assert replayed.activation_event.event_id == activated.activation_event.event_id
    with pytest.raises(ProposalValidationError, match="IMMUTABLE"):
        activate_policy_pack_version(
            policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
            policy_version="2026.05",
            activated_by="policy_checker_2",
            source_content_hash=detail.policy_pack.content_hash,
            idempotency_key="activate-again",
            reason={"purpose": "second activation should fail"},
        )


def test_invalid_policy_pack_definition_fails_fast_with_diagnostics() -> None:
    store = PolicyPackCatalogStore(
        [
            {
                "policy_pack_id": "BAD_REFERENCE",
                "policy_version": "2026.05",
                "policy_family": "BAD_REFERENCE",
                "display_name": "Bad Reference",
                "activation_state": "DRAFT",
                "maker_checker_required": False,
                "schema_version": "rfc0025.policy-pack-catalog.v1",
                "applicability": {"jurisdiction_scope": ["SG"]},
                "source_requirements": ["client_classification"],
                "rules": [
                    {
                        "rule_id": "bad-rule",
                        "severity": "BLOCKING",
                        "required_evidence_fields": [],
                    }
                ],
                "disclosure_templates": [],
                "consent_templates": [],
                "approval_routes": [],
                "sample_fixture_refs": ["PB_SG_GLOBAL_BAL_001"],
            }
        ]
    )

    with pytest.raises(ProposalValidationError) as exc:
        store.validate_policy_pack_version(
            policy_pack_id="BAD_REFERENCE",
            policy_version="2026.05",
            requested_by="policy_steward_1",
            idempotency_key="validate-bad-reference",
            reason={"purpose": "prove diagnostics"},
        )

    assert "RULE_ID_NOT_UPPER_SNAKE_CASE" in str(exc.value)
    assert "bad-rule_REQUIRED_EVIDENCE_FIELDS_REQUIRED" in str(exc.value)
