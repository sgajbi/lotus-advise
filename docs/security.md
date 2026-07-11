# Lotus Advise Security

This document records the current security hardening baseline for Lotus Advise.

## Current Baseline

- Dependency health and security audit are repo-native gates.
- API error-boundary hardening reduces the risk of leaking sensitive lower-layer details.
- Advisory-copilot structured payload tests reject raw AI payload and sensitive unredacted inputs.
- Downstream `lotus-report` and `lotus-ai` requests require bounded trusted actor and tenant
  identity; missing or malformed values fail closed before HTTP submission.
- Downstream report requests require source-derived as-of date, reporting currency, and
  jurisdiction/booking-center metadata; missing or conflicting values fail closed before HTTP
  submission.
- Bandit security findings are enforced through `make bandit-severity-regression-gate`, which is
  called by `make security-audit` and has a compatibility alias at
  `make bandit-high-severity-gate`.
- Current Bandit inventory is governed by `quality/bandit_security_baseline.v1.json`: `0` high,
  `26` medium, and `0` low severity findings. High findings are never baselined; current medium/low
  entries require owner, rationale, expiry, linked remediation, and compensating controls.

## Current Gaps

- The current Bandit medium baseline remains non-certifying security debt. Issue #435 tracks
  reducing or retiring the constant-owned SQL-template entries before their `2026-12-31` expiry.
- Full authentication, authorization, CORS, header, and API abuse-protection inventories need
  separate implementation-backed review slices.
- Broader route-level authenticated caller-context resolution remains a separate authorization
  slice; this baseline covers downstream identity propagation for report and AI adapters.
- Security findings must remain evidence-based and must not imply legal, regulatory, or bank
  certification signoff.

## Next Steps

- Reduce the current medium Bandit baseline by replacing constant-owned SQL template false
  positives with Bandit-clean helpers where practical.
