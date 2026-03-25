
# RFC-0013: Advisory Proposal Persistence, Workflow Lifecycle, and Audit Model

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Depends On** | RFC-0004, RFC-0005, RFC-0006, RFC-0007 |
| **Strongly Recommended** | RFC-0011, RFC-0012, RFC-0017 |
| **Doc Location** | `docs/rfcs/RFC-0013-proposal-persistence-workflow-lifecycle.md` |
| **Backward Compatibility** | Existing `/advisory/proposals/simulate` and `/advisory/proposals/artifact` unchanged |

---

## 0. Executive Summary

Current reality note (2026-03-25):
- the advisory proposal lifecycle APIs and repository port are implemented,
- the repository abstraction and workflow model are valuable and should remain,
- the RFC must now align to `RFC-0005` and `RFC-0006`, where PostgreSQL-only advisory runtime is
  the target posture and `lotus-advise` is an advisory orchestration service in the Lotus estate,
- in-memory implementation history is no longer the defining architecture direction for this RFC,
- Slice 1 lifecycle provenance foundation is implemented,
- Slice 2 audit-read hardening is implemented,
- Slice 3 concurrency and idempotency hardening is implemented,
- Slice 4 PostgreSQL completion and operational hardening is implemented.

RFC-0013 defines the advisory-owned persistence and workflow lifecycle model for proposals so they
can move through a real private-banking workflow:

- Save and version proposals (immutable proposal artifacts + evidence bundle)
- Track workflow state transitions (draft → review → client consent → execution-ready → executed/expired)
- Enforce **auditability**, **immutability**, **determinism**, and **idempotency**
- Provide APIs for advisor apps to create, retrieve, list, transition, and attach approvals/consents

This RFC is the advisory lifecycle and audit backbone that turns simulation and workspace activity
into a usable, reviewable advisory product.

---

## 1. Motivation / Problem Statement

Simulation results are ephemeral. Advisory workflows require:

- **A durable proposal record** (what was proposed, when, by whom)
- **Evidence bundle** (snapshots + assumptions) to reproduce results
- **Immutable client-facing artifact** and its versions (what the client approved)
- **Workflow state + approvals trail** (risk/compliance/client consent)
- **Idempotent creation** (avoid duplicates from retries)
- **Concurrency control** (avoid inconsistent transitions)

---

## 2. Scope

### 2.1 In Scope
- Advisory-owned lifecycle persistence for:
  - proposal metadata
  - immutable proposal versions
  - append-only workflow transitions
  - approvals/consents records (structured)
  - idempotency records for create operations
  - advisory execution handoff correlation records where later slices require them
- APIs:
  - create proposal (runs simulation and stores artifact)
  - get proposal and versions
  - list proposals with filters
  - transition workflow state
  - attach approvals/consent
  - supportability reads: workflow timeline, approvals list, lineage hashes, idempotency lookup
- Audit logging in repository storage (append-only workflow event log)
- Runtime configurability via environment variables for lifecycle enablement, evidence storage,
  expected-state enforcement, portfolio-context enforcement, and simulation-flag enforcement.

### 2.2 Out of Scope
- Runtime backend policy and PostgreSQL-only cutover rules, which belong to `RFC-0005`
- Integration with external consent tools / e-signature providers
- Integration with OMS execution confirmation (can be a later RFC)
- Jurisdiction-specific data retention rules (config hooks only)
- PII encryption policies beyond basic at-rest encryption (document extension points)
- Canonical portfolio, risk, reporting, or AI ownership that belongs in other Lotus services

---

## 3. Key Principles (Non-Negotiable)

1) **Immutability of proposal versions**
   Once a proposal version is created, its `artifact_json`, `evidence_bundle_json`, and hashes must be immutable.

2) **Append-only workflow history**
   Current status is derived from last event; all transitions are retained.

3) **Idempotent create**
   Same canonical input + same Idempotency-Key must return the same created proposal/version.

