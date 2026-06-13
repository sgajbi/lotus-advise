from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    SUPPORTED_CLAIM_CLASSIFICATIONS,
    AdvisoryBankDemoProofPack,
    AdvisoryDemoScenarioContract,
    AdvisorySupportedClaimRegister,
    ArtifactPolicy,
    BackendRuntimePosture,
    DemoScenarioStep,
    ProofAsset,
    RuntimeEndpointEvidence,
    SupportedClaim,
    SupportedClaimProofRequirement,
    normalize_runtime_base_url,
)
from src.core.common.canonical import hash_canonical_payload


def _proof_requirement() -> SupportedClaimProofRequirement:
    return SupportedClaimProofRequirement(
        requirement_id="backend-proof",
        evidence_ref="proof.assets.backend_summary",
    )


def _artifact_policy() -> ArtifactPolicy:
    return ArtifactPolicy(
        commit_allowed_access_classes=[
            "COMMIT_SAFE_SUMMARY",
            "CUSTOMER_CONSUMABLE_SUMMARY",
        ],
        local_only_access_classes=[
            "LOCAL_ONLY_RUNTIME_EVIDENCE",
            "SECRET_MATERIAL",
        ],
        sensitive_material_rules=[
            "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local.",
        ],
    )


def _implementation_backed_claim(claim_id: str = "advisor_journey_supported") -> SupportedClaim:
    return SupportedClaim(
        claim_id=claim_id,
        title="Advisor journey supported",
        classification="IMPLEMENTATION_BACKED",
        audiences=["BUSINESS_USER", "SALES", "CLIENT_DEMO"],
        allowed_materials=["WIKI", "DEMO_SCRIPT"],
        claim_text="Advisor cockpit and governed proof evidence are available for review.",
        evidence_refs=["proof.assets.backend_summary"],
        proof_requirements=[_proof_requirement()],
        wording_rules=["Do not claim external client communication."],
    )


def test_supported_claim_taxonomy_matches_platform_contract() -> None:
    assert SUPPORTED_CLAIM_CLASSIFICATIONS == (
        "IMPLEMENTATION_BACKED",
        "BACKEND_BACKED_UI_PENDING",
        "DEGRADED_SUPPORTED",
        "PLANNED_RFC",
        "UNSUPPORTED",
    )


def test_scenario_contract_requires_the_canonical_proof_marker() -> None:
    scenario = AdvisoryDemoScenarioContract(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        governed_as_of_date=date(2026, 5, 28),
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        required_evidence_markers=[RFC28_CANONICAL_PROOF_MARKER],
        required_source_products=["AdvisoryCopilotInteractionRecord:v1"],
        unsupported_boundaries=["CLIENT_READY_PUBLICATION_BLOCKED"],
        steps=[
            DemoScenarioStep(
                step_id="advisor_cockpit",
                title="Advisor opens cockpit",
                owner_repository="lotus-advise",
                required_evidence_refs=["cockpit.snapshot"],
                required_workbench_panels=["advisory.advisor_cockpit"],
            )
        ],
    )

    assert scenario.contract_name == "AdvisoryDemoScenarioContract"
    assert scenario.contract_version == "v1"

    with pytest.raises(ValidationError, match="proof_marker"):
        AdvisoryDemoScenarioContract(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            governed_as_of_date=date(2026, 5, 28),
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            required_evidence_markers=["OTHER_MARKER"],
            required_source_products=["AdvisoryCopilotInteractionRecord:v1"],
            unsupported_boundaries=["CLIENT_READY_PUBLICATION_BLOCKED"],
            steps=[
                DemoScenarioStep(
                    step_id="advisor_cockpit",
                    title="Advisor opens cockpit",
                    owner_repository="lotus-advise",
                )
            ],
        )


