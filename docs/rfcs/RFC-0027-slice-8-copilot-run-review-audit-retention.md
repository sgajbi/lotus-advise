# RFC-0027 Slice 8 - Copilot Run Persistence, Review, Audit, and Retention

Status: IMPLEMENTED - DOMAIN PERSISTENCE AND REVIEW AUDIT FOUNDATION ONLY

## Outcome

Slice 8 makes governed advisory copilot runs durable and reviewable inside `lotus-advise`.
It does not expose public copilot APIs, Gateway routes, Workbench surfaces, data-product promotion,
or canonical front-office proof. Those remain blocked until later RFC-0027 slices implement and
validate them end to end.

Implemented capability:

1. `AdvisoryCopilotRunRecord` stores the bounded evidence packet, request hash, output hash,
   review posture, creator/caller context, tenant, correlation id, lotus-ai workflow run refs,
   workflow-pack lineage, guardrail reasons, retention class, legal hold posture, and expiry.
   Current hardening also stores bounded claim-grounding posture in output sections and lineage so
   unsupported or unverifiable provider claims remain audit-visible but not review-ready.
2. `AdvisoryCopilotReviewRecord` stores approve, reject, supersede, and expire review actions with
   previous/new posture, actor, reason, idempotency, request hash, and correlation id.
3. `persist_advisory_copilot_run` creates replay-safe run records without storing raw prompts,
   provider responses, unsafe raw output, or unrestricted source payloads.
4. `record_advisory_copilot_review` applies idempotent review actions, prevents non-idempotent
   mutation after terminal postures, and preserves audit lineage separately from proposal approval.
5. `InMemoryAdvisoryCopilotRepository` supports fast unit and service testing.
6. `PostgresAdvisoryCopilotRepository` and migration namespace `advisory_copilot` provide the
   production persistence path.
7. proposal-version run history is bounded by repository-level keyset pagination so repeated
   canonical proof runs do not require unbounded run-history reads.
8. Production cutover migration checks now include the `advisory_copilot` namespace.

## Persistence Posture

The record design intentionally separates copilot review state from proposal lifecycle approval
state. A copilot output can be approved for internal use only; it does not approve a proposal,
policy decision, client communication, order, execution handoff, or report publication.

Persisted records include:

1. evidence-packet id and hash,
2. safe request summary and request hash,
3. review-gated output sections, claim-grounding posture, and output hash,
4. guardrail result codes,
5. lotus-ai workflow-pack id, version, workflow run id, model version, prompt-template lineage,
   output-schema lineage, and evaluation-pack ref,
6. caller app, tenant id, requested-by actor, idempotency key, and correlation id,
7. retention class, legal-hold flag, and retention expiry,
8. proposal-version lineage used for indexed, newest-first run-history pagination.

Raw prompt text, raw provider output, provider payloads, unsafe rejected text, and unrestricted
source payloads are rejected before persistence.

## Review Actions

Supported review actions:

1. `APPROVE_FOR_INTERNAL_USE`
2. `REJECT`
3. `SUPERSEDE`
4. `EXPIRE`

Review actions are idempotent when an idempotency key is supplied. Reusing a key with a different
request hash is rejected. Once a run is terminal, a different non-idempotent review action is
rejected so audit history cannot be silently rewritten.

## Retention

Current retention defaults:

1. `ADVISORY_REVIEW_RECORD`: seven years
2. `MODEL_RISK_AUDIT`: seven years
3. `SUPPORTABILITY_DIAGNOSTIC`: ninety days

Legal hold is represented directly on the run record and suspends normal expiry handling for
downstream operational processes.

## Validation Evidence

Targeted commands:

1. `python -m ruff check src/core/advisory_copilot src/infrastructure/advisory_copilot src/api/production_cutover_contract.py scripts/postgres_migrate.py tests/unit/advisory/engine/test_advisory_copilot_persistence.py tests/unit/shared/dependencies/test_production_cutover_contract.py tests/unit/shared/dependencies/test_postgres_migrate_targets.py tests/unit/test_rfc0027_slice8_copilot_persistence_contract.py`
2. `python -m pytest tests/unit/advisory/engine/test_advisory_copilot_persistence.py tests/unit/shared/dependencies/test_production_cutover_contract.py tests/unit/shared/dependencies/test_postgres_migrate_targets.py tests/unit/test_rfc0027_slice8_copilot_persistence_contract.py -q`

Implementation-backed test coverage:

1. run persistence and idempotent replay,
2. changed-request idempotency conflicts,
3. raw prompt/raw AI payload rejection,
4. review action idempotency and audit records,
5. terminal posture protection,
6. proposal-version run lookup and keyset pagination,
7. invalid cursor rejection,
8. production cutover migration namespace coverage.

## Remaining RFC-0027 Boundary

This slice is not a supported product claim by itself. RFC-0027 still requires certified Advise APIs,
Gateway integration, Workbench product surfaces, canonical automation expansion, data-product
promotion, and live front-office proof before advisory copilot can be listed as a supported feature.
