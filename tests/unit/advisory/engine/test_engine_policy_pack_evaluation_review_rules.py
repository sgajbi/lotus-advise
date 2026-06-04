from src.core.policy_packs.evaluation_review_rules import (
    evaluate_best_interest_cost,
    evaluate_conflict_disclosure,
)


def _rule(rule_id: str) -> dict:
    return {
        "rule_id": rule_id,
        "required_evidence_fields": ["fee_evidence", "conflict_evidence"],
    }


def test_policy_evaluation_review_rules_project_best_interest_cost_posture() -> None:
    pending = evaluate_best_interest_cost(
        rule=_rule("SG_BEST_INTEREST_COST_REVIEW"),
        evidence_bundle={
            "artifact": {
                "assumptions_and_limits": {
                    "costs_and_fees": {"included": False},
                    "tax": {"included": False},
                    "execution": {"included": True},
                }
            }
        },
    )

    assert pending.status == "PENDING_REVIEW"
    assert pending.outcome == "BEST_INTEREST_COST_REASONABLENESS_REVIEW_REQUIRED"
    assert pending.missing_evidence == ["fee_evidence", "cost_evidence", "tax_evidence"]

    ready = evaluate_best_interest_cost(
        rule=_rule("SG_BEST_INTEREST_COST_REVIEW"),
        evidence_bundle={
            "artifact": {
                "assumptions_and_limits": {
                    "costs_and_fees": {"included": True},
                    "tax": {"included": True},
                    "execution": {"included": True},
                }
            }
        },
    )
    assert ready.status == "READY"
    assert ready.outcome == "BEST_INTEREST_COST_TAX_AND_FRICTION_EVIDENCE_READY_FOR_REVIEW"


def test_policy_evaluation_review_rules_project_conflict_and_documents_posture() -> None:
    blocked = evaluate_conflict_disclosure(
        rule=_rule("SG_CONFLICT_REVIEW"),
        evidence_bundle={
            "inputs": {
                "shelf_entries": [{"instrument_id": "NOTE_A"}],
                "proposed_trades": [{"instrument_id": "NOTE_A"}],
            },
            "artifact": {"disclosures": {"product_docs": []}},
            "conflict_evidence": {"material_conflict": True},
        },
    )

    assert blocked.status == "BLOCKED"
    assert blocked.outcome == "CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED"
    assert blocked.missing_evidence == ["product_document:NOTE_A"]
    assert blocked.reason_codes == [
        "MATERIAL_CONFLICT_REQUIRES_SUPERVISORY_REVIEW",
        "PRODUCT_DOCUMENTATION_INCOMPLETE_FOR_PROPOSED_TRADES",
    ]

    ready = evaluate_conflict_disclosure(
        rule=_rule("SG_CONFLICT_REVIEW"),
        evidence_bundle={
            "inputs": {
                "shelf_entries": [{"instrument_id": "ETF_A"}],
                "proposed_trades": [{"instrument_id": "ETF_A"}],
            },
            "artifact": {"disclosures": {"product_docs": [{"instrument_id": "ETF_A"}]}},
            "conflict_evidence": {"material_conflict": False},
        },
    )
    assert ready.status == "READY"
    assert ready.outcome == "CONFLICT_AND_PRODUCT_DOCUMENT_EVIDENCE_READY_FOR_REVIEW"