def test_scenario_contract_bounds_steps_and_refs() -> None:
    with pytest.raises(ValidationError, match="scenario step title"):
        DemoScenarioStep(
            step_id="unsafe_step",
            title="Raw prompt review",
            owner_repository="lotus-advise",
        )

    with pytest.raises(ValidationError, match="entries must be unique"):
        DemoScenarioStep(
            step_id="duplicate_refs",
            title="Advisor opens cockpit",
            owner_repository="lotus-advise",
            required_evidence_refs=["cockpit.snapshot", "cockpit.snapshot"],
        )

    with pytest.raises(ValidationError, match="step_id values must be unique"):
        AdvisoryDemoScenarioContract(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            governed_as_of_date=date(2026, 5, 28),
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            required_evidence_markers=[RFC28_CANONICAL_PROOF_MARKER],
            required_source_products=["AdvisoryCopilotInteractionRecord:v1"],
            unsupported_boundaries=["CLIENT_READY_PUBLICATION_BLOCKED"],
            steps=[
                DemoScenarioStep(
                    step_id="advisor_cockpit",
                    title="Advisor opens cockpit",
                    owner_repository="lotus-advise",
                ),
                DemoScenarioStep(
                    step_id="advisor_cockpit",
                    title="Advisor reviews proof",
                    owner_repository="lotus-advise",
                ),
            ],
        )

    with pytest.raises(ValidationError, match="unsupported_boundaries"):
        AdvisoryDemoScenarioContract(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            governed_as_of_date=date(2026, 5, 28),
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            required_evidence_markers=[RFC28_CANONICAL_PROOF_MARKER],
            required_source_products=["AdvisoryCopilotInteractionRecord:v1"],
            unsupported_boundaries=["Client output includes raw prompt material."],
            steps=[
                DemoScenarioStep(
                    step_id="advisor_cockpit",
                    title="Advisor opens cockpit",
                    owner_repository="lotus-advise",
                )
            ],
        )


