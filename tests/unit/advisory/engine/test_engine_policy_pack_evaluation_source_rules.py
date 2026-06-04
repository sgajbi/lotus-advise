from src.core.policy_packs.evaluation_source_rules import (
    evaluate_mandate_rule,
    required_source_result,
)


def _rule(required_fields: list[str]) -> dict:
    return {
        "rule_id": "GLOBAL_SOURCE_READINESS_REQUIRED",
        "required_evidence_fields": required_fields,
    }


def test_policy_evaluation_source_rules_block_missing_required_source_sections() -> None:
    result = required_source_result(
        rule=_rule(["core_product_eligibility_target_market_complexity"]),
        source_posture={"sections": []},
    )

    assert result is not None
    assert result.status == "BLOCKED"
    assert result.outcome == "SOURCE_EVIDENCE_BLOCKED"
    assert result.missing_evidence == ["core_product_eligibility_target_market_complexity"]
    assert result.reason_codes == ["POLICY_SOURCE_SECTION_MISSING"]


def test_policy_evaluation_source_rules_collect_pending_policy_source_readiness() -> None:
    result = required_source_result(
        rule=_rule(["policy_source_readiness.overall_posture"]),
        source_posture={
            "overall_posture": "PENDING_REVIEW",
            "sections": [
                {
                    "key": "risk_concentration",
                    "status": "PENDING_REVIEW",
                    "missing_evidence": ["risk_lens"],
                    "reason_codes": ["RISK_LENS_PENDING"],
                }
            ],
        },
    )

    assert result is not None
    assert result.status == "PENDING_REVIEW"
    assert result.missing_evidence == ["risk_lens"]
    assert result.reason_codes == ["RISK_LENS_PENDING"]


def test_policy_evaluation_source_rules_block_blocked_policy_source_readiness() -> None:
    result = required_source_result(
        rule=_rule(["policy_source_readiness.source_authority"]),
        source_posture={
            "overall_posture": "BLOCKED",
            "sections": [
                {
                    "key": "core_product_eligibility_target_market_complexity",
                    "status": "BLOCKED",
                    "missing_evidence": ["target_market"],
                    "reason_codes": ["TARGET_MARKET_MISSING"],
                }
            ],
        },
    )

    assert result is not None
    assert result.status == "BLOCKED"
    assert result.outcome == "SOURCE_EVIDENCE_BLOCKED"
    assert result.missing_evidence == ["target_market"]
    assert result.reason_codes == ["TARGET_MARKET_MISSING"]


def test_policy_evaluation_source_rules_return_none_for_ready_source_sections() -> None:
    result = required_source_result(
        rule=_rule(["core_product_eligibility_target_market_complexity"]),
        source_posture={
            "sections": [
                {
                    "key": "core_product_eligibility_target_market_complexity",
                    "status": "READY",
                    "missing_evidence": [],
                    "reason_codes": [],
                }
            ],
        },
    )

    assert result is None


def test_policy_evaluation_source_rules_project_mandate_readiness_refs() -> None:
    result = evaluate_mandate_rule(
        rule={
            "rule_id": "GLOBAL_MANDATE_RESTRICTIONS_REVIEW",
            "required_evidence_fields": ["core_mandate_objectives_restrictions"],
        },
        source_posture={
            "sections": [
                {
                    "key": "core_mandate_objectives_restrictions",
                    "evidence_refs": ["core://mandate"],
                }
            ]
        },
    )

    assert result.status == "READY"
    assert result.evidence_refs == ["core://mandate"]
    assert result.source_authority_refs == ["lotus-core:core_mandate_objectives_restrictions"]
