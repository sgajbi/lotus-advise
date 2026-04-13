from src.core.advisory.risk_lens import extract_risk_lens


class _ProposalResult:
    def __init__(self, explanation):
        self.explanation = explanation


def test_extract_risk_lens_returns_copy_for_valid_payload() -> None:
    payload = {
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_proposed": "0.12"},
        }
    }

    extracted = extract_risk_lens(_ProposalResult(payload))

    assert extracted == payload["risk_lens"]
    assert extracted is not payload["risk_lens"]


def test_extract_risk_lens_rejects_missing_or_invalid_source_service() -> None:
    assert extract_risk_lens(_ProposalResult(None)) is None
    assert extract_risk_lens(_ProposalResult({"risk_lens": []})) is None
    assert extract_risk_lens(_ProposalResult({"risk_lens": {"source_service": ""}})) is None