def test_supported_claim_register_requires_evidence_and_unique_claim_ids() -> None:
    register = AdvisorySupportedClaimRegister(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        claims=[_implementation_backed_claim()],
        artifact_policy=_artifact_policy(),
    )

    assert register.contract_name == "AdvisorySupportedClaimRegister"
    assert register.claims[0].classification == "IMPLEMENTATION_BACKED"

    with pytest.raises(ValidationError, match="IMPLEMENTATION_BACKED claims require evidence"):
        SupportedClaim(
            claim_id="unsupported_evidence",
            title="Unsupported evidence",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="This should not be promotable.",
        )

    with pytest.raises(ValidationError, match="proof requirements must use declared evidence refs"):
        SupportedClaim(
            claim_id="invalid_requirement_ref",
            title="Invalid requirement ref",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["WIKI"],
            claim_text="Advisor proof evidence is available for review.",
            evidence_refs=["proof.assets.material_field_review"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError, match="claim_id values must be unique"):
        AdvisorySupportedClaimRegister(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            claims=[
                _implementation_backed_claim("duplicate"),
                _implementation_backed_claim("duplicate"),
            ],
            artifact_policy=_artifact_policy(),
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        SupportedClaim(
            claim_id="unsafe_claim_text",
            title="Unsafe claim text",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="Raw prompt evidence is available for client review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        SupportedClaim(
            claim_id="unsafe_provider_response",
            title="Unsafe provider response",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="Provider_response evidence is available for client review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        SupportedClaim(
            claim_id="unsafe_provider_output",
            title="Unsafe provider output",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="Provider_output and trace_id evidence are available for review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError):
        SupportedClaim(
            claim_id="x" * 161,
            title="Oversized claim id",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="Advisor proof evidence is available for review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )


def test_supported_claim_register_bounds_taxonomy_and_policy_lists() -> None:
    with pytest.raises(ValidationError, match="taxonomy lists must be unique"):
        SupportedClaim(
            claim_id="duplicate_audience",
            title="Duplicate audience",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES", "SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="Advisor proof evidence is available for review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError, match="cannot target client demos"):
        SupportedClaim(
            claim_id="ui_pending_client_demo",
            title="UI pending client demo",
            classification="BACKEND_BACKED_UI_PENDING",
            audiences=["CLIENT_DEMO"],
            allowed_materials=["WIKI"],
            claim_text="Advisor proof evidence is available for review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError, match="cannot use client-facing materials"):
        SupportedClaim(
            claim_id="ui_pending_product_one_pager",
            title="UI pending product one pager",
            classification="BACKEND_BACKED_UI_PENDING",
            audiences=["PRE_SALES"],
            allowed_materials=["PRODUCT_ONE_PAGER"],
            claim_text="Advisor proof evidence is available for review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )

    with pytest.raises(ValidationError, match="entries must be unique"):
        SupportedClaim(
            claim_id="duplicate_wording",
            title="Duplicate wording",
            classification="IMPLEMENTATION_BACKED",
            audiences=["SALES"],
            allowed_materials=["DEMO_SCRIPT"],
            claim_text="Advisor proof evidence is available for review.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
            wording_rules=[
                "Do not claim external client communication.",
                "Do not claim external client communication.",
            ],
        )

    with pytest.raises(ValidationError, match="access classes must be unique"):
        ArtifactPolicy(
            commit_allowed_access_classes=[
                "COMMIT_SAFE_SUMMARY",
                "COMMIT_SAFE_SUMMARY",
            ],
            local_only_access_classes=["LOCAL_ONLY_RUNTIME_EVIDENCE"],
            sensitive_material_rules=[
                "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local.",
            ],
        )

    with pytest.raises(ValidationError, match="sensitive material rules must be unique"):
        ArtifactPolicy(
            commit_allowed_access_classes=["COMMIT_SAFE_SUMMARY"],
            local_only_access_classes=["LOCAL_ONLY_RUNTIME_EVIDENCE"],
            sensitive_material_rules=[
                "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local.",
                "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local.",
            ],
        )


def test_planned_unsupported_and_ui_pending_claims_cannot_use_client_materials() -> None:
    with pytest.raises(ValidationError, match="cannot be client-facing"):
        SupportedClaim(
            claim_id="planned_external_certification",
            title="External certification",
            classification="PLANNED_RFC",
            audiences=["RFP_SECURITY"],
            allowed_materials=["RFP_RESPONSE"],
            claim_text="External certification is planned.",
        )

    with pytest.raises(ValidationError, match="cannot be client-facing"):
        SupportedClaim(
            claim_id="unsupported_security_pack",
            title="Unsupported security pack",
            classification="UNSUPPORTED",
            audiences=["RFP_SECURITY"],
            allowed_materials=["PRODUCT_ONE_PAGER"],
            claim_text="External security pack publication is not supported.",
        )

    with pytest.raises(ValidationError, match="cannot use screenshots"):
        SupportedClaim(
            claim_id="backend_only_claim",
            title="Backend proof available",
            classification="BACKEND_BACKED_UI_PENDING",
            audiences=["DEVELOPER"],
            allowed_materials=["SCREENSHOT"],
            claim_text="Backend proof is available, but UI is pending.",
            evidence_refs=["proof.assets.backend_summary"],
            proof_requirements=[_proof_requirement()],
        )


def test_proof_pack_indexes_assets_and_blocks_sensitive_committed_material() -> None:
    proof_pack = AdvisoryBankDemoProofPack(
        proof_pack_id="proof_pack_rfc28_001",
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        generated_at=datetime(2026, 5, 28, 9, 0, tzinfo=UTC),
        correlation_id="corr_rfc28_001",
        client_ready_posture="CLIENT_READY_PUBLICATION_BLOCKED",
        repository_shas={"lotus-advise": "abc123"},
        evidence_markers=[RFC28_CANONICAL_PROOF_MARKER],
        scenario_contract_ref="lotus-advise://contracts/rfc0028/scenario.v1.json",
        supported_claim_register_ref="lotus-advise://contracts/rfc0028/claims.v1.json",
        source_product_refs=["AdvisoryCopilotInteractionRecord:v1"],
        assets=[
            ProofAsset(
                asset_id="backend_summary",
                asset_type="API_RESPONSE_SUMMARY",
                source_repository="lotus-advise",
                uri="output/rfc0028/sanitized-summary.json",
                access_class="COMMIT_SAFE_SUMMARY",
                retention_class="COMMIT_SOURCE",
                evidence_refs=["advisor_journey_supported"],
                content_hash=hash_canonical_payload({"asset": "summary"}),
                commit_allowed=True,
            )
        ],
        unsupported_boundaries=["CLIENT_READY_PUBLICATION_BLOCKED"],
    )

    assert proof_pack.contract_name == "AdvisoryBankDemoProofPack"
    assert proof_pack.assets[0].commit_allowed is True

    with pytest.raises(ValidationError, match="proof_marker"):
        AdvisoryBankDemoProofPack(
            **{**proof_pack.model_dump(), "evidence_markers": ["OTHER_MARKER"]}
        )

    with pytest.raises(ValidationError, match="cannot be commit_allowed"):
        ProofAsset(
            asset_id="raw_runtime",
            asset_type="LOCAL_RUNTIME_BUNDLE",
            source_repository="lotus-workbench",
            uri="output/rfc0028/raw-runtime.json",
            access_class="LOCAL_ONLY_RUNTIME_EVIDENCE",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            commit_allowed=True,
        )

    with pytest.raises(ValidationError, match="commit-safe access class"):
        ProofAsset(
            asset_id="restricted_summary",
            asset_type="API_RESPONSE_SUMMARY",
            source_repository="lotus-advise",
            uri="output/rfc0028/restricted-summary.json",
            access_class="RESTRICTED_CUSTOMER_EVIDENCE",
            retention_class="COMMIT_SOURCE",
            content_hash=hash_canonical_payload({"asset": "restricted"}),
            commit_allowed=True,
        )

    with pytest.raises(ValidationError, match="COMMIT_SOURCE retention"):
        ProofAsset(
            asset_id="local_retention_summary",
            asset_type="API_RESPONSE_SUMMARY",
            source_repository="lotus-advise",
            uri="output/rfc0028/local-retention-summary.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            content_hash=hash_canonical_payload({"asset": "local-retention"}),
            commit_allowed=True,
        )

    with pytest.raises(ValidationError, match="require a content_hash"):
        ProofAsset(
            asset_id="unhashed_summary",
            asset_type="API_RESPONSE_SUMMARY",
            source_repository="lotus-advise",
            uri="output/rfc0028/unhashed-summary.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="COMMIT_SOURCE",
            commit_allowed=True,
        )

    with pytest.raises(ValidationError, match="must not include URL"):
        ProofAsset(
            asset_id="unsafe_uri",
            asset_type="LOCAL_RUNTIME_BUNDLE",
            source_repository="lotus-advise",
            uri="output/rfc0028/raw-runtime.json?token=should-not-leak",
            access_class="LOCAL_ONLY_RUNTIME_EVIDENCE",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            commit_allowed=False,
        )

    with pytest.raises(ValidationError, match="lotus-advise logical contract reference"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "scenario_contract_ref": "https://example.invalid/rfc0028/scenario.json",
            }
        )

    with pytest.raises(ValidationError, match="credentials, query, or fragment"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "supported_claim_register_ref": (
                    "lotus-advise://rfc0028/supported-claim-register.v1.json?token=leak"
                ),
            }
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "scenario_contract_ref": "lotus-advise://rfc0028/secret-contract.json",
            }
        )

    with pytest.raises(ValidationError, match="parent-directory traversal"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "supported_claim_register_ref": (
                    "lotus-advise://rfc0028/../supported-claim-register.v1.json"
                ),
            }
        )

    with pytest.raises(ValidationError, match="control characters"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "scenario_contract_ref": "lotus-advise://rfc0028/scenario.v1.json\x00leak",
            }
        )

    with pytest.raises(ValidationError, match="must include a contract path"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "supported_claim_register_ref": "lotus-advise://rfc0028",
            }
        )

    with pytest.raises(ValidationError, match="canonical sha256 digest"):
        ProofAsset(
            asset_id="bad_hash",
            asset_type="API_RESPONSE_SUMMARY",
            source_repository="lotus-advise",
            uri="output/rfc0028/summary.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            content_hash="sha256:not-real",
            commit_allowed=False,
        )

    with pytest.raises(ValidationError, match="repository sha cannot contain sensitive"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "repository_shas": {"lotus-advise": "token=should-not-leak"},
            }
        )

    with pytest.raises(ValidationError):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "client_ready_posture": "CLIENT_READY_APPROVED",
            }
        )

    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "generated_at": datetime(
                    2026,
                    5,
                    28,
                    9,
                    0,
                    tzinfo=timezone(timedelta(hours=1)),
                ),
            }
        )

    with pytest.raises(ValidationError, match="repository name cannot contain sensitive"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "repository_shas": {"secret-repository": "abc123"},
            }
        )

    with pytest.raises(ValidationError, match="repository names must be unique"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "repository_shas": {
                    "lotus-advise": "abc123",
                    " lotus-advise ": "def456",
                },
            }
        )

    with pytest.raises(ValidationError, match="asset ids must be unique"):
        AdvisoryBankDemoProofPack(
            **{
                **proof_pack.model_dump(),
                "assets": [proof_pack.assets[0], proof_pack.assets[0]],
            }
        )


