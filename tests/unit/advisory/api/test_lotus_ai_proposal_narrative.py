from __future__ import annotations

import httpx
import pytest

from src.core.advisory.narrative_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativePolicy,
    ProposalNarrativePolicyContext,
    ProposalNarrativeSourceRef,
)
from src.integrations.lotus_ai.proposal_narrative import (
    LotusAIProposalNarrativeUnavailableError,
    _build_workflow_pack_request,
    generate_proposal_narrative_draft_with_lotus_ai,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeClient:
    def __init__(
        self,
        *args,
        responses: dict[str, _FakeResponse] | None = None,
        raised_error: Exception | None = None,
        **kwargs,
    ) -> None:
        self._responses = responses or {}
        self._raised_error = raised_error

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    def post(self, url: str, json: dict[str, object]) -> _FakeResponse:
        if self._raised_error is not None:
            raise self._raised_error
        response = self._responses.get(url)
        if response is None:
            raise AssertionError(f"unexpected request url: {url}")
        return response


def _grounding_packet() -> ProposalNarrativeGroundingPacket:
    return ProposalNarrativeGroundingPacket(
        packet_id="pgp_ai_adapter_001",
        policy_version="proposal-narrative-deterministic.v1",
        audience="ADVISOR_REVIEW",
        source_refs=[
            ProposalNarrativeSourceRef(
                ref_type="decision_summary",
                ref_id="pr_ai_adapter_001",
                field_path="proposal_decision_summary.decision_status",
            )
        ],
        input_hashes={"artifact_hash": "sha256:abc123"},
        facts={
            "proposal_status": "READY",
            "recommended_next_step": "CLIENT_CONSENT",
            "risk_status": "AVAILABLE",
        },
    )


def _narrative_policy() -> ProposalNarrativePolicy:
    return ProposalNarrativePolicy(
        policy_version="advisory-narrative-policy.2026-05",
        status="READY_FOR_ADVISOR_REVIEW",
        context=ProposalNarrativePolicyContext(
            jurisdiction="SG",
            product_types=["EQUITY"],
            risk_posture="STANDARD",
            client_audience="ADVISOR_REVIEW",
        ),
        prohibited_claims=["guaranteed return", "risk-free"],
    )


def test_workflow_pack_request_uses_structured_grounding_packet_without_raw_prompt() -> None:
    request_payload = _build_workflow_pack_request(
        grounding_packet=_grounding_packet(),
        narrative_policy=_narrative_policy(),
        requested_sections=["EXECUTIVE_SUMMARY"],
        requested_by="advisor_123",
    )

    task_request = request_payload["task_request"]
    assert isinstance(task_request, dict)
    context = task_request["context"]
    assert isinstance(context, dict)
    payload = context["payload"]
    assert isinstance(payload, dict)

    assert request_payload["pack_id"] == "proposal_narrative_draft.pack"
    assert task_request["input_mode"] == "STRUCTURED_CONTEXT"
    assert "prompt" not in task_request
    assert "instruction" not in task_request
    assert "prompt" not in payload
    assert "instruction" not in payload
    assert payload["grounding_packet"]["packet_id"] == "pgp_ai_adapter_001"
    assert payload["requested_sections"] == ["EXECUTIVE_SUMMARY"]
    assert [item["instruction_id"] for item in payload["approved_instructions"]] == [
        "USE_GROUNDING_FACTS_ONLY",
        "NO_CLIENT_READY_LANGUAGE",
        "PRESERVE_LIMITATIONS",
    ]
    assert context["source_refs"] == [
        "decision_summary:pr_ai_adapter_001:proposal_decision_summary.decision_status"
    ]


def test_generate_proposal_narrative_draft_returns_sections_and_ai_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "http://lotus-ai.dev.lotus"
    monkeypatch.setenv("LOTUS_AI_BASE_URL", base_url)
    monkeypatch.setattr(
        "src.integrations.lotus_ai.proposal_narrative.httpx.Client",
        lambda *args, **kwargs: _FakeClient(
            *args,
            responses={
                f"{base_url}/platform/workflow-packs/execute": _FakeResponse(
                    200,
                    {
                        "execution": {
                            "status": "COMPLETED",
                            "result": {
                                "model_version": "lotus-ai-governed-model.v1",
                                "sections": [
                                    {
                                        "section_key": "EXECUTIVE_SUMMARY",
                                        "title": " Executive Summary ",
                                        "text": " Advisor-review AI draft. ",
                                    }
                                ],
                            },
                        },
                        "workflow_pack_run": {"run_id": "packrun_proposal_narrative_001"},
                    },
                )
            },
            **kwargs,
        ),
    )

    response = generate_proposal_narrative_draft_with_lotus_ai(
        grounding_packet=_grounding_packet(),
        narrative_policy=_narrative_policy(),
        requested_sections=["EXECUTIVE_SUMMARY"],
        requested_by="advisor_123",
    )

    assert response.sections[0].section_key == "EXECUTIVE_SUMMARY"
    assert response.sections[0].text == "Advisor-review AI draft."
    assert response.lineage.workflow_run_id == "packrun_proposal_narrative_001"
    assert response.lineage.model_version == "lotus-ai-governed-model.v1"
    assert response.lineage.fallback_reason is None


def test_generate_proposal_narrative_draft_masks_timeout_and_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTUS_AI_BASE_URL", "http://lotus-ai.dev.lotus")
    monkeypatch.setattr(
        "src.integrations.lotus_ai.proposal_narrative.httpx.Client",
        lambda *args, **kwargs: _FakeClient(
            *args,
            raised_error=httpx.ReadTimeout("timeout"),
            **kwargs,
        ),
    )

    with pytest.raises(LotusAIProposalNarrativeUnavailableError) as exc:
        generate_proposal_narrative_draft_with_lotus_ai(
            grounding_packet=_grounding_packet(),
            narrative_policy=_narrative_policy(),
            requested_sections=["EXECUTIVE_SUMMARY"],
            requested_by="advisor_123",
        )

    assert str(exc.value) == "LOTUS_AI_NARRATIVE_UNAVAILABLE"
