PROPOSAL_READY_EXAMPLE = {
    "summary": "Proposal simulation ready",
    "value": {
        "status": "READY",
        "proposal_run_id": "pr_demo1234",
        "correlation_id": "corr_demo1234",
        "intents": [
            {"intent_type": "CASH_FLOW", "currency": "USD", "amount": "2000.00"},
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_GROWTH",
                "quantity": "40",
            },
        ],
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
    },
}

PROPOSAL_PENDING_EXAMPLE = {
    "summary": "Proposal simulation pending review",
    "value": {
        "status": "PENDING_REVIEW",
        "proposal_run_id": "pr_demo5678",
        "correlation_id": "corr_demo5678",
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
        "rule_results": [{"rule_id": "CASH_BAND", "severity": "SOFT", "status": "FAIL"}],
    },
}

PROPOSAL_BLOCKED_EXAMPLE = {
    "summary": "Proposal simulation blocked",
    "value": {
        "status": "BLOCKED",
        "proposal_run_id": "pr_demo9999",
        "correlation_id": "corr_demo9999",
        "diagnostics": {
            "warnings": ["PROPOSAL_WITHDRAWAL_NEGATIVE_CASH"],
            "data_quality": {"price_missing": [], "fx_missing": []},
        },
    },
}

PROPOSAL_409_EXAMPLE = {
    "summary": "Idempotency hash conflict",
    "value": {"detail": "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"},
}
