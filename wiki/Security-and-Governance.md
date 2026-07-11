# Security and Governance

## Governing Posture

`lotus-advise` is governed by Lotus platform CI, OpenAPI, vocabulary, and context standards.

## Current Scope

This page records security, release-governance, claim-control, and evidence hygiene rules that are
currently enforced or required before `lotus-advise` capabilities are promoted.

## Reader Map

| Reader | Start here |
| --- | --- |
| Agent or developer | Hard Rules, Security Baseline Governance, License/IP Evidence Governance |
| Release operator | Release Metadata Governance |
| Demo or RFP reviewer | RFC-0028 Proof Artifact Governance |

Locally relevant governance includes:

- RFC-0066 advisory and manage split
- RFC-0067 API vocabulary and OpenAPI governance
- RFC-0072 multi-lane CI governance
- RFC-0073 ecosystem context governance
- RFC-0082 upstream contract-family classification

## Sensitive Boundaries

The highest-risk documentation and implementation drift usually appears at these integration boundaries:

1. advisory versus management ownership
2. local interpretation versus upstream core or risk authority
3. workspace assistance versus decision authority
4. reporting or execution request posture versus actual ownership

## Hard Rules

1. UI and support layers must not generate or rerank proposal alternatives
2. decision-summary posture must remain backend-owned
3. local fallback or degraded behavior must not be presented as canonical upstream truth
4. live runtime evidence matters when advisory behavior changes materially
5. outbound report and AI calls must not substitute synthetic tenant or actor defaults; trusted
   identity must be bounded and present before downstream submission
6. policy-control write routes must authorize an Advise `PolicyControlPrincipal` before state
   mutation; body actor fields are compatibility echoes and cannot satisfy role, capability,
   maker-checker, tenant, legal-entity, proposal, or portfolio scope on their own
7. advisory copilot review routes must authorize a trusted reviewer principal before state
   mutation; body `actor_id` is only a compatibility echo and cannot satisfy role, capability,
   maker-checker, tenant, proposal, portfolio, or idempotency replay authority on its own
8. outbound report calls must preserve source-derived as-of date, reporting currency, and
   jurisdiction instead of silently applying market or current-date defaults
9. release images must be built and pushed by CI only, tagged by Git SHA, labelled with support-safe
   OCI metadata, accompanied by digest-bearing release evidence, SBOM, scan, signature, and
   provenance attestation, and deployed by digest
10. Bandit findings must pass `make bandit-severity-regression-gate`: high findings are blocked,
   current medium/low entries must match the governed baseline, and new, stale, expired, or
   worsened medium/low entries fail CI
11. dependency license/IP posture must pass `make license-ip-gate`: runtime and development graphs,
    including transitive packages, must match the committed inventory and any review-required terms
    must have owner-approved expiring exceptions
12. dependency lock posture must pass `make dependency-lock-gate`: `uv.lock` must match the
    requirements install strategy, requirement-file hashes, and dependency inventory hash

## Policy-Control Principal Governance

Policy-pack validation/activation and policy-evaluation finalization, review-event, sign-off,
report-package, and AI-evidence writes derive authority from trusted policy-control headers:
`X-Actor-Id`, `X-Role`, `X-Tenant-Id`, `X-Legal-Entity-Code`, `X-Correlation-Id`, service identity,
route capability, and evaluation-scoped proposal/portfolio authorization. Supported roles are
domain-specific: `POLICY_STEWARD` validates packs and can record review events,
`POLICY_CHECKER` activates packs and records sign-off/report-package commands, `ADVISOR` finalizes
evaluations, and `COMPLIANCE_REVIEWER` records review and AI-evidence requests where allowed.

Request-body actor fields remain for compatibility with existing consumers, but they are not an
identity source. Advise rejects body/header actor mismatches, missing/expired principals, wrong
roles, missing capabilities, and cross-scope proposal, portfolio, tenant, or legal-entity access
before application state transitions. Successful audit events retain trusted subject, role, tenant,
legal entity, correlation id, service identity, and capability metadata.

## Advisory Copilot Review Principal Governance

Advisory copilot review writes derive authority from trusted reviewer headers before application
state transitions. Supported reviewer roles are `ADVISORY_SUPERVISOR`, `COMPLIANCE_REVIEWER`, and
`POLICY_CHECKER`; the required capability is `advisory.copilot.review`. The authorized portfolio
must match the persisted run portfolio, the authorized proposal must match when the run is
proposal-scoped, and the trusted tenant must match the run tenant.

