# RFC-0001: PostgreSQL-Only Production Mode Cutover

| Metadata | Details |
| --- | --- |
| **Status** | SUPERSEDED |
| **Created** | 2026-02-20 |
| **Superseded By** | RFC-0005 |
| **Doc Location** | `docs/rfcs/RFC-0001-postgres-only-production-mode-cutover.md` |

## 1. Historical Purpose

This RFC introduced the first production-grade persistence guardrail for `lotus-advise`:

- non-dev production profiles had to run with advisory PostgreSQL persistence,
- startup had to fail fast when that requirement was violated,
- CI and deployment flows gained the first production-profile validation path.

That transition was valuable and remains implemented history.

## 2. Why It Is Superseded

`RFC-0001` described an intermediate state:

1. production environments were PostgreSQL-only,
2. local and other transitional runtime modes could still remain available,
3. stricter runtime consolidation would happen later.

That is no longer the right source of truth for the advisory platform direction.

Under the `RFC-0006` vision, `lotus-advise` needs one unified persistence posture, not a split
between transitional and final runtime expectations.

## 3. What Remains True

The following outcomes from this RFC remain valid:

1. production-profile advisory persistence guardrails were a necessary first step,
2. fail-fast startup validation is still the correct control pattern,
3. migration and startup smoke validation remain required for a bank-grade service.

## 4. What Replaces It

`RFC-0005` is now the active source of truth for:

1. PostgreSQL-only advisory runtime persistence,
2. advisory-only database scope,
3. final hard-cutover direction for runtime persistence behavior.

## 5. Disposition

Keep this RFC for historical traceability only.

Do not use it as the primary persistence-direction RFC for future advisory design or delivery.
