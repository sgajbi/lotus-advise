from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

IdeaProposalIntakeStatus = Literal["ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED"]
IdeaProposalIntakeSupportabilityStatus = Literal["not_certified"]
IdeaProposalIntentType = Literal[
    "REVIEW_FOR_ADVISORY_PROPOSAL",
    "CREATE_ADVISORY_PROPOSAL_DRAFT",
]

IDEA_PROPOSAL_INTAKE_CERTIFICATION_BLOCKERS = [
    "suitability_policy_authority_remains_lotus_advise",
    "advisory_proposal_creation_not_certified",
    "proposal_lifecycle_persistence_not_certified",
    "client_publication_authority_blocked",
]

IDEA_PROPOSAL_INTAKE_REQUEST_EXAMPLE: dict[str, Any] = {
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

IDEA_PROPOSAL_INTAKE_RESPONSE_EXAMPLE: dict[str, Any] = {
    "intake_id": "ipi_7a1d2b3c4d5e",
    "intake_status": "ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED",
    "supportability_status": "not_certified",
    "source_authority": "lotus-idea",
    "proposal_authority": "lotus-advise",
    "target_product": "lotus-advise:AdvisoryProposalLifecycleRecord:v1",
    "route_existence_proven": True,
    "proposal_record_created": False,
    "suitability_authority_granted": False,
    "order_created": False,
    "client_publication_authorized": False,
    "certification_blockers": IDEA_PROPOSAL_INTAKE_CERTIFICATION_BLOCKERS,
    "evidence_refs": [
        "contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
        "src/api/proposals/routes_idea_intake.py",
        "src/core/proposals/idea_proposal_intake.py",
    ],
    "received_at": "2026-06-21T10:10:00+00:00",
    "correlation_id": "corr-idea-proposal-001",
}

IDEA_PROPOSAL_INTAKE_ERROR_EXAMPLE: dict[str, Any] = {
    "detail": "UNSUPPORTED_QUERY_PARAMETER: dry_run not supported for this endpoint"
}


class IdeaProposalSourceRef(BaseModel):
    source_system: Literal["lotus-idea"] = Field(
        description="Source system that owns the referenced opportunity evidence.",
        examples=["lotus-idea"],
    )
    source_type: str = Field(
        min_length=1,
        max_length=96,
        description="Source-owned evidence type or product name.",
        examples=["IdeaCandidate"],
    )
    source_id: str = Field(
        min_length=1,
        max_length=160,
        description=(
            "Source-owned identifier. Advise does not infer portfolio, account, client, or "
            "product facts from this value."
        ),
        examples=["idea_candidate_001"],
    )
    content_hash: str | None = Field(
        default=None,
        max_length=160,
        description="Optional source-owned content hash for replay and lineage checks.",
        examples=["sha256:abc123"],
    )

    @field_validator("source_type", "source_id", "content_hash")
    @classmethod
    def _trim_source_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("IDEA_PROPOSAL_SOURCE_REF_REQUIRED")
        return trimmed


class IdeaProposalIntakeRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_PROPOSAL_INTAKE_REQUEST_EXAMPLE}}

    source_system: Literal["lotus-idea"] = Field(
        description="Producer system submitting the reviewed opportunity handoff.",
        examples=["lotus-idea"],
    )
    source_product: Literal["lotus-idea:IdeaCandidate:v1"] = Field(
        description="Source data product represented by the handoff.",
        examples=["lotus-idea:IdeaCandidate:v1"],
    )
    idea_candidate_id: str = Field(
        min_length=1,
        max_length=160,
        description=(
            "lotus-idea candidate identifier. Advise uses it only for source-safe lineage and "
            "does not infer advisory suitability from it."
        ),
        examples=["idea_candidate_001"],
    )
    conversion_intent_id: str = Field(
        min_length=1,
        max_length=160,
        description="lotus-idea conversion-intent identifier used for deterministic intake proof.",
        examples=["conversion_intent_001"],
    )
    intent_type: IdeaProposalIntentType = Field(
        description=(
            "Requested advisory-side intake posture. This route acknowledges only the handoff "
            "foundation and does not create proposal lifecycle state or suitability evidence."
        ),
        examples=["REVIEW_FOR_ADVISORY_PROPOSAL"],
    )
    source_refs: list[IdeaProposalSourceRef] = Field(
        min_length=1,
        max_length=16,
        description="Source-safe idea evidence references supplied by lotus-idea.",
    )

    @field_validator("idea_candidate_id", "conversion_intent_id")
    @classmethod
    def _trim_required_identifier(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("IDEA_PROPOSAL_IDENTIFIER_REQUIRED")
        return trimmed


class IdeaProposalIntakeResponse(BaseModel):
    model_config = {"json_schema_extra": {"example": IDEA_PROPOSAL_INTAKE_RESPONSE_EXAMPLE}}

    intake_id: str = Field(
        description="Deterministic source-safe intake identifier derived from handoff fields.",
        examples=["ipi_7a1d2b3c4d5e"],
    )
    intake_status: IdeaProposalIntakeStatus = Field(
        description="Bounded route-foundation status; not an advisory proposal status.",
        examples=["ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED"],
    )
    supportability_status: IdeaProposalIntakeSupportabilityStatus = Field(
        description="Certification posture for this route foundation.",
        examples=["not_certified"],
    )
    source_authority: Literal["lotus-idea"] = Field(
        description="Source authority for idea candidate and conversion-intent evidence.",
        examples=["lotus-idea"],
    )
    proposal_authority: Literal["lotus-advise"] = Field(
        description="Advisory proposal and suitability authority retained by lotus-advise.",
        examples=["lotus-advise"],
    )
    target_product: Literal["lotus-advise:AdvisoryProposalLifecycleRecord:v1"] = Field(
        description="Advise-owned product that future certified realization may update.",
        examples=["lotus-advise:AdvisoryProposalLifecycleRecord:v1"],
    )
    route_existence_proven: bool = Field(
        description="True because this route exists and is covered by contract tests.",
        examples=[True],
    )
    proposal_record_created: bool = Field(
        description="False until a later certified advisory proposal realization persists one.",
        examples=[False],
    )
    suitability_authority_granted: bool = Field(
        description="False; this route does not run suitability or approve advisory use.",
        examples=[False],
    )
    order_created: bool = Field(
        description="False; no order, OMS instruction, fill, or settlement evidence is created.",
        examples=[False],
    )
    client_publication_authorized: bool = Field(
        description="False; this route does not authorize client communication or publication.",
        examples=[False],
    )
    certification_blockers: list[str] = Field(
        description="Remaining blockers before this route can support certified realization.",
        examples=[IDEA_PROPOSAL_INTAKE_CERTIFICATION_BLOCKERS],
    )
    evidence_refs: list[str] = Field(
        description="Implementation and contract evidence references for the route foundation.",
    )
    received_at: str = Field(
        description="UTC timestamp when the handoff envelope was acknowledged.",
        examples=["2026-06-21T10:10:00+00:00"],
    )
    correlation_id: str = Field(
        description="Caller or generated correlation id for source-safe operational tracing.",
        examples=["corr-idea-proposal-001"],
    )


def acknowledge_idea_proposal_intake(
    request: IdeaProposalIntakeRequest,
    *,
    correlation_id: str,
    received_at: datetime | None = None,
) -> IdeaProposalIntakeResponse:
    timestamp = received_at or datetime.now(timezone.utc)
    intake_id = _intake_id(
        idea_candidate_id=request.idea_candidate_id,
        conversion_intent_id=request.conversion_intent_id,
        intent_type=request.intent_type,
    )
    return IdeaProposalIntakeResponse(
        intake_id=intake_id,
        intake_status="ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED",
        supportability_status="not_certified",
        source_authority="lotus-idea",
        proposal_authority="lotus-advise",
        target_product="lotus-advise:AdvisoryProposalLifecycleRecord:v1",
        route_existence_proven=True,
        proposal_record_created=False,
        suitability_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        certification_blockers=list(IDEA_PROPOSAL_INTAKE_CERTIFICATION_BLOCKERS),
        evidence_refs=[
            "contracts/idea-proposal-intake/lotus-advise-idea-proposal-intake.v1.json",
            "src/api/proposals/routes_idea_intake.py",
            "src/core/proposals/idea_proposal_intake.py",
        ],
        received_at=timestamp.isoformat(),
        correlation_id=correlation_id,
    )


def _intake_id(*, idea_candidate_id: str, conversion_intent_id: str, intent_type: str) -> str:
    digest = sha256(
        f"{idea_candidate_id}|{conversion_intent_id}|{intent_type}".encode()
    ).hexdigest()
    return f"ipi_{digest[:12]}"