Request-body `actor_id` remains a compatibility echo for existing consumers, but it is not an
identity source. Advise rejects body/header actor mismatches, missing principals, wrong roles,
missing capabilities, cross-scope access, tenant mismatch, and self-review before review state or
idempotency state can mutate. Successful review audit records retain trusted principal metadata
and maker-checker authorization evidence alongside the review reason.

## Release Metadata Governance

`GET /version` exposes support-safe build metadata only: service name/version, Git commit, branch,
repository URL, build timestamp, CI run ID, and image digest when injected by release/deployment.
It must not expose runtime configuration, DSNs, tokens, tenant identifiers, actor identifiers, raw
headers, or downstream base URLs.

The release-image evidence path is intentionally split:

1. PR/local builds validate Dockerfile build args, OCI labels, and label content without pushing.
2. Main Releasability pushes the Git-SHA image, records the registry digest, validates dependency
   lock evidence, generates SBOM, license/IP inventory, and vulnerability-scan artifacts, signs the
   digest, creates provenance attestation, and uploads the release manifest.
3. Deployment must reference the digest from the retained manifest and promote the same immutable
   image across environments.

## Security Baseline Governance

`quality/bandit_security_baseline.v1.json` is the governed Bandit medium/low baseline. It is not a
security certification claim. Each accepted entry carries a stable fingerprint, owner, rationale,
expiry, linked remediation, and compensating control. The current baseline records `0` high, `26`
medium, and `0` low findings, with remediation tracked in issue #435.

Use `make bandit-severity-regression-gate` for the direct gate. `make security-audit` runs the same
gate after dependency health. `make bandit-high-severity-gate` remains only as a compatibility alias.

## License/IP Evidence Governance

`docs/standards/license-ip-policy.v1.json` classifies allowed, review-required, and prohibited
dependency license terms. `docs/standards/license-ip-inventory.v1.json` records the current runtime
and development dependency graphs, including transitive packages, policy classification, and
approved exceptions. `NOTICE.md` records the third-party notice posture.

Use `make license-ip-inventory` to regenerate the committed inventory after dependency changes, and
`make license-ip-gate` to verify release posture. New unclassified, prohibited, missing-metadata, or
expired-exception findings fail CI.

## Dependency Lock Governance

`uv.lock` is the generated lock mirror for the current requirements-based install strategy. It
records requirement-file hashes, the license/IP inventory hash, direct pins, transitive package
versions, package groups, extras, and requirement-line hashes.

Use `make dependency-lock` after changing `requirements.txt`, `requirements-prod.txt`,
`requirements-dev.txt`, or generated dependency inventory. `make dependency-lock-gate` fails on
missing packages, version drift, stale manifest hashes, or Python-runtime incompatibility.

## RFC-0028 Proof Artifact Governance

RFC-0028 bank-demo proof is governed as implementation evidence, not marketing copy. The supported
claim register controls which product, security, RFP, demo, and proof-guide statements can be used
by business-facing material. Claims must stay in one of the documented postures: implementation
backed, blocked, planned, local-only, or secret material. Commercial wording must map back to the
supported-claim register and proof-pack evidence before it is reused outside engineering.

Runtime proof artifacts are sanitized before they become commit-safe or demo-supporting evidence:

1. runtime base URLs must not include credentials, query strings, or fragments
2. proof artifact references must stay as local relative paths and must not include URL schemes,
   authorities, credentials, query strings, fragments, absolute paths, parent-directory traversal,
   control characters, or sensitive credential, AI-input, or runtime-payload path material
3. HTTP 422 request-validation errors must not echo rejected sensitive input values
4. summaries redact credential, AI-input, runtime-payload, trace, and correlation material
5. endpoint posture records bounded integer `latency_ms` values only
6. local-only runtime outputs under `output/` must not be treated as wiki or README source truth
7. committed proof assets must use commit-safe or customer-consumable access classes,
   `COMMIT_SOURCE` retention, and a canonical content hash

The proof boundary remains deliberately conservative. RFC-0028 does not certify bank-specific
attestations, legal/regulatory advice, completed policy sign-off/approval, external client
communication, client-ready publication, or OMS/order/fill/settlement. Any future promotion of
those claims requires implementation evidence, tests at the owning layer, and updated API/wiki/RFC
truth in the same slice.

## RFC-0027 Copilot Evidence Governance

Governed advisory copilot output is internal advisor/reviewer evidence, not client-ready advice or
model authority. Evidence-section models, unsupported-evidence messages, action projections, and
copilot structured-payload persistence reject unredacted AI input, provider-output,
trace/correlation, run-ledger, and unrestricted runtime-payload wording at the lowest boundary.
This keeps UI, API, persistence, and replay paths aligned with the same business-copy redaction
rule.