4) **Separation of Domain vs Persistence**
   Domain objects do not depend on SQLAlchemy details; repositories are ports/adapters.

5) **Reproducibility**
   Stored evidence must allow re-running and matching the stored hashes (within stated deterministic rules).

---

## 4. Domain Model

### 4.1 Proposal (aggregate root)
- `proposal_id` (stable)
- `portfolio_id`
- `mandate_id` (optional)
- `jurisdiction` (optional but recommended)
- `created_by` (advisor id)
- `created_at`
- `current_state` (derived)
- `current_version` (derived)

### 4.2 ProposalVersion (immutable)
- `proposal_version_id`
- `proposal_id`
- `version_no` (1..N)
- `created_at`
- `request_hash` (sha256 canonical request)
- `artifact_hash` (sha256 canonical artifact, excluding volatile fields as specified)
- `simulation_hash` (optional; hash of core simulation output)
- `artifact_json` (canonical JSON)
- `evidence_bundle_json` (canonical JSON)
- `gate_decision_json` (snapshot of gate at time of version creation)
- `status_at_creation` (READY / PENDING_REVIEW / BLOCKED)

### 4.3 WorkflowEvent (append-only)
- `event_id`
- `proposal_id`
- `event_type`:
  - `CREATED`
  - `SUBMITTED_FOR_RISK_REVIEW`
  - `RISK_APPROVED`
  - `SUBMITTED_FOR_COMPLIANCE_REVIEW`
  - `COMPLIANCE_APPROVED`
  - `CLIENT_CONSENT_RECORDED`
  - `EXECUTION_REQUESTED`
  - `EXECUTED`
  - `REJECTED`
  - `EXPIRED`
  - `CANCELLED`
- `from_state`, `to_state`
- `actor_id`
- `occurred_at`
- `reason` (structured JSON)
- `related_version_no` (optional: which version is being reviewed/approved)

### 4.4 Approval / Consent Records
Store as structured entries linked to workflow events:
- `approval_id`
- `proposal_id`
- `approval_type` (RISK / COMPLIANCE / CLIENT_CONSENT)
- `approved` (bool)
- `actor_id`
- `occurred_at`
- `details_json` (e.g., consent channel, doc refs, comments)
- `related_version_no`

---

## 5. Persistence Design (PostgreSQL)

Architecture note:
- This section defines the advisory-owned target-state database design.
- It should be read together with `RFC-0005`, which owns the PostgreSQL-only runtime posture.
- The repository port remains valid, but target-state persistence is PostgreSQL-backed advisory
  storage rather than a mixed-backend model.

### 5.1 Tables (minimal)
1) `proposals`
2) `proposal_versions`
3) `proposal_workflow_events`
4) `proposal_approvals`
5) `idempotency_keys` (optional but recommended)

### 5.2 Suggested schema (high-level)
#### proposals
- `proposal_id` PK (text/uuid)
- `portfolio_id` text
- `mandate_id` text null
- `jurisdiction` text null
- `created_by` text
- `created_at` timestamptz
- `last_event_at` timestamptz
- `current_state` text (denormalized for speed; derived and updated transactionally)
- `current_version_no` int

Indexes:
- `(portfolio_id, created_at desc)`
- `(created_by, created_at desc)`
- `(current_state, last_event_at desc)`

#### proposal_versions
- `proposal_version_id` PK
- `proposal_id` FK
- `version_no` int
- `created_at` timestamptz
- `request_hash` text
- `artifact_hash` text
- `status_at_creation` text
- `artifact_json` jsonb
- `evidence_bundle_json` jsonb
- `gate_decision_json` jsonb

Constraints:
- unique `(proposal_id, version_no)`
- optional unique `(proposal_id, request_hash)` (prevents duplicate versions if same request repeated)

