from __future__ import annotations

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "Advisory Simulation",
        "description": (
            "Core advisory proposal simulation endpoints used to evaluate a proposed set of "
            "portfolio actions and generate deterministic proposal evidence."
        ),
    },
    {
        "name": "Advisory Proposal Lifecycle",
        "description": (
            "Persisted advisory proposal workflow endpoints covering creation, versioning, "
            "state transitions, approvals, report requests, and execution handoff."
        ),
    },
    {
        "name": "Advisory Proposal Memo",
        "description": (
            "RFC-0024 advisor proposal memo endpoints for persisted memo evidence packs, "
            "projection posture, review events, report-package lineage, memo lineage, and "
            "replay evidence. Gateway, Workbench, and advisor-use report/render/archive "
            "support are available with client-ready memo publication gated."
        ),
    },
    {
        "name": "Advisory Policy Evaluation",
        "description": (
            "RFC-0025 certified Advise API endpoints for policy evaluation records, replay, "
            "review queues, lineage, append-only review/sign-off/report reference events, and "
            "sign-off source packages. Gateway, Workbench, and advisor/compliance report "
            "realization are available with client-ready publication gated."
        ),
    },
    {
        "name": "Advisory Policy Packs",
        "description": (
            "Policy-pack catalog endpoints for governed version lookup, validation, activation, "
            "and supportability evidence used by advisory policy evaluation workflows."
        ),
    },
    {
        "name": "Advisor Cockpit",
        "description": (
            "RFC-0026 Advise-owned cockpit APIs for source-backed action lists, snapshots, "
            "supportability posture, idempotent acknowledgement, active cockpit data-product "
            "posture, and Gateway/Workbench canonical proof. Client-ready publication, "
            "external client communication, CRM system-of-record behavior, OMS order "
            "lifecycle, and completed policy approval authority remain gated."
        ),
    },
    {
        "name": "Advisory Copilot",
        "description": (
            "RFC-0027 Advise-owned governed advisory copilot APIs for bounded evidence "
            "packets, workflow-pack-backed actions, run retrieval, review audit, proposal "
            "version run lookup, Gateway/Workbench consumption, data-product support, "
            "canonical proof, and supportability posture. Client-ready publication remains "
            "gated."
        ),
    },
    {
        "name": "Bank Demo Proof",
        "description": (
            "RFC-0028 source-owned bank-demo proof APIs for scenario contracts, "
            "supported-claim governance, and sanitized proof-pack capture. These APIs do "
            "not approve client-ready publication, external client communication, OMS order "
            "lifecycle, or RFP/security claims."
        ),
    },
    {
        "name": "Advisory Operations & Support",
        "description": (
            "Operational lookup and investigation endpoints for async status, workflow "
            "history, lineage, approval history, idempotency tracing, and execution support."
        ),
    },
    {
        "name": "Advisory Workspace",
        "description": (
            "Workspace-oriented drafting endpoints for iterative advisory preparation before "
            "formal proposal lifecycle ownership begins."
        ),
    },
    {
        "name": "Integration",
        "description": (
            "Platform-facing service capability and contract discovery endpoints used by "
            "other Lotus services and orchestration layers."
        ),
    },
    {
        "name": "Tactical House View",
        "description": (
            "Source-owned advisory cohort endpoints for governed tactical house-view "
            "affected-portfolio evaluation."
        ),
    },
    {
        "name": "Health",
        "description": "Operational liveness and readiness probes for runtime health verification.",
    },
    {
        "name": "Runtime",
        "description": (
            "Support-safe runtime build, image, and release metadata used for operator "
            "diagnostics and release-evidence reconciliation."
        ),
    },
    {
        "name": "Monitoring",
        "description": (
            "Operational telemetry endpoints for metrics scraping and observability tooling."
        ),
    },
]

__all__ = ["OPENAPI_TAGS"]
