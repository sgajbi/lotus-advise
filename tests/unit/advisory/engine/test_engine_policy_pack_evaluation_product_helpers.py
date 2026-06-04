from src.core.policy_packs.evaluation_product_helpers import (
    client_segment_allowed,
    is_complex_or_private_product,
    jurisdiction_allowed,
    proposed_shelf_rows,
)


def test_policy_evaluation_product_helpers_project_proposed_shelf_rows() -> None:
    evidence_bundle = {
        "inputs": {
            "shelf_entries": [
                {"instrument_id": "FUND_A", "status": "APPROVED"},
                {"instrument_id": "NOTE_B", "status": "APPROVED"},
            ],
            "proposed_trades": [
                {"instrument_id": "FUND_A"},
                {"instrument_id": "MISSING_C"},
            ],
        }
    }

    rows = proposed_shelf_rows(evidence_bundle)

    assert rows["FUND_A"] == {"instrument_id": "FUND_A", "status": "APPROVED"}
    assert rows["MISSING_C"] is None
    assert "NOTE_B" not in rows


def test_policy_evaluation_product_helpers_read_direct_and_nested_product_policy() -> None:
    shelf = {
        "attributes": {
            "eligibility": {"jurisdictions": ["SG"]},
            "target_market": {"client_segments": ["PRIVATE_BANKING"]},
        }
    }

    assert jurisdiction_allowed(shelf, "SG") is True
    assert jurisdiction_allowed(shelf, "HK") is False
    assert client_segment_allowed(shelf, "HNW") is True


def test_policy_evaluation_product_helpers_detect_complex_and_private_products() -> None:
    assert is_complex_or_private_product({"complexity": "STRUCTURED"}) is True
    assert is_complex_or_private_product({"attributes": {"private_asset": True}}) is True
    assert is_complex_or_private_product({"attributes": {"complexity": "PLAIN_VANILLA"}}) is False
