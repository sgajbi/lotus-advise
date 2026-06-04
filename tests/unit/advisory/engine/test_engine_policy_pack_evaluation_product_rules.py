from src.core.policy_packs.evaluation_product_rules import (
    evaluate_sg_complex_product_disclosure,
    evaluate_sg_product_eligibility,
)


def _rule(rule_id: str) -> dict:
    return {
        "rule_id": rule_id,
        "severity": "BLOCKING",
        "required_evidence_fields": [
            "core_product_eligibility_target_market_complexity",
        ],
    }


def test_policy_evaluation_product_rules_block_missing_or_ineligible_products() -> None:
    result = evaluate_sg_product_eligibility(
        rule=_rule("SG_AI_PRODUCT_ELIGIBILITY_REVIEW"),
        evidence_bundle={
            "inputs": {
                "shelf_entries": [
                    {
                        "instrument_id": "NOTE_A",
                        "eligibility": {"jurisdictions": ["HK"]},
                        "target_market": {"client_segments": ["PROFESSIONAL_INVESTOR"]},
                    }
                ],
                "proposed_trades": [
                    {"instrument_id": "NOTE_A"},
                    {"instrument_id": "MISSING_B"},
                ],
            }
        },
        jurisdiction="SG",
        client_segment="PRIVATE_BANKING",
    )

    assert result.status == "BLOCKED"
    assert result.outcome == "ELIGIBILITY_REVIEW_REQUIRED"
    assert result.missing_evidence == ["shelf_entry:MISSING_B"]
    assert result.reason_codes == [
        "PRODUCT_NOT_ELIGIBLE_FOR_JURISDICTION",
        "PRODUCT_NOT_IN_TARGET_MARKET_FOR_CLIENT_SEGMENT",
        "PRODUCT_SHELF_ENTRY_MISSING_FOR_PROPOSED_TRADE",
    ]


def test_policy_evaluation_product_rules_project_complex_disclosure_posture() -> None:
    pending = evaluate_sg_complex_product_disclosure(
        rule=_rule("SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW"),
        evidence_bundle={
            "inputs": {
                "shelf_entries": [
                    {"instrument_id": "NOTE_A", "attributes": {"structured_product": True}}
                ],
                "proposed_trades": [{"instrument_id": "NOTE_A"}],
            }
        },
    )

    assert pending.status == "PENDING_REVIEW"
    assert pending.outcome == "DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED"
    assert pending.missing_evidence == [
        "advisor_reviewed_disclosure:NOTE_A",
        "client_consent:NOTE_A",
    ]

    ready = evaluate_sg_complex_product_disclosure(
        rule=_rule("SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW"),
        evidence_bundle={
            "inputs": {
                "shelf_entries": [{"instrument_id": "ETF_A", "complexity": "PLAIN_VANILLA"}],
                "proposed_trades": [{"instrument_id": "ETF_A"}],
            }
        },
    )
    assert ready.status == "READY"
    assert ready.outcome == "NO_COMPLEX_PRODUCT_DISCLOSURE_TRIGGER"