#### proposal_workflow_events
- `event_id` PK
- `proposal_id` FK
- `event_type` text
- `from_state` text
- `to_state` text
- `actor_id` text
- `occurred_at` timestamptz
- `reason_json` jsonb
- `related_version_no` int null

Index:
- `(proposal_id, occurred_at asc)`

#### proposal_approvals
- `approval_id` PK
- `proposal_id` FK
- `approval_type` text
- `approved` bool
- `actor_id` text
- `occurred_at` timestamptz
- `details_json` jsonb
- `related_version_no` int null

#### idempotency_keys
- `idempotency_key` text PK
- `request_hash` text
- `proposal_id` text
- `proposal_version_no` int
- `created_at` timestamptz
- `expires_at` timestamptz

Policy:
- TTL cleanup job later (or periodic vacuum strategy)

---

## 6. API Design

All endpoints follow the `/advisory/...` route family.

### 6.1 Create proposal (simulation + persistence)
`POST /advisory/proposals`

Headers:
- `Idempotency-Key` required
- `X-Correlation-Id` optional

Body:
- same as `POST /advisory/proposals/simulate` request
- plus optional metadata:
  - `title`, `advisor_notes`, `jurisdiction`

Behavior:
1) Validate Idempotency-Key and compute canonical `request_hash`
2) Check `idempotency_keys`:
   - if key exists and request_hash matches → return same proposal/version
   - if key exists and request_hash differs → 409 Problem Details
3) Run simulation + artifact generation (RFC-0011)
4) Persist:
   - proposal row (if new)
   - proposal_version row (version_no=1)
   - workflow event `CREATED`
   - idempotency_keys row
5) Return:
   - proposal_id, version_no, current_state, artifact summary, gate_decision

### 6.2 Get proposal (metadata + current)
`GET /advisory/proposals/{proposal_id}`

Returns:
- proposal metadata
- current state
- current version summary
- last gate decision

### 6.3 List proposals
`GET /advisory/proposals?portfolio_id=&state=&created_by=&from=&to=&limit=&cursor=`

Returns:
- paginated list of proposal summaries

### 6.4 Get proposal version
`GET /advisory/proposals/{proposal_id}/versions/{version_no}`

Returns:
- full artifact + evidence bundle (or allow `?include_evidence=false`)

### 6.5 Create new version (re-simulate with changes)
`POST /advisory/proposals/{proposal_id}/versions`

Body:
- same as simulate request
- must reference same portfolio_id/mandate context unless explicitly allowed

Behavior:
- run simulation + build artifact
- create new `proposal_versions` row with version_no = current+1
- add workflow event `NEW_VERSION_CREATED`

### 6.6 Transition workflow state
`POST /advisory/proposals/{proposal_id}/transitions`

