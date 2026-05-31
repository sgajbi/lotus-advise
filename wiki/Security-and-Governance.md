# Security and Governance

## Governing Posture

`lotus-advise` is governed by Lotus platform CI, OpenAPI, vocabulary, and context standards.

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
   control characters, or sensitive token/secret/prompt/raw-payload path material
3. HTTP 422 request-validation errors must not echo rejected sensitive input values
4. summaries redact secrets, tokens, prompts, raw payloads, trace IDs, and correlation IDs
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
copilot structured-payload persistence reject raw prompt, provider-response, trace/correlation,
run-ledger, and raw-payload wording at the lowest boundary. This keeps UI, API, persistence, and
replay paths aligned with the same business-copy redaction rule.
