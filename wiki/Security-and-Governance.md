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

The highest-risk documentation and implementation drift usually appears at these seams:

1. advisory versus management ownership
2. local interpretation versus upstream core or risk authority
3. workspace assistance versus decision authority
4. reporting or execution request posture versus actual ownership

## Hard Rules

1. UI and support layers must not generate or rerank proposal alternatives
2. decision-summary posture must remain backend-owned
3. local fallback or degraded behavior must not be presented as canonical upstream truth
4. live runtime evidence matters when advisory behavior changes materially