def test_runtime_posture_blocks_secret_urls_and_sanitizes_probe_summaries() -> None:
    posture = BackendRuntimePosture(
        base_url="https://advise.dev.lotus:8443/runtime/",
        environment="local",
        endpoints=[
            RuntimeEndpointEvidence(
                endpoint="/platform/capabilities",
                http_status=200,
                posture="READY",
                latency_ms=12,
                summary={
                    "status": "ok",
                    "feature_keys": ["advisory.bank_demo_proof"],
                    "Authorization": "Bearer should-not-leak",
                    "degraded_reasons": [
                        "see https://advise.dev.lotus/ready?token=should-not-leak#fragment"
                    ],
                    "diagnostics": {
                        "trace_id": "trace-123",
                        "trace id": "trace-456",
                        "correlation-id": "corr-789",
                        "safe": "runtime capability summary",
                    },
                },
            )
        ],
    )

    endpoint = posture.endpoints[0]
    assert posture.base_url == "https://advise.dev.lotus:8443/runtime"
    assert endpoint.latency_ms == 12
    assert endpoint.summary["Authorization"] == "[REDACTED]"
    assert endpoint.summary["diagnostics"]["trace_id"] == "[REDACTED]"
    assert endpoint.summary["diagnostics"]["trace id"] == "[REDACTED]"
    assert endpoint.summary["diagnostics"]["correlation-id"] == "[REDACTED]"
    assert "token" not in endpoint.summary["degraded_reasons"][0]
    assert endpoint.summary["diagnostics"]["safe"] == "runtime capability summary"

    with pytest.raises(ValidationError, match="credentials, query, or fragment"):
        BackendRuntimePosture(
            base_url="https://user:secret@advise.dev.lotus/health?token=abc",
            environment="local",
            endpoints=[RuntimeEndpointEvidence(endpoint="/health", posture="READY", summary={})],
        )

    with pytest.raises(ValidationError, match="path without query or fragment"):
        RuntimeEndpointEvidence(endpoint="/health?token=abc", posture="READY", summary={})


