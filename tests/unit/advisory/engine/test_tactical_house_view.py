from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.tactical_house_view import (
    TacticalHouseViewCohortRequest,
    build_tactical_house_view_affected_cohort,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def _request() -> TacticalHouseViewCohortRequest:
    return TacticalHouseViewCohortRequest.model_validate(
        {
            "tactical_view": {
                "tactical_view_id": "thv_2026_05_asia_duration",
                "tactical_view_version": "2026.05",
                "theme_id": "asia_duration_reduce",
                "as_of_date": "2026-05-14",
                "target_action": "REDUCE",
                "rationale": "Reduce duration exposure in Asia balanced discretionary books.",
                "source_refs": [
                    {
                        "source_system": "lotus-advise",
                        "source_type": "TACTICAL_HOUSE_VIEW",
                        "source_id": "thv_2026_05_asia_duration",
                        "source_version": "2026.05",
                        "content_hash": "sha256:house-view",
                    }
                ],
                "reason_codes": ["TACTICAL_DURATION_REDUCTION"],
            },
            "candidate_portfolios": [
                {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                    "portfolio_type": "DISCRETIONARY",
                    "discretionary_mandate": True,
                    "booking_center_code": "Singapore",
                    "current_exposure_weight": "0.18",
                    "alignment_signal": "OVERWEIGHT",
                    "source_refs": [
                        {
                            "source_system": "lotus-core",
                            "source_type": "HoldingsAsOf",
                            "source_id": "holdings:PB_SG_GLOBAL_BAL_001:2026-05-14",
                            "source_version": "v1",
                            "content_hash": "sha256:holdings",
                        },
                        {
                            "source_system": "lotus-risk",
                            "source_type": "RiskMetricsReport",
                            "source_id": "risk:PB_SG_GLOBAL_BAL_001:2026-05-14",
                            "source_version": "v1",
                            "content_hash": "sha256:risk",
                        },
                    ],
                    "reason_codes": ["DURATION_EXPOSURE_ABOVE_HOUSE_VIEW"],
                },
                {
                    "portfolio_id": "PB_SG_ADVISORY_002",
                    "portfolio_type": "ADVISORY",
                    "discretionary_mandate": False,
                    "current_exposure_weight": "0.22",
                    "alignment_signal": "OVERWEIGHT",
                    "source_refs": [
                        {
                            "source_system": "lotus-core",
                            "source_type": "HoldingsAsOf",
                            "source_id": "holdings:PB_SG_ADVISORY_002:2026-05-14",
                        }
                    ],
                },
            ],
            "eligible_portfolio_types": ["DISCRETIONARY"],
            "min_exposure_weight": "0.10",
            "correlation_id": "corr-thv-001",
        }
    )


def test_tactical_house_view_facade_delegates_models_and_rules() -> None:
    facade_source = (REPO_ROOT / "src/core/tactical_house_view.py").read_text(encoding="utf-8")
    model_source = (REPO_ROOT / "src/core/tactical_house_view_models.py").read_text(
        encoding="utf-8"
    )
    rule_source = (REPO_ROOT / "src/core/tactical_house_view_rules.py").read_text(encoding="utf-8")

    assert "from src.core.tactical_house_view_models import" in facade_source
    assert "from src.core.tactical_house_view_rules import" in facade_source
    assert "class TacticalHouseViewCohortRequest(" not in facade_source
    assert "class TacticalHouseViewAffectedCohort(" not in facade_source
    assert "def candidate_exclusion_reasons(" not in facade_source
    assert "def supportability(" not in facade_source
    assert "class TacticalHouseViewCohortRequest(" in model_source
    assert "class TacticalHouseViewAffectedCohort(" in model_source
    assert "def candidate_exclusion_reasons(" in rule_source
    assert "def supportability(" in rule_source


def test_tactical_house_view_cohort_preserves_source_backed_inclusions_and_exclusions() -> None:
    cohort = build_tactical_house_view_affected_cohort(
        _request(),
        generated_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
    )

    assert cohort.product_name == "TacticalHouseViewAffectedCohort"
    assert cohort.product_version == "v1"
    assert cohort.cohort_id.startswith("sha256:")
    assert cohort.content_hash.startswith("sha256:")
    assert cohort.supportability.state == "READY"
    assert cohort.supportability.evaluated_candidate_count == 2
    assert cohort.supportability.affected_count == 1
    assert cohort.supportability.excluded_count == 1
    assert cohort.affected_portfolios[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert cohort.affected_portfolios[0].inclusion_reason_codes == [
        "DURATION_EXPOSURE_ABOVE_HOUSE_VIEW",
        "TACTICAL_HOUSE_VIEW_OVERWEIGHT",
        "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
    ]
    assert cohort.excluded_portfolios[0].portfolio_id == "PB_SG_ADVISORY_002"
    assert sorted(cohort.excluded_portfolios[0].exclusion_reason_codes) == [
        "TACTICAL_HOUSE_VIEW_NON_DISCRETIONARY_MANDATE",
        "TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPE_NOT_ELIGIBLE",
    ]
    assert {ref.source_system for ref in cohort.source_refs} == {
        "lotus-advise",
        "lotus-core",
        "lotus-risk",
    }


def test_tactical_house_view_normalizes_legacy_portfolio_type_alias() -> None:
    payload = _request().model_dump(mode="json")
    payload["candidate_portfolios"][0]["portfolio_type"] = "DPM"
    payload.pop("eligible_portfolio_types")
    request = TacticalHouseViewCohortRequest.model_validate(payload)

    assert request.eligible_portfolio_types == ["DISCRETIONARY", "MANAGED"]

    cohort = build_tactical_house_view_affected_cohort(
        request,
        generated_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
    )

    assert cohort.affected_portfolios[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_tactical_house_view_cohort_is_empty_when_no_candidate_is_eligible() -> None:
    request = _request().model_copy(update={"eligible_portfolio_types": ["PRIVATE_ADVISORY"]})

    cohort = build_tactical_house_view_affected_cohort(
        request,
        generated_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
    )

    assert cohort.affected_portfolios == []
    assert cohort.supportability.state == "EMPTY"
    assert cohort.supportability.reason_codes == [
        "TACTICAL_HOUSE_VIEW_NO_ELIGIBLE_AFFECTED_PORTFOLIOS"
    ]
    assert cohort.supportability.affected_count == 0
    assert cohort.supportability.excluded_count == 2


def test_tactical_house_view_minimum_exposure_requires_source_exposure_evidence() -> None:
    payload = _request().model_dump(mode="json")
    payload["candidate_portfolios"][0]["current_exposure_weight"] = None
    request = TacticalHouseViewCohortRequest.model_validate(payload)

    cohort = build_tactical_house_view_affected_cohort(
        request,
        generated_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
    )

    assert cohort.affected_portfolios == []
    assert cohort.excluded_portfolios[1].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert "TACTICAL_HOUSE_VIEW_EXPOSURE_EVIDENCE_MISSING" in (
        cohort.excluded_portfolios[1].exclusion_reason_codes
    )


def test_tactical_house_view_minimum_exposure_excludes_below_threshold_candidate() -> None:
    payload = _request().model_dump(mode="json")
    payload["candidate_portfolios"][0]["current_exposure_weight"] = "0.05"
    request = TacticalHouseViewCohortRequest.model_validate(payload)

    cohort = build_tactical_house_view_affected_cohort(
        request,
        generated_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
    )

    assert cohort.affected_portfolios == []
    assert cohort.excluded_portfolios[1].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert "TACTICAL_HOUSE_VIEW_EXPOSURE_BELOW_MINIMUM" in (
        cohort.excluded_portfolios[1].exclusion_reason_codes
    )


def test_tactical_house_view_candidate_requires_source_refs() -> None:
    payload = _request().model_dump(mode="json")
    payload["candidate_portfolios"][0]["source_refs"] = []

    with pytest.raises(ValueError, match="source_refs"):
        TacticalHouseViewCohortRequest.model_validate(payload)
