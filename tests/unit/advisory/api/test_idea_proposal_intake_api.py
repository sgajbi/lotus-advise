from fastapi.testclient import TestClient

from src.api.main import app
from src.core.proposals.idea_proposal_intake import (
    IDEA_PROPOSAL_INTAKE_CERTIFICATION_BLOCKERS,
    IdeaProposalIntakeRequest,
    acknowledge_idea_proposal_intake,
)


def _payload() -> dict[str, object]:
    return {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_candidate_001",
        "conversion_intent_id": "conversion_intent_001",
        "intent_type": "REVIEW_FOR_ADVISORY_PROPOSAL",
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_candidate_001",
                "content_hash": "sha256:abc123",
            }
        ],
    }


def test_idea_proposal_intake_route_returns_source_safe_non_proposal_posture() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/advisory/proposals/idea-intake",
            json=_payload(),
            headers={"X-Correlation-Id": "corr-idea-proposal-001"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["intake_id"].startswith("ipi_")
    assert body["intake_status"] == "ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED"
    assert body["supportability_status"] == "not_certified"
    assert body["source_authority"] == "lotus-idea"
    assert body["proposal_authority"] == "lotus-advise"
    assert body["target_product"] == "lotus-advise:AdvisoryProposalLifecycleRecord:v1"
    assert body["route_existence_proven"] is True
    assert body["proposal_record_created"] is False
    assert body["suitability_authority_granted"] is False
    assert body["order_created"] is False
    assert body["client_publication_authorized"] is False
    assert body["certification_blockers"] == IDEA_PROPOSAL_INTAKE_CERTIFICATION_BLOCKERS
    assert body["correlation_id"] == "corr-idea-proposal-001"


def test_idea_proposal_intake_rejects_query_parameters() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/advisory/proposals/idea-intake?dry_run=true",
            json=_payload(),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: dry_run not supported for this endpoint"
    )


def test_idea_proposal_intake_domain_acknowledgement_is_deterministic() -> None:
    request = IdeaProposalIntakeRequest.model_validate(_payload())

    first = acknowledge_idea_proposal_intake(request, correlation_id="corr-a")
    second = acknowledge_idea_proposal_intake(request, correlation_id="corr-b")

    assert first.intake_id == second.intake_id
    assert first.proposal_record_created is False
    assert first.suitability_authority_granted is False
    assert first.order_created is False
    assert first.client_publication_authorized is False


def test_idea_proposal_intake_route_is_documented_in_openapi() -> None:
    app.openapi_schema = None
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    operation = openapi["paths"]["/advisory/proposals/idea-intake"]["post"]
    assert operation["summary"] == "Accept lotus-idea Proposal Intake Foundation"
    assert "does not grant suitability" in operation["description"]
    assert "202" in operation["responses"]
