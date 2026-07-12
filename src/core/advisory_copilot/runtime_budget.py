from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from typing import Any

ADVISORY_COPILOT_RUNTIME_BUDGET_CONTRACT_VERSION = "advisory-copilot-runtime-budget.v1"
ADVISORY_COPILOT_RUNTIME_BUDGET_CONFIG_REF = "contracts/advisory-copilot/runtime-budget.v1.json"
ADVISORY_COPILOT_RETRYABLE_TRANSPORT_ERRORS = (
    "ConnectError",
    "ConnectTimeout",
    "PoolTimeout",
    "ReadTimeout",
)
DEFAULT_ADVISORY_COPILOT_TIMEOUT_MS = 10_000
DEFAULT_ADVISORY_COPILOT_MAX_ATTEMPTS = 2
DEFAULT_ADVISORY_COPILOT_RETRY_BACKOFF_MS = 100
DEFAULT_ADVISORY_COPILOT_MAX_INPUT_CHARACTERS = 32_000
DEFAULT_ADVISORY_COPILOT_MAX_OUTPUT_CHARACTERS = 20_000
DEFAULT_ADVISORY_COPILOT_MAX_PROMPT_TOKENS = 8_000
DEFAULT_ADVISORY_COPILOT_MAX_COMPLETION_TOKENS = 1_200
DEFAULT_ADVISORY_COPILOT_MAX_TOTAL_TOKENS = 9_200
DEFAULT_ADVISORY_COPILOT_MAX_CHARGEABLE_COST_UNITS = 50_000
DEFAULT_ADVISORY_COPILOT_MAX_CONCURRENT_REQUESTS = 4
_CHARS_PER_TOKEN_ESTIMATE = 4


@dataclass(frozen=True)
class AdvisoryCopilotRuntimeBudget:
    timeout_ms: int = DEFAULT_ADVISORY_COPILOT_TIMEOUT_MS
    max_attempts: int = DEFAULT_ADVISORY_COPILOT_MAX_ATTEMPTS
    retry_backoff_ms: int = DEFAULT_ADVISORY_COPILOT_RETRY_BACKOFF_MS
    max_input_characters: int = DEFAULT_ADVISORY_COPILOT_MAX_INPUT_CHARACTERS
    max_output_characters: int = DEFAULT_ADVISORY_COPILOT_MAX_OUTPUT_CHARACTERS
    max_prompt_tokens: int = DEFAULT_ADVISORY_COPILOT_MAX_PROMPT_TOKENS
    max_completion_tokens: int = DEFAULT_ADVISORY_COPILOT_MAX_COMPLETION_TOKENS
    max_total_tokens: int = DEFAULT_ADVISORY_COPILOT_MAX_TOTAL_TOKENS
    max_chargeable_cost_units: int = DEFAULT_ADVISORY_COPILOT_MAX_CHARGEABLE_COST_UNITS
    max_concurrent_requests: int = DEFAULT_ADVISORY_COPILOT_MAX_CONCURRENT_REQUESTS


@dataclass(frozen=True)
class AdvisoryCopilotRuntimeUsage:
    character_count: int
    token_estimate: int


class AdvisoryCopilotRuntimeBudgetExceeded(ValueError):
    def __init__(self, reason_code: str, telemetry: dict[str, Any]) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.telemetry = telemetry


def advisory_copilot_runtime_budget_controls(
    budget: AdvisoryCopilotRuntimeBudget | None = None,
) -> dict[str, Any]:
    resolved = budget or AdvisoryCopilotRuntimeBudget()
    return {
        "contract_version": ADVISORY_COPILOT_RUNTIME_BUDGET_CONTRACT_VERSION,
        "config_ref": ADVISORY_COPILOT_RUNTIME_BUDGET_CONFIG_REF,
        "deadline_ms": resolved.timeout_ms,
        "retry_policy": {
            "max_attempts": resolved.max_attempts,
            "backoff_ms": resolved.retry_backoff_ms,
            "retryable_transport_errors": list(ADVISORY_COPILOT_RETRYABLE_TRANSPORT_ERRORS),
            "retry_non_idempotent_operations": False,
            "retry_provider_validation_errors": False,
        },
        "token_budget": {
            "max_prompt_tokens": resolved.max_prompt_tokens,
            "max_completion_tokens": resolved.max_completion_tokens,
            "max_total_tokens": resolved.max_total_tokens,
        },
        "payload_budget": {
            "max_input_characters": resolved.max_input_characters,
            "max_output_characters": resolved.max_output_characters,
        },
        "cost_budget": {
            "max_chargeable_cost_units": resolved.max_chargeable_cost_units,
            "pricing_source": "lotus-ai-provider-configuration",
            "application_defined_provider_pricing": False,
        },
        "concurrency_budget": {
            "max_concurrent_requests_per_process": resolved.max_concurrent_requests,
        },
    }


