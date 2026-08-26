from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.openapi.utils import get_openapi
from pydantic import ValidationError

from src.api.main import app
from src.core.advisory.benchmark_assignment_evidence import (
    BenchmarkAssignmentEvidenceResolution,
    BenchmarkAssignmentSourceEvidence,
)
from src.core.advisory.proposal_review_evidence import build_proposal_review_evidence
from src.core.advisory.proposal_review_evidence_models import (
    BenchmarkAssignmentEvidence,
    MandateLimitObservation,
)
from src.core.advisory.valuation_context_models import (
    ProposalValuationContext,
    ProposalValuationContextState,
)
from src.integrations import lotus_core


def _valuation_context() -> ProposalValuationContext:
    states = [
        ProposalValuationContextState(requested_as_of_date=date, supportability="READY")
        for date in ("2026-03-25", "2026-03-26")
    ]
    return ProposalValuationContext(current_state=states[0], simulated_state=states[1])


def test_projection_preserves_source_owned_current_benchmark_and_unavailable_mandate_states() -> (
    None
):
    evidence = build_proposal_review_evidence(
        policy_context={"benchmark_id": "BM_1", "mandate_id": "MANDATE_1"},
        valuation_context=_valuation_context(),
        benchmark_assignment_resolution=BenchmarkAssignmentEvidenceResolution(
            source_evidence=BenchmarkAssignmentSourceEvidence(
                effective_benchmark_id="BM_GLOBAL_BALANCED",
                effective_as_of_date="2026-03-25",
                effective_from_date="2026-01-01",
                effective_to_date=None,
                assignment_source="benchmark_policy_engine",
                assignment_status="active",
                assignment_recorded_at=datetime(2026, 3, 25, 9, 15, tzinfo=UTC),
                assignment_version=3,
                assignment_policy_pack_id="policy_pb_v1",
                assignment_source_system="mandate-booking-system",
                assignment_contract_version="rfc_062_v1",
                source_product_name="BenchmarkAssignment",
                source_product_version="v1",
                source_tenant_id="tenant_sg",
                source_generated_at=datetime(2026, 3, 25, 9, 16, tzinfo=UTC),
                source_restatement_version="v1",
                source_reconciliation_status="RECONCILED",
                source_data_quality_status="COMPLETE",
                source_latest_evidence_at=datetime(2026, 3, 25, 9, 14, tzinfo=UTC),
                source_batch_fingerprint="batch_20260325_0001",
                source_snapshot_id="snapshot_554",
                source_content_hash=(
                    "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                ),
                source_references=("lotus-core://benchmark/PF_1/2026-03-25",),
                source_lineage={
                    "source_owner": "lotus-core",
                    "source_product": "BenchmarkAssignment",
                },
                source_evidence_current=True,
                source_freshness_status="CURRENT",
                source_policy_version="policy-v1",
                supportability="READY",
            )
        ),
    )
    assert (
        evidence.benchmark_assignment.requested_benchmark_id,
        evidence.benchmark_assignment.effective_benchmark_id,
        evidence.benchmark_assignment.requested_as_of_date,
        evidence.benchmark_assignment.supportability,
    ) == ("BM_1", "BM_GLOBAL_BALANCED", "2026-03-25", "READY")
    assert (
        evidence.benchmark_assignment.effective_from_date,
        evidence.benchmark_assignment.assignment_source,
        evidence.benchmark_assignment.assignment_version,
        evidence.benchmark_assignment.assignment_contract_version,
        evidence.benchmark_assignment.source_product_version,
        evidence.benchmark_assignment.source_data_quality_status,
        evidence.benchmark_assignment.benchmark_assignment_content_hash,
        evidence.benchmark_assignment.source_lineage,
        evidence.benchmark_assignment.source_evidence_current,
    ) == (
        "2026-01-01",
        "benchmark_policy_engine",
        3,
        "rfc_062_v1",
        "v1",
        "COMPLETE",
        "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        {"source_owner": "lotus-core", "source_product": "BenchmarkAssignment"},
        True,
    )
    assert (
        evidence.current_mandate_limits.mandate_id,
        evidence.current_mandate_limits.requested_as_of_date,
        evidence.simulated_mandate_limits.requested_as_of_date,
    ) == ("MANDATE_1", "2026-03-25", "2026-03-26")
    unavailable = build_proposal_review_evidence(
        policy_context={"benchmark_id": "  ", "mandate_id": 123},
        valuation_context=_valuation_context(),
    )
    assert (
        unavailable.benchmark_assignment.requested_benchmark_id,
        unavailable.current_mandate_limits.mandate_id,
    ) == (None, None)


def test_mandate_limit_observation_preserves_typed_source_values() -> None:
    observation = MandateLimitObservation(
        limit_code="MAX_SINGLE_POSITION",
        limit_name="Maximum single position weight",
        dimension="instrument_weight",
        scope="portfolio",
        observed_value=Decimal("0.08"),
        maximum=Decimal("0.10"),
        unit="PERCENT_OF_NAV",
        outcome="WITHIN_LIMIT",
        severity="INFO",
        source_references=["lotus-core:mandate:MAX_SINGLE_POSITION:2026-03-25"],
    )
    assert (observation.observed_value, observation.maximum, observation.source_references) == (
        Decimal("0.08"),
        Decimal("0.10"),
        ["lotus-core:mandate:MAX_SINGLE_POSITION:2026-03-25"],
    )


def test_evidence_models_reject_extensions_and_core_route_is_isolated_to_its_adapter() -> None:
    with pytest.raises(ValidationError):
        BenchmarkAssignmentEvidence(
            supportability="UNAVAILABLE",
            opaque_payload={"effective_benchmark_id": "BM_INFERRED"},
        )
    integration_root = Path(lotus_core.__file__).parent
    route_modules = sorted(
        path.name
        for path in integration_root.glob("*.py")
        if "benchmark-assignment" in path.read_text(encoding="utf-8")
    )
    assert route_modules == ["benchmark_assignment.py"]


def test_source_evidence_contract_round_trips_without_losing_replay_context() -> None:
    evidence = build_proposal_review_evidence(
        policy_context={"benchmark_id": "BM_1"},
        valuation_context=_valuation_context(),
        benchmark_assignment_resolution=BenchmarkAssignmentEvidenceResolution.unavailable(
            "BENCHMARK_EVIDENCE_SOURCE_NOT_FOUND"
        ),
    )

    restored = type(evidence).model_validate(evidence.model_dump(mode="json"))

    assert restored == evidence


def test_proposal_result_openapi_publishes_additive_review_evidence_contract() -> None:
    schemas = get_openapi(title=app.title, version=app.version, routes=app.routes)["components"][
        "schemas"
    ]
    assert schemas["ProposalResult"]["properties"]["proposal_review_evidence"]["$ref"] == (
        "#/components/schemas/ProposalReviewEvidence"
    )
    assert set(schemas["ProposalReviewEvidence"]["required"]) == {
        "benchmark_assignment",
        "current_mandate_limits",
        "simulated_mandate_limits",
    }
    properties = schemas["BenchmarkAssignmentEvidence"]["properties"]
    assert {
        "effective_from_date",
        "effective_to_date",
        "assignment_source",
        "assignment_status",
        "assignment_recorded_at",
        "assignment_version",
        "assignment_contract_version",
        "source_product_name",
        "source_product_version",
        "source_generated_at",
        "source_data_quality_status",
        "benchmark_assignment_content_hash",
        "source_evidence_current",
        "source_freshness_status",
        "source_lineage",
    } <= set(properties)
    timestamp_schemas = properties["assignment_recorded_at"]["anyOf"]
    hash_schemas = properties["benchmark_assignment_content_hash"]["anyOf"]
    assert {schema.get("format") for schema in timestamp_schemas} == {"date-time", None}
    assert {schema.get("pattern") for schema in hash_schemas} == {"^sha256:[0-9a-f]{64}$", None}
