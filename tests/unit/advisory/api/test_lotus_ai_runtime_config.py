from __future__ import annotations

from collections.abc import Callable

import pytest

from src.integrations.lotus_ai import (
    advisory_copilot,
    policy_evidence,
    proposal_memo,
    proposal_narrative,
    rationale,
)
from src.integrations.lotus_ai.advisory_copilot import LotusAIAdvisoryCopilotUnavailableError
from src.integrations.lotus_ai.policy_evidence import LotusAIPolicyEvidenceUnavailableError
from src.integrations.lotus_ai.proposal_memo import LotusAIProposalMemoUnavailableError
from src.integrations.lotus_ai.proposal_narrative import LotusAIProposalNarrativeUnavailableError
from src.integrations.lotus_ai.rationale import LotusAIRationaleUnavailableError
from src.integrations.lotus_ai.runtime_config import (
    LotusAITenantIdentityError,
    resolve_lotus_ai_tenant_id,
)


@pytest.mark.parametrize(
    ("resolver", "error_type", "message"),
    [
        (
            proposal_narrative._resolve_base_url,
            LotusAIProposalNarrativeUnavailableError,
            "LOTUS_AI_NARRATIVE_UNAVAILABLE",
        ),
        (
            proposal_memo._resolve_base_url,
            LotusAIProposalMemoUnavailableError,
            "LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE",
        ),
        (
            policy_evidence._resolve_base_url,
            LotusAIPolicyEvidenceUnavailableError,
            "LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE",
        ),
        (
            rationale._resolve_base_url,
            LotusAIRationaleUnavailableError,
            "LOTUS_AI_RATIONALE_UNAVAILABLE",
        ),
        (
            advisory_copilot._resolve_base_url,
            LotusAIAdvisoryCopilotUnavailableError,
            "LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
        ),
    ],
)
def test_lotus_ai_adapters_sanitize_configured_base_url(
    monkeypatch: pytest.MonkeyPatch,
    resolver: Callable[[], str],
    error_type: type[Exception],
    message: str,
) -> None:
    monkeypatch.setenv(
        "LOTUS_AI_BASE_URL",
        "https://user:secret@lotus-ai:8400/api?token=should-not-leak#fragment",
    )

    assert resolver() == "https://lotus-ai:8400/api"


@pytest.mark.parametrize(
    ("resolver", "error_type", "message"),
    [
        (
            proposal_narrative._resolve_base_url,
            LotusAIProposalNarrativeUnavailableError,
            "LOTUS_AI_NARRATIVE_UNAVAILABLE",
        ),
        (
            proposal_memo._resolve_base_url,
            LotusAIProposalMemoUnavailableError,
            "LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE",
        ),
        (
            policy_evidence._resolve_base_url,
            LotusAIPolicyEvidenceUnavailableError,
            "LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE",
        ),
        (
            rationale._resolve_base_url,
            LotusAIRationaleUnavailableError,
            "LOTUS_AI_RATIONALE_UNAVAILABLE",
        ),
        (
            advisory_copilot._resolve_base_url,
            LotusAIAdvisoryCopilotUnavailableError,
            "LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
        ),
    ],
)
def test_lotus_ai_adapters_reject_invalid_configured_base_url(
    monkeypatch: pytest.MonkeyPatch,
    resolver: Callable[[], str],
    error_type: type[Exception],
    message: str,
) -> None:
    monkeypatch.setenv("LOTUS_AI_BASE_URL", "ftp://lotus-ai:8400")

    with pytest.raises(error_type, match=message):
        resolver()


def test_lotus_ai_tenant_id_requires_configured_trusted_context(monkeypatch) -> None:
    monkeypatch.delenv("LOTUS_ADVISE_TENANT_ID", raising=False)

    with pytest.raises(LotusAITenantIdentityError, match="LOTUS_AI_TENANT_ID_UNAVAILABLE"):
        resolve_lotus_ai_tenant_id()


def test_lotus_ai_tenant_id_uses_bounded_configured_value(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", " tenant-private-bank-001 ")

    assert resolve_lotus_ai_tenant_id() == "tenant-private-bank-001"


def test_lotus_ai_tenant_id_rejects_control_characters(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant-private-bank-001\x7f")

    with pytest.raises(LotusAITenantIdentityError, match="LOTUS_AI_TENANT_ID_UNAVAILABLE"):
        resolve_lotus_ai_tenant_id()


def test_lotus_ai_tenant_id_rejects_over_length_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "t" * 129)

    with pytest.raises(LotusAITenantIdentityError, match="LOTUS_AI_TENANT_ID_UNAVAILABLE"):
        resolve_lotus_ai_tenant_id()