def advisory_copilot_payload_usage(payload: Any) -> AdvisoryCopilotRuntimeUsage:
    character_count = len(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    )
    return AdvisoryCopilotRuntimeUsage(
        character_count=character_count,
        token_estimate=estimated_token_count(character_count),
    )


def estimated_token_count(character_count: int) -> int:
    return ceil(character_count / _CHARS_PER_TOKEN_ESTIMATE)


def validate_advisory_copilot_input_budget(
    *,
    usage: AdvisoryCopilotRuntimeUsage,
    budget: AdvisoryCopilotRuntimeBudget,
    telemetry: dict[str, Any],
) -> None:
    if usage.character_count > budget.max_input_characters:
        raise AdvisoryCopilotRuntimeBudgetExceeded(
            "COPILOT_AI_INPUT_BUDGET_EXHAUSTED",
            telemetry,
        )
    if usage.token_estimate > budget.max_prompt_tokens:
        raise AdvisoryCopilotRuntimeBudgetExceeded(
            "COPILOT_AI_PROMPT_TOKEN_BUDGET_EXHAUSTED",
            telemetry,
        )
    if usage.token_estimate + budget.max_completion_tokens > budget.max_total_tokens:
        raise AdvisoryCopilotRuntimeBudgetExceeded(
            "COPILOT_AI_TOTAL_TOKEN_BUDGET_EXHAUSTED",
            telemetry,
        )


def validate_advisory_copilot_output_budget(
    *,
    usage: AdvisoryCopilotRuntimeUsage,
    budget: AdvisoryCopilotRuntimeBudget,
    telemetry: dict[str, Any],
) -> None:
    if usage.character_count > budget.max_output_characters:
        raise AdvisoryCopilotRuntimeBudgetExceeded(
            "COPILOT_AI_OUTPUT_BUDGET_EXHAUSTED",
            telemetry,
        )
    if usage.token_estimate > budget.max_completion_tokens:
        raise AdvisoryCopilotRuntimeBudgetExceeded(
            "COPILOT_AI_COMPLETION_TOKEN_BUDGET_EXHAUSTED",
            telemetry,
        )


def advisory_copilot_runtime_budget_telemetry(
    *,
    budget: AdvisoryCopilotRuntimeBudget,
    attempt_count: int,
    latency_ms: int | None,
    fallback_reason: str | None,
    retry_exhausted: bool,
    last_error_type: str | None,
    input_usage: AdvisoryCopilotRuntimeUsage | None = None,
    output_usage: AdvisoryCopilotRuntimeUsage | None = None,
) -> dict[str, Any]:
    return {
        "contract_version": ADVISORY_COPILOT_RUNTIME_BUDGET_CONTRACT_VERSION,
        "config_ref": ADVISORY_COPILOT_RUNTIME_BUDGET_CONFIG_REF,
        "attempt_count": attempt_count,
        "max_attempts": budget.max_attempts,
        "deadline_ms": budget.timeout_ms,
        "retry_backoff_ms": budget.retry_backoff_ms,
        "retry_exhausted": retry_exhausted,
        "fallback_reason": fallback_reason,
        "last_error_type": last_error_type,
        "latency_ms": latency_ms,
        "input_character_count": _usage_character_count(input_usage),
        "input_token_estimate": _usage_token_estimate(input_usage),
        "output_character_count": _usage_character_count(output_usage),
        "output_token_estimate": _usage_token_estimate(output_usage),
        "max_prompt_tokens": budget.max_prompt_tokens,
        "max_completion_tokens": budget.max_completion_tokens,
        "max_total_tokens": budget.max_total_tokens,
        "max_chargeable_cost_units": budget.max_chargeable_cost_units,
        "max_concurrent_requests_per_process": budget.max_concurrent_requests,
    }


def _usage_character_count(usage: AdvisoryCopilotRuntimeUsage | None) -> int | None:
    return None if usage is None else usage.character_count


def _usage_token_estimate(usage: AdvisoryCopilotRuntimeUsage | None) -> int | None:
    return None if usage is None else usage.token_estimate