def test_runtime_base_url_normalization_preserves_safe_runtime_location() -> None:
    assert (
        normalize_runtime_base_url(" https://ADVISE.dev.lotus:8443/runtime/ ")
        == "https://advise.dev.lotus:8443/runtime"
    )
    assert normalize_runtime_base_url("http://localhost:8080/") == "http://localhost:8080"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (" ", "present and bounded"),
        ("ftp://advise.dev.lotus", "http\\(s\\) URL with a host"),
        ("https:///runtime", "http\\(s\\) URL with a host"),
        ("https://user:secret@advise.dev.lotus", "credentials, query, or fragment"),
        ("https://advise.dev.lotus?token=abc", "credentials, query, or fragment"),
        ("https://advise.dev.lotus#token=abc", "credentials, query, or fragment"),
    ],
)
def test_runtime_base_url_normalization_rejects_unsafe_or_malformed_values(
    value: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_runtime_base_url(value)


def test_runtime_posture_redacts_sensitive_values_in_neutral_summary_fields() -> None:
    endpoint = RuntimeEndpointEvidence(
        endpoint="/health/ready",
        http_status=503,
        posture="DEGRADED",
        summary={
            "detail": "Dependency returned Authorization: Bearer should-not-leak",
            "message": "token=should-not-leak",
            "provider": "Provider output included internal model detail.",
            "error": "Traceback (most recent call last): File C:/Users/local/app.py",
            "safe": "readiness check degraded",
        },
    )

    assert endpoint.summary["detail"] == "[REDACTED]"
    assert endpoint.summary["message"] == "[REDACTED]"
    assert endpoint.summary["provider"] == "[REDACTED]"
    assert endpoint.summary["error"] == "[REDACTED]"
    assert endpoint.summary["safe"] == "readiness check degraded"


def test_bank_demo_model_facade_preserves_focused_model_ownership() -> None:
    assert AdvisoryDemoScenarioContract.__module__.endswith(".scenario_models")
    assert DemoScenarioStep.__module__.endswith(".scenario_models")
    assert AdvisorySupportedClaimRegister.__module__.endswith(".supported_claim_models")
    assert SupportedClaim.__module__.endswith(".supported_claim_models")
    assert ArtifactPolicy.__module__.endswith(".supported_claim_models")
    assert ProofAsset.__module__.endswith(".proof_asset_models")
    assert AdvisoryBankDemoProofPack.__module__.endswith(".proof_pack_models")


def test_bank_demo_internal_modules_import_focused_models_not_facade() -> None:
    bank_demo_dir = Path("src/core/bank_demo_proof")
    internal_modules = [
        path for path in bank_demo_dir.glob("*.py") if path.name not in {"__init__.py", "models.py"}
    ]

    for path in internal_modules:
        assert "from src.core.bank_demo_proof.models import" not in path.read_text(
            encoding="utf-8"
        ), path
