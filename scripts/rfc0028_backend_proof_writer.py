from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.bank_demo_proof import BackendProofCaptureBundle


def write_backend_proof_capture_bundle(
    bundle: BackendProofCaptureBundle,
    *,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "metadata": output_dir / "metadata.json",
        "scenario_contract": output_dir / "scenario-contract.json",
        "supported_claim_register": output_dir / "supported-claim-register.json",
        "proof_pack": output_dir / "proof-pack.json",
        "document_proof_summary": output_dir / "document-proof-summary.json",
        "journey_integration_proof_summary": (
            output_dir / "journey-integration-proof-summary.json"
        ),
        "commercial_material_pack": output_dir / "commercial-material-pack.json",
        "runtime_posture": output_dir / "runtime-posture.json",
        "sanitized_runtime_summary": output_dir / "sanitized-runtime-summary.json",
        "material_field_review": output_dir / "material-field-review.json",
        "summary": output_dir / "capture-summary.md",
        "manifest": output_dir / "manifest.json",
    }
    _write_json(paths["metadata"], bundle.metadata.model_dump(mode="json"))
    _write_json(paths["scenario_contract"], bundle.scenario_contract.model_dump(mode="json"))
    _write_json(
        paths["supported_claim_register"],
        bundle.supported_claim_register.model_dump(mode="json"),
    )
    _write_json(paths["proof_pack"], bundle.proof_pack.model_dump(mode="json"))
    _write_json(
        paths["document_proof_summary"],
        bundle.document_proof_summary.model_dump(mode="json"),
    )
    _write_json(
        paths["journey_integration_proof_summary"],
        bundle.journey_integration_proof_summary.model_dump(mode="json"),
    )
    _write_json(
        paths["commercial_material_pack"],
        bundle.commercial_material_pack.model_dump(mode="json"),
    )
    _write_json(paths["runtime_posture"], bundle.runtime_posture.model_dump(mode="json"))
    _write_json(paths["sanitized_runtime_summary"], bundle.sanitized_runtime_summary)
    _write_json(
        paths["material_field_review"],
        [review.model_dump(mode="json") for review in bundle.material_field_reviews],
    )
    paths["summary"].write_text(_render_capture_summary(bundle), encoding="utf-8")
    _write_json(
        paths["manifest"],
        {
            "artifact_family": "rfc0028.backend-proof-capture.v1",
            "proof_pack_id": bundle.proof_pack.proof_pack_id,
            "scenario_id": bundle.proof_pack.scenario_id,
            "primary_portfolio_id": bundle.proof_pack.primary_portfolio_id,
            "proof_marker": bundle.proof_pack.proof_marker,
            "client_ready_posture": bundle.proof_pack.client_ready_posture,
            "artifacts": _manifest_artifact_refs(paths, output_dir),
        },
    )
    return paths


def _manifest_artifact_refs(paths: dict[str, Path], output_dir: Path) -> dict[str, str]:
    artifact_refs: dict[str, str] = {}
    for key, path in paths.items():
        artifact_refs[key] = path.relative_to(output_dir).as_posix()
    return artifact_refs


def _render_capture_summary(bundle: BackendProofCaptureBundle) -> str:
    blocked_boundaries = "\n".join(
        f"- {boundary}" for boundary in bundle.proof_pack.unsupported_boundaries
    )
    material_reviews = "\n".join(
        f"- `{review.source_path}`: `{review.observed_value}` ({review.review_posture})"
        for review in bundle.material_field_reviews
    )
    runtime_rows = []
    for endpoint in bundle.runtime_posture.endpoints:
        latency = f"{endpoint.latency_ms} ms" if endpoint.latency_ms is not None else "not measured"
        runtime_rows.append(
            f"- `{endpoint.endpoint}`: `{endpoint.posture}` / `{endpoint.http_status}`"
            f" / `{latency}`"
        )
    runtime = "\n".join(runtime_rows)
    document_rows = "\n".join(
        "- "
        f"`{document.document_family}`: report `{document.report_package_status}`, "
        f"render `{document.render_ref_status}`, archive `{document.archive_ref_status}`, "
        f"retention `{document.archive_retention_posture}`, "
        f"client-ready `{document.client_ready_document_status}`"
        for document in bundle.document_proof_summary.documents
    )
    ai_rows = "\n".join(
        "- "
        f"`{row.evidence_family}`: `{row.proof_posture}` / AI `{row.ai_status}`, "
        f"review required `{row.human_review_required}`, "
        f"authoritative `{row.authoritative_for_advice}`, guardrail `{row.guardrail_status}`"
        for row in bundle.journey_integration_proof_summary.ai_model_risk_controls
    )
    policy = bundle.journey_integration_proof_summary.policy_evidence
    cockpit = bundle.journey_integration_proof_summary.cockpit_evidence
    commercial_materials = "\n".join(
        "- "
        f"`{material.material_id}`: `{material.material_type}` / "
        f"claims `{', '.join(material.mapped_claim_ids)}`"
        for material in bundle.commercial_material_pack.materials
    )
    return (
        "# RFC-0028 Backend Proof Capture\n\n"
        f"- proof pack: `{bundle.proof_pack.proof_pack_id}`\n"
        f"- scenario: `{bundle.proof_pack.scenario_id}`\n"
        f"- portfolio: `{bundle.proof_pack.primary_portfolio_id}`\n"
        f"- proof marker: `{bundle.proof_pack.proof_marker}`\n"
        f"- client-ready posture: `{bundle.proof_pack.client_ready_posture}`\n"
        f"- correlation id: `{bundle.proof_pack.correlation_id}`\n\n"
        "## Runtime Posture\n\n"
        f"{runtime}\n\n"
        "## Document Proof\n\n"
        f"{document_rows}\n\n"
        "## AI, Policy, And Cockpit Integration Proof\n\n"
        f"{ai_rows}\n\n"
        f"- policy: `{policy.policy_pack_id}` / `{policy.policy_version}` / "
        f"`{policy.evaluation_status}` / client-ready `{policy.client_ready_publication}`\n"
        f"- cockpit panel: `{cockpit.required_workbench_panel}` / "
        f"`{cockpit.proof_posture}` / client-ready `{cockpit.client_ready_publication}`\n\n"
        "## Commercial, RFP, Security, Architecture, ROI, And Demo Material\n\n"
        f"{commercial_materials}\n\n"
        f"- publication posture: `{bundle.commercial_material_pack.publication_posture}`\n"
        f"- blocked claims: `{', '.join(bundle.commercial_material_pack.blocked_claims)}`\n\n"
        "## Material Field Review\n\n"
        f"{material_reviews}\n\n"
        "## Unsupported Boundaries\n\n"
        f"{blocked_boundaries}\n"
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
