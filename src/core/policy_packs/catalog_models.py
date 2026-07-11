from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PolicyPackActivationState = Literal["DRAFT", "ACTIVE", "SUPERSEDED", "DISABLED"]
PolicyPackValidationStatus = Literal["READY", "BLOCKED"]
PolicyPackEventType = Literal["POLICY_PACK_VALIDATED", "POLICY_PACK_ACTIVATED"]


class PolicyPackAuditEvent(BaseModel):
    event_id: str = Field(
        description="Deterministic audit event identifier for policy-pack catalog activity.",
        examples=["ppev_001"],
    )
    event_type: PolicyPackEventType = Field(
        description="Policy-pack catalog event type.",
        examples=["POLICY_PACK_VALIDATED"],
    )
    policy_pack_id: str = Field(
        description="Policy pack identifier.",
        examples=["SG_PRIVATE_BANKING_REFERENCE"],
    )
    policy_version: str = Field(
        description="Policy pack version.",
        examples=["2026.05"],
    )
    actor_id: str = Field(
        description="Actor that requested the validation or activation event.",
        examples=["policy_steward_1"],
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp for the event.",
        examples=["2026-05-26T01:00:00+00:00"],
    )
    content_hash: str = Field(
        description="Canonical hash of the source policy-pack definition at event time.",
        examples=["sha256:policy-pack-content"],
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Idempotency key supplied for replay-safe command handling.",
        examples=["activate-sg-reference-001"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured reason, diagnostics, and maker-checker posture for the event.",
        examples=[{"validation_status": "READY"}],
    )


class PolicyPackSummary(BaseModel):
    policy_pack_id: str = Field(
        description="Stable policy pack identifier.",
        examples=["GLOBAL_PRIVATE_BANKING_BASELINE"],
    )
    policy_version: str = Field(description="Policy pack version.", examples=["2026.05"])
    policy_family: str = Field(
        description="Policy family represented by this pack.",
        examples=["GLOBAL_PRIVATE_BANKING"],
    )
    display_name: str = Field(
        description="Advisor and operator friendly policy-pack name.",
        examples=["Global Private Banking Baseline"],
    )
    activation_state: PolicyPackActivationState = Field(
        description=(
            "Current activation posture of this immutable policy-pack version. Exactly one "
            "version per policy pack may be ACTIVE; activating a newer version supersedes the "
            "prior active version."
        ),
        examples=["ACTIVE"],
    )
    reference_posture: str = Field(
        description="Reference-pack posture and legal-advice boundary.",
        examples=["REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE"],
    )
    maker_checker_required: bool = Field(
        description="Whether activation requires a checker different from the validator.",
        examples=[True],
    )
    content_hash: str = Field(
        description="Canonical hash of the source policy-pack definition.",
        examples=["sha256:policy-pack-content"],
    )


class PolicyPackDetailResponse(BaseModel):
    policy_pack: PolicyPackSummary = Field(description="Policy pack metadata.")
    applicability: dict[str, Any] = Field(
        description=(
            "Applicability selectors for jurisdiction, booking, legal entity, client segment, "
            "and product scope."
        ),
        examples=[{"jurisdiction_scope": ["SG"]}],
    )
    source_requirements: list[str] = Field(
        description=(
            "Source-owned evidence required before later policy evaluation may claim outcomes."
        ),
        examples=[["client_classification", "risk_policy_metrics"]],
    )
    rules: list[dict[str, Any]] = Field(
        description="Rule summaries and required evidence. These are not legal advice.",
        examples=[[{"rule_id": "SG_AI_COMPLEX_PRODUCT_REVIEW"}]],
    )
    disclosure_templates: list[dict[str, Any]] = Field(
        description="Versioned disclosure template summaries for later review/sign-off flows.",
        examples=[[{"template_id": "SG_COMPLEX_PRODUCT_DISCLOSURE"}]],
    )
    consent_templates: list[dict[str, Any]] = Field(
        description="Versioned consent template summaries for later review/sign-off flows.",
        examples=[[{"template_id": "SG_COMPLEX_PRODUCT_CONSENT"}]],
    )
    approval_routes: list[dict[str, Any]] = Field(
        description="Configured approval route summaries for later policy result mapping.",
        examples=[[{"route_id": "INVESTMENT_COUNSELLOR_REVIEW"}]],
    )
    sample_fixture_refs: list[str] = Field(
        description="Synthetic sample fixtures used for dry-run validation.",
        examples=[["fixtures/policy-packs/sg-private-banking-reference.json"]],
    )
    supportability: dict[str, Any] = Field(
        description="Current RFC-0025 support boundary for this policy pack.",
        examples=[
            {
                "policy_evaluation_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API",
                "gateway_supported": True,
                "gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF",
                "client_ready_publication": "BLOCKED",
            }
        ],
    )
    audit_events: list[PolicyPackAuditEvent] = Field(
        default_factory=list,
        description="Append-only validation and activation audit events for this pack version.",
    )


class PolicyPackListResponse(BaseModel):
    items: list[PolicyPackSummary] = Field(
        description="Policy pack versions visible to the caller.",
        examples=[[{"policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE"}]],
    )
    catalog_posture: dict[str, Any] = Field(
        description="Catalog support posture and RFC-0025 boundary.",
        examples=[
            {
                "policy_catalog": "SUPPORTED_BY_RFC0025_SLICE5",
                "workbench_supported": True,
                "workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI",
                "client_ready_publication": "BLOCKED",
            }
        ],
    )


class PolicyPackValidationRequest(BaseModel):
    requested_by: str = Field(
        description=(
            "Compatibility actor echo for policy-pack validation. The route authorizes and records "
            "the trusted principal from policy-control headers and rejects a mismatch."
        ),
        examples=["policy_steward_1"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured validation reason retained in audit evidence.",
        examples=[{"purpose": "pre-activation validation"}],
    )


class PolicyPackValidationResponse(BaseModel):
    policy_pack: PolicyPackSummary = Field(description="Validated policy pack metadata.")
    validation_status: PolicyPackValidationStatus = Field(
        description="Validation result for this policy-pack version.",
        examples=["READY"],
    )
    diagnostics: list[str] = Field(
        description="Validation diagnostics. Empty when validation is ready.",
        examples=[["RULE_ID_NOT_UPPER_SNAKE_CASE"]],
    )
    validation_event: PolicyPackAuditEvent = Field(
        description="Append-only validation audit event."
    )
    replayed: bool = Field(
        description="Whether this response replayed a prior idempotent validation event.",
        examples=[False],
    )


class PolicyPackActivationRequest(BaseModel):
    activated_by: str = Field(
        description=(
            "Compatibility actor echo for policy-pack activation. The route authorizes and records "
            "the trusted policy checker from policy-control headers and rejects a mismatch."
        ),
        examples=["policy_checker_1"],
    )
    source_content_hash: str = Field(
        description="Expected canonical content hash from the validated policy pack.",
        examples=["sha256:policy-pack-content"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured activation reason retained in audit evidence.",
        examples=[{"purpose": "activate SG private banking reference pack"}],
    )


class PolicyPackActivationResponse(BaseModel):
    policy_pack: PolicyPackSummary = Field(description="Policy pack metadata after activation.")
    activation_event: PolicyPackAuditEvent = Field(
        description=(
            "Append-only activation audit event. The reason payload identifies the previous "
            "active version, resulting active version, actor, idempotency key, and timestamp."
        )
    )
    replayed: bool = Field(
        description="Whether this response replayed a prior idempotent activation event.",
        examples=[False],
    )
