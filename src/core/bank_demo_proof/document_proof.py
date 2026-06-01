from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.validation import (
    normalize_required_rfc28_text,
    normalize_rfc28_business_text,
)

DocumentProofFamily = Literal["PROPOSAL_MEMO", "POLICY_SIGN_OFF"]
DocumentProofClaimPosture = Literal["ADVISOR_USE_SUPPORTED", "CLIENT_READY_BLOCKED"]
_RFC28_DOCUMENT_STATUS_MAX_LENGTH = 120
_RFC28_DOCUMENT_DEGRADED_REASON_MAX_LENGTH = 512
_RFC28_DOCUMENT_FORMAT_MAX_ITEMS = 8
_RFC28_SUPPORTED_DOCUMENT_FORMATS = {"pdf", "docx", "html"}


class AdvisoryDocumentProof(BaseModel):
    document_family: DocumentProofFamily = Field(
        description="Document/evidence family proven by the backend proof pack."
    )
    claim_posture: DocumentProofClaimPosture = Field(
        description="Whether the document proof is advisor-use supported or client-ready blocked."
    )
    report_status: str = Field(description="Observed report status.")
    report_package_status: str = Field(description="Observed report package status.")
    requested_output_formats: list[str] = Field(
        min_length=1,
        max_length=_RFC28_DOCUMENT_FORMAT_MAX_ITEMS,
        description="Requested deterministic report output formats.",
    )
    render_ref_status: str = Field(description="Bounded render reference status.")
    archive_ref_status: str = Field(description="Bounded archive reference status.")
    archive_retention_posture: str = Field(description="Archive retention ownership posture.")
    archive_legal_hold_posture: str = Field(description="Archive legal-hold ownership posture.")
    archive_access_audit_ref_status: str = Field(
        description="Bounded archive access-audit reference status."
    )
    client_ready_document_status: str = Field(description="Client-ready document request posture.")
    degraded_reason: str | None = Field(
        default=None,
        max_length=_RFC28_DOCUMENT_DEGRADED_REASON_MAX_LENGTH,
        description="Bounded degraded reason when report/render/archive is unavailable.",
    )

    @field_validator(
        "report_status",
        "report_package_status",
        "render_ref_status",
        "archive_ref_status",
        "archive_retention_posture",
        "archive_legal_hold_posture",
        "archive_access_audit_ref_status",
        "client_ready_document_status",
    )
    @classmethod
    def _status_fields_must_be_bounded(cls, value: str) -> str:
        return normalize_rfc28_business_text(
            value,
            field_name="document proof status",
            max_length=_RFC28_DOCUMENT_STATUS_MAX_LENGTH,
        )

    @field_validator("requested_output_formats")
    @classmethod
    def _requested_formats_must_be_supported(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            output_format = normalize_required_rfc28_text(
                str(item),
                field_name="requested output format",
            ).lower()
            if output_format not in _RFC28_SUPPORTED_DOCUMENT_FORMATS:
                raise ValueError("requested output format is not supported")
            normalized.append(output_format)
        if len(set(normalized)) != len(normalized):
            raise ValueError("requested output formats must be unique")
        return normalized

    @field_validator("degraded_reason")
    @classmethod
    def _degraded_reason_must_be_business_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_rfc28_business_text(
            value,
            field_name="document degraded reason",
            max_length=_RFC28_DOCUMENT_DEGRADED_REASON_MAX_LENGTH,
        )

    @model_validator(mode="after")
    def _client_ready_and_archive_posture_must_be_truthful(self) -> AdvisoryDocumentProof:
        if self.claim_posture == "CLIENT_READY_BLOCKED":
            if "NOT_SUPPORTED" not in self.client_ready_document_status:
                raise ValueError("CLIENT_READY_BLOCKED requires a NOT_SUPPORTED document status")
        if self.report_package_status == "ARCHIVED":
            expected = {
                self.render_ref_status,
                self.archive_ref_status,
                self.archive_access_audit_ref_status,
            }
            if expected != {"RECORDED"}:
                raise ValueError("ARCHIVED report packages require recorded render/archive refs")
            if self.archive_retention_posture != "OWNED_BY_LOTUS_ARCHIVE":
                raise ValueError("ARCHIVED report packages require lotus-archive retention posture")
            if self.archive_legal_hold_posture != "OWNED_BY_LOTUS_ARCHIVE":
                raise ValueError(
                    "ARCHIVED report packages require lotus-archive legal-hold posture"
                )
        return self


class AdvisoryDocumentProofSummary(BaseModel):
    contract_name: Literal["AdvisoryDocumentProofSummary"] = Field(
        default="AdvisoryDocumentProofSummary"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(description="RFC-0028 scenario identifier.")
    primary_portfolio_id: str = Field(description="Canonical portfolio identifier.")
    proof_marker: str = Field(description="Proof marker that must be included in the proof pack.")
    client_ready_publication: Literal["BLOCKED"] = Field(default="BLOCKED")
    documents: list[AdvisoryDocumentProof] = Field(
        min_length=1,
        max_length=_RFC28_DOCUMENT_FORMAT_MAX_ITEMS,
        description="Document proof rows included in the RFC-0028 proof pack.",
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _summary_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_rfc28_business_text(
            value,
            field_name="document proof summary field",
            max_length=_RFC28_DOCUMENT_STATUS_MAX_LENGTH,
        )

    @model_validator(mode="after")
    def _document_families_must_be_unique(self) -> AdvisoryDocumentProofSummary:
        families = [document.document_family for document in self.documents]
        if len(set(families)) != len(families):
            raise ValueError("document proof families must be unique")
        return self


def build_document_proof_summary(
    live_runtime_payload: dict[str, Any],
) -> AdvisoryDocumentProofSummary:
    parity = _dict_at(live_runtime_payload, "parity")
    return AdvisoryDocumentProofSummary(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        documents=[
            _document_from_snapshot(
                _dict_at(parity, "proposal_memo"),
                document_family="PROPOSAL_MEMO",
                client_ready_key="client_ready_document_block_status",
            ),
            _document_from_snapshot(
                _dict_at(parity, "proposal_policy"),
                document_family="POLICY_SIGN_OFF",
                client_ready_key="client_ready_document_block_status",
            ),
        ],
    )


def _document_from_snapshot(
    snapshot: dict[str, Any],
    *,
    document_family: DocumentProofFamily,
    client_ready_key: str,
) -> AdvisoryDocumentProof:
    client_ready_status = str(_required_value_at(snapshot, client_ready_key))
    return AdvisoryDocumentProof(
        document_family=document_family,
        claim_posture="CLIENT_READY_BLOCKED",
        report_status=str(_required_value_at(snapshot, "report_status")),
        report_package_status=str(_required_value_at(snapshot, "report_package_status")),
        requested_output_formats=_requested_output_formats_from_snapshot(snapshot),
        render_ref_status=str(_required_value_at(snapshot, "render_ref_status")),
        archive_ref_status=str(_required_value_at(snapshot, "archive_ref_status")),
        archive_retention_posture=str(_required_value_at(snapshot, "archive_retention_posture")),
        archive_legal_hold_posture=str(_required_value_at(snapshot, "archive_legal_hold_posture")),
        archive_access_audit_ref_status=str(
            _required_value_at(snapshot, "archive_access_audit_ref_status")
        ),
        client_ready_document_status=client_ready_status,
        degraded_reason=snapshot.get("report_degraded_reason"),
    )


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"RFC0028_DOCUMENT_PROOF_FIELD_MISSING: {key}")
    return value


def _required_value_at(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise ValueError(f"RFC0028_DOCUMENT_PROOF_FIELD_MISSING: {key}")
    return payload[key]


def _requested_output_formats_from_snapshot(snapshot: dict[str, Any]) -> list[str]:
    value = _required_value_at(snapshot, "requested_output_formats")
    if not isinstance(value, list):
        raise ValueError("RFC0028_DOCUMENT_PROOF_FIELD_INVALID: requested_output_formats")
    return [str(item) for item in value]
