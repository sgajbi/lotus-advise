from __future__ import annotations

import json
from pathlib import Path

from src.core.advisory_copilot import (
    ADVISORY_COPILOT_RUNTIME_BUDGET_CONFIG_REF,
    ADVISORY_COPILOT_RUNTIME_BUDGET_CONTRACT_VERSION,
    AdvisoryCopilotRuntimeBudget,
    advisory_copilot_payload_usage,
    advisory_copilot_runtime_budget_controls,
    advisory_copilot_runtime_budget_telemetry,
    estimated_token_count,
)

CONTRACT_PATH = Path("contracts/advisory-copilot/runtime-budget.v1.json")


def test_advisory_copilot_runtime_budget_controls_match_contract() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    controls = advisory_copilot_runtime_budget_controls()

    assert contract["contract_version"] == ADVISORY_COPILOT_RUNTIME_BUDGET_CONTRACT_VERSION
    assert controls["contract_version"] == contract["contract_version"]
    assert controls["config_ref"] == ADVISORY_COPILOT_RUNTIME_BUDGET_CONFIG_REF
    assert controls["deadline_ms"] == contract["deadline_ms"]
    assert controls["retry_policy"] == contract["retry_policy"]
    assert (
        controls["token_budget"]["max_prompt_tokens"]
        == (contract["token_budget"]["max_prompt_tokens"])
    )
    assert (
        controls["token_budget"]["max_completion_tokens"]
        == (contract["token_budget"]["max_completion_tokens"])
    )
    assert (
        controls["token_budget"]["max_total_tokens"]
        == (contract["token_budget"]["max_total_tokens"])
    )
    assert controls["payload_budget"] == contract["payload_budget"]
    assert controls["cost_budget"] == contract["cost_budget"]
    assert controls["concurrency_budget"] == contract["concurrency_budget"]


def test_advisory_copilot_runtime_budget_uses_bounded_token_estimate() -> None:
    usage = advisory_copilot_payload_usage({"text": "abcd" * 9})

    assert usage.character_count > 0
    assert usage.token_estimate == estimated_token_count(usage.character_count)
    assert estimated_token_count(1) == 1
    assert estimated_token_count(4) == 1
    assert estimated_token_count(5) == 2


def test_advisory_copilot_runtime_budget_telemetry_is_bounded_and_sanitized() -> None:
    budget = AdvisoryCopilotRuntimeBudget()
    input_usage = advisory_copilot_payload_usage({"input": "source backed evidence"})
    output_usage = advisory_copilot_payload_usage({"output": "advisor review only"})

    telemetry = advisory_copilot_runtime_budget_telemetry(
        budget=budget,
        attempt_count=2,
        latency_ms=17,
        fallback_reason="COPILOT_AI_RETRY_BUDGET_EXHAUSTED",
        retry_exhausted=True,
        last_error_type="ReadTimeout",
        input_usage=input_usage,
        output_usage=output_usage,
    )

    assert set(telemetry) == {
        "contract_version",
        "config_ref",
        "attempt_count",
        "max_attempts",
        "deadline_ms",
        "retry_backoff_ms",
        "retry_exhausted",
        "fallback_reason",
        "last_error_type",
        "latency_ms",
        "input_character_count",
        "input_token_estimate",
        "output_character_count",
        "output_token_estimate",
        "max_prompt_tokens",
        "max_completion_tokens",
        "max_total_tokens",
        "max_chargeable_cost_units",
        "max_concurrent_requests_per_process",
    }
    assert telemetry["attempt_count"] == 2
    assert telemetry["retry_exhausted"] is True
    assert telemetry["last_error_type"] == "ReadTimeout"
    assert telemetry["input_token_estimate"] == input_usage.token_estimate
    assert telemetry["output_token_estimate"] == output_usage.token_estimate
    assert "source backed evidence" not in str(telemetry)
