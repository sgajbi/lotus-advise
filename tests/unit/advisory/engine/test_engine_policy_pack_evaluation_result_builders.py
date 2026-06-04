from src.core.policy_packs.evaluation_result_builders import (
    rule_blocked,
    rule_pending,
    rule_ready,
    source_refs_for_rule,
)


def _rule() -> dict:
    return {
        "rule_id": "SG_TEST_RULE",
        "required_evidence_fields": [
            "policy_source_readiness.overall_posture",
            "fee_evidence",
            "risk_concentration",
            "core_mandate_objectives_restrictions",
            "risk_concentration",
        ],
    }


def test_policy_evaluation_result_builders_dedupe_source_refs_and_defaults() -> None:
    assert source_refs_for_rule(_rule()) == [
        "lotus-advise:policy_source_readiness",
        "lotus-advise:proposal_artifact_policy_evidence",
        "lotus-risk:risk_concentration",
        "lotus-core:core_mandate_objectives_restrictions",
    ]

    ready = rule_ready(_rule(), "TEST_READY")
    assert ready.status == "READY"
    assert ready.severity == "REVIEW_REQUIRED"
    assert ready.reason_codes == ["SG_TEST_RULE_READY"]

    pending = rule_pending(
        _rule(),
        outcome="TEST_PENDING",
        missing_evidence=["fee_evidence", "fee_evidence", ""],
        reason_codes=["MISSING_FEE", "MISSING_FEE"],
        required_actions=["REVIEW_FEE", "REVIEW_FEE"],
    )
    assert pending.status == "PENDING_REVIEW"
    assert pending.missing_evidence == ["fee_evidence"]
    assert pending.reason_codes == ["MISSING_FEE"]
    assert pending.required_actions == ["REVIEW_FEE"]

    blocked = rule_blocked(
        {**_rule(), "severity": "BLOCKING"},
        outcome="TEST_BLOCKED",
        missing_evidence=["conflict_evidence", "conflict_evidence"],
        reason_codes=["CONFLICT", "CONFLICT"],
        required_actions=["SUPERVISORY_REVIEW", "SUPERVISORY_REVIEW"],
    )
    assert blocked.status == "BLOCKED"
    assert blocked.severity == "BLOCKING"
    assert blocked.missing_evidence == ["conflict_evidence"]