Body:
```json
{
  "event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW",
  "actor_id": "user_123",
  "related_version_no": 2,
  "reason": { "comment": "New issuer breach, needs review" }
}
````

Validation:

* enforce valid state machine transitions (see Section 7)
* optimistic concurrency: require `if_match_version_no` or `expected_state`

Return:

* updated current_state
* latest workflow event

### 6.7 Record approval / consent

`POST /advisory/proposals/{proposal_id}/approvals`

Body:

```json
{
  "approval_type": "CLIENT_CONSENT",
  "approved": true,
  "actor_id": "client_abc",
  "related_version_no": 2,
  "details": { "channel": "IN_PERSON", "captured_by": "advisor_1" }
}
```

Behavior:

* write approval record
* write workflow event `CLIENT_CONSENT_RECORDED`
* update current_state accordingly

### 6.8 Supportability and investigation reads

Read-only operational endpoints for support teams:
- `GET /advisory/proposals/{proposal_id}/workflow-events`
- `GET /advisory/proposals/{proposal_id}/approvals`
- `GET /advisory/proposals/{proposal_id}/lineage`
- `GET /advisory/proposals/idempotency/{idempotency_key}`

These are intended for audit, incident response, and reproducibility investigation.

---

## 7. Workflow State Machine (Institutional MVP)

### 7.1 States

* `DRAFT` (created but not submitted)
* `RISK_REVIEW` (submitted)
* `COMPLIANCE_REVIEW` (submitted)
* `AWAITING_CLIENT_CONSENT`
* `EXECUTION_READY`
* `EXECUTED`
* `REJECTED`
* `CANCELLED`
* `EXPIRED`

### 7.2 Transition rules (core)

* `DRAFT` → `RISK_REVIEW` or `COMPLIANCE_REVIEW` (based on GateDecision or manual override)
* `RISK_REVIEW` → `AWAITING_CLIENT_CONSENT` (approved) OR `REJECTED`
* `COMPLIANCE_REVIEW` → `AWAITING_CLIENT_CONSENT` (approved) OR `REJECTED`
* `AWAITING_CLIENT_CONSENT` → `EXECUTION_READY` (consent recorded)
* `EXECUTION_READY` → `EXECUTED` (execution confirmed) OR `EXPIRED`
* Any non-terminal → `CANCELLED`

### 7.3 GateDecision integration (recommended)

On version creation, evaluate GateDecision:

* if gate = BLOCKED → proposal remains DRAFT but flagged (cannot proceed)
* if gate = COMPLIANCE_REVIEW_REQUIRED → suggest transition to COMPLIANCE_REVIEW
* if gate = RISK_REVIEW_REQUIRED → suggest transition to RISK_REVIEW
* if gate = CLIENT_CONSENT_REQUIRED → suggest AWAITING_CLIENT_CONSENT

This is advisory; transitions are explicit API calls.

---

## 8. Concurrency & Idempotency

### 8.1 Idempotency

* Create endpoints must be idempotent via `Idempotency-Key`
* The key must map to `(request_hash, proposal_id, version_no)`
* Conflicts return 409 Problem Details

### 8.2 Optimistic locking

For transitions:

* require client to send:

  * `expected_state` OR `expected_last_event_at`
    If mismatch:
* return 409 Problem Details (`STATE_CONFLICT`)

### 8.3 Transaction boundaries

Persist updates in a single DB transaction:

* insert workflow event
* update proposals.current_state and last_event_at
* insert approval if needed

---

## 9. Audit & Security Considerations (MVP)

### 9.1 Audit

* `proposal_workflow_events` is append-only (no updates/deletes)
* store actor_id and reason_json
* include correlation_id in reason_json or as a column (recommended)

### 9.2 Data minimization

* Evidence bundle may include market snapshots; ensure you are comfortable storing it.
* Optionally support `include_evidence=false` storage mode (store references only) — can be added later.
  For MVP: store full evidence bundle to guarantee reproducibility.

### 9.3 Access control (placeholder)

Define interface hooks:

* `AuthorizationContext` (advisor entitlements, portfolio access)
  Implementation can be stubbed for MVP if not needed.

---

## 10. Implementation Plan (Slices)

### Slice 1: Lifecycle Provenance Foundation

Outcome:
- persisted proposals carry first-class origin metadata that distinguishes direct proposal creation
  from workspace handoff lineage,
- workspace-to-lifecycle handoff becomes auditable from proposal reads and list views without
  reconstructing provenance indirectly from workflow event payloads.

Implementation shape:
1. add advisory lifecycle provenance fields to the proposal aggregate and API read models,
2. persist workspace-origin linkage in advisory-owned lifecycle storage,
3. wire workspace handoff to create proposals with explicit lifecycle provenance,
4. keep direct create flows explicitly marked as direct advisory lifecycle creation.

Acceptance gate:
1. proposal create responses, get responses, and list responses expose lifecycle origin metadata,
2. workspace handoff creates proposals that persist source workspace lineage,
3. PostgreSQL migration coverage and repository tests validate the persisted lifecycle provenance.

### Slice 2: Lifecycle Contract and Audit Read Hardening

Outcome:
- lifecycle supportability reads become stronger and more explicit for advisory operators,
- proposal lineage reads are consistently shaped for incident review and replay analysis.

Implementation shape:
1. tighten proposal detail, version lineage, approval, and workflow timeline contracts,
2. ensure supportability reads remain advisory-owned and bank-grade,
3. strengthen OpenAPI documentation and examples for lifecycle investigation flows.

Acceptance gate:
1. lifecycle support APIs remain fully documented and Lotus-branded,
2. lineage, approval, and workflow reads are deterministic and replay-safe,
3. meaningful tests cover audit read invariants rather than superficial field presence.

### Slice 3: Concurrency, State-Machine, and Idempotency Hardening

Outcome:
- lifecycle write paths behave predictably under retries, stale clients, and conflicting transitions.

Implementation shape:
1. tighten optimistic state checks and transition validation,
2. harden idempotent create and approval replay behavior,
3. keep failure semantics explicit and stable for gateway/workbench use.

Acceptance gate:
1. conflicting transition and idempotency scenarios return stable failures,
2. workflow history remains append-only and proposal versions remain immutable,
3. tests cover conflict and replay edge cases with real domain meaning.

### Slice 4: PostgreSQL Completion and Operational Hardening

Outcome:
- lifecycle persistence is production-ready under the PostgreSQL-only runtime posture from
  `RFC-0005`.

Implementation shape:
1. complete PostgreSQL-backed lifecycle validation and migration coverage,
2. ensure supportability, startup, and operational guardrails reflect advisory-only persistence,
3. keep observability and diagnostics aligned with lifecycle operations.

Acceptance gate:
1. lifecycle persistence behaves correctly under PostgreSQL integration tests,
2. runtime supportability reads remain aligned to `RFC-0005`,
3. the lifecycle persistence model remains advisory-only and consistent with `RFC-0006`.

---

## 11. Testing Plan

### 11.1 Unit tests

* state machine transitions valid/invalid
* idempotency:

  * same key + same request_hash returns same proposal/version
  * same key + different request_hash → 409
* version immutability: attempt to update artifact_json is rejected at repository level

### 11.2 Integration tests (Postgres)

- Required for target-state completion.
- Current integration coverage uses FastAPI test client and live API calls against `uvicorn` and Docker.
- Final closure for this RFC requires PostgreSQL-backed lifecycle validation under the runtime rules
  from `RFC-0005`.

### 11.3 Golden tests

* Golden tests remain for simulation outputs.
* Persistence tests should assert stable schema and key invariants, not full JSON equality.

---

## 12. Acceptance Criteria (DoD)

* Proposals can be created idempotently and stored through the advisory persistence model.
* Proposal versions are immutable and include artifact + evidence bundle + hashes.
* Workflow events are append-only; current state is consistent and derived from events.
* Approvals/consents are recorded and produce workflow transitions.
* Concurrency conflicts return 409 Problem Details.
* API + engine tests and live demo-pack validation run reliably in CI/dev.
* PostgreSQL-backed lifecycle persistence is aligned to `RFC-0005`.
* The lifecycle persistence model remains advisory-only and consistent with `RFC-0006`.

### 12.1 MVP Runtime Config Delivered
Configuration is implementation-faithful and currently delivered via environment variables:
- `PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED` (default `true`)
- `PROPOSAL_STORE_EVIDENCE_BUNDLE` (default `true`)
- `PROPOSAL_REQUIRE_EXPECTED_STATE` (default `true`)
- `PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION` (default `false`)
- `PROPOSAL_REQUIRE_SIMULATION_FLAG` (default `true`)
- `PROPOSAL_SUPPORT_APIS_ENABLED` (default `true`)

---

## 13. Follow-ups

* Integrate with execution systems (OMS) for `EXECUTED` confirmation
* Retention & archival policy per jurisdiction
* PII encryption and key management enhancements
* External consent providers and document signing


