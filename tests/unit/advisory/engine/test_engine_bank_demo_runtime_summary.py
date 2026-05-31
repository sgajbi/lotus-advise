from __future__ import annotations

import pytest

from src.core.bank_demo_proof.runtime_summary import (
    sanitize_live_runtime_summary,
    select_fields,
    value_at,
)
from tests.unit.advisory.engine.test_engine_bank_demo_proof_capture import _live_runtime_payload


def test_runtime_summary_projects_demo_safe_fields_without_source_hashes() -> None:
    summary = sanitize_live_runtime_summary(_live_runtime_payload())

    assert summary["proposal_lifecycle"]["execution_terminal_status"] == "EXECUTED"
    assert summary["proposal_policy"]["evaluation_status"] == "PENDING_REVIEW"
    assert summary["proposal_policy"]["workflow_client_ready_publication"] == "BLOCKED"
    assert summary["proposal_memo"]["review_client_ready_publication"] == "BLOCKED"
    assert "memo_hash" not in summary["proposal_memo"]
    assert "source_input_hash" not in summary["proposal_memo"]
    assert "source_narrative_hash" not in summary["proposal_narrative"]


def test_runtime_summary_fails_closed_when_required_contract_sections_are_missing() -> None:
    payload = _live_runtime_payload()
    del payload["parity"]["proposal_policy"]

    with pytest.raises(ValueError, match="RFC0028_BACKEND_PROOF_FIELD_MISSING"):
        sanitize_live_runtime_summary(payload)


def test_runtime_summary_value_at_reports_missing_dotted_contract_path() -> None:
    with pytest.raises(
        ValueError,
        match="RFC0028_BACKEND_PROOF_FIELD_MISSING: parity.proposal_policy.evaluation_status",
    ):
        value_at({"parity": {"proposal_policy": {}}}, "parity.proposal_policy.evaluation_status")


def test_runtime_summary_select_fields_preserves_defined_shape_with_missing_values() -> None:
    assert select_fields({"status": "READY"}, ("status", "missing")) == {
        "status": "READY",
        "missing": None,
    }
